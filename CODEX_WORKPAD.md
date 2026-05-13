# FAFSA Engine Workpad

## Portfolio Readiness Validation - 2026-05-12

Scope: make the existing validation suite runnable in a base development
environment without requiring optional hosted LLM SDKs.

Initial failure:

```bash
python3 -m unittest discover -s tests
```

Result: failed before running tests because `tests/test_llm_backends.py`
imported `ClaudeBackend`, which imported the optional `anthropic` package at
module import time.

Diagnosis:

- The repo uses pytest-style tests, so `unittest discover` is not the correct
  validation command.
- Optional LLM adapters were imported eagerly, which made the base test suite
  depend on optional provider packages.

Changes:

- `llm.base.get_backend()` now imports only the selected backend.
- `llm.claude_backend` and `llm.openai_backend` now create provider clients
  through lazy factory functions with explicit install guidance.
- `tests/test_llm_backends.py` mocks the local adapter factory seams instead of
  patching provider SDK modules.

Validation run:

```bash
python3 -m py_compile llm/base.py llm/claude_backend.py llm/openai_backend.py tests/test_llm_backends.py
```

Result: passed.

```bash
python3 -m pytest
```

Result: passed, `31 tests`.

```bash
git diff --check
```

Result: passed.

Disposition:

- FAFSA Engine has a green base validation command: `python3 -m pytest`.
- Optional provider SDK behavior is now isolated behind adapter boundaries.

## FAFSA-H Formula A Slice - 2026-05-13

Branch: `codex/fafsa-next-red-gate-slice-3`

Scope: one narrow, non-circular ED Formula A correctness slice against the
remaining red gate.

Baseline reproduced:

```bash
python3 -m pytest tests/test_isir_validation.py -q
```

Result before changes: `17 passed`, with validation at `33/42` Formula A
records passing, `9/42` failing, and diagnostics
`sai=9, parent_total_allowances=8, paai=8, pc=8,
student_available_income=1, student_total_allowances=1, sci=1`.

Diagnosis:

- Failing line 72 had parent spouse FTI earnings (`51068`) and spouse tax, but
  blank parent 1 FTI AGI.
- `reconstruct_family()` was still backfilling parent 1 wages from generated
  parent total income, so payroll tax was computed on both generated total
  income and spouse earnings.
- The source-field correction is to use explicit parent earned-income sources
  when any are present, and only use generated parent total income as a wage
  proxy when no parent earned-income source exists.

Change:

- `fafsa/isir.py` no longer backfills parent 1 wages from generated parent
  total income when spouse FTI earning/tax evidence is present.
- `tests/test_isir_validation.py` adds a regression test for the spouse-only
  FTI earnings record.
- README and verification-count tests now encode the new red baseline:
  `34/42` pass, `8/42` fail.

Validation:

```bash
python3 -m pytest tests/test_isir_validation.py -q
```

Result after change: `18 passed`.

Updated diagnostics: `sai=8, parent_total_allowances=7, paai=7, pc=7,
student_available_income=1, student_total_allowances=1, sci=1`.

Residual risk:

- The gate remains red. Remaining parent allowance/PAAI/PC mismatches still
  require source-field or formula evidence and should not be fixed by
  back-solving from generated ED outputs.

## PR Packaging - 2026-05-13

Branch: `codex/fafsa-isir-validation-contract`

Rebased onto `origin/main` before packaging because `main` already contained
the first optional-SDK import isolation and README ED-validation warning PRs.
The packaged delta preserves those warnings and keeps the no-optional-SDK
import guard tests.

Validation:

```bash
python3 -m pytest tests/test_llm_backends.py -q
```

Result: passed, `18 passed in 0.23s`.

```bash
git diff --check
```

Result: passed.

Blocker:

- ED correctness remains red/blocked. This slice only packages the validation
  contract and LLM adapter boundary; it does not restore agreement with ED ISIR
  dependent-student records.
