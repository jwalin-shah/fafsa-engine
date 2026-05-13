from __future__ import annotations
import json
from llm.base import LLMBackend
from fafsa.kb import SAITrace, fmt_trace

_FIELDS_HINT = (
    "parent_agi, family_size, num_parents, older_parent_age, "
    "student_agi, parent_earned_income_p1, parent_earned_income_p2, "
    "parent_cash_savings, parent_investment_net_worth, parent_business_farm_net_worth, "
    "student_cash_savings, student_investment_net_worth"
)


def _create_openai_client():
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install fafsa-engine[openai] to use OpenAIBackend.") from exc
    return OpenAI()


class OpenAIBackend(LLMBackend):
    def __init__(self, model: str = "gpt-4o-mini", client=None):
        self.client = client or _create_openai_client()
        self.model = model

    def extract_facts(self, query: str) -> dict:
        system_prompt = (
            "You are a FAFSA financial expert. Your goal is to extract family facts for an SAI calculation.\n"
            "For every field you extract, you MUST provide:\n"
            "1. 'value': The numeric value (integer).\n"
            "2. 'citation': The exact quote from the user's query.\n"
            "3. 'reasoning': Why this value maps to this field.\n\n"
            "If a value is not explicitly mentioned, do not include it. "
            "Handle abbreviations like '80k' as 80000.\n"
            f"Available fields: {_FIELDS_HINT}\n\n"
            "Return a JSON object where each key is a field name and the value is an object with {value, citation, reasoning}."
        )
        resp = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
        )
        raw_extraction = json.loads(resp.choices[0].message.content)
        # Return the full detailed extraction for the UI/engine
        print("\n[Extraction Reasoning]")
        for field, detail in raw_extraction.items():
            if isinstance(detail, dict) and "value" in detail:
                print(f"  - {field:30}: {detail['value']} (based on \"{detail.get('citation','')}\")")
                print(f"    Reason: {detail.get('reasoning','')}")
        return raw_extraction

    def narrate_proof(self, trace: SAITrace) -> str:
        formatted = fmt_trace(trace, verbose=True)
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": (
                f"Explain this FAFSA SAI calculation in plain English for a student and their family.\n"
                f"Be conversational and clear. 3-5 sentences. Do not repeat the raw numbers — interpret them.\n\n"
                f"Proof trace:\n{formatted}"
            )}],
        )
        return resp.choices[0].message.content.strip()
