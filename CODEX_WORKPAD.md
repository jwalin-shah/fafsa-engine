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

## FAFSA-K Formula A Diagnostic Slice - 2026-05-13

Branch: `codex/fafsa-parent-wage-source-slice`

Scope: one narrow, non-circular diagnostic slice against the remaining Formula
A red gate, focused on parent allowance failures and the unresolved
no-parent-FTI wage proxy.

Diagnosis:

- Current merged baseline remains `34/42` Formula A records passing and `8/42`
  failing.
- The five no-parent-FTI failures all use
  `parent_wage_proxy_source=parent_total_income_proxy`.
- For those five records in the current diagnostics model, the parent total
  allowance delta exactly equals the parent payroll tax delta; income protection
  allowance and employment expense allowance are already aligned, so the
  visible residual is isolated to payroll tax computed from the
  generated-total-income wage proxy.

Change:

- `fafsa/isir.py` now includes `parent_payroll_tax` in field-level intermediate
  diagnostics.
- `tests/test_isir_validation.py` asserts that no-parent-FTI failures are
  isolated to the payroll proxy rather than an opaque total-allowance mismatch.
- `README.md` updates the red-baseline diagnostic signatures.

Validation:

```bash
python3 -m pytest tests/test_isir_validation.py -q
```

Result: passed, `21 passed`.

```bash
python3 -m pytest -q
```

Result: passed, `49 passed`.

```bash
git diff --check
```

Result: passed.

Explicit gate check:

```bash
python3 - <<'PY'
from fafsa.isir import validate_isir_file
report = validate_isir_file('data/IDSA25OP-20240308.txt')
print(f'Formula A gate: {report.passed}/{report.dependent_records} passed, {report.failed} failed, {report.skipped} skipped, all_passed={report.all_passed}')
print('diagnostic_summary=', report.diagnostic_summary)
print('failure_signature_summary=', report.failure_signature_summary)
print('diagnostic_summary_by_source=', report.diagnostic_summary_by_source)
PY
```

Result: `34/42` passed, `8` failed, `0` skipped, `all_passed=False`.
The no-parent-FTI signature is now
`parent_payroll_tax,parent_total_allowances,paai,pc,sai` for five records.

Residual risk:

- This is a diagnostic slice, not a reconstruction correction. It does not
  change SAI outputs or improve the pass count.
- The remaining no-parent-FTI records still lack a real parent earned-income
  source in the parsed layout, so using generated parent total income as wages
  remains a proxy and should not be back-solved from ED generated payroll
  outputs.

## FAFSA-L Formula A Negative Rounding Slice - 2026-05-13

Branch: `codex/fafsa-negative-rounding-slice`

Scope: one narrow formula correction for ED rounding of negative half-dollar
values.

Diagnosis:

- Baseline after `#22` was `34/42` Formula A records passing and `8/42`
  failing.
- ISIR line 65 had only `sci,sai` mismatches: student available income
  `-2349`, ED student contribution from income `-1175`, and engine result
  `-1174`.
- The formula path used `math.floor(x + 0.5)`, which rounds `-1174.5` toward
  zero instead of away from zero.

Change:

- `fafsa.kb._ed_round()` now rounds negative half-dollar values away from zero.
- `fafsa.validate._ed_round_local()` now matches the engine helper used by
  deterministic random-family test fixture generation.
- `tests/test_fafsa_kb.py` covers positive and negative half-dollar rounding.
- `tests/test_isir_validation.py` and `README.md` update the red baseline to
  `35/42` passing and `7/42` failing.

Validation:

```bash
python3 -m pytest tests/test_fafsa_kb.py tests/test_isir_validation.py -q
```

Result: passed, `32 passed`.

Explicit gate check:

```bash
python3 - <<'PY'
from fafsa.isir import validate_isir_file
report = validate_isir_file('data/IDSA25OP-20240308.txt')
print(f'Formula A gate: {report.passed}/{report.dependent_records} passed, {report.failed} failed, {report.skipped} skipped, all_passed={report.all_passed}')
print('diagnostic_summary=', report.diagnostic_summary)
print('failure_signature_summary=', report.failure_signature_summary)
PY
```

