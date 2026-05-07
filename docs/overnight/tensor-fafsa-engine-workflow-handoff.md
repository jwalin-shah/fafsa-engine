# tensor-fafsa-engine workflow handoff audit

Queue item: `tensor-fafsa-engine-workflow-handoff`
Repo path: `/Users/jwalinshah/projects/agent-stack/.agent-stack-worktrees/2026-05-07-overnight-marathon/tensor-fafsa-engine-workflow-handoff`
Branch: `codex/goal-tensor-fafsa-engine-workflow-handoff`
Starting HEAD: `af625d0502548b76af5b7363366866592c504b82` (`af625d0 refactor: depend on shared tensor-logic`)
Initial dirty state: `git status --short --branch` returned only `## codex/goal-tensor-fafsa-engine-workflow-handoff`; no tracked or untracked repo changes before this report.

## Repo purpose

This repo is a small Python FAFSA Student Aid Index proof engine. The intended shape is:

- Deterministic formula code in `fafsa/kb.py`, with `DependentFamily`, `IndependentFamily`, `CitedValue`, and `SAITrace` dataclasses plus `prove_sai()` dispatch (`fafsa/kb.py:23`, `fafsa/kb.py:62`, `fafsa/kb.py:87`, `fafsa/kb.py:95`, `fafsa/kb.py:181`).
- ED fixed-width test ISIR parsing and reconstruction in `fafsa/isir.py`, with hard-coded field slices and `validate_isir_file()` (`fafsa/isir.py:17`, `fafsa/isir.py:72`, `fafsa/isir.py:129`).
- A cached verification layer in `fafsa/validate.py` that reports whether the engine agrees with ED test data (`fafsa/validate.py:105`, `fafsa/validate.py:113`).
- LLM fact extraction and narration backends in `llm/`, selected by `FAFSA_LLM` (`llm/base.py:25`, `llm/base.py:31`).
- Three user-facing surfaces: CLI demo (`demo.py:17`), interactive terminal wizard (`fafsa/wizard.py:214`), and Modal web UI/API (`app.py:1`, `app.py:432`, `app.py:438`, `app.py:456`, `app.py:484`).
- A Medicaid proof-pattern demo in `medicaid/kb.py`, currently outside the packaged modules listed in `pyproject.toml` (`medicaid/kb.py:1`, `pyproject.toml:20`).

The most important handoff finding is that README-level correctness claims are currently contradicted by local validation: the bundled ED validation suite reports 40 failures out of 42 dependent records processed.

## Evidence gathered

Commands and local observations:

- `llm-tldr tree .` showed a compact repo with `fafsa/`, `llm/`, `medicaid/`, `tests/`, `data/IDSA25OP-20240308.txt`, `app.py`, `demo.py`, `DEPLOY.md`, `README.md`, `pyproject.toml`, and `uv.lock`.
- `git rev-parse HEAD` returned `af625d0502548b76af5b7363366866592c504b82`.
- `git log --oneline -5` shows recent history moving toward shared tensor logic and ED validation: `af625d0 refactor: depend on shared tensor-logic`, `f1e2fb3 feat: complete compliance engine with verified extraction and interactive wizard`, `d2eea87 chore: add app entry point and deploy notes`, `60ec4b3 feat: MLX backend for local Mac dev`, `834cb46 fix: replace self-consistency verifier with ED ground-truth validation`.
- `python --version` and `python -m pytest --version` both failed with `python: command not found`; `python3 --version` returned `Python 3.12.8`; `python3 -m pytest --version` returned `pytest 9.0.3`.
- `wc -l data/IDSA25OP-20240308.txt` returned `103`, while validation code later processes 42 Formula A records from that file.
- `du -sh data/IDSA25OP-20240308.txt uv.lock .` returned `776K`, `272K`, and `1.2M`; this is a small audit surface with a nontrivial local ED fixture.
- `ls -ld ../tensor-logic` failed with `No such file or directory`, but `pyproject.toml` requires `tensor-logic @ file:../tensor-logic` (`pyproject.toml:8`).
- `python3 -m pytest tests/test_fafsa_kb.py -q -k "not verify"` passed: `7 passed, 3 deselected`.
- `python3 -m pytest tests/test_fafsa_kb.py tests/test_isir_validation.py -q` failed: `5 failed, 9 passed`; the failures are all around ED verification, with `2/103 ED test ISIRs pass, 40 fail`.
- `python3 -c "from fafsa.isir import validate_isir_file; ..."` returned `total=103 passed=2 failed=40 skipped=0` and first failures at fixture lines 42, 43, and 48.
- `python3 -m pytest tests/test_llm_backends.py -q` failed during collection because `llm/claude_backend.py` imports `anthropic` and the local Python environment lacks that optional package.
- `python3 -m pytest -q` failed during collection for the same `ModuleNotFoundError: No module named 'anthropic'`.

