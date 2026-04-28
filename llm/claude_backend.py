from __future__ import annotations
import json
import anthropic
from llm.base import LLMBackend
from fafsa.kb import SAITrace, fmt_trace

_FIELDS_HINT = (
    "parent_agi, family_size, num_parents, older_parent_age, "
    "student_agi, parent_earned_income_p1, parent_earned_income_p2, "
    "parent_cash_savings, parent_investment_net_worth, parent_business_farm_net_worth, "
    "student_cash_savings, student_investment_net_worth"
)


class ClaudeBackend(LLMBackend):
    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        self.client = anthropic.Anthropic()
        self.model = model

    def extract_facts(self, query: str) -> dict:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": (
                f"Extract FAFSA family financial data from the query below.\n"
                f"Return JSON only. Include only fields you can determine. "
                f"All monetary values are integers in dollars.\n\n"
                f"Available fields: {_FIELDS_HINT}\n\nQuery: {query}\n\nJSON:"
            )}],
        )
        return json.loads(msg.content[0].text)

    def narrate_proof(self, trace: SAITrace) -> str:
        formatted = fmt_trace(trace, verbose=True)
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": (
                f"Explain this FAFSA SAI calculation in plain English for a student and their family.\n"
                f"Be conversational and clear. 3-5 sentences. Do not repeat the raw numbers — interpret them.\n\n"
                f"Proof trace:\n{formatted}\n\nExplanation:"
            )}],
        )
        return msg.content[0].text.strip()
