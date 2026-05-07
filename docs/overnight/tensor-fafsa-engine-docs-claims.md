# Overnight docs-claims audit: tensor-fafsa-engine

Queue item: `tensor-fafsa-engine-docs-claims`

Repo: `tensor-fafsa-engine`

Worktree: `/Users/jwalinshah/projects/agent-stack/.agent-stack-worktrees/2026-05-07-overnight-marathon/tensor-fafsa-engine-docs-claims`

Audit date: 2026-05-07

Focus: README/docs claims, supported evidence, unsupported claims, non-claims, validation notes, and next safe work.

## Executive finding

The README currently overstates the verified status of the engine. Local execution of the bundled ISIR validator reports `ISIRReport(total=103, passed=2, failed=40, skipped=0, ...)`, and the focused FAFSA validation tests fail with `5 failed, 9 passed`. That directly contradicts the README claim that all 42 dependent-student ED test ISIRs pass.

The repo does contain a real deterministic FAFSA rule engine and a bundled ED test file, but morning review should treat the public docs as unsafe until the validation claim is reconciled. The most urgent docs-claim fixes are:

- Replace or gate the `42/42` verification claim in `README.md`.
- Fix the quickstart/runtime story; `python` is missing in this local shell, `python3 demo.py ...` fails before Ollama because optional Claude/OpenAI imports are eager, and `uv run` fails in the isolated worktree because `../tensor-logic` is missing.
- Bring `DEPLOY.md` in line with `app.py`; the docs describe `/sai`, but the app exposes `/extract`, `/compute`, `/health`, and `/`.
- Clarify the relationship with `tensor-logic`; it exists as a sibling portfolio repo, but this isolated worktree does not contain `../tensor-logic`, and this repo's code does not import `tensor_logic`.

## Repo state and purpose

Purpose inferred from local files: a small Python FAFSA Student Aid Index proof engine with LLM-backed fact extraction/narration, Modal deployment notes, a Medicaid proof-pattern demo, and tests around the FAFSA arithmetic, ED ISIR validation, and LLM backends.

Current branch and dirty state before the report:

- `git status --short --branch` output: `## codex/goal-tensor-fafsa-engine-docs-claims`
- `git rev-parse HEAD` output before this report: `af625d0502548b76af5b7363366866592c504b82`
- `git remote -v` shows `origin https://github.com/jwalin-shah/fafsa-engine.git`
- `git status --short --ignored` was clean after removing generated ignored state from local proof commands.

Local repo shape from `llm-tldr tree .`:

- Docs: `README.md`, `DEPLOY.md`
- Entrypoints: `demo.py`, `app.py`, `examples/counterfactual.py`, `fafsa/wizard.py`
- FAFSA engine: `fafsa/kb.py`, `fafsa/isir.py`, `fafsa/validate.py`
- LLM layer: `llm/base.py`, `llm/ollama_backend.py`, `llm/mlx_backend.py`, `llm/claude_backend.py`, `llm/openai_backend.py`
- Other rule demo: `medicaid/kb.py`
- Validation assets: `data/IDSA25OP-20240308.txt`, `tests/test_isir_validation.py`, `tests/test_fafsa_kb.py`, `tests/test_llm_backends.py`

## Commands run