File evidence:

- README claims a successful demo and says the engine is "validated against 42/42 ED test ISIRs" (`README.md:30`, `README.md:31`, `README.md:53`, `README.md:57`).
- README quick start uses `python demo.py` and says "No API key required" (`README.md:38`, `README.md:43`, `README.md:46`), but this machine only has `python3`, and provider-specific paths require either a local Ollama daemon/model or API keys.
- README claims the derivation substrate is `tensor_logic/` (`README.md:88`), while this checkout has no `tensor_logic/` directory and the configured sibling path is absent.
- `pyproject.toml` has runtime dependencies on `torch`, `requests`, and the missing sibling `tensor-logic` (`pyproject.toml:5`), optional provider extras for `anthropic`, `openai`, and `mlx-lm` (`pyproject.toml:11`), and no dev/test extra or script table.
- `pyproject.toml` packages only `fafsa` and `llm`, so `medicaid` is not shipped even though README describes "Beyond FAFSA" domains (`pyproject.toml:20`, `README.md:76`, `medicaid/kb.py:1`).
- `fafsa/kb.py` implements formulas A, B, and C in one file, but its core tests only cover basic invariants and do not validate independent-student outputs against ED fixtures (`fafsa/kb.py:2`, `fafsa/kb.py:181`, `tests/test_fafsa_kb.py:5`, `tests/test_isir_validation.py:1`).
- `fafsa/isir.py` reports `ISIRReport.total` as all file lines, not dependent records processed (`fafsa/isir.py:51`, `fafsa/isir.py:125`, `fafsa/isir.py:170`), which explains the observed `2/103` message even though 42 dependent records were processed.
- `tests/test_isir_validation.py` is explicit that failure means the engine diverged from federal ground truth and "any SAI it produces should not be trusted" (`tests/test_isir_validation.py:8`).
- `app.py` documents `/extract` and `/compute`, but `DEPLOY.md` documents `POST /sai` and a `backend` payload field that the app does not implement (`app.py:11`, `app.py:12`, `DEPLOY.md:33`, `DEPLOY.md:44`).
- `app.py` creates Modal functions with `LLM_SECRET` but leaves `required_keys=[]` (`app.py:40`), while `get_backend()` defaults to `ollama` (`llm/base.py:31`, `llm/base.py:34`) and the Modal image installs `anthropic`, `openai`, and `requests`, not an Ollama service (`app.py:27`).
- `app.py` health is a plain liveness response and does not check the ED ISIR validation status despite the module docstring saying `/health` includes validation status (`app.py:13`, `app.py:484`, `app.py:488`).
- LLM field hints are duplicated across Ollama, Claude, OpenAI, and MLX backends (`llm/ollama_backend.py:10`, `llm/claude_backend.py:7`, `llm/openai_backend.py:7`, `llm/mlx_backend.py:16`), and those hints cover only a subset of `DependentFamily` fields.

## Risks and stale assumptions

