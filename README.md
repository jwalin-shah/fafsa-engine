# fafsa-engine

An experimental FAFSA SAI proof engine with LLM-backed fact extraction.

The current ED validation gate is red. Treat computed SAI values as
experimental until the Formula A discrepancies below are fixed.

```
$ python demo.py "My parents make $80k, family of 4"

============================================================
Query: My parents make $80k, family of 4
============================================================

[1/4] Extracting facts...
  parent_agi: 80000
  family_size: 4

[2/4] Computing SAI proof...
  total_income              $80,000   2024-25 SAI Guide, Formula A, Line 1
  income_protection        $29,040   Table A2, family 4
  available_income          $50,960
  ...
  student_aid_index          $8,150

[3/4] Generating explanation...

  With $80,000 in parental income for a family of four, your parents'
  available income after allowances is about $51,000. The formula
  applies a bracketed rate to that figure, producing a parental
  contribution of around $8,000. Your SAI is 8,150.

[4/4] Verifying...
❌ engine FAILED ED validation: 36/42 Formula A dependent ED records pass,
6 fail, 0 skipped (103 file lines scanned). Engine output is not trustworthy.
```

## Quick start

```bash
git clone https://github.com/your-org/fafsa-engine
cd fafsa-engine
uv pip install -e .
ollama pull qwen3.5:4b
python demo.py "My parents make $80k, family of 4"
```

Runs in under 30 seconds on CPU. No API key required.

The package metadata currently declares `tensor-logic @ file:../tensor-logic`.
That sibling repo exists in the local tensor workspace, but this repo's runtime
code does not import `tensor_logic` today. Fresh or isolated checkouts need the
sibling path in place for editable installs, or the dependency strategy needs to
be reconciled before this is portable.

## What you see

- **Facts extracted** — the LLM reads your query and pulls out income, family size, and other variables
- **Proof tree** — the engine computes every step deterministically, with a citation to the ED formula
- **Narration** — the LLM explains the result in plain English
- **Verification status** — the engine checks itself against the U.S. Department of Education's [official 2024-25 test ISIRs](https://github.com/usedgov/fafsa-test-isirs-2024-25). The bundled local gate is currently red: 36 of 42 Formula A dependent records pass, 6 fail, and 0 are skipped.

The engine is the deterministic calculation layer. The LLM is the language layer. Because the current ED validation gate is red, treat computed results as experimental until the Formula A discrepancies are fixed.

> **What "verified" means here:** `verify()` reports whether the local engine currently agrees with ED's published dependent-student test records. Today it returns unverified because the gate is red. When the gate is green, "verified" means component-level validation against ED's published test data; it still does *not* mean every input you provide has been individually checked against ED.

## Current ED validation status

Run:

```bash
python3 -m pytest tests/test_isir_validation.py tests/test_fafsa_kb.py -q
```

Current result: `34 passed`. These tests intentionally encode the red baseline
so the public claim stays honest: `36/42` Formula A dependent ED records pass,
`6/42` fail, and `0` are skipped.

Failure taxonomy from the current gate:

| Category | Count |
|---|---:|
| Engine SAI lower than ED target | 2 |
| Engine SAI at `-1500` floor while ED target is higher | 1 |
| Engine SAI higher than ED target | 4 |
| Absolute delta within 1,000 | 6 |
| Absolute delta from 1,001 to 10,000 | 0 |
| Absolute delta from 10,001 to 50,000 | 0 |

Aggregate mismatches across the 6 failing Formula A records are:

| ISIR output field | Mismatching records |
|---|---:|
| Student Aid Index (`sai`) | 6/6 |
| Parent payroll tax | 6/6 |
| Parent adjusted available income (`paai`) | 6/6 |
| Parent total allowances | 6/6 |
| Parent contribution (`pc`) | 6/6 |
| Student available income | 1/6 |
| Student total allowances | 1/6 |

The current red baseline now separates records by parent input source:

| Parent input source | Total | Passed | Failed |
|---|---:|---:|---:|
| Parent FTI fields parsed | 36 | 35 | 1 |
| No parent FTI fields parsed | 6 | 1 | 5 |

The six records without parsed parent FTI values are now reconstructed from
the ED-published generated parent total income and total allowance fields, which
clears the prior `eea` mismatch cluster. Parent manually entered asset fields
are parsed from the ED record-layout positions 1946-1966, clearing one
additional no-parent-FTI record. Parent FTI records now use the ED-published
generated parent total income as the Formula A line 3 reconstruction source,
while retaining raw parent FTI AGI as the earned-income proxy for payroll and
employment expense calculations. Student input fields now use corrected ISIR
offsets, and generated student total income is used as the Formula A line 22
reconstruction source. If a parent FTI spouse earning source is present while
the parent 1 FTI AGI field is blank, the parser no longer backfills parent 1
wages from generated parent total income. That clears one parent-FTI payroll
allowance mismatch without using ED output values as an oracle. The remaining
no-parent-FTI failure signature is
`parent_payroll_tax,parent_total_allowances,paai,pc,sai` for five records. In
the current diagnostics model, the parent total allowance delta equals the
parent payroll tax delta, which isolates the visible residual to the
generated-total-income wage proxy.
Negative half-dollar values now round away from zero, matching the ED test ISIR
record with student contribution from income `-1175` and moving the red gate to
35/42. Parent FTIM filing status now controls payroll jointness when present,
clearing one parent-FTI payroll-tax mismatch and moving the red gate to 36/42.
The remaining parent-FTI failure is
`parent_payroll_tax,parent_total_allowances,paai,pc,student_total_allowances,student_available_income,sai`,
one record.

That spread points to formula and/or fixed-width reconstruction drift, so this
slice does not claim ED validation is restored. Failing records now include
field-level diagnostics for the comparable ED intermediates (`ipa`, `eea`,
parent payroll tax, parent total allowances, `paai`, `pc`, student total
allowances, student available income, `sci`, `sca`, and `sai`), the parent input
source, and aggregate summaries by source and failure signature. The next
correction slice can target the five no-parent-FTI reconstruction records
separately from the remaining parent FTI record.

## How it works

Federal SAI guidelines are encoded as Python arithmetic with ED citations at every step. The proof engine runs your family's facts through those rules and returns a derivation trace — every intermediate value, every formula, every regulation reference. The LLM extracts your facts from plain English and narrates the result; it cannot touch the computation.

## Swap the LLM

| Backend | Command |
|---|---|
| Ollama (default) | `python demo.py "..."` |
| MLX (Apple Silicon, no daemon) | `uv pip install -e ".[mlx]"; FAFSA_LLM=mlx python demo.py "..."` |
| Claude | `FAFSA_LLM=claude python demo.py "..."` |
| OpenAI | `FAFSA_LLM=openai python demo.py "..."` |

Switch models: `FAFSA_LLM_MODEL=mlx-community/Qwen2.5-1.5B-Instruct-4bit python demo.py "..."`

The MLX backend runs the LM directly via Apple's `mlx_lm` — no separate daemon, no HTTP, uses unified GPU memory efficiently. Best choice for local dev on a Mac with constrained RAM.

## Beyond FAFSA

Future proof-engine domains should stay out of the product claim surface until
the FAFSA ED gate is green or the new domain has its own scoped validation. This
repo currently contains a small Medicaid demo module, not a validated Medicaid,
tax, clinical, or visa product.

## Engine

Rules live in `fafsa/kb.py`. The current derivation trace is Python arithmetic
plus cited values. `tensor-logic` is a real sibling repo and a declared path
dependency in `pyproject.toml`, but it is not imported by the current FAFSA
runtime code; treat it as a dependency strategy to reconcile, not evidence that
this checkout contains a `tensor_logic/` substrate.

## Disclaimer

Not financial advice. Not a replacement for the official [FAFSA4caster](https://studentaid.gov/aid-estimator/).

## License

MIT