Result: `35/42` passed, `7` failed, `0` skipped, `all_passed=False`.

Residual risk:

- Product correctness is still not complete. The remaining failures are
  parent payroll/allowance propagation issues, and the no-parent-FTI records
  still should not be fixed by back-solving ED generated payroll outputs.

## FAFSA-M Formula A Parent Filing Status Slice - 2026-05-13

Branch: `codex/fafsa-parent-filing-status-slice`

Scope: one narrow source-field reconstruction for parent FTI payroll tax.

Diagnosis:

- Baseline after `#23` was `35/42` Formula A records passing and `7/42`
  failing.
- ISIR line 86 had parent earned income `155895`, no spouse earned income,
  parent FTIM filing status `4`, ED parent payroll tax `11374`, and engine
  parent payroll tax `11925`.
- The engine used `num_parents == 2` as the payroll jointness signal, which
  selected the joint OASDI cap even when the real FTIM filing status was not
  married filing jointly.

Change:

- `DependentFamily` now carries optional `parent_filing_status`.
- ISIR reconstruction parses parent FTIM filing status from the real source
  field immediately before parent FTIM AGI.
- Formula A parent payroll tax uses `parent_filing_status == 2` for jointness
  when that source field is present, and preserves the old `num_parents == 2`
  fallback otherwise.
- `tests/test_isir_validation.py` covers line 86 and updates the red baseline
  to `36/42` passing and `6/42` failing.
- `tests/test_fafsa_kb.py` covers the missing-filing-status fallback so
  existing keyword callers keep the old `num_parents == 2` behavior.

Validation:

```bash
python3 -m pytest tests/test_isir_validation.py -q
```

Result: passed, `22 passed`.

```bash
python3 -m pytest -q
```

Result: passed, `52 passed`.

```bash
git diff --check
```

Result: passed.

Explicit gate check:

```bash
python3 - <<'PY'
from fafsa.isir import validate_isir_file
report = validate_isir_file('data/IDSA25OP-20240308.txt')
print(f'Formula A gate: {report.passed}/{report.dependent_records} passed, {report.failed} failed, {report.skipped} skipped, all_passed={report.all_passed}')
print('diagnostic_summary=', report.diagnostic_summary)
print('failure_signature_summary=', report.failure_signature_summary)
PY
```

Result: `36/42` passed, `6` failed, `0` skipped, `all_passed=False`.

Residual risk:

- Product correctness is still not complete. The five no-parent-FTI failures
  still use generated parent total income as the wage proxy, and the remaining
  parent-FTI failure has parent payroll/allowance drift plus downstream student
  allowance drift.

## FAFSA-N Formula A Remaining Failure Diagnostics - 2026-05-13

Branch: `codex/fafsa-remaining-failure-diagnostics`

Scope: one diagnostic-only slice against the remaining six Formula A failures.

Diagnosis:

- Baseline after `#24` remains red at `36/42` Formula A records passing and
  `6/42` failing.
- Five no-parent-FTI records still fail through the generated parent total
  income wage proxy.
- The single remaining parent-FTI record has parent payroll/allowance drift
  that makes PAAI negative in the engine, which then creates a downstream
  parents-negative-PAAI allowance mismatch on the student side.

Change:

- `fafsa/isir.py` now maps the ED parent available income output field.
- `fafsa/isir.py` now maps the ED parents negative PAAI allowance output field.
- `tests/test_isir_validation.py` asserts that the remaining parent-FTI
  failure exposes the parent available income and parents-negative-PAAI
  propagation instead of hiding it behind total allowance fields.
- `README.md` updates the current red-baseline failure signatures.

Validation:

```bash
python3 -m pytest tests/test_isir_validation.py -q
```

Result: passed, `23 passed`.

```bash
python3 -m pytest -q
```

Result: passed, `53 passed`.

