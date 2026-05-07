# tensor-fafsa-engine 30-minute extension action plan

Date: 2026-05-07
Branch: `codex/goal-tensor-fafsa-engine-30min-action-plan`
Head inspected: `af625d0502548b76af5b7363366866592c504b82`

## Executive summary

This repo should not move to demo/deploy work until the ED validation claim is reconciled. The README and tests say the FAFSA engine passes `42/42` official dependent-student ISIR records, but the current local validation reports `2` passing and `40` failing Formula A records. The failure is not cosmetic: `fafsa.validate.verify()` returns `verified=False` and says the engine output is not trustworthy.

The next implementation queue should prioritize the ISIR parser/reconstruction and formula agreement work, then clean up packaging, docs, and deployment contracts so future agents can run the same validation path from a clean checkout.

## Previous overnight report reconciliation

No previous overnight report was present in this repo.

Evidence:

- `llm-tldr search "overnight" .` returned `[]`.
- `rg --files` listed only source, tests, data, README, DEPLOY, pyproject, and lock files before this report.
- `docs/`, `runs/`, and `items/` were missing before creating this report.

Because there is no prior repo-local report to reconcile, nothing has already been covered in an overnight handoff. The work that should move into the implementation queue is the five follow-up tasks below, in priority order.

## Concrete file-path observations

1. `README.md:31` and `README.md:53` claim the engine is validated against `42/42` ED test ISIRs. Current local validation contradicts this with `passed=2 failed=40`.

2. `tests/test_isir_validation.py:33` asserts `report.failed == 0`, and `tests/test_isir_validation.py:37` asserts `report.passed == 42`. The test is valuable and currently fails, so it is the right primary red/green target.

3. `fafsa/isir.py:17` defines fixed-width field positions, and `fafsa/isir.py:72` reconstructs `DependentFamily` from those positions. The reconstruction only populates a subset of `DependentFamily` fields, so the first debugging pass should compare every failing ED row's target intermediate values to the reconstructed inputs.

4. `fafsa/isir.py:105` sets `p1_wages = p_agi`, and `fafsa/isir.py:107` falls back from missing student wages to student AGI. These heuristics can materially change payroll tax and employment-expense allowances, making them prime suspects for broad ISIR disagreement.

5. `fafsa/isir.py:170` returns `ISIRReport(len(lines), passed, failed, skipped, failures)`. `len(lines)` is `103`, while the file has `42` Formula A records. This makes verification messages say `2/103` even though only dependent records are being validated.

6. `fafsa/validate.py:130` uses the cached ISIR report and `fafsa/validate.py:132` correctly marks traces unverified when failures exist. The verification layer is surfacing the problem; the broken layer is likely ISIR reconstruction, formula implementation, or stale docs/test expectations.

7. `fafsa/kb.py:187` implements dependent Formula A, and `fafsa/kb.py:238` implements independent Formula B/C. The ED validation and tests only cover Formula A, while README positioning implies broader "proof engine" confidence.

8. `fafsa/kb.py:150` defines `_apa()` as always `0`, and `fafsa/kb.py:210` hardcodes parent asset protection allowance to `0`. If this is intentionally 2024-25-specific, it should be locked behind year-specific tests or documented as such.

9. `app.py:13` advertises `/health` as "liveness + ED ISIR validation status", but `app.py:486` returns only `{"status": "ok"}`. A deployed service could look healthy while the validation gate is failing.

10. `DEPLOY.md:44` says `POST /sai` accepts a `backend` field, but `app.py:456` defines `compute(payload)` and `app.py:474` chooses the backend only from environment via `get_backend()`. Either the endpoint contract or implementation is stale.

11. `pyproject.toml:8` depends on `tensor-logic @ file:../tensor-logic`, but `../tensor-logic` is missing in this worktree. `README.md:88` also says the derivation substrate is `tensor_logic/`, yet this repo has no such package directory and `fafsa/kb.py` does not import it.

