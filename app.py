"""Modal deployment for fafsa-engine.

Deploy:
    modal deploy app.py

Local dev:
    modal serve app.py

Endpoints:
    GET  /         — interactive Web Wizard UI
    POST /extract  — JSON {query: str} → extracted facts with reasoning
    POST /compute  — JSON {facts: dict} → SAI trace + narration
    GET  /health   — liveness + ED ISIR validation status
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
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>FAFSA Compliance Wizard</title>
  <style>
    :root {
      --primary: #2563eb;
      --primary-hover: #1d4ed8;
      --bg: #f8fafc;
      --surface: #ffffff;
      --border: #e2e8f0;
      --text: #0f172a;
      --text-light: #64748b;
      --radius: 8px;
      --success: #16a34a;
      --success-bg: #dcfce7;
    }
    body {
      font-family: system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      margin: 0;
      padding: 2rem;
    }
    .container {
      max-width: 800px;
      margin: 0 auto;
    }
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.5rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    h1 { font-size: 1.5rem; margin-top: 0; margin-bottom: 1.5rem; color: var(--primary); }
    h2 { font-size: 1.25rem; margin-top: 0; margin-bottom: 1rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }
    h3 { font-size: 1rem; margin: 0 0 0.5rem 0; }
    textarea {
      width: 100%;
      min-height: 100px;
      padding: 0.75rem;
      border: 1px solid var(--border);
      border-radius: 4px;
      font-family: inherit;
      box-sizing: border-box;
      resize: vertical;
    }
    input[type="number"] {
      width: 100%;
      padding: 0.5rem;
      border: 1px solid var(--border);
      border-radius: 4px;
      font-family: inherit;
      box-sizing: border-box;
      font-weight: 600;
    }
    button {
      background: var(--primary);
      color: white;
      border: none;
      padding: 0.75rem 1.5rem;
      border-radius: 4px;
      cursor: pointer;
      font-size: 1rem;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
    }
    button:hover { background: var(--primary-hover); }
    button:disabled { opacity: 0.7; cursor: not-allowed; }
    .secondary-btn {
      background: #f1f5f9;
      color: var(--text);
      border: 1px solid var(--border);
    }
    .secondary-btn:hover { background: #e2e8f0; }
    
    .field-row {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      margin-bottom: 1.5rem;
      padding-bottom: 1.5rem;
      border-bottom: 1px solid #f1f5f9;
    }
    .field-row:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
    .field-header { display: flex; justify-content: space-between; align-items: baseline; }
    .field-name { font-weight: 600; color: var(--text); font-size: 0.95rem; }
    .field-input { flex-shrink: 0; width: 150px; }
    .reasoning-box {
      background: #f8fafc;
      border-left: 3px solid var(--primary);
      padding: 0.75rem;
      font-size: 0.875rem;
      border-radius: 0 4px 4px 0;
    }
    .citation { font-style: italic; color: var(--text-light); margin-bottom: 0.25rem; }
    .reason { color: #334155; }
    
    .proof-tree {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.875rem;
      background: #1e293b;
      color: #f8fafc;
      padding: 1rem;
      border-radius: var(--radius);
      overflow-x: auto;
      white-space: pre;
      line-height: 1.6;
    }
    .proof-label { color: #93c5fd; }
    .proof-value { color: #a7f3d0; font-weight: bold; }
    .proof-cite { color: #94a3b8; font-style: italic; }
    
    .step-indicator { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
    .step { flex: 1; padding: 0.5rem; text-align: center; border-bottom: 3px solid var(--border); color: var(--text-light); font-weight: 600; font-size: 0.875rem; }
    .step.active { border-color: var(--primary); color: var(--primary); }
    .step.done { border-color: var(--success); color: var(--success); }
    
    .hidden { display: none !important; }
    .flex-between { display: flex; justify-content: space-between; align-items: center; }
    
    .result-banner {
      background: var(--success-bg);
      color: var(--success);
      padding: 1rem;
      border-radius: var(--radius);
      margin-bottom: 1rem;
      text-align: center;
    }
    .result-sai { font-size: 2.5rem; font-weight: bold; margin: 0; }
  </style>
</head>
<body>

<div class="container">
  <h1>FAFSA Compliance Engine</h1>
  
  <div class="step-indicator">
    <div class="step active" id="indicator-1">1. Query</div>
    <div class="step" id="indicator-2">2. Verify Facts</div>
    <div class="step" id="indicator-3">3. Proof Trace</div>
  </div>

  <!-- STEP 1: QUERY -->
  <div class="card" id="step-1">
    <h2>Describe your financial situation</h2>
    <p style="color: var(--text-light); margin-top: -0.5rem; font-size: 0.9rem;">
      Enter your family's financial details in plain English. The AI will extract the necessary facts for the FAFSA Student Aid Index (SAI) formula.
    </p>
    <textarea id="query-input" placeholder="e.g., I'm a dependent student. My parents make $85,000 combined and paid $6,200 in taxes. We are a family of 4. My dad is 50. I have $2,000 in savings."></textarea>
    <div style="margin-top: 1rem; text-align: right;">
      <button id="btn-extract">Extract Facts &rarr;</button>
    </div>
  </div>

  <!-- STEP 2: VERIFY FACTS -->
  <div class="card hidden" id="step-2">
    <div class="flex-between">
      <h2>Verify Extracted Facts</h2>
      <button class="secondary-btn" id="btn-back-1" style="padding: 0.4rem 0.8rem; font-size: 0.85rem;">&larr; Back</button>
    </div>
    <p style="color: var(--text-light); margin-top: -0.5rem; font-size: 0.9rem;">
      Review the extracted values. The reasoning shows exactly <i>why</i> the AI selected each number. <strong>Correct any mistakes directly in the inputs.</strong>
    </p>
    
    <div id="facts-container"></div>
    
    <!-- Add Fact Button -->
    <div style="margin: 1.5rem 0; padding: 1rem; border: 1px dashed var(--border); border-radius: var(--radius);">
      <h3 style="font-size: 0.9rem; color: var(--text-light);">Manually Add a Field</h3>
      <div style="display: flex; gap: 0.5rem;">
        <input type="text" id="new-field-name" placeholder="Field name (e.g. student_agi)" style="flex: 2; padding: 0.5rem;">
        <input type="number" id="new-field-val" placeholder="Value" style="flex: 1; padding: 0.5rem;">
        <button class="secondary-btn" id="btn-add-field" style="padding: 0.5rem 1rem;">Add</button>
      </div>
    </div>
    
    <div style="margin-top: 1.5rem; text-align: right; border-top: 1px solid var(--border); padding-top: 1rem;">
      <button id="btn-compute">Compute SAI Proof &rarr;</button>
    </div>
  </div>

  <!-- STEP 3: RESULTS -->
  <div class="card hidden" id="step-3">
    <div class="flex-between">
      <h2>Computation Result</h2>
      <button class="secondary-btn" id="btn-back-2" style="padding: 0.4rem 0.8rem; font-size: 0.85rem;">&larr; Edit Facts</button>
    </div>
    
    <div class="result-banner">
      <div style="font-size: 0.9rem; text-transform: uppercase; font-weight: bold; letter-spacing: 0.05em;">Calculated Student Aid Index (SAI)</div>
      <div class="result-sai" id="result-sai-val">...</div>
    </div>
    
    <h3>Plain English Explanation</h3>
    <p id="result-narration" style="background: #f8fafc; padding: 1rem; border-radius: 4px; color: var(--text);"></p>
    
    <h3 style="margin-top: 1.5rem;">Deterministic Proof Trace</h3>
    <p style="color: var(--text-light); font-size: 0.85rem; margin-top: -0.25rem;">This trace mathematically proves the result using the ED formulas.</p>
    <div class="proof-tree" id="result-trace"></div>
  </div>

</div>

<script>
  const UI = {
    s1: document.getElementById('step-1'),
    s2: document.getElementById('step-2'),
    s3: document.getElementById('step-3'),
    i1: document.getElementById('indicator-1'),
    i2: document.getElementById('indicator-2'),
    i3: document.getElementById('indicator-3'),
    query: document.getElementById('query-input'),
    btnExtract: document.getElementById('btn-extract'),
    btnCompute: document.getElementById('btn-compute'),
    factsContainer: document.getElementById('facts-container'),
    saiVal: document.getElementById('result-sai-val'),
    narration: document.getElementById('result-narration'),
    trace: document.getElementById('result-trace'),
    btnBack1: document.getElementById('btn-back-1'),
    btnBack2: document.getElementById('btn-back-2'),
    newFieldName: document.getElementById('new-field-name'),
    newFieldVal: document.getElementById('new-field-val'),
    btnAddField: document.getElementById('btn-add-field'),
  };

  let extractedFacts = {};

  function showStep(step) {
    UI.s1.classList.add('hidden'); UI.s2.classList.add('hidden'); UI.s3.classList.add('hidden');
    UI.i1.className = 'step'; UI.i2.className = 'step'; UI.i3.className = 'step';
    
    if (step === 1) { 
      UI.s1.classList.remove('hidden'); 
      UI.i1.classList.add('active'); 
    }
    if (step === 2) { 
      UI.s2.classList.remove('hidden'); 
      UI.i1.classList.add('done'); UI.i2.classList.add('active'); 
    }
    if (step === 3) { 
      UI.s3.classList.remove('hidden'); 
      UI.i1.classList.add('done'); UI.i2.classList.add('done'); UI.i3.classList.add('active'); 
    }
  }

  function renderFacts(facts) {
    UI.factsContainer.innerHTML = '';
    if (Object.keys(facts).length === 0) {
      UI.factsContainer.innerHTML = '<p>No facts extracted.</p>';
      return;
    }
    
    for (const [key, data] of Object.entries(facts)) {
      const val = typeof data === 'object' ? data.value : data;
      const citation = typeof data === 'object' && data.citation ? data.citation : '';
      const reasoning = typeof data === 'object' && data.reasoning ? data.reasoning : 'Manually added/edited.';
      
      const row = document.createElement('div');
      row.className = 'field-row';
      row.innerHTML = `
        <div class="field-header">
          <div class="field-name">${key}</div>
          <div class="field-input">
            <input type="number" data-key="${key}" value="${val}" />
          </div>
        </div>
        <div class="reasoning-box">
          ${citation ? `<div class="citation">"${citation}"</div>` : ''}
          <div class="reason">${reasoning}</div>
        </div>
      `;
      UI.factsContainer.appendChild(row);
    }
  }

  function gatherFacts() {
    const inputs = UI.factsContainer.querySelectorAll('input[type="number"]');
    const finalFacts = {};
    inputs.forEach(inp => {
      finalFacts[inp.dataset.key] = parseInt(inp.value, 10);
    });
    return finalFacts;
  }

  UI.btnBack1.addEventListener('click', () => showStep(1));
  UI.btnBack2.addEventListener('click', () => showStep(2));

  UI.btnAddField.addEventListener('click', () => {
    const k = UI.newFieldName.value.trim();
    const v = parseInt(UI.newFieldVal.value, 10);
    if (k && !isNaN(v)) {
      extractedFacts[k] = { value: v, reasoning: "Manually added by user." };
      renderFacts(extractedFacts);
      UI.newFieldName.value = '';
      UI.newFieldVal.value = '';
    }
  });

  UI.btnExtract.addEventListener('click', async () => {
    const q = UI.query.value.trim();
    if (!q) return alert('Please enter a query');
    
    UI.btnExtract.disabled = true;
    UI.btnExtract.textContent = 'Extracting...';
    
    try {
      const r = await fetch('/extract', {
        method: 'POST',
        headers: {'content-type': 'application/json'},
        body: JSON.stringify({query: q})
      });
      const data = await r.json();
      if (data.error) throw new Error(data.error);
      
      extractedFacts = data.facts;
      renderFacts(extractedFacts);
      showStep(2);
    } catch (e) {
      alert('Error: ' + e.message);
    } finally {
      UI.btnExtract.disabled = false;
      UI.btnExtract.textContent = 'Extract Facts \u2192';
    }
  });

  UI.btnCompute.addEventListener('click', async () => {
    const facts = gatherFacts();
    
    UI.btnCompute.disabled = true;
    UI.btnCompute.textContent = 'Computing...';
    
    try {
      const r = await fetch('/compute', {
        method: 'POST',
        headers: {'content-type': 'application/json'},
        body: JSON.stringify({facts})
      });
      const data = await r.json();
      if (data.error) throw new Error(data.error);
      
      UI.saiVal.textContent = `$${data.trace.sai.toLocaleString()}`;
      UI.narration.textContent = data.narration;
      
      // Render trace
      let traceHtml = '';
      data.trace.steps.forEach(s => {
        const valStr = s.value.toLocaleString();
        traceHtml += `<span class="proof-label">${s.label.padEnd(45)}</span> = <span class="proof-value">${valStr.padStart(10)}</span>  <span class="proof-cite">[${s.citation}]</span>\n`;
      });
      UI.trace.innerHTML = traceHtml;
      
      showStep(3);
    } catch (e) {
      alert('Error: ' + e.message);
    } finally {
      UI.btnCompute.disabled = false;
      UI.btnCompute.textContent = 'Compute SAI Proof \u2192';
    }
  });
</script>
</body>
</html>
"""