- `llm-tldr tree .` observed a 2,596-line repo surface across README/deploy docs, app/demo entrypoints, FAFSA code, LLM backends, Medicaid demo, tests, and the bundled ISIR file.
- `git status --short --branch` observed the branch as `codex/goal-tensor-fafsa-engine-docs-claims`.
- `git rev-parse --show-toplevel && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD` confirmed the worktree path, branch, and starting SHA `af625d0502548b76af5b7363366866592c504b82`.
- `rtk read README.md`, `rtk read DEPLOY.md`, and `rtk read pyproject.toml` captured the claim-bearing docs and package metadata.
- `rtk read fafsa/kb.py`, `rtk read fafsa/isir.py`, `rtk read fafsa/validate.py`, `rtk read demo.py`, `rtk read app.py`, `rtk read llm/*.py`, `rtk read medicaid/kb.py`, and `rtk read tests/*.py` checked local support for the docs claims.
- `python` commands failed with `/opt/homebrew/bin/bash: line 1: python: command not found`, which matters because README and demo usage use `python`.
- `python3 --version` output: `Python 3.12.8`.
- `python3 - <<'PY' ... validate_isir_file() ... PY` output: `ISIRReport(total=103, passed=2, failed=40, skipped=0, ...)` and `all_passed= False`.
- `python3 -m pytest tests/test_isir_validation.py tests/test_fafsa_kb.py -q` failed with `5 failed, 9 passed`; failures are the ED ISIR pass-count assertions and verification-message assertions.
- `PYTHONPATH=. python3 -m pytest tests/test_llm_backends.py -q` failed during collection with `ModuleNotFoundError: No module named 'anthropic'`.
- `uv --version` output: `uv 0.11.5 (Homebrew 2026-04-08 aarch64-apple-darwin)`.
- `uv run python ... validate_isir_file()` and `uv run pytest ...` both failed while creating package metadata: `relative path without a working directory: ../tensor-logic`.
- `python3 demo.py "My parents make $80k, family of 4"` failed with `ModuleNotFoundError: No module named 'anthropic'` via `llm.base.get_backend()`.
- `python3 - <<'PY' ... prove_sai(DependentFamily(parent_agi=80000, family_size=4)) ... PY` produced `sai= 8150`, so the README sample SAI is locally reproducible when bypassing LLM extraction and verification.
- `python3 - <<'PY' ... verify(trace) ... PY` returned `verified= False` and message `engine FAILED ED validation: 2/103 ED test ISIRs pass, 40 fail`.
- `python3 - <<'PY' from app import index, health ... PY` failed with `ModuleNotFoundError: No module named 'modal'`.
- `python3 examples/counterfactual.py` failed with `ModuleNotFoundError: No module named 'fafsa'`; `PYTHONPATH=. python3 examples/counterfactual.py` produced the expected income sweep.
- `python3 - <<'PY' ... prove_medicaid(...) ... PY` produced a Medicaid eligibility trace, supporting the existence of a demo but not full Medicaid product claims.
- `fd repos.json /Users/jwalinshah/projects/agent-stack -d 5` found `/Users/jwalinshah/projects/agent-stack/repos.json`.
- Reading `repos.json` showed the related tensor repos: `tensor-experiments`, `tensor-fafsa-engine`, `tensor-quicksilver-zk`, `tensor-taxes`, and `tensor-logic`.
- `llm-tldr tree /Users/jwalinshah/projects/tensor/tensor-logic` confirmed a real sibling `tensor_logic/` package, but not inside this isolated worktree.
- `git -C /Users/jwalinshah/projects/tensor/tensor-logic status --short --branch` showed that sibling checkout is dirty; no sibling edits were made.

## Claim inventory

### Supported locally

- README says rules live in `fafsa/kb.py`. This is supported: `fafsa/kb.py` defines `DependentFamily`, `IndependentFamily`, `CitedValue`, `SAITrace`, constants, `prove_sai()`, `_prove_sai_dependent()`, `_prove_sai_independent()`, `prove_sai_counterfactual()`, and `fmt_trace()`.
- README says every computation step has ED citations. Mostly supported structurally: `fafsa/kb.py` creates `CitedValue` steps with citation/formula strings, and `tests/test_fafsa_kb.py` checks that every step has `citation` and `formula`.
- README sample SAI `8,150` is reproducible only for a direct `DependentFamily(parent_agi=80000, family_size=4)` call. Local command output produced `sai= 8150`.
- README says the LLM is a language/fact extraction layer and cannot directly mutate the computation. Supported by structure: `demo.py` calls `backend.extract_facts()`, filters to `DependentFamily` fields, then uses `prove_sai()`.
- README says model swapping is controlled by `FAFSA_LLM`/`FAFSA_LLM_MODEL`. Supported in intent: `llm/base.py` resolves `FAFSA_LLM` and defaults models for Ollama/MLX.
- README says a Medicaid rule file exists. Supported only as a demo: `medicaid/kb.py` defines `Household`, FPL constants, `prove_medicaid()`, and `fmt_medicaid_trace()`.
- The repo has ED test data: `data/IDSA25OP-20240308.txt` exists and `wc -l` reports 103 lines.
- The repo has explicit validation tests: `tests/test_isir_validation.py` uses the bundled ISIR file and asserts zero failures and exactly 42 passing Formula A records.
- The counterfactual example works if run with repo root on `PYTHONPATH`: `PYTHONPATH=. python3 examples/counterfactual.py` produced an SAI sweep from parent AGI `$40,000` through `$130,000` in the captured output.

