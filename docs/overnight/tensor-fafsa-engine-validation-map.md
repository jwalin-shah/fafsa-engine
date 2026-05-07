# tensor-fafsa-engine validation-map audit

Queue item: `tensor-fafsa-engine-validation-map`
Repo: `tensor-fafsa-engine`
Branch: `codex/goal-tensor-fafsa-engine-validation-map`
HEAD at audit start: `af625d0502548b76af5b7363366866592c504b82`
Audit date: 2026-05-07

## Scope

This is a read-only validation-map audit. Product code, generated data, secrets,
external services, deploys, pushes, PR creation, and tracker updates were out of
scope. The only intended tracked change is this report.

## Repo Purpose

`fafsa-engine` is a small Python FAFSA Student Aid Index proof engine with an
LLM fact-extraction/narration layer. The deterministic core computes SAI traces
from dataclass inputs in `fafsa/kb.py`; `fafsa/isir.py` attempts to validate
Formula A records against a bundled Department of Education ISIR fixture;
`demo.py`, `fafsa/wizard.py`, and `app.py` expose CLI, interactive, and Modal
deployment paths.

## Current State

- `git status --short --branch` initially reported only
  `## codex/goal-tensor-fafsa-engine-validation-map`.
- `git status --short` before editing was empty.
- `git rev-parse HEAD` returned
  `af625d0502548b76af5b7363366866592c504b82`.
- `git remote -v` points to `https://github.com/jwalin-shah/fafsa-engine.git`.
- No project-level `AGENTS.md` or `CLAUDE.md` is tracked; `rg --files -g
  'AGENTS.md' -g 'CLAUDE.md' ...` found only `README.md`, `DEPLOY.md`,
  `pyproject.toml`, and `uv.lock`.
- Running `uv run ...` created ignored `.venv/` local state before failing.
  `.gitignore` ignores `.venv/`, `__pycache__/`, `*.pyc`, `*.egg-info/`,
  `dist/`, `.DS_Store`, and `.env`.

## Validation Inventory

Primary validation files and surfaces:

- `tests/test_isir_validation.py` is the ground-truth validation gate. It loads
  `data/IDSA25OP-20240308.txt` and asserts that all Formula A records pass.
- `tests/test_fafsa_kb.py` covers deterministic trace shape, monotonicity smoke
  checks, formatting, and `verify()` messaging.
- `tests/test_llm_backends.py` covers mocked Ollama, Claude, OpenAI, and MLX
  backend behavior, but imports optional SDK modules at collection time.
- `fafsa/isir.py` defines fixed-width ISIR field positions, reconstructs a
  `DependentFamily`, runs `prove_sai`, and returns `ISIRReport`.
- `fafsa/validate.py` caches `validate_isir_file()` and reports whether engine
  output is verified against the bundled ISIR data.
- `README.md` documents quick-start commands and claims 42/42 ED ISIR validation.
- `DEPLOY.md` documents Modal commands and endpoint names.
- `pyproject.toml` defines runtime dependencies, optional LLM extras, and the
  setuptools package list.
- `uv.lock` locks optional packages including `anthropic`, `openai`, and
  `mlx-lm`, but the default editable install path is currently broken.

## Evidence

1. `llm-tldr tree .` shows a compact repo: `fafsa/`, `llm/`, `medicaid/`,
   `tests/`, `data/IDSA25OP-20240308.txt`, `app.py`, `demo.py`,
   `DEPLOY.md`, `README.md`, `pyproject.toml`, and `uv.lock`.
2. `pyproject.toml:5-9` declares dependencies `torch`, `requests`, and
   `tensor-logic @ file:../tensor-logic`.
3. `pyproject.toml:11-14` defines optional extras for `claude`, `openai`, and
   `mlx`; `pyproject.toml:20-21` packages only `fafsa` and `llm`, not `data`,
   `examples`, or `medicaid`.
4. `README.md:30-33` and `README.md:53-57` claim 42/42 ED ISIR validation.
5. `README.md:41-43` recommends `uv pip install -e .`, `ollama pull
   qwen3.5:4b`, then `python demo.py ...`.
