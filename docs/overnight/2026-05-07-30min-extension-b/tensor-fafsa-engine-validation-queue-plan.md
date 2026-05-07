# tensor-fafsa-engine validation and queue-readiness audit

Queue item: `tensor-fafsa-engine-validation-queue-plan`
Branch: `codex/goal-tensor-fafsa-engine-validation-queue-plan`
Audit date: 2026-05-07
HEAD at audit start: `af625d0`

## Scope

This is a second-pass validation and queue-readiness audit for the local
`tensor-fafsa-engine` worktree. I did not edit product code, create a PR, push,
deploy, update trackers, or call external services. I found no repo-local
first-pass extension report, `runs/*/result.json`, or `runs/*/handoff.md` to
reconcile, so this report records the current validation reality from the
checkout itself.

## Commands run

```bash
llm-tldr tree .
git status --short
git rev-parse --short HEAD
rg --files --hidden -g '!.git'
rtk read pyproject.toml
rtk read README.md
rtk read DEPLOY.md
llm-tldr search "pytest|test|uv run|streamlit|OPENAI|ANTHROPIC|OLLAMA|MLX|FAFSA|Student Aid Index|SAI" .
python3 --version
command -v uv
command -v pytest
test -d ../tensor-logic && printf 'present\n' || printf 'missing\n'
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_llm_backends.py -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_isir_validation.py -q -p no:cacheprovider
python3 - <<'PY'
from pathlib import Path
p=Path('data/IDSA25OP-20240308.txt')
lines=p.read_text().splitlines()
print('lines', len(lines))
print('first_len', len(lines[0]) if lines else 0)
print('formula_A', sum(1 for l in lines if len(l)>=7700 and l[187:188]=='A'))
PY
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from fafsa.isir import validate_isir_file
r=validate_isir_file()
print(r)
print('failures_first_5', r.failures[:5])
PY
```

Validation command required by the queue item:

```bash
git status --short
```

Initial result: exit 0, no output. Final result should show only this report as
the intentional worktree change unless another process edits the tree.

## Validation reality

The local pytest suite is not green. The strongest blocker is the ED ISIR claim:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q -p no:cacheprovider
```

Result: exit 1, `25 passed, 5 failed in 1.20s`.

Failures:

- `tests/test_fafsa_kb.py::test_verify_returns_verified_when_engine_passes_isir_validation`
- `tests/test_fafsa_kb.py::test_verify_message_mentions_isir_count`
- `tests/test_isir_validation.py::test_engine_passes_all_isir_records`
- `tests/test_isir_validation.py::test_isir_count_is_42`
- `tests/test_isir_validation.py::test_report_all_passed_property`

The bundled ED file has 103 records and 42 Formula A records. Current
`validate_isir_file()` reports `passed=2`, `failed=40`, `skipped=0`. Because
`ISIRReport.total` is set to the full file length, the user-facing verification
message says `2/103 ED test ISIRs pass`, which is doubly misleading: only 42
Formula A records were considered, and only 2 currently match.

Focused validation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_isir_validation.py -q -p no:cacheprovider
```

Result: exit 1, `1 passed, 3 failed`.

