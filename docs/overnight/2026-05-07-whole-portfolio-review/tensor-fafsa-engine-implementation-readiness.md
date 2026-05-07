# tensor-fafsa-engine Implementation-Readiness Review

Queue item: `tensor-fafsa-engine-implementation-readiness`  
Repo branch: `codex/goal-tensor-fafsa-engine-implementation-readiness`  
Review base HEAD: `af625d0502548b76af5b7363366866592c504b82`  
Review date: 2026-05-07

## Readiness Summary

This repo is not ready for broad implementation work until the deterministic
validation story is reconciled. The README and tests claim the engine passes
42/42 ED Formula A ISIR records, but the current local deterministic test run
reports only 2 passing Formula A records and 40 failures. The next executable
work should first restore or correct that validation contract, then make the
test/dependency/deploy paths reproducible in isolated worktrees.

No repo-local prior overnight reports or `runs/` outputs were present in this
worktree. No CI config was present in the tracked file list.

## Concrete File Evidence

1. `README.md:31-57` claims the engine is validated against 42/42 ED test ISIRs
   and carefully caveats that individual user inputs are not independently
   checked.
2. `tests/test_isir_validation.py:33-41` encodes the same 42/42 validation
   contract with assertions that `report.failed == 0`, `report.passed == 42`,
   and `report.skipped == 0`.
3. `data/IDSA25OP-20240308.txt` contains 103 lines, while `fafsa/isir.py:170`
   returns `ISIRReport(len(lines), passed, failed, skipped, failures)`, so
   `report.total` currently means all file lines rather than the number of
   dependent Formula A records tested.
4. `fafsa/isir.py:125-170` filters dependent records with `line[187:188] ==
   "A"`, reconstructs inputs from fixed positions, and compares only final SAI.
   The current run found 42 dependent records but only 2 matched ED output.
5. `fafsa/kb.py:23-59` defines the dependent Formula A input surface, and
   `fafsa/kb.py:187-235` computes the traced dependent SAI. This is the core
   surface any validation fix will need to protect.
6. `fafsa/kb.py:62-84` and `fafsa/kb.py:238-260` define and start implementing
   independent Formula B/C support, but the validation suite is currently
   anchored to dependent Formula A only.
7. `pyproject.toml:5-14` declares runtime deps plus optional `claude`,
   `openai`, and `mlx` extras, but there is no test/dev extra. A full test run
   fails during collection because `tests/test_llm_backends.py:8-10` imports
   optional backend modules whose third-party packages are not installed.
8. `pyproject.toml:8` depends on `tensor-logic @ file:../tensor-logic`, but
   `../tensor-logic` is missing in this isolated worktree. `README.md:88` also
   references a `tensor_logic/` derivation substrate that is not present in this
   repo.
9. `pyproject.toml:20-21` packages only `fafsa` and `llm`, while
   `medicaid/kb.py:1-12` is tracked and imports `fafsa.kb` trace structures.
   That makes the "Beyond FAFSA" path visible in source but not installable as
   a package.
10. `app.py:21-35` imports Modal and builds a Modal image with FastAPI,
    Anthropic, OpenAI, and Requests installed inside the image. Neither `modal`
    nor `fastapi` is locked in `uv.lock`; `DEPLOY.md:7-10` tells operators to
    manually `uv pip install modal`.
11. `DEPLOY.md:42-44` documents `POST /sai` with a `backend` field, but
    `app.py:438-482` exposes separate `/extract` and `/compute` endpoints and
    resolves the backend from environment through `llm.base.get_backend()`.
12. `app.py:9-13` describes `/health` as liveness plus ED ISIR validation
    status, but `app.py:484-488` returns only `{"status": "ok"}`.
13. `app.py:297-323` renders LLM-provided `citation` and `reasoning` with
    `innerHTML`. If this UI is deployed publicly, extracted text should be
    escaped or rendered through text nodes before users can safely trust it.
14. `demo.py:37-64` has a deterministic human confirmation loop for extracted
    facts before constructing `DependentFamily`; the web path in `app.py:327-333`
    gathers values directly from inputs and sends them to `/compute`.

## Validation Commands Run

- `python -m pytest tests`
  - Result: failed before test start because `python` is not available in this
    worktree shell (`command not found`).
- `python3 -m pytest tests`
  - Result: failed during collection. `tests/test_llm_backends.py` imports
    `llm.claude_backend`, which imports `anthropic`; `anthropic` is not
    installed.
- `python3 -m pytest tests/test_isir_validation.py tests/test_fafsa_kb.py`
  - Result: 9 passed, 5 failed.
  - Key failure: `validate_isir_file()` returned `ISIRReport(total=103,
    passed=2, failed=40, skipped=0, ...)`, contradicting the expected 42/42
    ED validation contract.