### Unsupported or contradicted locally

- README lines 31-33 and 53-57 claim `42/42` ED ISIR validation. Local validator output contradicts this: `passed=2`, `failed=40`, `all_passed=False`.
- README quickstart uses `python demo.py ...`; local shell has no `python` command. With `python3`, `demo.py` still fails before Ollama because `llm/base.py` eagerly imports Claude/OpenAI backends and `anthropic` is not installed.
- README line 46 says no API key is required. The default Ollama path should not require an API key, but it currently requires importable optional API client packages due to eager imports in `llm/base.py`. In this bare environment it fails on `anthropic` before reaching Ollama.
- README line 46 says the demo runs in under 30 seconds on CPU. This was not validated; the demo did not reach model execution locally.
- README line 68 says `uv pip install -e ".[mlx]"` supports MLX, but `uv run` failed in this isolated worktree because `pyproject.toml` depends on `tensor-logic @ file:../tensor-logic` and that relative path is absent here.
- README line 72 suggests `FAFSA_LLM_MODEL=mlx-community/Qwen2.5-1.5B-Instruct-4bit`, while `llm/base.py` defaults MLX to `mlx-community/Qwen3.5-2B-MLX-4bit` and `llm/mlx_backend.py` docstring says `mlx-community/Qwen2.5-0.5B-Instruct-4bit`. The MLX model docs are internally inconsistent.
- README line 88 says the derivation substrate is `tensor_logic/`. This worktree has no `tensor_logic/` directory. A sibling portfolio repo exists at `/Users/jwalinshah/projects/tensor/tensor-logic`, and commit `af625d0` removed an in-repo `tensor_logic/` package in favor of `pyproject.toml`'s sibling dependency.
- DEPLOY lines 25-35 describe a `fafsa-engine-sai` endpoint and `POST /sai`; `app.py` documents and implements `/extract`, `/compute`, `/health`, and `/`, not `/sai`.
- `app.py` line 13 says `/health` returns ED ISIR validation status, but `health()` returns only `{"status": "ok"}`.
- `app.py` imports `modal` at module import time, but `pyproject.toml` does not declare `modal`; local import failed with `ModuleNotFoundError: No module named 'modal'`.
- DEPLOY line 40 claims Claude Haiku 3.5 cost around `$0.001/query`; no local cost evidence exists, and the current Claude backend default is `claude-haiku-4-5-20251001`, not "Haiku 3.5".
- DEPLOY line 44 says `POST /sai` accepts a `backend` field. Current `app.py` does not expose `/sai`, and `extract()`/`compute()` do not read a `backend` field.
- README "Beyond FAFSA" lists tax, clinical, and visa eligibility as same-engine future domains. This repo has only a simple Medicaid demo and no local tax, clinical, or visa modules. The sibling `tensor-taxes` repo exists in `repos.json`, but that is separate from this repo.

## Evidence notes by file