1. Stale correctness claim: README and verification tests expect `42/42`, but local validation returns `passed=2 failed=40`. This is a release blocker because the repo's own test text says failed ED validation makes SAI output untrustworthy.
2. Handoff-blocking dependency shape: `pyproject.toml` now depends on a sibling `../tensor-logic`, but that path is absent in this worktree. Fresh install commands are likely blocked unless the runner checks out sibling repos into exactly the expected location.
3. Optional provider imports break basic collection: `tests/test_llm_backends.py` imports `ClaudeBackend` and `OpenAIBackend` at module import time, so a minimal local Python environment cannot run full tests without optional extras.
4. Deployment contract drift: `DEPLOY.md` documents `/sai` and a request-time backend selector, while `app.py` exposes `/extract` and `/compute` and always delegates backend choice to environment variables.
5. Modal default is probably not runnable as documented: default backend is Ollama, but the Modal image installs no Ollama daemon/model; provider secrets are optional at the Modal secret declaration, so missing keys may fail only at request time.
6. Health endpoint overclaims validation status: docs say `/health` includes ED validation, but the code only returns `{"status": "ok"}`.
7. Packaged surface is unclear: `medicaid/kb.py` reuses FAFSA trace structures for a "demo consistency" eligibility score, but `medicaid` is not packaged or tested. README's "domain-agnostic" claim should not become implementation scope until ownership is decided.
8. Year and formula source assumptions are frozen in code/docs (`2024-25`, March 2024 guide). Future work needs product judgment before changing award-year constants or user-facing claims.

## Work Pack candidates

### 1. Restore ED validation truth before any product work

Scope: `fafsa/isir.py`, `fafsa/kb.py`, `fafsa/validate.py`, `tests/test_isir_validation.py`, `tests/test_fafsa_kb.py`, and README validation wording only if behavior changes.

Acceptance criteria:

- `validate_isir_file()` reports the number of dependent records processed separately from raw fixture line count.
- All 42 dependent Formula A records in `data/IDSA25OP-20240308.txt` pass, or the issue explicitly documents which ED fields/formulas are unsupported and removes the `42/42` claim.
- `verify(trace)` returns an accurate message and cannot claim component-level validation while failures exist.
- Add a focused regression around at least the first observed failing record (`lineno=42`, target `6096`, actual `8312`) before changing formulas.

Validation command:

- `python3 -m pytest tests/test_isir_validation.py tests/test_fafsa_kb.py -q`
- Expected current status: fail (`5 failed, 9 passed`).
- Expected after completion: pass.

Stop condition:

- Stop if resolving the mismatch requires changing regulatory interpretation without a product/legal decision about FAFSA award year or supported Formula A fields.

### 2. Make local validation collect in a clean minimal environment

Scope: `llm/base.py`, provider backend imports, `tests/test_llm_backends.py`, and `pyproject.toml` dependency metadata.

Acceptance criteria:

- Full pytest collection does not require `anthropic`, `openai`, or `mlx_lm` unless the relevant optional extra is installed.
- Backend tests either patch imports safely or skip provider-specific tests with a clear skip reason when extras are missing.
- A documented dev/test install path exists, for example a `test` optional extra or README validation section.
- No real LLM calls, API keys, local daemons, or model downloads are required for unit tests.

Validation command:

- `python3 -m pytest tests/test_llm_backends.py -q`
- Expected current status: fail during collection with `ModuleNotFoundError: No module named 'anthropic'`.
- Expected after completion: pass or intentionally skip missing-provider tests while preserving patched unit coverage.

### 3. Align Modal API, docs, backend defaults, and health behavior

Scope: `app.py`, `DEPLOY.md`, README deployment/API notes, and new app-contract tests if a lightweight Modal import strategy is feasible.

Acceptance criteria:

- The documented endpoint names match the actual app: either implement `POST /sai` or update docs to use `/extract` and `/compute`.
- If request payload accepts `backend`, app honors it; if not, docs remove that claim and document `FAFSA_LLM`.
- Modal runtime default selects a backend that can actually run with the documented setup, or startup/health clearly reports missing backend prerequisites.
- `/health` either includes ED validation status as documented or docs stop claiming that.
- Tests cover the pure Python payload-cleaning and trace serialization paths without requiring Modal credentials.