12. `pyproject.toml:5` includes runtime deps `torch`, `requests`, and the local tensor dependency, but not `modal`, `fastapi`, `pytest`, `anthropic`, or `openai`. `app.py:21` imports `modal` at module import time, and `DEPLOY.md:8` separately instructs users to install Modal.

13. `llm/base.py:19` defines default local models for Ollama and MLX only. `llm/claude_backend.py:16` and `llm/openai_backend.py:16` hardcode provider defaults, and tests mock these clients rather than proving real provider availability.

14. `examples/counterfactual.py:6` imports `fafsa.kb`, but running the script directly under `uv run --no-project python examples/counterfactual.py` cannot see the repo root on `sys.path`. It works with `PYTHONPATH=.` or after a working package install.

15. `demo.py:37` enters an interactive confirmation loop after LLM extraction. That is useful for users, but it blocks deterministic noninteractive demo validation unless a CLI flag or facts-input mode is added.

16. `medicaid/kb.py:12` reuses `SAITrace` for Medicaid and `medicaid/kb.py:59` notes it is hijacking the SAI field as an eligibility score. This supports the "proof pattern" story, but it is not tested and should remain demo-scoped until there is a domain-specific trace type or tests.

## Validation surface and results

Required queue validation:

```bash
git status --short
```

Result before report writing: passed with no output. Final run after report writing exited `0` and showed `?? docs/`, which is the requested new report directory.

Additional health probes run during audit:

```bash
uv run --no-project python - <<'PY'
from fafsa.isir import validate_isir_file
r = validate_isir_file()
print(f"total={r.total} passed={r.passed} failed={r.failed} skipped={r.skipped} all_passed={r.all_passed}")
print(r.failures[:3])
PY
```

Result: `total=103 passed=2 failed=40 skipped=0 all_passed=False`. First failures included line 42 target `6096` actual `8312`, line 43 target `4514` actual `-960`, and line 48 target `1169` actual `3548`.

```bash
uv run --no-project --with pytest python -m pytest tests/test_isir_validation.py -q
```

Result: failed, `3 failed, 1 passed`. Failures are the ED agreement assertion, the `42` pass-count assertion, and `report.all_passed`.

```bash
uv run --no-project --with pytest python -m pytest tests/test_fafsa_kb.py -q
```

Result: failed, `2 failed, 8 passed`. The failing tests are both verification-message tests that expect ED validation to pass.

```bash
uv run --no-project --with pytest --with requests --with anthropic --with openai python -m pytest tests/test_llm_backends.py -q
```

Result: passed, `16 passed in 2.65s`. This validates mocked backend parsing/factory behavior, not live providers.

```bash
uv run --no-project python -m compileall fafsa llm medicaid tests demo.py app.py examples/counterfactual.py
```

Result: passed. Syntax/import compilation is healthy.

```bash
UV_CACHE_DIR=/tmp/uv-cache-fafsa uv run python -m pytest tests
```

Result: blocked in this sandbox by network access while resolving `setuptools>=61.0` from PyPI. A previous cached attempt also showed package metadata trouble around `tensor-logic @ file:../tensor-logic`. This means clean project-level validation is not reliable in the current worktree.

```bash
PYTHONPATH=. UV_CACHE_DIR=/tmp/uv-cache-fafsa uv run --no-project python examples/counterfactual.py
```

Result: passed as a smoke with `PYTHONPATH=.`; first rows showed SAI rising from `-1500` at `$40,000` and `$50,000` parent AGI to `315` at `$60,000`.

## Known blockers

- ED validation is failing. Until `tests/test_isir_validation.py` passes, the public `42/42` verification claim should be treated as false.
- Clean project install/test is blocked by dependency setup. The current worktree lacks `../tensor-logic`, and sandboxed `uv run` cannot fetch build dependencies from PyPI.
- Live LLM, Modal deploy, and provider-cost checks require external services or credentials and are outside this read-only audit scope.
- No prior overnight report exists in-repo, so there is no earlier action-plan artifact to reuse or close out.

## Implementation-ready follow-up tasks

### 1. Restore ED ISIR validation agreement

Owned files:

