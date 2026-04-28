from __future__ import annotations
import json
import os
import requests
from llm.base import LLMBackend
from fafsa.kb import SAITrace, fmt_trace

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

_FIELDS_HINT = (
    "parent_agi, family_size, num_parents, older_parent_age, "
    "student_agi, parent_earned_income_p1, parent_earned_income_p2, "
    "parent_cash_savings, parent_investment_net_worth, parent_business_farm_net_worth, "
    "student_cash_savings, student_investment_net_worth"
)

_EXTRACT_PROMPT = """\
Extract FAFSA family financial data from the query below.
Return JSON only — no explanation, no markdown.
Include only fields you can determine from the query.
All monetary values are integers in dollars.

Available fields: {fields}

Query: {query}

JSON:"""

_NARRATE_PROMPT = """\
Explain this FAFSA SAI calculation in plain English for a student and their family.
Be conversational and clear. 3-5 sentences. Do not repeat the raw numbers — interpret them.

Proof trace:
{trace}

Explanation:"""


class OllamaBackend(LLMBackend):
    def __init__(self, model: str = "qwen3.5:4b"):
        self.model = model

    def extract_facts(self, query: str) -> dict:
        prompt = _EXTRACT_PROMPT.format(fields=_FIELDS_HINT, query=query)
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": self.model, "prompt": prompt, "format": "json", "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        return json.loads(resp.json()["response"])

    def narrate_proof(self, trace: SAITrace) -> str:
        prompt = _NARRATE_PROMPT.format(trace=fmt_trace(trace, verbose=True))
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()
