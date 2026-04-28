import json
import os
import pytest
from unittest.mock import MagicMock, patch

from fafsa.kb import DependentFamily, prove_sai
from llm.base import get_backend
from llm.ollama_backend import OllamaBackend
from llm.claude_backend import ClaudeBackend
from llm.openai_backend import OpenAIBackend


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_trace():
    return prove_sai(DependentFamily(parent_agi=80_000, family_size=4))


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
    with patch("anthropic.Anthropic", return_value=mock_client):
        result = ClaudeBackend().extract_facts("My parents make $80k, family of 4")
    assert result == {"parent_agi": 80000, "family_size": 4}


def test_claude_narrate_proof_returns_str():
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(text="Your SAI is...")]
    with patch("anthropic.Anthropic", return_value=mock_client):
        result = ClaudeBackend().narrate_proof(_make_trace())
    assert isinstance(result, str)


# ── OpenAIBackend ──────────────────────────────────────────────────────────────

def test_openai_extract_facts_parses_json():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content='{"parent_agi": 80000, "family_size": 4}'))
    ]
    with patch("llm.openai_backend.OpenAI", return_value=mock_client):
        result = OpenAIBackend().extract_facts("My parents make $80k, family of 4")
    assert result == {"parent_agi": 80000, "family_size": 4}


def test_openai_narrate_proof_returns_str():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="Your SAI is..."))
    ]
    with patch("llm.openai_backend.OpenAI", return_value=mock_client):
        result = OpenAIBackend().narrate_proof(_make_trace())
    assert isinstance(result, str)


# ── get_backend factory ────────────────────────────────────────────────────────

def test_get_backend_default_ollama():
    clean = {k: v for k, v in os.environ.items() if k not in ("FAFSA_LLM", "FAFSA_LLM_MODEL")}
    with patch.dict(os.environ, clean, clear=True):
        backend = get_backend()
    assert isinstance(backend, OllamaBackend)
    assert backend.model == "qwen3.5:4b"


def test_get_backend_claude():
    with patch.dict(os.environ, {"FAFSA_LLM": "claude"}):
        backend = get_backend()
    assert isinstance(backend, ClaudeBackend)


def test_get_backend_openai():
    mock_client = MagicMock()
    with patch.dict(os.environ, {"FAFSA_LLM": "openai"}):
        with patch("llm.openai_backend.OpenAI", return_value=mock_client):
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
