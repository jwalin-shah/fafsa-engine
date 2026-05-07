# fafsa-engine

An LLM will tell you your SAI. This will prove it.

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
❌ engine FAILED ED validation: 2/42 Formula A dependent ED records pass,
40 fail, 0 skipped (103 file lines scanned). Engine output is not trustworthy.
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

## What you see

- **Facts extracted** — the LLM reads your query and pulls out income, family size, and other variables
- **Proof tree** — the engine computes every step deterministically, with a citation to the ED formula
- **Narration** — the LLM explains the result in plain English
- **Verification status** — the engine checks itself against the U.S. Department of Education's [official 2024-25 test ISIRs](https://github.com/usedgov/fafsa-test-isirs-2024-25). The bundled local gate is currently red: 2 of 42 Formula A dependent records pass, 40 fail, and 0 are skipped.

The engine is the deterministic calculation layer. The LLM is the language layer. Because the current ED validation gate is red, treat computed results as experimental until the Formula A discrepancies are fixed.

> **What "verified" means here:** `verify()` reports whether the local engine currently agrees with ED's published dependent-student test records. Today it returns unverified because the gate is red. When the gate is green, "verified" means component-level validation against ED's published test data; it still does *not* mean every input you provide has been individually checked against ED.

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

Same engine, different rule file:
- Medicaid eligibility (income thresholds, asset limits)
- Tax compliance (bracket arithmetic, deduction rules)
- Clinical guidelines (dosage calculations, contraindication checks)
- Visa eligibility (income requirements, documentation rules)

The proof pattern is domain-agnostic. FAFSA is the first instance.

## Engine

Rules live in `fafsa/kb.py`. Derivation substrate is `tensor_logic/`. See Domingos (2025) for the theoretical foundation.

## Disclaimer

Not financial advice. Not a replacement for the official [FAFSA4caster](https://studentaid.gov/aid-estimator/).

## License

MIT