- `README.md`: primary public claims live at lines 31-33 (`42/42` validation), 36-46 (quickstart/no-key/under-30-sec), 53-57 (verification meaning), 63-74 (backend/model swap), 76-88 (beyond FAFSA/tensor_logic substrate).
- `DEPLOY.md`: deployment claims live at lines 3, 25-35, 40, 44, and 48.
- `pyproject.toml`: core dependencies are `torch`, `requests`, and `tensor-logic @ file:../tensor-logic`; optional extras are `anthropic`, `openai`, and `mlx-lm`. There is no `modal` or `pytest` dependency.
- `app.py`: imports `modal` at line 21, adds `fastapi[standard]`, `anthropic`, `openai`, and `requests` to the Modal image, defines `/extract` and `/compute` handlers, and returns only `{"status": "ok"}` from health.
- `demo.py`: calls `get_backend()` before any computation and includes an interactive extracted-facts confirmation loop. The README's noninteractive transcript does not mention that prompt.
- `llm/base.py`: imports `ClaudeBackend` and `OpenAIBackend` before selecting the default Ollama branch, so optional dependencies affect the default backend.
- `llm/mlx_backend.py`: docstring default model conflicts with `llm/base.py` and README model examples.
- `fafsa/kb.py`: contains the deterministic rule implementation and citations, including the dependent-family SAI calculation and the `DependentFamily` defaults used by the README sample.
- `fafsa/isir.py`: parses the bundled fixed-width ISIR file, reconstructs Formula A families, and returns `ISIRReport(len(lines), passed, failed, skipped, failures)`. Note that `total` is the full line count, not Formula A count.
- `fafsa/validate.py`: returns a failed verification result when `report.failed > 0`, which is exactly what local execution observed.
- `tests/test_isir_validation.py`: asserts the strong ED claim; currently fails locally.
- `tests/test_llm_backends.py`: imports optional backend packages at module import time; currently cannot collect in a bare install missing `anthropic`.
- `medicaid/kb.py`: supports only a simplified Medicaid proof trace using FPL and 138 percent expansion threshold; it is not evidence for production Medicaid eligibility, tax, clinical, or visa support.
- `examples/counterfactual.py`: advertised usage fails by path unless the repo root is on `PYTHONPATH`.

## Risks and stale assumptions

1. Verification claim risk: The strongest public claim is false under local execution. If `README.md` is used externally, it may state that the engine is ED-validated when `verify()` currently says the engine output is not trustworthy.

2. Environment portability risk: The current package relies on `tensor-logic @ file:../tensor-logic`. That works only when the repo is checked out next to the sibling `tensor-logic` repo. It breaks isolated worktrees and fresh clones unless docs explain the sibling requirement or the dependency is packaged differently.

3. Optional dependency risk: `llm/base.py` makes optional API backends required for the default Ollama path by importing all backends eagerly. This undermines "No API key required" and makes full tests fail before mocks can run.

4. Deployment-doc drift: `DEPLOY.md` and `app.py` disagree on endpoint names, request shape, backend selection, and health semantics. A deploy user following the docs would call a nonexistent `/sai` endpoint.

5. Health/status risk: `app.py` advertises ED ISIR validation status but returns only liveness. This could create a false sense of safety in deployment monitoring.

6. Model-doc drift: README, `llm/base.py`, and `llm/mlx_backend.py` name different MLX default/example models. This makes reproducibility and support harder.

7. Example/script invocation risk: `examples/counterfactual.py` cannot be run exactly as documented from the repo root without `PYTHONPATH=.` or installation.

8. Future-domain claim risk: Medicaid exists only as a simplified demo, while tax/clinical/visa are not present in this repo. The docs should frame those as future possibilities, not supported capabilities.

## Sibling repo overlap

`/Users/jwalinshah/projects/agent-stack/repos.json` places this repo in the `tensor` group alongside:

- `tensor-experiments`
- `tensor-fafsa-engine`
- `tensor-quicksilver-zk`
- `tensor-taxes`
- `tensor-logic`

Relevant overlap and handoff risks:

- `tensor-logic` is real at `/Users/jwalinshah/projects/tensor/tensor-logic` and contains a `tensor_logic/` package plus docs and tests. This supports the README's conceptual substrate claim in the portfolio, but not as an in-repo path in this worktree.
- `tensor-taxes` exists as a separate sibling repo with `taxes/kb.py`, `taxes/tables.py`, `taxes/validate.py`, `llm/base.py`, and tests. README's "Tax compliance" claim should point to that sibling as a related project, not imply this repo currently supports tax.
- `tensor-experiments` contains `experiments/exp80_fafsa_kb.py`, `experiments/exp80_fafsa_wizard.py`, and `experiments/validate_exp80_isir.py`, so FAFSA logic appears to have experimental ancestry. Morning review can use those files for historical context, but product docs should not depend on experimental chat or hidden lineage.
- The sibling `tensor-logic` checkout has local dirty state. No sibling edits were made; this audit only read shallow structure/status for comparison.

