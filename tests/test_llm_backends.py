import builtins
import importlib.util
import json
import os
import sys
import pytest
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

from fafsa.kb import DependentFamily, prove_sai
from llm.base import get_backend
from llm.ollama_backend import OllamaBackend
from llm.claude_backend import ClaudeBackend
from llm.openai_backend import OpenAIBackend


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_trace():
    return prove_sai(DependentFamily(parent_agi=80_000, family_size=4))


def _fake_module(name: str, **attrs):
    module = ModuleType(name)
    for attr_name, attr_value in attrs.items():
        setattr(module, attr_name, attr_value)
    return module


def _block_optional_sdk_imports(monkeypatch):
    blocked = {"anthropic", "openai", "mlx_lm"}
    for name in blocked:
        monkeypatch.delitem(sys.modules, name, raising=False)

    real_import = builtins.__import__
    imported = []

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.split(".", 1)[0] in blocked:
            imported.append(name)
            raise ModuleNotFoundError(f"No module named {name!r}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    return imported


# ── OllamaBackend ──────────────────────────────────────────────────────────────

def test_ollama_extract_facts_parses_json():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": '{"parent_agi": 80000, "family_size": 4}'}
    mock_resp.raise_for_status.return_value = None
    with patch("requests.post", return_value=mock_resp):
        result = OllamaBackend().extract_facts("My parents make $80k, family of 4")
    assert result == {"parent_agi": 80000, "family_size": 4}


def test_ollama_narrate_proof_returns_str():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "Your SAI is determined by your family's income..."}
    mock_resp.raise_for_status.return_value = None
    with patch("requests.post", return_value=mock_resp):
        result = OllamaBackend().narrate_proof(_make_trace())
    assert isinstance(result, str)
    assert len(result) > 0


def test_ollama_custom_model():
    backend = OllamaBackend(model="gemma4:4b")
    assert backend.model == "gemma4:4b"


# ── ClaudeBackend ──────────────────────────────────────────────────────────────

def test_claude_extract_facts_parses_json():
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [
        MagicMock(text='{"parent_agi": 80000, "family_size": 4}')
    ]
    fake_anthropic = _fake_module("anthropic", Anthropic=MagicMock(return_value=mock_client))
    with patch.dict(sys.modules, {"anthropic": fake_anthropic}):
        result = ClaudeBackend().extract_facts("My parents make $80k, family of 4")
    assert result == {"parent_agi": 80000, "family_size": 4}


def test_claude_narrate_proof_returns_str():
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(text="Your SAI is...")]
    fake_anthropic = _fake_module("anthropic", Anthropic=MagicMock(return_value=mock_client))
    with patch.dict(sys.modules, {"anthropic": fake_anthropic}):
        result = ClaudeBackend().narrate_proof(_make_trace())
    assert isinstance(result, str)


# ── OpenAIBackend ──────────────────────────────────────────────────────────────

def test_openai_extract_facts_parses_json():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content='{"parent_agi": 80000, "family_size": 4}'))
    ]
    fake_openai = _fake_module("openai", OpenAI=MagicMock(return_value=mock_client))
    with patch.dict(sys.modules, {"openai": fake_openai}):
        result = OpenAIBackend().extract_facts("My parents make $80k, family of 4")
    assert result == {"parent_agi": 80000, "family_size": 4}


def test_openai_narrate_proof_returns_str():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="Your SAI is..."))
    ]
    fake_openai = _fake_module("openai", OpenAI=MagicMock(return_value=mock_client))
    with patch.dict(sys.modules, {"openai": fake_openai}):
        result = OpenAIBackend().narrate_proof(_make_trace())
    assert isinstance(result, str)


# ── get_backend factory ────────────────────────────────────────────────────────