Optional-backend collection is environment-dependent:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_llm_backends.py -q -p no:cacheprovider
```

Result: exit 2, collection fails on `ModuleNotFoundError: No module named
'anthropic'`. The standalone `pytest` executable is a Homebrew Python 3.14
script and did collect those tests, which means local validation can vary by
runner Python.

## File-path observations

1. `README.md:31` and `README.md:53` claim the engine is validated against
   `42/42` ED test ISIRs, but the current suite reports only 2 matching Formula
   A records and 40 mismatches.
2. `README.md:41` and `README.md:43` document `uv pip install -e .` and
   `python demo.py ...`; this host has no `python` executable, only
   `python3`, and the editable install is likely blocked by a missing sibling
   dependency.
3. `README.md:88` says the derivation substrate is `tensor_logic/`, while
   `pyproject.toml:8` depends on `tensor-logic @ file:../tensor-logic`; the
   isolated worktree does not contain `../tensor-logic`.
4. `pyproject.toml:5-9` declares runtime dependencies but no dev/test extra
   containing `pytest`; `tests/test_llm_backends.py` still imports optional
   providers at collection time.
5. `pyproject.toml:20-21` packages only `fafsa` and `llm`; `medicaid/kb.py` is
   present but not packaged, despite README positioning the pattern as
   extensible beyond FAFSA.
6. `tests/test_isir_validation.py:33-45` is the right smoke gate for the ED
   claim, but it is currently red and should block any release or queue item
   that relies on the README verification tick.
7. `tests/test_fafsa_kb.py:59-78` asserts `verify()` reports a successful ED
   validation and includes `42/42`; those assertions fail because the cached
   ISIR report is red.
8. `fafsa/isir.py:129-170` returns `ISIRReport(len(lines), passed, failed,
   skipped, failures)`, so the report denominator is all 103 file records, not
   the 42 dependent Formula A records processed by `_is_dependent_record()`.
9. `fafsa/isir.py:72-122` reconstructs `DependentFamily` from a narrow subset of
   fixed-width fields and backfills family structure from IPA/EEA; the first
   failures show large target/actual differences, so this is the highest-value
   place to instrument before changing formula code.
10. `fafsa/validate.py:105-110` caches the ISIR report once per process; after
   fixes, tests should include a way to avoid stale cached results when
   validating alternate files.
11. `app.py:9-13` documents endpoints `/extract`, `/compute`, and `/health`;
   `DEPLOY.md:25-35` documents a `/sai` URL and a `{"query": ...}` payload that
   is not implemented by the Modal functions.
12. `app.py:484-488` returns only `{"status": "ok"}` from health, while the
   module docstring at `app.py:13` says health includes ED ISIR validation
   status.
13. `demo.py:46-62` requires an interactive confirmation loop, so the README
   quick-start command is not an automation-friendly validation command.
14. `.github/workflows/*`, `docs/overnight/*`, `runs/*/result.json`, and
   `runs/*/handoff.md` are absent from this checkout, so there is no CI gate or
   first-pass runner artifact to compare against.

## Known blockers

- ED validation is currently false: 2 Formula A records pass and 40 fail.
- The README's `42/42` validation claim is not supported by local tests.
- `python` is not available on this host, but docs and examples use it.
- `../tensor-logic` is missing, so the declared editable dependency is not
  queue-ready in this isolated worktree.
- `anthropic`, `mlx_lm`, and `modal` are not installed in the local Python 3.12
  environment; optional backend and deployment validation need either extras or
  collection-time skips.
- No CI workflow exists to preserve the validation command once fixed.
- Deploy docs mention `/sai`, but the app implements `/extract`, `/compute`, and
  `/health`.

## Safe implementation tasks

1. Restore ED ISIR validation.
   Owned files: `fafsa/isir.py`, `fafsa/kb.py`, `tests/test_isir_validation.py`,
   `tests/test_fafsa_kb.py`.
   Acceptance criteria: all 42 Formula A records pass; `validate_isir_file()`
   reports a dependent-record denominator; `verify()` says `42/42` only when
   `failed == 0`; first failure diagnostics identify the source fields needed
   for debugging.
   Smallest validation:
   ```bash
   PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q -p no:cacheprovider tests/test_isir_validation.py tests/test_fafsa_kb.py
   ```

2. Make test execution reproducible from the project environment.
   Owned files: `pyproject.toml`, `uv.lock`, `tests/test_llm_backends.py`.
   Acceptance criteria: project metadata defines a test/dev extra; optional
   provider tests skip cleanly when extras are absent or install through the
   documented command; `python3 -m pytest` and the chosen `uv run` command use
   the same dependency set.
   Smallest validation:
   ```bash
   uv run --extra claude --extra openai pytest -q -p no:cacheprovider tests/test_llm_backends.py
   ```

3. Fix package/worktree dependency assumptions.
   Owned files: `pyproject.toml`, `README.md`, `uv.lock`.
   Acceptance criteria: a fresh isolated checkout can install without requiring
   an undocumented sibling path, or the sibling requirement is explicitly
   documented as a workspace prerequisite; packaged modules match the repo's
   supported surface.
   Smallest validation:
   ```bash
   uv pip install -e . --dry-run
   ```

4. Align Modal app and deployment docs.
   Owned files: `app.py`, `DEPLOY.md`, optional `tests/test_app_contract.py`.
   Acceptance criteria: docs list only implemented endpoints, payload examples
   match the actual route handlers, and `/health` either reports ED validation
   status or no longer claims to.
   Smallest validation:
   ```bash
   PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider tests/test_app_contract.py
   ```

5. Add a minimal CI gate after local validation is green.
   Owned files: `.github/workflows/validation.yml`, `pyproject.toml`,
   `README.md`.
   Acceptance criteria: CI installs the project with the documented test extra,
   runs the ED ISIR validation tests and backend unit tests, does not require
   secrets or external services, and fails on the current 2/42 ED mismatch until
   task 1 is complete.
   Smallest validation:
   ```bash
   git status --short
   ```

## Handoff

Changed files:

- `docs/overnight/2026-05-07-30min-extension-b/tensor-fafsa-engine-validation-queue-plan.md`

Commit SHA: `af625d0` at audit start; no local commit was created.
PR URL: none; PR creation was out of scope.
Validation command: `git status --short`
Validation result: exit 0 before report creation with no output. After report
creation, exit 0 with:

```text
?? docs/
```

That untracked directory contains only this report.

Blockers for implementation queue readiness:

- Fix or explicitly downgrade the ED `42/42` claim before shipping.
- Decide how this repo should be installed in isolated worktrees without
  `../tensor-logic`.
- Pick one canonical validation entrypoint, preferably a `uv run ... pytest`
  command that includes optional test dependencies or skips them deterministically.
