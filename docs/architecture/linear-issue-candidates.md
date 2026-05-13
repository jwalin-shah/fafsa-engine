# Architecture Issue Candidates - 2026-05-12

Do not implement yet. These are planning candidates from a read-only architecture review.

## 1. Create a Formula Engine Module

Files: `fafsa/kb.py`, `tests/test_fafsa_kb.py`

Acceptance criteria:
- `prove_sai()` remains the public Interface.
- ED tables, line calculations, and trace construction are separately testable.
- Current red ED validation baseline is preserved unless the issue explicitly owns a correctness fix.

Validation: `python -m pytest tests/test_fafsa_kb.py tests/test_isir_validation.py -v`

## 2. Split ISIR validation into parsing, reconstruction, and comparison

Files: `fafsa/isir.py`, `fafsa/validate.py`, `tests/test_isir_validation.py`

Acceptance criteria:
- Fixed-width parsing has direct tests.
- Reconstruction assumptions are visible in one Module.
- Validation output still reports the current dependent record counts.

Validation: `python -m pytest tests/test_isir_validation.py -v`

## 3. Add fact intake and trace presentation adapters

Files: `demo.py`, `app.py`, `fafsa/wizard.py`, `llm/`

Acceptance criteria:
- UI/CLI frontends share a deterministic fact schema.
- LLM extraction and narration remain outside the deterministic calculation Module.
- Existing mocked backend tests pass.

Validation: `python -m pytest tests/test_llm_backends.py tests/test_fafsa_kb.py -v`
