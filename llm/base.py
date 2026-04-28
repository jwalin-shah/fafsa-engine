from __future__ import annotations
import os
from abc import ABC, abstractmethod
from fafsa.kb import SAITrace


class LLMBackend(ABC):
    @abstractmethod
    def extract_facts(self, query: str) -> dict:
        """Extract DependentFamily fields from natural language. Returns dict of field:value."""
        ...

    @abstractmethod
    def narrate_proof(self, trace: SAITrace) -> str:
        """Explain SAITrace in plain English. Returns 3-5 sentence narration."""
        ...


def get_backend() -> LLMBackend:
    """Resolve backend from FAFSA_LLM env var (default: ollama)."""
    from llm.ollama_backend import OllamaBackend
    from llm.claude_backend import ClaudeBackend
    from llm.openai_backend import OpenAIBackend

    name = os.environ.get("FAFSA_LLM", "ollama").lower()
    model = os.environ.get("FAFSA_LLM_MODEL", "qwen3.5:4b")

    if name == "ollama":
        return OllamaBackend(model=model)
    if name == "claude":
        return ClaudeBackend()
    if name == "openai":
        return OpenAIBackend()
    raise ValueError(f"Unknown FAFSA_LLM backend: {name!r}. Choose: ollama, claude, openai")