def _trace_to_dict(trace) -> dict:
    """Serialize an SAITrace to plain JSON."""
    return {
        "sai": trace.sai,
        "auto_neg1500": getattr(trace, "auto_neg1500", False),
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
def extract(payload: dict) -> dict:
    import sys
    sys.path.insert(0, "/root")
    from llm.base import get_backend

    query = (payload.get("query") or "").strip()
    if not query:
        return {"error": "query is required"}

    try:
        backend = get_backend()
        raw = backend.extract_facts(query)
        return {"facts": raw}
    except Exception as e:
        return {"error": f"fact extraction failed: {e}"}

@app.function(secrets=[LLM_SECRET], timeout=60)
@modal.fastapi_endpoint(method="POST")
def compute(payload: dict) -> dict:
    import sys
    sys.path.insert(0, "/root")
    from fafsa.kb import DependentFamily, prove_sai
    from llm.base import get_backend

    facts_input = payload.get("facts", {})
    
    # We still use DependentFamily as default for now, since it covers Formula A
    valid = {f.name for f in fields(DependentFamily)}
    clean_facts = {k: int(v) for k, v in facts_input.items() if k in valid}
    
    try:
        family = DependentFamily(**clean_facts)
        trace = prove_sai(family)
        
        backend = get_backend()
        narration = backend.narrate_proof(trace)
        
        return {
            "trace": _trace_to_dict(trace),
            "narration": narration
        }
    except Exception as e:
        return {"error": f"computation failed: {e}"}

@app.function(timeout=30)
@modal.fastapi_endpoint(method="GET")
def health() -> dict:
    """Liveness check."""
    return {"status": "ok"}