- Required queue validation: `git status --short`

## Risks And Blockers

- The ED validation claim is currently stale or broken. This blocks safe feature
  work because user-facing verification text would be false for the current
  checkout.
- Full local test execution is not reproducible from the base environment:
  `python` is absent, optional LLM dependencies are imported during test
  collection, and there is no test/dev extra.
- Fresh dependency sync is likely brittle in isolated queue worktrees because
  the local `../tensor-logic` dependency is missing.
- Deployment docs and Modal endpoints disagree, so implementation agents cannot
  safely add API work without first choosing the public contract.
- The public UI currently trusts LLM-provided strings for HTML construction.
- There is no tracked CI workflow or local validation script that defines the
  minimum pre-merge bar.

## Implementation-Ready Follow-Up Tasks

### 1. Restore the ED ISIR validation contract

Owned files: `fafsa/kb.py`, `fafsa/isir.py`, `tests/test_isir_validation.py`,
`tests/test_fafsa_kb.py`.

Acceptance criteria:
- `validate_isir_file()` reports 42 dependent Formula A records checked, 42
  passed, 0 failed, and 0 skipped, or the README/test wording is deliberately
  changed to the real supported scope.
- `ISIRReport.total` is made unambiguous, either by counting tested Formula A
  records or by adding a separate field for raw file line count.
- `verify()` does not return a green verification result unless the ED
  validation report has no failures.

Smallest useful validation:
- `python3 -m pytest tests/test_isir_validation.py tests/test_fafsa_kb.py -q`

### 2. Make the test environment reproducible without live LLM deps

Owned files: `pyproject.toml`, `uv.lock`, `tests/test_llm_backends.py`,
`README.md`.

Acceptance criteria:
- A clean checkout can install a documented test/dev extra.
- `tests/test_llm_backends.py` collects without `anthropic`, `openai`, or
  `mlx_lm` installed, using lazy imports, mocks, or explicit skips.
- The documented test command matches the package metadata.

Smallest useful validation:
- `python3 -m pytest tests/test_llm_backends.py -q`
- `python3 -m pytest tests -q`

### 3. Reconcile the package/install contract

Owned files: `pyproject.toml`, `uv.lock`, `README.md`, and any repo-local docs
that describe `tensor-logic` or packaged modules.

Acceptance criteria:
- The repo can be installed in an isolated worktree without an undocumented
  sibling checkout, or the sibling dependency is documented as a required
  workspace prerequisite.
- The README no longer references a missing `tensor_logic/` path.
- Tracked packages intended for use, including any Medicaid demo, are either
  included in package metadata and tested or clearly marked out of scope.

Smallest useful validation:
- `uv sync --locked --extra test`
- `uv run python -c "import fafsa; from fafsa.kb import DependentFamily, prove_sai"`

### 4. Align Modal deployment docs, API routes, and health semantics

Owned files: `app.py`, `DEPLOY.md`, `pyproject.toml`, `uv.lock`,
`tests/test_app_contract.py`.

Acceptance criteria:
- `DEPLOY.md` documents the actual routes exposed by `app.py`, or `app.py`
  implements the documented `/sai` contract.
- Backend selection is either accepted from the documented request payload or
  explicitly documented as environment-based only.
- `/health` returns ED validation status if the docs continue to claim it.
- Modal/FastAPI deploy dependencies are represented in package metadata or a
  clearly named deploy extra.

Smallest useful validation:
- `python3 -m py_compile app.py`
- `python3 -m pytest tests/test_app_contract.py -q`

### 5. Harden the web fact-review path before public demo work

Owned files: `app.py`, `tests/test_app_contract.py` or
`tests/test_app_html.py`.

Acceptance criteria:
- LLM-provided `citation`, `reasoning`, and field names are escaped or rendered
  through text nodes instead of string-concatenated `innerHTML`.
- Browser-submitted facts are validated against `DependentFamily` fields and
  reject empty, `NaN`, or non-integer values before computation.
- The web flow keeps the deterministic fact-confirmation invariant present in
  `demo.py`.

Smallest useful validation:
- `python3 -m pytest tests/test_app_contract.py tests/test_app_html.py -q`

## Suggested Launch Order

1. Fix ED ISIR validation first; it is the trust anchor for every product claim.
2. Make tests installable and collection-safe.
3. Repair install/package metadata so future agents can work from isolated
   worktrees.
4. Align deploy/API docs and add contract tests.
5. Harden the browser path before exposing public demo traffic.