```bash
git diff --check
```

Result: passed.

Explicit gate check:

```bash
python3 - <<'PY'
from fafsa.isir import validate_isir_file
report = validate_isir_file('data/IDSA25OP-20240308.txt')
print(f'Formula A gate: {report.passed}/{report.dependent_records} passed, {report.failed} failed, {report.skipped} skipped, all_passed={report.all_passed}')
print('diagnostic_summary=', report.diagnostic_summary)
print('failure_signature_summary=', report.failure_signature_summary)
PY
```

Result: `36/42` passed, `6` failed, `0` skipped, `all_passed=False`.

Residual risk:

- This does not change Formula A outputs. It narrows the next correctness work
  but still leaves product correctness blocked.
- No-parent-FTI payroll should still not be fixed by back-solving ED generated
  payroll outputs.

## FAFSA-O Formula A Manual Parent Source Slice - 2026-05-13

Branch: `codex/fafsa-no-parent-fti-source-audit`

Scope: one bounded source-field reconstruction slice for Formula A records with
no parsed parent FTI fields, focused on replacing the generated-total-income
wage proxy with manual wage, tax, and filing-status sources.

Evidence:

- Official ISIR layout workbook downloaded from FSA Partners:
  `/tmp/fafsa-spec/isir-layout.xlsx`.
- Parent manual source fields used by this slice:
  - Filing status: position 1802.
  - Income earned from work: positions 1803-1813.
  - Adjusted gross income: positions 1869-1878.
  - Income tax paid: positions 1879-1887.
  - Spouse/partner income earned from work: positions 2295-2305.
  - Spouse/partner adjusted gross income: positions 2361-2370.
  - Spouse/partner income tax paid: positions 2371-2379.

Diagnosis:

- Baseline after `#25` was `36/42` Formula A records passing and `6/42`
  failing.
- The five no-parent-FTI failures all had self-reported parent manual income,
  tax, and filing-status source fields available in the official layout.
- One affected record used filing status code `3`, so the Medicare threshold
  needed the married-filing-separately threshold rather than the ordinary
  single threshold.

Change:

- `fafsa/isir.py` now parses parent and spouse/partner manual earned income,
  AGI, and tax fields, plus parent manual filing status, for records without
  parent FTI. The parsed AGI fields are asserted in tests, but the current
  Formula A line 3 reconstruction still uses the earlier generated parent total
  income source documented by prior slices.
- `fafsa/kb.py` now applies the married-filing-separately Medicare threshold
  when parent filing status is code `3`, with parent and spouse caps applied
  separately when both wage fields are present.
- Tests now assert representative no-parent-FTI records pass from manual source
  fields rather than generated parent total income wage proxy behavior.
- README public validation claims now encode the narrowed red gate:
  `41/42` passing, `1/42` failing.

Validation:

```bash
python3 -m pytest tests/test_isir_validation.py -q
```

Result: passed, `23 passed`.

```bash
python3 -m pytest tests/test_fafsa_kb.py tests/test_isir_validation.py -q
```

Result: passed, `37 passed`.

Explicit gate check:

```bash
python3 - <<'PY'
from fafsa.isir import validate_isir_file
report = validate_isir_file('data/IDSA25OP-20240308.txt')
print(f'{report.passed}/{report.dependent_records} failed={report.failed} all={report.all_passed}')
print('diagnostic_summary=', report.diagnostic_summary)
print('source_summary=', report.source_summary)
print('failure_signature_summary=', report.failure_signature_summary)
PY
```

Result: `41/42` passed, `1` failed, `0` skipped, `all_passed=False`.
The no-parent-FTI source bucket is now `6` passed, `0` failed.

Residual risk:

- Product correctness is still not complete. One parent-FTI record remains red
  with parent payroll/allowance drift and downstream negative-PAAI/student
  allowance propagation.
- The no-parent-FTI pass count still depends on the pre-existing generated
  parent total income source for Formula A line 3. This slice only removes the
  generated-total-income wage proxy from payroll reconstruction.
