"""MLX backend — runs an instruct model directly on Apple Silicon via mlx_lm.

No HTTP server, no separate daemon — uses the unified-memory GPU directly.
Best choice for local dev on a Mac with constrained RAM.

Defaults to ``mlx-community/Qwen2.5-0.5B-Instruct-4bit`` (~250MB on disk)
for fast iteration. Override with ``FAFSA_LLM_MODEL`` env var.
"""
from __future__ import annotations
import json
import re
from llm.base import LLMBackend
from fafsa.kb import SAITrace, fmt_trace


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


# Module-level cache so repeated backend instantiations don't reload the model.
_LOADED: dict[str, tuple] = {}


def _load(model_name: str):
    if model_name not in _LOADED:
        from mlx_lm import load
        _LOADED[model_name] = load(model_name)
    return _LOADED[model_name]


def _generate(model, tokenizer, prompt: str, max_tokens: int) -> str:
    """Wrapper around mlx_lm.generate that handles chat templates and thinking models."""
    from mlx_lm import generate
    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
        messages = [{"role": "user", "content": prompt}]
        # Qwen3 family emits <think>...</think> reasoning by default; we want the
        # JSON / narration only. Pass enable_thinking=False when the template
        # accepts it, fall back to a plain template otherwise.
        try:
            templated = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            templated = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
            )
        return generate(model, tokenizer, prompt=templated, max_tokens=max_tokens, verbose=False)
    return generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens, verbose=False)


def _strip_thinking(text: str) -> str:
    """Strip <think>...</think> blocks and 'Thinking Process:' prose if present."""
    # Drop everything up to and including a closing </think>
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    # Drop a leading 'Thinking Process:' / 'Reasoning:' block heuristically — keep
    # output from the first JSON object or first numeric/sentence start.
    return text.lstrip()


def _extract_json(text: str) -> dict:
    """Pull the first {...} JSON object out of an LLM response, tolerating chatter."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in MLX response: {text[:200]!r}")
    return json.loads(match.group(0))


class MLXBackend(LLMBackend):
    def __init__(self, model: str = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"):
        self.model_name = model
        self._model, self._tokenizer = _load(model)

    def extract_facts(self, query: str) -> dict:
        prompt = _EXTRACT_PROMPT.format(fields=_FIELDS_HINT, query=query)
        raw = _generate(self._model, self._tokenizer, prompt, max_tokens=512)
        return _extract_json(_strip_thinking(raw))

    def narrate_proof(self, trace: SAITrace) -> str:
        prompt = _NARRATE_PROMPT.format(trace=fmt_trace(trace, verbose=True))
        raw = _generate(self._model, self._tokenizer, prompt, max_tokens=600)
        return _strip_thinking(raw).strip()