6. `README.md:88` says rules live in `fafsa/kb.py` and the derivation substrate
   is `tensor_logic/`, but no `tensor_logic/` directory is tracked in this repo.
7. `tests/test_isir_validation.py:22-26` creates an `ISIRReport` fixture from
   `data/IDSA25OP-20240308.txt`; `tests/test_isir_validation.py:33-45` asserts
   zero failures, exactly 42 passes, zero skips, and `all_passed`.
8. `fafsa/isir.py:17-45` hard-codes fixed-width field offsets; `fafsa/isir.py:
   72-122` reconstructs a `DependentFamily`; `fafsa/isir.py:129-170` computes
   pass/fail counts.
9. `fafsa/validate.py:105-110` caches the ISIR report; `fafsa/validate.py:
   132-139` returns a failed verification message when any ISIR failures exist.
10. `tests/test_llm_backends.py:8-10` imports `OllamaBackend`, `ClaudeBackend`,
    and `OpenAIBackend` at module import time.
11. `llm/base.py:25-44` imports all backend classes before branching on
    `FAFSA_LLM`, so missing optional packages break even the default Ollama path.
12. `llm/claude_backend.py:3` imports `anthropic` at module import time, and
    `llm/openai_backend.py:3` imports `OpenAI` at module import time.
13. `app.py:9-13` documents endpoints `/`, `/extract`, `/compute`, and
    `/health`, while `DEPLOY.md:25-35` documents `index`, `sai`, and `health`
    URLs plus a POST to `/sai`.
14. `app.py:484-488` implements `health()` as only `{"status": "ok"}` despite
    `app.py:13` saying the health endpoint includes ED ISIR validation status.
15. `data/IDSA25OP-20240308.txt` is 103 lines and 793,718 bytes; the first line
    width check returned 7,706 bytes.

## Commands Run

Environment probes:

```bash
python --version
```

Observed: failed with `python: command not found`.

```bash
python3 --version
```

Observed: `Python 3.12.8`.

```bash
python3 -m pytest --version
```

Observed: `pytest 9.0.3`.

```bash
uv --version
```

Observed: `uv 0.11.5 (Homebrew 2026-04-08 aarch64-apple-darwin)`.

Install/uv validation:

```bash
uv run python --version
uv run pytest --version
```

Observed: both failed while generating editable package metadata:

```text
error: Failed to generate package metadata for `fafsa-engine==0.1.0 @ editable+.`
  Caused by: Failed to parse metadata from built wheel
  Caused by: relative path without a working directory: ../tensor-logic
tensor-logic @ file:../tensor-logic
               ^^^^^^^^^^^^^^^^^^^^
```

Direct pytest validation:

```bash
python3 -m pytest tests/test_isir_validation.py -q
```

Observed: 1 passed, 3 failed. `ISIRReport(total=103, passed=2, failed=40,
skipped=0, ...)`; first failures included line 42 target `6096` vs actual
`8312`, line 43 target `4514` vs actual `-960`, and line 48 target `1169` vs
actual `3548`.

```bash
python3 -m pytest tests/test_fafsa_kb.py -q
```

Observed: 8 passed, 2 failed. Failures are verification-message tests that now
receive `engine FAILED ED validation: 2/103 ED test ISIRs pass, 40 fail`.

```bash
python3 -m pytest tests/test_llm_backends.py -q
python3 -m pytest -q
```

Observed: both fail at collection with `ModuleNotFoundError: No module named
'anthropic'`, reached through `tests/test_llm_backends.py -> llm/claude_backend.py`.

Direct engine probes:

```bash
python3 - <<'PY'
from fafsa.kb import DependentFamily, prove_sai
trace = prove_sai(DependentFamily(parent_agi=80000, family_size=4))
print(trace.sai)
print(len(trace.steps))
PY
```

Observed: `8150` and `25`. The core in-process calculation can run from repo
root without installation.

```bash
python3 - <<'PY'
from fafsa.validate import make_family, verify
from fafsa.kb import prove_sai
trace = prove_sai(make_family(0))
result = verify(trace)
print(result.verified)
print(result.message)
PY
```

Observed: `False`, then `engine FAILED ED validation: 2/103 ED test ISIRs pass,
40 fail. Engine output is not trustworthy.`

