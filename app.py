"""Modal deployment for fafsa-engine.

Deploy:
    modal deploy app.py

Local dev:
    modal serve app.py

Endpoints:
    GET  /         — minimal HTML form
    POST /sai      — JSON {query: str, backend?: "claude"|"openai"} → result JSON
    GET  /health   — liveness + ED ISIR validation status

Defaults to Claude backend (no GPU, $0 idle, ~$0.001/query). Set
ANTHROPIC_API_KEY in Modal secrets before deploying.
"""
from __future__ import annotations

import os
from dataclasses import asdict, fields
from pathlib import Path

import modal


REPO_ROOT = Path(__file__).parent

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi[standard]",
        "anthropic",
        "openai",
        "requests",
    )
    .add_local_dir(REPO_ROOT / "fafsa", remote_path="/root/fafsa")
    .add_local_dir(REPO_ROOT / "llm", remote_path="/root/llm")
    .add_local_dir(REPO_ROOT / "data", remote_path="/root/data")
)

app = modal.App("fafsa-engine", image=image)

LLM_SECRET = modal.Secret.from_name(
    "fafsa-llm-keys",
    required_keys=[],  # ANTHROPIC_API_KEY and/or OPENAI_API_KEY
)


HTML_FORM = """<!doctype html>
<html><head><title>fafsa-engine</title>
<style>
  body { font-family: ui-monospace, Menlo, monospace; max-width: 720px; margin: 3rem auto; padding: 0 1rem; }
  textarea { width: 100%; min-height: 4rem; padding: .5rem; font: inherit; }
  button { padding: .5rem 1rem; font: inherit; cursor: pointer; }
  pre { background: #f4f4f4; padding: 1rem; overflow: auto; white-space: pre-wrap; }
  .verified { color: #0a7d28; }
  .unverified { color: #a05a00; }
  h1 { font-size: 1.2rem; }
</style></head><body>
<h1>fafsa-engine — an LLM tells you your SAI; this proves it</h1>
<form id="f">
  <textarea name="q" placeholder="My parents make $80k, family of 4">My parents make $80k, family of 4</textarea><br><br>
  <button type="submit">Compute SAI</button>
</form>
<pre id="out"></pre>
<script>
document.getElementById('f').addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = e.target.q.value;
  const out = document.getElementById('out');
  out.textContent = 'computing...';
  const r = await fetch('/sai', {
    method: 'POST',
    headers: {'content-type': 'application/json'},
    body: JSON.stringify({query: q})
  });
  const j = await r.json();
  out.textContent = JSON.stringify(j, null, 2);
});
</script>
</body></html>
"""


def _trace_to_dict(trace) -> dict:
    """Serialize an SAITrace to plain JSON."""
    return {
        "sai": trace.sai,
        "auto_neg1500": trace.auto_neg1500,
        "steps": [
            {
                "label": s.label,
                "value": s.value,
                "citation": s.citation,
                "formula": s.formula,
            }
            for s in trace.steps
        ],
    }


@app.function(secrets=[LLM_SECRET], timeout=60)
@modal.fastapi_endpoint(method="GET", docs=False)
def index():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(HTML_FORM)


@app.function(secrets=[LLM_SECRET], timeout=60)
@modal.fastapi_endpoint(method="POST")
def sai(payload: dict) -> dict:
    """Run the full pipeline: query → facts → proof → narration → verification."""
    import sys
    sys.path.insert(0, "/root")

    from fafsa.kb import DependentFamily, prove_sai
    from fafsa.validate import verify
    from llm.base import get_backend

    query = (payload.get("query") or "").strip()
    if not query:
        return {"error": "query is required"}

    backend_name = payload.get("backend") or os.environ.get("FAFSA_LLM", "claude")
    os.environ["FAFSA_LLM"] = backend_name

    try:
        backend = get_backend()
    except Exception as e:
        return {"error": f"backend init failed: {e}"}

    # 1. Extract facts
    try:
        raw = backend.extract_facts(query)
    except Exception as e:
        return {"error": f"fact extraction failed: {e}"}

    valid = {f.name for f in fields(DependentFamily)}
    facts = {k: v for k, v in raw.items() if k in valid and v is not None}
    family = DependentFamily(**facts)

    # 2. Compute proof
    trace = prove_sai(family)

    # 3. Narrate
    try:
        narration = backend.narrate_proof(trace)
    except Exception as e:
        narration = f"(narration failed: {e})"

    # 4. Verify
    result = verify(trace)

    return {
        "query": query,
        "backend": backend_name,
        "facts": facts,
        "trace": _trace_to_dict(trace),
        "narration": narration,
        "verification": {
            "verified": result.verified,
            "message": result.message,
        },
    }


@app.function(timeout=30)
@modal.fastapi_endpoint(method="GET")
def health() -> dict:
    """Liveness check + ED ISIR validation status."""
    import sys
    sys.path.insert(0, "/root")

    from fafsa.isir import validate_isir_file

    try:
        report = validate_isir_file()
        return {
            "status": "ok" if report.all_passed else "engine_diverged",
            "isir_total": report.total,
            "isir_passed": report.passed,
            "isir_failed": report.failed,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
