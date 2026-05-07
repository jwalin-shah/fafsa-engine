# tensor-fafsa-engine risk and validation review

Date: 2026-05-07
Branch: `codex/goal-tensor-fafsa-engine-risk-and-validation-review`
HEAD at review start: `af625d0502548b76af5b7363366866592c504b82`
Scope: repo-local read-only review plus this report. No product code, tracker, PR, push, deploy, or external service changes.

## Summary

This repo is not implementation-ready for new feature work until the validation chain is repaired. The highest-risk finding is that the central ED ISIR correctness gate currently fails: direct validation reports `2` passing Formula A records and `40` failing Formula A records, while the README and tests expect `42/42`.

The next work should prioritize making the existing correctness claims true again, then making installation/test collection deterministic. Deployment and LLM work should wait until those gates are green.

## Evidence reviewed

- `llm-tldr tree .`
- `rg --files -uu -g '!.git/**' -g '!uv.lock'`
- `rtk read README.md`
- `rtk read DEPLOY.md`
- `rtk read pyproject.toml`
- `rtk read fafsa/isir.py`
- `rtk read fafsa/validate.py`
- `rtk read fafsa/kb.py`
- `rtk read app.py`
- `rtk read tests/test_isir_validation.py`
- `rtk read tests/test_fafsa_kb.py`
- `rtk read tests/test_llm_backends.py`
- `rtk read llm/base.py`
- `rtk read llm/claude_backend.py`
- `rtk read llm/openai_backend.py`
- `rtk read llm/ollama_backend.py`
- `rtk read llm/mlx_backend.py`
- `git status --short`
- `git log --oneline -10`

No previous repo-local overnight outputs were present: `docs/` and `runs/` did not exist before this report.

## Validation commands run

Required queue validation before report:

```bash
git status --short
```

Result: passed with no output before this report was added.

Additional validation probes:

```bash
rtk pytest tests
```

Result: failed with `Pytest: No tests collected`.

```bash
uv run pytest tests
```

Result: failed before tests because package metadata could not be generated:
`relative path without a working directory: ../tensor-logic`.

```bash
python3 -m pytest tests
```

Result: failed during collection because `tests/test_llm_backends.py` imports `llm/claude_backend.py`, which imports optional dependency `anthropic`; `anthropic` is not installed in the base environment.

```bash
python3 -m pytest tests/test_isir_validation.py tests/test_fafsa_kb.py
```

Result: failed with `5 failed, 9 passed`. The failures show `ISIRReport(total=103, passed=2, failed=40, skipped=0, ...)`, and `verify()` returns `engine FAILED ED validation: 2/103 ED test ISIRs pass, 40 fail`.

```bash
python3 -c "from fafsa.isir import validate_isir_file; r=validate_isir_file(); print(r); print(r.failures[:3])"
```

Result: confirmed `ISIRReport(total=103, passed=2, failed=40, skipped=0, ...)`. First failures include:

- line 42: target `6096`, actual `8312`, parent AGI `75000`, parent tax `6205`, student AGI `13500`, family size `2`
- line 43: target `4514`, actual `-960`, parent AGI `59234`, parent tax `5089`, student AGI `0`, family size `4`
- line 48: target `1169`, actual `3548`, parent AGI `55000`, parent tax `3921`, student AGI `11980`, family size `2`

## File-path observations

1. `README.md` claims the engine is validated against `42/42` ED test ISIRs and shows that as the public verification tick, but local validation now reports `2/103` pass and `40` Formula A failures.

2. `data/IDSA25OP-20240308.txt` is present and has `103` lines. The validation code filters Formula A records, so the README/test denominator should be based on dependent records, not all file lines.

3. `fafsa/isir.py` returns `ISIRReport(len(lines), passed, failed, skipped, failures)`, so `total` is currently the full file line count instead of the number of dependent Formula A records evaluated.