def test_import_llm_base_does_not_import_optional_sdks(monkeypatch):
    imported = _block_optional_sdk_imports(monkeypatch)
    module_path = Path(__file__).parents[1] / "llm" / "base.py"
    spec = importlib.util.spec_from_file_location("llm_base_import_probe", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert imported == []


def test_get_backend_default_ollama():
    clean = {k: v for k, v in os.environ.items() if k not in ("FAFSA_LLM", "FAFSA_LLM_MODEL")}
    with patch.dict(os.environ, clean, clear=True):
        backend = get_backend()
    assert isinstance(backend, OllamaBackend)
    assert backend.model == "qwen3.5:4b"


def test_get_backend_default_ollama_without_optional_sdks(monkeypatch):
    imported = _block_optional_sdk_imports(monkeypatch)
    clean = {k: v for k, v in os.environ.items() if k not in ("FAFSA_LLM", "FAFSA_LLM_MODEL")}
    with patch.dict(os.environ, clean, clear=True):
        backend = get_backend()
    assert isinstance(backend, OllamaBackend)
    assert backend.model == "qwen3.5:4b"
    assert imported == []


def test_get_backend_claude():
    fake_anthropic = _fake_module("anthropic", Anthropic=MagicMock(return_value=MagicMock()))
    with patch.dict(os.environ, {"FAFSA_LLM": "claude"}):
        with patch.dict(sys.modules, {"anthropic": fake_anthropic}):
            backend = get_backend()
    assert isinstance(backend, ClaudeBackend)


def test_get_backend_openai():
    mock_client = MagicMock()
    fake_openai = _fake_module("openai", OpenAI=MagicMock(return_value=mock_client))
    with patch.dict(os.environ, {"FAFSA_LLM": "openai"}):
        with patch.dict(sys.modules, {"openai": fake_openai}):
            backend = get_backend()
    assert isinstance(backend, OpenAIBackend)


def test_get_backend_custom_model():
    with patch.dict(os.environ, {"FAFSA_LLM": "ollama", "FAFSA_LLM_MODEL": "gemma4:4b"}):
        backend = get_backend()
    assert isinstance(backend, OllamaBackend)
    assert backend.model == "gemma4:4b"


def test_get_backend_unknown_raises():
    with patch.dict(os.environ, {"FAFSA_LLM": "unknown"}):
        with pytest.raises(ValueError, match="Unknown FAFSA_LLM backend"):
            get_backend()


# ── MLXBackend ─────────────────────────────────────────────────────────────────

def _patched_mlx_backend(generate_returns: str, model: str = "mlx-community/Qwen3.5-2B-MLX-4bit"):
    """Build an MLXBackend whose model is mocked, so tests don't load real weights."""
    from llm.mlx_backend import MLXBackend
    fake_tok = MagicMock()
    fake_tok.chat_template = None  # take the plain-prompt path
    fake_tok.apply_chat_template = MagicMock(return_value="prompt")
    fake_model = MagicMock()
    with patch("llm.mlx_backend._load", return_value=(fake_model, fake_tok)):
        with patch("llm.mlx_backend.generate", create=True, return_value=generate_returns):
            with patch("mlx_lm.generate", return_value=generate_returns):
                backend = MLXBackend(model=model)
                backend._tokenizer = fake_tok
                backend._model = fake_model
                yield backend


def test_mlx_extract_facts_parses_json_after_thinking():
    """Qwen3 emits 'Thinking Process:' prose before JSON — backend must strip it."""
    raw = (
        "Thinking Process:\n"
        "1. Parse the query.\n"
        "2. Extract numeric values.\n\n"
        '{"parent_agi": 80000, "family_size": 4, "num_parents": 2}'
    )
    from llm.mlx_backend import MLXBackend, _strip_thinking, _extract_json
    parsed = _extract_json(_strip_thinking(raw))
    assert parsed == {"parent_agi": 80000, "family_size": 4, "num_parents": 2}


def test_mlx_strip_thinking_removes_think_tags():
    from llm.mlx_backend import _strip_thinking
    raw = "<think>internal reasoning ...</think>\n{\"x\": 1}"
    assert _strip_thinking(raw).strip() == '{"x": 1}'


def test_mlx_extract_json_raises_on_no_json():
    from llm.mlx_backend import _extract_json
    with pytest.raises(ValueError, match="No JSON object found"):
        _extract_json("just prose, no braces here")


def test_get_backend_mlx_default_model():
    with patch.dict(os.environ, {"FAFSA_LLM": "mlx"}, clear=False):
        with patch("llm.mlx_backend._load") as mock_load:
            mock_load.return_value = (MagicMock(), MagicMock())
            backend = get_backend()
    from llm.mlx_backend import MLXBackend
    assert isinstance(backend, MLXBackend)
    assert backend.model_name == "mlx-community/Qwen3.5-2B-MLX-4bit"
