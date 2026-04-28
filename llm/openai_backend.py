from __future__ import annotations
import json
from openai import OpenAI
from llm.base import LLMBackend
from fafsa.kb import SAITrace, fmt_trace

_FIELDS_HINT = (
    "parent_agi, family_size, num_parents, older_parent_age, "
    "student_agi, parent_earned_income_p1, parent_earned_income_p2, "
    "parent_cash_savings, parent_investment_net_worth, parent_business_farm_net_worth, "
    "student_cash_savings, student_investment_net_worth"
)


class OpenAIBackend(LLMBackend):
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI()
        self.model = model

    def extract_facts(self, query: str) -> dict:
        resp = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": (
                f"Extract FAFSA family financial data from the query below.\n"
                f"Return JSON only. Include only fields you can determine. "
                f"All monetary values are integers in dollars.\n\n"
                f"Available fields: {_FIELDS_HINT}\n\nQuery: {query}"
            )}],
        )
        return json.loads(resp.choices[0].message.content)

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
