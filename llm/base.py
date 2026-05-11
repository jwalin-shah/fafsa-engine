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


_DEFAULT_MODEL = {
    "ollama": "qwen3.5:4b",
    "mlx": "mlx-community/Qwen3.5-2B-MLX-4bit",
}


def get_backend() -> LLMBackend:
    """Resolve backend from FAFSA_LLM env var (default: ollama)."""
    name = os.environ.get("FAFSA_LLM", "ollama").lower()
    model = os.environ.get("FAFSA_LLM_MODEL") or _DEFAULT_MODEL.get(name, "qwen3.5:4b")

    if name == "ollama":
        from llm.ollama_backend import OllamaBackend
        return OllamaBackend(model=model)
    if name == "claude":
        from llm.claude_backend import ClaudeBackend
        return ClaudeBackend()
    if name == "openai":
        from llm.openai_backend import OpenAIBackend
        return OpenAIBackend()
    if name == "mlx":
        from llm.mlx_backend import MLXBackend
        return MLXBackend(model=model)
    raise ValueError(
        f"Unknown FAFSA_LLM backend: {name!r}. Choose: ollama, mlx, claude, openai"
    )
