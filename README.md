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
✅ engine validated against 42/42 ED test ISIRs (parent contribution
schedule, SAI summation, IPA table). This specific input was computed
by the same engine but was not independently checked against ED.
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
- **Verification tick** — the engine's components are validated against the U.S. Department of Education's [official 2024-25 test ISIRs](https://github.com/usedgov/fafsa-test-isirs-2024-25): all 42 dependent-student records pass the parent contribution schedule, SAI summation, and IPA table checks

The engine is the source of truth. The LLM is the language layer. Swap the model, the math doesn't change.

> **What "verified" means here:** The engine has passed component-level validation against ED's published test data. That means the parent contribution schedule, SAI summation, and IPA table have all been independently checked. It does *not* mean every input you provide has been individually checked against ED — only that the engine producing the result has been validated on ED's own cases.

## How it works

Federal SAI guidelines are encoded as Python arithmetic with ED citations at every step. The proof engine runs your family's facts through those rules and returns a derivation trace — every intermediate value, every formula, every regulation reference. The LLM extracts your facts from plain English and narrates the result; it cannot touch the computation.

## Swap the LLM

| Backend | Command |
|---|---|
| Ollama (default) | `python demo.py "..."` |
| Claude | `FAFSA_LLM=claude python demo.py "..."` |
| OpenAI | `FAFSA_LLM=openai python demo.py "..."` |

Switch models: `FAFSA_LLM_MODEL=gemma4:4b python demo.py "..."`

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