## Validation command candidates

Required queue validation:

- `git status --short`
- Expected status after committing only this report: pass with no output.

Cheap docs/report validation:

- `git status --short docs/overnight/tensor-fafsa-engine-docs-claims.md`
- Expected while uncommitted: pass, shows only this report as untracked or modified.

Core SAI smoke:

- `python3 - <<'PY'\nfrom fafsa.kb import DependentFamily, prove_sai\nprint(prove_sai(DependentFamily(parent_agi=80000, family_size=4)).sai)\nPY`
- Observed status: pass; output `8150`.

ED validation claim proof:

- `python3 - <<'PY'\nfrom fafsa.isir import validate_isir_file\nreport = validate_isir_file()\nprint(report)\nprint(report.all_passed)\nPY`
- Observed status: command exits 0, but claim fails semantically; output includes `passed=2`, `failed=40`, `all_passed=False`.

Focused FAFSA tests:

- `PYTHONPATH=. python3 -m pytest tests/test_isir_validation.py tests/test_fafsa_kb.py -q`
- Observed status: fail; `5 failed, 9 passed`.

LLM backend tests:

- `PYTHONPATH=. python3 -m pytest tests/test_llm_backends.py -q`
- Observed status: fail during collection; `ModuleNotFoundError: No module named 'anthropic'`.

Package/env validation:

- `uv run pytest tests/test_isir_validation.py tests/test_fafsa_kb.py -q`
- Observed status: fail before tests; package metadata parse error for `tensor-logic @ file:../tensor-logic`.

Quickstart check:

- `python3 demo.py "My parents make $80k, family of 4"`
- Observed status: fail; `ModuleNotFoundError: No module named 'anthropic'`.

Modal app import check:

- `python3 - <<'PY'\nfrom app import health\nprint(health())\nPY`
- Observed status: fail; `ModuleNotFoundError: No module named 'modal'`.

Example script check:

- `python3 examples/counterfactual.py`
- Observed status: fail; `ModuleNotFoundError: No module named 'fafsa'`.
- Workaround candidate: `PYTHONPATH=. python3 examples/counterfactual.py`; observed pass.

## Next safe work

### Task 1: Reconcile ED validation claim before publishing docs

Acceptance criteria:

- `README.md` no longer claims `42/42` unless `validate_isir_file()` actually passes all Formula A records locally.
- `fafsa/validate.py` message and README language agree on pass/fail semantics.
- `tests/test_isir_validation.py` assertions reflect the intended validator contract.
- If the engine is supposed to pass all records, the parser/math fix is implemented before restoring the claim.

Validation:

- `PYTHONPATH=. python3 -m pytest tests/test_isir_validation.py tests/test_fafsa_kb.py -q`
- Expected after real fix: pass.
- Expected for docs-only correction without engine fix: tests may still fail, but README must not claim success.

### Task 2: Make the default no-key demo path actually no-key

Acceptance criteria:

- `FAFSA_LLM` default `ollama` can instantiate without installed `anthropic` or `openai`.
- Backend-specific imports happen only inside selected backend branches.
- `python3 demo.py "My parents make $80k, family of 4"` reaches Ollama or fails only on Ollama availability, not optional API client imports.
- README quickstart says `python3` or otherwise documents Python executable assumptions.

Validation:

- `python3 - <<'PY'\nfrom llm.base import get_backend\nb = get_backend()\nprint(type(b).__name__)\nPY`
- Expected after fix in a bare env: `OllamaBackend`.
- `PYTHONPATH=. python3 -m pytest tests/test_llm_backends.py -q`
- Expected after dependency/test isolation fix: pass without real network/API keys.

### Task 3: Repair packaging for isolated worktrees and fresh clones

Acceptance criteria:

- `uv run ...` works in the Goal Pack isolated worktree or docs explicitly state the required sibling checkout layout.
- The `tensor-logic` dependency is either published/resolved in a portable way or removed from this package if unused.
- README quickstart does not use `uv pip install -e .` without noting environment creation and sibling dependency requirements.