4. `fafsa/isir.py` reconstructs ED records from hard-coded fixed-width positions and then calls `prove_sai()`. The first three observed failures are broad enough that this is likely a formula/reconstruction drift issue, not a single rounding edge case.

5. `fafsa/validate.py` caches `validate_isir_file()` and surfaces failed validation through `verify()`. This is good fail-closed behavior, but it currently means any demo verification result should say the engine is not trustworthy.

6. `tests/test_isir_validation.py` is the right core correctness gate: it checks no failed records, exactly `42` passed Formula A records, zero skipped records, and `report.all_passed`.

7. `tests/test_fafsa_kb.py` checks the public verification message contains `42/42`; this catches stale denominator/message behavior but now fails because the underlying validation is red.

8. `pyproject.toml` declares `tensor-logic @ file:../tensor-logic`, but `uv run pytest tests` fails metadata generation with `relative path without a working directory: ../tensor-logic`. This blocks the documented `uv` workflow.

9. `uv.lock` lists `fafsa-engine` dependencies as `requests` and `torch`, and optional extras for `anthropic`, `openai`, and `mlx-lm`; it does not reflect the `tensor-logic` path dependency from `pyproject.toml`.

10. `tests/test_llm_backends.py` imports `ClaudeBackend` and `OpenAIBackend` at module import time. Because `llm/claude_backend.py` imports `anthropic` at top level, the full test suite cannot collect in a base environment without optional extras.

11. `app.py` imports `modal`, defines `/extract`, `/compute`, and `/health`, and its docstring says `/health` includes ED ISIR validation status. The actual `health()` handler returns only `{"status": "ok"}`.

12. `DEPLOY.md` documents `POST /sai` with `{"query": "...", "backend": "claude" | "openai"}`, but `app.py` exposes separate `/extract` and `/compute` endpoints and does not accept a per-request `backend` field.

13. `pyproject.toml` packages only `fafsa` and `llm`; `medicaid/` has a package file and demo knowledge base but is not included in packaging.

14. `fafsa/kb.py` implements `IndependentFamily` and a Formula B/C path, but the ED ground-truth test file and current correctness tests focus on dependent Formula A records only. Formula B/C should not be treated as validated.

15. `llm/base.py` defaults Ollama to `qwen3.5:4b`, and `README.md` tells users to pull the same model. There is no local smoke test proving the default model name is available or that the demo path works without a live Ollama daemon.

16. There is no `.github/workflows/*`, `Makefile`, tox config, or pytest tool configuration. The repo has tests, but no committed CI entry point that enforces them.

## Risks and blockers

- Correctness blocker: ED ISIR validation is failing on 40 of 42 Formula A records. New product work should stop until this is fixed or explicitly scoped away from FAFSA correctness claims.

- Trust blocker: Public docs still claim `42/42` validation, while `verify()` currently reports failure. This is a stale safety claim with user-facing implications.

- Install blocker: `uv run pytest tests` cannot build project metadata because of the relative `tensor-logic` path dependency.

- Test-collection blocker: full-suite `python3 -m pytest tests` cannot collect without optional `anthropic`; optional LLM deps are not isolated from base tests.

- Deployment risk: Modal docs and app endpoints disagree, and `/health` does not expose validation status despite the app docstring saying it does.

- Coverage risk: Formula B/C and Medicaid demo code exist but are not covered by ground-truth fixtures comparable to the dependent FAFSA Formula A path.

- Process risk: no CI workflow means the broken ED validation and optional-dependency collection failure can sit unnoticed after commits.

## Implementation-ready follow-up tasks

### 1. Restore ED ISIR correctness gate

Owned files:

- `fafsa/kb.py`
- `fafsa/isir.py`
- `fafsa/validate.py`
- `tests/test_isir_validation.py`
- `tests/test_fafsa_kb.py`

Acceptance criteria:

- `validate_isir_file()` evaluates exactly the Formula A records it intends to validate.
- The ED validation report passes all 42 Formula A records with `failed == 0` and `skipped == 0`.
- `verify()` returns `verified=True` only when the ED gate is green.
- Public verification message denominator is intentionally defined and matches tests, preferably `42/42` Formula A records rather than full file lines.

Smallest useful validation:

```bash
python3 -m pytest tests/test_isir_validation.py tests/test_fafsa_kb.py
python3 -c "from fafsa.isir import validate_isir_file; r=validate_isir_file(); assert (r.passed, r.failed, r.skipped) == (42, 0, 0); print(r)"
```

### 2. Repair project install and lock metadata

Owned files:

- `pyproject.toml`
- `uv.lock`
- `README.md`

Acceptance criteria:

- The repo can be installed and tested with `uv run` from a fresh checkout/worktree.
- The `tensor-logic` relationship is made explicit and reproducible: either a valid workspace/path dependency exists, or the unused dependency is removed.
- `uv.lock` matches `pyproject.toml`.
- README quick-start commands match the actual install path.

Smallest useful validation:

```bash
uv run python -c "import fafsa.kb; import fafsa.isir; print('ok')"
uv run pytest tests/test_isir_validation.py -q
```

### 3. Make optional LLM backend tests collect in a base environment

Owned files:

- `tests/test_llm_backends.py`
- `llm/base.py`
- `llm/claude_backend.py`
- `llm/openai_backend.py`
- `llm/mlx_backend.py`
- `pyproject.toml`

Acceptance criteria:

- Base test collection does not fail when `anthropic`, `openai`, or `mlx_lm` are not installed.
- Optional backend tests either use `pytest.importorskip()` or are split behind extras-specific commands.
- Backend factory tests continue to prove `FAFSA_LLM` selection behavior.

Smallest useful validation:

```bash
python3 -m pytest tests/test_llm_backends.py -q
python3 -m pytest tests -q
```

### 4. Align Modal API behavior, deployment docs, and health checks

Owned files:

- `app.py`
- `DEPLOY.md`
- `pyproject.toml`
- `tests/test_app.py`

Acceptance criteria:

- `DEPLOY.md` documents the endpoints that `app.py` actually exposes, or `app.py` implements the documented `/sai` endpoint.
- `/health` returns at least liveness plus ED validation summary, including pass/fail counts.
- Modal/FastAPI dependencies are declared in project metadata or deployment docs clearly state they are deployment-only.
- App tests cover request validation and endpoint shape without requiring a live Modal deploy or real LLM credentials.

Smallest useful validation:

```bash
python3 -m pytest tests/test_app.py -q
python3 -m pytest tests/test_isir_validation.py tests/test_fafsa_kb.py -q
```

### 5. Add committed CI and validation entry points

Owned files:

- `.github/workflows/ci.yml`
- `pyproject.toml`
- `README.md`

Acceptance criteria:

- CI runs on pull requests against supported Python versions.
- CI installs the repo deterministically, including whatever extras are required for tests.
- CI runs the ED validation tests and LLM backend unit tests.
- README names the same local validation command CI runs.

Smallest useful validation:

```bash
python3 -m pytest tests/test_isir_validation.py tests/test_fafsa_kb.py
python3 -m pytest tests/test_llm_backends.py
```

## Handoff

Changed files:

- `docs/overnight/2026-05-07-whole-portfolio-review/tensor-fafsa-engine-risk-and-validation-review.md`

Current blockers:

- ED validation is red: `2` Formula A records pass and `40` fail.
- `uv run pytest tests` is blocked by `pyproject.toml` metadata parsing for `tensor-logic @ file:../tensor-logic`.
- Full-suite `python3 -m pytest tests` collection is blocked by missing optional `anthropic`.
- No PR was created; pushes and external tracker updates are out of scope for this queue item.

Final queue validation:

```bash
git status --short
```

Result: passed and reported the intended untracked report directory: `?? docs/`.