Example/demo probes:

```bash
python3 demo.py "My parents make $80k, family of 4"
```

Observed: fails before using Ollama because `get_backend()` imports
`llm.claude_backend`, which imports missing `anthropic`.

```bash
python3 examples/counterfactual.py
```

Observed: fails with `ModuleNotFoundError: No module named 'fafsa'` because
running a file inside `examples/` puts `examples/` on `sys.path`, not the repo
root.

```bash
PYTHONPATH=. python3 examples/counterfactual.py
```

Observed: passes and prints a parent AGI to SAI sweep from `$40,000` through
`$200,000`.

Syntax smoke:

```bash
python3 -m compileall -q fafsa llm tests app.py demo.py examples/counterfactual.py medicaid
```

Observed: passed with no output.

Data fixture probes:

```bash
wc -l data/IDSA25OP-20240308.txt
wc -c data/IDSA25OP-20240308.txt
head -n 1 data/IDSA25OP-20240308.txt | wc -c
```

Observed: 103 lines, 793,718 bytes, first line 7,706 bytes.

## Validation Map

| Command | Purpose | Expected Current Status | Notes |
| --- | --- | --- | --- |
| `git status --short` | Queue-item validation command | Passes; shows report as untracked/modified after this audit | Required by Goal Pack. |
| `python3 -m compileall -q fafsa llm tests app.py demo.py examples/counterfactual.py medicaid` | Syntax-only local smoke | Pass | Does not validate runtime imports or correctness. |
| `python3 -m pytest tests/test_isir_validation.py -q` | ED ISIR correctness gate | Fail: 1 passed, 3 failed | Strongest current correctness signal; contradicts 42/42 docs claim. |
| `python3 -m pytest tests/test_fafsa_kb.py -q` | Core trace and verify smoke | Fail: 8 passed, 2 failed | Failures are downstream of failed ISIR validation. |
| `python3 -m pytest tests/test_llm_backends.py -q` | Mocked backend unit tests | Fail at collection | Missing optional `anthropic` blocks collection. |
| `python3 -m pytest -q` | Full local test suite | Fail at collection | Stops on missing `anthropic` before reaching all test failures. |
| `uv run pytest -q` | Locked environment test path | Fail before tests | Editable metadata cannot parse `tensor-logic @ file:../tensor-logic`. |
| `python3 demo.py "My parents make $80k, family of 4"` | README demo smoke | Fail | Missing optional `anthropic` breaks default Ollama path. |
| `PYTHONPATH=. python3 examples/counterfactual.py` | Local example smoke | Pass | Direct `python3 examples/counterfactual.py` fails without `PYTHONPATH`. |
| `modal serve app.py` | Modal local deployment | Not run | External auth/service side effects out of scope. |

## Risks And Stale Assumptions

1. The 42/42 validation claim is stale or the ISIR parser/engine has regressed.
   Local `python3 -m pytest tests/test_isir_validation.py -q` reports only 2
   passing Formula A records and 40 failing records.
2. The default README quick start assumes `python` exists, but this host only
   had `python3`; `python --version` failed.
3. The `uv` path is broken by the relative `tensor-logic @ file:../tensor-logic`
   dependency. This prevents a clean, documented install/test loop even before
   correctness validation runs.
4. Optional LLM dependencies are not isolated. `llm/base.py` imports Claude and
   OpenAI backends before checking `FAFSA_LLM`, so missing `anthropic` breaks
   default Ollama usage and full test collection.
5. Backend tests rely on optional SDK imports at test module import time, so the
   mocked tests cannot run in a minimal environment.
6. `DEPLOY.md` endpoint names are stale relative to `app.py`: docs mention
   `/sai`, while code exposes `/extract` and `/compute`.
7. `app.py` advertises ED ISIR validation status in `/health`, but the endpoint
   returns only liveness. This can give deployment monitors false confidence.
8. `ISIRReport.total` stores total file lines, not total dependent records. The
   failure message `2/103 ED test ISIRs pass, 40 fail` mixes file-line count
   with dependent-record pass/fail count.