Validation:

- `uv run python - <<'PY'\nfrom fafsa.kb import DependentFamily, prove_sai\nprint(prove_sai(DependentFamily(parent_agi=80000, family_size=4)).sai)\nPY`
- Expected after fix: pass with `8150`.
- `uv run pytest tests/test_isir_validation.py tests/test_fafsa_kb.py -q`
- Expected after Task 1 plus packaging fix: pass.

### Task 4: Align Modal deploy docs with `app.py`

Acceptance criteria:

- `DEPLOY.md` lists the actual endpoints from `app.py`: `/`, `/extract`, `/compute`, `/health`.
- If a single `/sai` endpoint is desired, implement it and test the documented curl.
- `health()` either returns ED validation status or docs call it liveness-only.
- Modal dependency story is clear: local `modal serve app.py` requires `modal`, while Modal image installs runtime dependencies.

Validation:

- If local modal is available: `modal serve app.py` and curl documented endpoints.
- Minimum local check: `python3 - <<'PY'\nimport ast\nprint([n.name for n in ast.parse(open('app.py').read()).body if isinstance(n, ast.FunctionDef)])\nPY`
- Expected: documented endpoints/functions match code.

### Task 5: Clarify future-domain claims

Acceptance criteria:

- README distinguishes implemented domains (`fafsa`, simplified `medicaid`) from related sibling projects (`tensor-taxes`) and speculative future domains (clinical, visa).
- Medicaid docs state the current scope: simple FPL/138 percent proof demo, not state-complete eligibility.
- Any sibling reference points to a real path or repo name from `repos.json`.

Validation:

- `rg -n "Beyond FAFSA|Medicaid|Tax|Clinical|Visa|tensor_logic" README.md medicaid/kb.py pyproject.toml`
- Expected after docs fix: claims are explicit about implemented vs future support.

## Non-goals for this queue item

- No product code changes.
- No generated data changes.
- No external services, deployments, uploads, or secret access.
- No GitHub PR creation or push.
- No edits to sibling tensor repos.
- No attempt to repair FAFSA math or parser behavior in this docs-claims audit.
- No claim that ED validation is truly wrong upstream; this report only records local repo behavior and local evidence.

## Unknowns

- Whether the current `2/42` Formula A pass result is a recent regression, an expected artifact of an incomplete parser, or a local data/layout mismatch.
- Whether the authoritative product direction is to depend on sibling `tensor-logic` directly, vendor a stable subset, or publish it as an installable package.
- Whether `DEPLOY.md` reflects an older `/sai` implementation that was intentionally split into `/extract` and `/compute`.
- Whether the README's "Domingos (2025)" theoretical-foundation reference maps to a real local document, paper, or private note; no local citation file was found in this repo.
- Whether the "under 30 seconds on CPU" claim is accurate on intended hardware; local demo never reached model execution.
- Whether the Modal cost estimate is current; no external pricing check was performed because this queue item is local read-only.

## Handoff

Changed files intended by this queue item:

- `docs/overnight/tensor-fafsa-engine-docs-claims.md`

Required validation command:

- `git status --short`

Actual validation result:

- Command exited 0 and output `?? docs/`, because the report is present but could not be staged/committed from this sandbox.

Commit:

- Not created. Attempted `git add docs/overnight/tensor-fafsa-engine-docs-claims.md && git diff --cached --stat`, but Git failed with `Unable to create '/Users/jwalinshah/projects/tensor/fafsa-engine/.git/worktrees/tensor-fafsa-engine-docs-claims/index.lock': Operation not permitted`.
- Current HEAD remains `af625d0502548b76af5b7363366866592c504b82`.

PR:

- None. PR creation was out of scope for this Goal Pack item.

Blockers:

- Commit creation is blocked by sandbox permissions because the worktree's Git metadata is outside the writable root.
- Product blockers recorded above: ED validation claim currently fails locally; isolated packaging is broken by `../tensor-logic`; default quickstart fails on missing optional dependencies; deploy docs are out of sync with code.