Validation command:

- Add and run `python3 -m pytest tests/test_app_contract.py -q`.
- Expected current status: no such test file; manual evidence shows docs/code mismatch.

### 4. Decide the shared tensor-logic and Medicaid packaging boundary

Scope: `pyproject.toml`, README engine/beyond-FAFSA claims, package layout, and possibly a separate repo/worktree if `tensor-logic` is intended to be a required sibling.

Acceptance criteria:

- A fresh checkout has a documented, reproducible install path. If `tensor-logic` is required, the repo explains how to place it; if not, remove the file dependency.
- README's `tensor_logic/` statement matches actual package/import names and local files.
- `medicaid` is either packaged and tested as a supported demo, or marked as non-shipped scratch/removed from product claims.
- No implementation worker mutates sibling repos unless its Work Pack explicitly owns that repo.

Validation command:

- `uv sync --frozen --all-extras` after dependency ownership is settled.
- Expected current status: likely blocked because `../tensor-logic` is missing; not run here to avoid creating environment artifacts.

## Validation map

| Command | Observed or expected status | Notes |
| --- | --- | --- |
| `git status --short` | Observed pass, exit 0: `?? docs/`. | This report is the only intended audit artifact under the new `docs/overnight/` path. |
| `python3 -m pytest tests/test_fafsa_kb.py -q -k "not verify"` | Observed pass: `7 passed, 3 deselected`. | Basic formula invariants only; not sufficient correctness proof. |
| `python3 -m pytest tests/test_fafsa_kb.py tests/test_isir_validation.py -q` | Observed fail: `5 failed, 9 passed`. | ED validation blocker: `passed=2 failed=40 skipped=0`. |
| `python3 -m pytest tests/test_llm_backends.py -q` | Observed fail during collection. | Missing optional `anthropic` package. |
| `python3 -m pytest -q` | Observed fail during collection. | Same missing optional provider package; full suite does not reach ED failures. |
| `uv sync --frozen --all-extras` | Not run; expected blocker. | Evidence: `pyproject.toml` points to missing `../tensor-logic`. |
| `modal serve app.py` / `modal deploy app.py` | Not run; expected external-service blocker. | Requires Modal auth/secrets and may not have a runnable default backend. |

## Non-goals for this slice

- No product code changes.
- No formula, parser, LLM, deployment, dependency, or README fixes.
- No sibling repo edits, generated data edits, secret reads, Modal calls, pushes, PR creation, merges, or tracker state changes.
- No attempt to decide FAFSA regulatory/product scope for future award years.

## Unknowns for morning review

- Whether `af625d0` intentionally expects the queue runner to materialize a sibling `tensor-logic` repo before install.
- Whether the current ED fixture is still meant to represent exactly 42 dependent test records, or whether the parser should track multiple record categories separately.
- Whether `/sai` is the desired public API, or whether the newer two-step `/extract` and `/compute` flow is the product contract.
- Whether Modal should default to Claude/OpenAI for public demos or support Ollama/MLX only locally.
- Whether `medicaid` is a product direction, a proof-pattern scratchpad, or stale code.
- Whether README's "Domingos (2025)" reference has a local citation/document that should be linked.

## Handoff

Changed file intended by this audit: `docs/overnight/tensor-fafsa-engine-workflow-handoff.md`.

Commit SHA: no new commit created in this local worker; starting HEAD is `af625d0502548b76af5b7363366866592c504b82`.

PR URL: none; PR creation is out of scope for the overnight read-only audit.

Required validation: `git status --short` ran successfully after writing this report and returned `?? docs/`.

Blockers:

- ED validation currently fails against the bundled fixture.
- Full pytest collection currently fails without optional provider packages.
- Fresh uv install is likely blocked by missing `../tensor-logic`.
- Deployment validation is blocked by external Modal credentials/secrets and an unresolved backend default.