- `fafsa/isir.py`
- `fafsa/kb.py`
- `tests/test_isir_validation.py`
- `data/IDSA25OP-20240308.txt`

Acceptance criteria:

- `validate_isir_file()` counts Formula A records separately from total file lines.
- All 42 Formula A records pass, or every remaining mismatch is explained by a documented, test-backed fixture limitation.
- Failure output includes enough reconstructed inputs and intermediate values to diagnose future regressions.
- `uv run --no-project --with pytest python -m pytest tests/test_isir_validation.py -q` passes.

Suggested validation command:

```bash
uv run --no-project --with pytest python -m pytest tests/test_isir_validation.py -q
```

### 2. Make verification claims generated from real validation

Owned files:

- `fafsa/validate.py`
- `tests/test_fafsa_kb.py`
- `README.md`

Acceptance criteria:

- `verify()` reports a denominator based on the number of validated Formula A records, not total file rows.
- README demo output matches a real local command after validation is fixed.
- No docs or tests claim `42/42` unless the validation command actually passes.
- `uv run --no-project --with pytest python -m pytest tests/test_fafsa_kb.py tests/test_isir_validation.py -q` passes.

Suggested validation command:

```bash
uv run --no-project --with pytest python -m pytest tests/test_fafsa_kb.py tests/test_isir_validation.py -q
```

### 3. Repair clean project install and dependency contract

Owned files:

- `pyproject.toml`
- `uv.lock`
- `README.md`
- `DEPLOY.md`

Acceptance criteria:

- A fresh checkout can run the documented test command without relying on a sibling repo that is not declared as part of the checkout contract.
- If `tensor-logic` is still required, the repo documents the workspace layout and validation command that includes it. If it is stale, remove it.
- Test-only dependencies are available through an explicit dev extra or documented `uv run --with ...` command.
- `uv run python -m pytest tests/test_isir_validation.py -q` reaches pytest rather than failing package metadata resolution.

Suggested validation command:

```bash
UV_CACHE_DIR=/tmp/uv-cache-fafsa uv run python -m pytest tests/test_isir_validation.py -q
```

### 4. Align Modal/API health and deploy docs with implementation

Owned files:

- `app.py`
- `DEPLOY.md`
- `tests/test_app_contract.py` (new)

Acceptance criteria:

- `/health` returns ED validation status, including passed, failed, skipped, and all_passed.
- The documented POST endpoint name matches the function Modal actually exposes.
- Either `backend` in the request payload is honored or the DEPLOY docs stop claiming it is accepted.
- Contract tests cover `_trace_to_dict`, health payload construction, and fact filtering without requiring Modal credentials.

Suggested validation command:

```bash
uv run --no-project --with pytest --with modal --with fastapi python -m pytest tests/test_app_contract.py -q
```

### 5. Add deterministic local smoke paths for demos and examples

Owned files:

- `demo.py`
- `examples/counterfactual.py`
- `tests/test_cli_smoke.py` (new)
- `README.md`

Acceptance criteria:

- `demo.py` has a noninteractive mode that accepts explicit facts or a mocked/no-LLM backend for CI.
- `examples/counterfactual.py` runs from a clean project command without needing ad hoc `PYTHONPATH=.`.
- README quick-start uses commands that work from a fresh checkout after the dependency contract is fixed.
- The smoke tests avoid external LLM services and prove deterministic compute, formatting, and verification behavior.

Suggested validation command:

```bash
uv run --no-project --with pytest python -m pytest tests/test_cli_smoke.py -q
```

## Recommended implementation queue order

1. Task 1: Restore ED ISIR validation agreement.
2. Task 2: Make verification claims generated from real validation.
3. Task 3: Repair clean project install and dependency contract.
4. Task 4: Align Modal/API health and deploy docs with implementation.
5. Task 5: Add deterministic local smoke paths for demos and examples.

Do not invest in public deploys or LLM UX polish before Tasks 1 and 2 pass. The product premise is deterministic, trusted computation; the current failing ED validation is the highest-leverage and highest-risk issue.
