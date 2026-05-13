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

## FAFSA-I Formula A Slice - 2026-05-13

Branch: `codex/fafsa-next-red-gate-slice-4`

Scope: one narrow, non-circular ED Formula A correctness slice against the
remaining red gate.

Baseline reproduced:

```bash
python3 -m pytest tests/test_isir_validation.py -q
```

Result before changes: `18 passed`, with validation at `34/42` Formula A
records passing, `8/42` failing, and diagnostics
`sai=8, parent_total_allowances=7, paai=7, pc=7,
student_available_income=1, student_total_allowances=1, sci=1`.

Diagnosis:

- The official 2024-25 ISIR record layout identifies parent annual child
  support received at positions `1939-1945`, immediately before parent cash at
  `1946-1952`.
- `DependentFamily` already includes `parent_child_support_received` in parent
  net worth, but `reconstruct_family()` parsed only parent cash, investments,
  and business/farm net worth.
- Failing line 91 has source parent child support of `30000` and parent cash of
  `26500`; the missing source field explained the asset-side portion of the
  PAAI mismatch without using generated ED outputs.

Change:

- `fafsa/isir.py` now parses parent child support from the ISIR source field and
  passes it into `DependentFamily`.
- `tests/test_isir_validation.py` adds a regression test for the affected
  source-field layout and resulting parent net worth.

Validation:

```bash
python3 -m pytest tests/test_isir_validation.py -q
```

Result after change: `19 passed`.

```bash
python3 -m pytest -q
```

Result: `47 passed`.

```bash
git diff --check
```

Result: passed.

Updated diagnostics: still `34/42` pass, `8/42` fail, `all_passed=False`.
Aggregate diagnostic counts are unchanged:
`sai=8, parent_total_allowances=7, paai=7, pc=7,
student_available_income=1, student_total_allowances=1, sci=1`.

Line 91 residual after the source-field fix:
`parent_total_allowances delta=412`, `paai delta=-412`, `pc delta=-194`,
`sai delta=-194`. The remaining mismatch appears tied to the unresolved
no-parent-FTI payroll/wage proxy and should not be fixed by back-solving from
generated ED output fields.

Gemini review:

- `gemini` was installed, but `timeout 90 gemini -p ...` did not return a
  review before the bound expired.

## FAFSA-J Formula A Slice - 2026-05-13

Branch: `codex/fafsa-next-red-gate-slice-5`

Scope: one more narrow, non-circular ED Formula A correctness slice against the
remaining red gate, focused on no-parent-FTI wage/payroll evidence.

Baseline reproduced:

```bash
python3 -m pytest tests/test_isir_validation.py -q
```

Result before changes: `19 passed`, with validation still at `34/42` Formula A
records passing, `8/42` failing, and diagnostics
`sai=8, parent_total_allowances=7, paai=7, pc=7,
student_available_income=1, student_total_allowances=1, sci=1`.

Diagnosis:

- The official 2024-25 ISIR record layout distinguishes parent FTIM AGI at
  positions `7328-7337` from parent total income earned at `7342-7352`.
- The local parser had been naming the earned-income slice as `p_agi_fti`.
  Runtime behavior mostly survived because generated parent total income
  replaces Formula A line 3, but the diagnostic surface hid which source was
  being used for wage/payroll reconstruction.
- All 5 no-parent-FTI failures now explicitly show
  `parent_wage_proxy_source=parent_total_income_proxy`, with parent earned
  income equal to generated parent total income and no spouse earned-income
  source. This exposes the unresolved missing source without back-solving from
  ED generated payroll/allowance outputs.

Change:

- `fafsa/isir.py` now maps parent FTIM AGI, exemptions, dependents, earned
  income, tax paid, and IRA deductible fields to their official layout slices.
- Parent earned-income reconstruction now reads `p_earned_fti` explicitly.
- Failing-record diagnostics now include `parent_wage_proxy_source`,
  `parent_earned_income_p1`, and `parent_earned_income_p2`.
- `tests/test_isir_validation.py` adds coverage that parent FTIM AGI and earned
  income are distinct source fields and that no-parent-FTI failures use the
  generated-total-income wage proxy.

Validation:

```bash
python3 -m pytest tests/test_isir_validation.py -q
```

Result: `20 passed`.

```bash
python3 -m pytest -q
```

Result: `48 passed`.

```bash
git diff --check
```

Result: passed.

Updated diagnostics: unchanged red gate, `34/42` pass, `8/42` fail,
`all_passed=False`; aggregate counts remain
`sai=8, parent_total_allowances=7, paai=7, pc=7,
student_available_income=1, student_total_allowances=1, sci=1`.

Gemini review:

- `gemini` was installed, but the bounded run could not complete usefully:
  unauthorized local tool calls were blocked, then the model quota was
  exhausted before a review was returned.
