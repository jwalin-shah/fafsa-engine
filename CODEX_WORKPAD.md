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
