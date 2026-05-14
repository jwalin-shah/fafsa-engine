# fafsa-engine

An experimental FAFSA SAI proof engine with LLM-backed fact extraction.

The bundled ED Formula A validation gate is green for the official 2024-25
dependent-student test ISIR records. Treat broader product claims as scoped to
that validation set unless they have their own evidence.

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
✅ engine validated against 42/42 Formula A dependent ED records (parent
final SAI output agreement). This specific input was computed by the same
engine but was not independently checked against ED.
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
- **Verification status** — the engine checks itself against the U.S. Department of Education's [official 2024-25 test ISIRs](https://github.com/usedgov/fafsa-test-isirs-2024-25). The bundled local Formula A gate is currently green: 42 of 42 dependent records pass, 0 fail, and 0 are skipped.

The engine is the deterministic calculation layer. The LLM is the language layer. The validation claim is limited to the bundled Formula A dependent-student ED test records.

> **What "verified" means here:** `verify()` reports whether the local engine's final SAI outputs currently agree with ED's published dependent-student test records. "Verified" means final-output validation against ED's published Formula A test data; it still does *not* mean every input you provide has been individually checked against ED or that every comparable intermediate field matches ED.

## Local validation gate

Before PR handoff, run the same local validation gate used by CI:

```bash
python3 -m pytest -q
```

Current result: `56 passed`. This is the authoritative local command for the
repo: it runs the ED ISIR gate, core formula/verification tests, and mocked LLM
backend tests without requiring provider secrets or optional hosted SDKs. The
suite intentionally encodes the green baseline so the public claim stays
honest: `42/42` Formula A dependent ED records pass, `0/42` fail, and `0` are
skipped.

The current green baseline separates records by parent input source:

| Parent input source | Total | Passed | Failed |
|---|---:|---:|---:|
| Parent FTI fields parsed | 36 | 36 | 0 |
| No parent FTI fields parsed | 6 | 6 | 0 |

The ED ISIR file under `data/` is a tracked validation fixture, not a runtime
output directory. Generated validation logs, local run manifests, tool caches,
and scratch outputs should stay in ignored local paths such as `.local/`,
`runs/`, `outputs/`, `artifacts/`, or `logs/`.

Records without parsed parent FTI values now use self-reported parent and
spouse manual source fields from the official 2024-25 ISIR layout for income
earned from work, income tax paid, and filing status. The relevant source
positions are parent manual fields 1802-1887 and spouse/partner manual fields
2294-2379. Filing status code `3` now applies the
married-filing-separately Medicare threshold for parent payroll tax, with caps
applied per earner when both parent and spouse wages exist. This clears the
prior five no-parent-FTI payroll/allowance failures without using ED generated
payroll tax as the wage source. These records still rely on the earlier
documented generated parent total income source for Formula A line 3.

Earlier slices also parse parent manually entered asset fields from the ED
record-layout positions 1946-1966, use parent FTI generated parent total income
as the Formula A line 3 reconstruction source while retaining raw earned income
for payroll and employment expense calculations, correct student ISIR offsets,
use generated student total income as Formula A line 22, avoid backfilling
parent 1 wages from generated parent total income when spouse-only FTI earnings
exist, round negative half-dollar values away from zero, and use parent FTIM
filing status for payroll jointness when present.

The final Formula A correction applies the official source-precedence rule that
self-reported income information replaces IRS FTI at field level when both are
populated. In the last parent-FTI record, parent-spouse self-reported earned
income and tax replace the corresponding parent-spouse FTI fields for payroll
and tax reconstruction, clearing the final SAI mismatch without back-solving
from generated ED output fields.

Failure records still include field-level diagnostics for comparable ED
intermediates (`ipa`, `eea`, parent payroll tax, parent total allowances,
parent available income, `paai`, `pc`, parents negative PAAI allowance, student
total allowances, student available income, `sci`, `sca`, and `sai`), the
parent input source, and aggregate summaries by source and failure signature.

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