9. `examples/counterfactual.py` is not runnable as documented from repo root
   without `PYTHONPATH=.`, because the script path changes import resolution.
10. `pyproject.toml` packages only `fafsa` and `llm`; the bundled data fixture is
    not declared as package data. Installed environments may lose the ISIR file
    required by `fafsa.validate`.

## Next Safe Work

### Task 1: Make the deterministic ISIR gate truthful again

Acceptance criteria:

- `python3 -m pytest tests/test_isir_validation.py -q` has an explicit expected
  outcome that matches the current engine state.
- Either the engine/parser is fixed to pass all 42 Formula A records, or the
  README and verification messaging stop claiming 42/42.
- `ISIRReport` distinguishes total file lines from total dependent records in
  names and user-facing messages.

Validation command:

```bash
python3 -m pytest tests/test_isir_validation.py tests/test_fafsa_kb.py -q
```

Expected current status: fail until the ISIR mismatch or claims are fixed.

### Task 2: Repair local environment and dependency validation

Acceptance criteria:

- A documented command creates/runs the project without requiring hidden sibling
  checkout assumptions.
- The `tensor-logic` dependency is either made valid for editable installs,
  removed if unused, or documented as an explicit local prerequisite with a
  validation check.
- Package data needed by runtime validation is included or validation locates it
  reliably in source and installed layouts.

Validation command:

```bash
uv run pytest tests/test_isir_validation.py -q
```

Expected current status: fail before tests with `relative path without a working
directory: ../tensor-logic`.

### Task 3: Isolate optional LLM SDK imports

Acceptance criteria:

- `python3 - <<'PY' ... get_backend() ... PY` returns `OllamaBackend` in a
  minimal environment when `FAFSA_LLM` is unset.
- `python3 demo.py "My parents make $80k, family of 4"` reaches the Ollama HTTP
  request path instead of failing on missing `anthropic`.
- Mocked backend tests skip or isolate optional SDK cases when extras are not
  installed.

Validation command:

```bash
python3 -m pytest tests/test_llm_backends.py -q
```

Expected current status: fail at collection with missing `anthropic`.

### Task 4: Align docs and runnable examples

Acceptance criteria:

- README quick-start commands match local binary names and dependency reality.
- `examples/counterfactual.py` is runnable from repo root by the documented
  command, or docs use `PYTHONPATH=.` / module execution explicitly.
- `DEPLOY.md` endpoint names match `app.py`.

Validation commands:

```bash
python3 examples/counterfactual.py
python3 demo.py "My parents make $80k, family of 4"
```

Expected current status: first fails with `No module named 'fafsa'`; second
fails with missing `anthropic`.

## Non-Goals

- Did not change FAFSA formulas, parsers, tests, package metadata, docs claims,
  deployment code, examples, or dependencies.
- Did not install packages from the network.
- Did not call Ollama, Anthropic, OpenAI, Modal, GitHub, or any external API.
- Did not run Modal deploy/serve commands.
- Did not inspect or modify sibling repos.
- Did not create commits, pushes, PRs, or external tracker updates.

## Unknowns

- Whether a sibling `../tensor-logic` checkout exists in the intended developer
  workspace and whether it is still required by runtime code. No tracked code in
  this repo imports `tensor_logic` directly, but `README.md` references it.
- Whether the ED ISIR fixed-width offsets are stale, the bundled fixture changed,
  or the SAI arithmetic regressed. The first failing records span income,
  tax, student-income, and zero-parent-AGI cases, so this needs a focused
  parser-vs-formula investigation.
- Whether CI installs all optional extras, skips LLM backend tests, or currently
  fails the same way as local `python3 -m pytest -q`.
- Whether deployment docs are meant to describe an older `/sai` endpoint or a
  future merged `/extract` plus `/compute` API.
- Whether `medicaid/` is an intentionally un-packaged sibling demo or dead code.

## Handoff

- Changed files: `docs/overnight/tensor-fafsa-engine-validation-map.md`.
- Product code changed: no.
- Validation command required by queue: `git status --short`.
- PR URL: none; PR creation was out of scope for this queue item.
- Blockers: validation is runnable locally, but substantive correctness checks
  currently fail as documented above.
