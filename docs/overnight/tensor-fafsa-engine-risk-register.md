# tensor-fafsa-engine risk-register audit

Queue item: `tensor-fafsa-engine-risk-register`

Audit date: 2026-05-07

Audited worktree: `/Users/jwalinshah/projects/agent-stack/.agent-stack-worktrees/2026-05-07-overnight-marathon/tensor-fafsa-engine-risk-register`

Starting branch: `codex/goal-tensor-fafsa-engine-risk-register`

Starting HEAD: `af625d0502548b76af5b7363366866592c504b82`

## Summary

`tensor-fafsa-engine` is a compact Python FAFSA Student Aid Index proof engine with LLM-backed fact extraction, deterministic arithmetic in `fafsa/kb.py`, official-looking ISIR fixture validation in `fafsa/isir.py`, provider adapters in `llm/`, and a Modal web deployment in `app.py`.

The highest risk is correctness drift: local tests contradict the README's `42/42` ED validation claim. `python3 -m pytest tests/test_fafsa_kb.py tests/test_isir_validation.py` collected 14 tests, passed 9, and failed 5. The validation report in the failure output says only 2 Formula A records passed while 40 failed. That means the public-facing verification language should not be trusted until the parser/formula mismatch is repaired or the claim is downgraded.

The next largest risks are privacy/security around public LLM-backed endpoints, unescaped browser rendering of LLM/user-derived content, and broken reproducibility from the local-path `tensor-logic @ file:../tensor-logic` dependency.

## Repo State

- `git status --short --branch` at audit start printed `## codex/goal-tensor-fafsa-engine-risk-register` and no tracked changes.
- `git rev-parse HEAD` printed `af625d0502548b76af5b7363366866592c504b82`.
- `llm-tldr tree .` showed the core layout: `fafsa/`, `llm/`, `medicaid/`, `tests/`, `app.py`, `demo.py`, `DEPLOY.md`, `README.md`, `pyproject.toml`, `uv.lock`, and `data/IDSA25OP-20240308.txt`.
- `rg --files docs` failed because `docs/` did not exist before this report.
- `git status --short` before writing this report returned no output.
- Validation attempts created ignored local artifacts: `.venv/`, `.pytest_cache/`, `fafsa_engine.egg-info/`, and Python `__pycache__/` directories. `rm -rf .venv .pytest_cache fafsa_engine.egg-info` was blocked by local policy, so they are recorded as ignored local state rather than cleaned. They are not tracked by `git status --short`.
- Local commit creation was attempted after writing this report, but `git add docs/overnight/tensor-fafsa-engine-risk-register.md` failed because the sandbox could not write the git worktree index: `Unable to create .../.git/worktrees/tensor-fafsa-engine-risk-register/index.lock: Operation not permitted`.

## Evidence Map

- `README.md:31-33` claims the engine validates against `42/42` ED test ISIRs.
- `README.md:46` claims it runs under 30 seconds on CPU with no API key required.
- `README.md:53-57` expands the `42/42` claim and says the component validation is the basis for the verification tick.
- `README.md:88` says the derivation substrate is `tensor_logic/`.
- `pyproject.toml:5-9` declares runtime dependencies on `torch`, `requests`, and `tensor-logic @ file:../tensor-logic`.
- `pyproject.toml:11-14` makes `anthropic`, `openai`, and `mlx-lm` optional extras.
- `pyproject.toml:20-21` packages only `fafsa` and `llm`; `medicaid` is present in the repo but not packaged.
- `uv.lock:263-291` locks `fafsa-engine` without `tensor-logic`, despite `pyproject.toml` declaring it.
- `app.py:25-35` builds a Modal image and copies `fafsa`, `llm`, and `data` into the deployed image.
- `app.py:40-42` loads Modal secret `fafsa-llm-keys` with `required_keys=[]`, so missing provider credentials are not checked at deploy/config time.
- `app.py:297-323` renders LLM-returned fact keys, citations, and reasoning through `row.innerHTML`.
- `app.py:350-390` sends user text and edited facts to `/extract` and `/compute`.
- `app.py:438-454` exposes `/extract` and returns raw exception text in JSON errors.
- `app.py:456-482` exposes `/compute`, casts incoming JSON values with `int(v)`, builds `DependentFamily`, calls the LLM for narration, and returns raw exception text in JSON errors.
- `app.py:484-488` implements `/health` as a static liveness response; it does not run ED validation.
- `llm/base.py:31-42` defaults `FAFSA_LLM` to `ollama`, then chooses Claude/OpenAI/MLX only by environment variable.
- `llm/ollama_backend.py:8` defaults `OLLAMA_URL` to `http://localhost:11434`.
- `llm/ollama_backend.py:49-73`, `llm/openai_backend.py:20-59`, and `llm/claude_backend.py:20-57` send financial query/proof content to model backends and print extraction reasoning with quoted user-derived text.
- `fafsa/kb.py:23-59` defines many dependent-family inputs but no range, sign, or field-level validation.
- `fafsa/kb.py:107-135` hard-codes 2024-25 formula constants, including income protection, payroll tax, asset, and income rates.
- `fafsa/kb.py:145-151` treats `family_size <= 2` as the table minimum and has `_apa()` hard-coded to `0`.
- `fafsa/isir.py:14-45` hard-codes fixed-width ISIR positions for validation.
- `fafsa/isir.py:105-107` reconstructs parent wages from parent AGI and falls back student earned income to AGI, a stale assumption candidate behind the failed ISIR tests.
- `tests/test_isir_validation.py:33-45` expects zero ISIR failures, exactly 42 passing records, no skipped records, and `report.all_passed`.
- `data/IDSA25OP-20240308.txt` is tracked, has 103 lines and 793718 bytes, and was observed to contain 178 `@test.com` matches and 174 `CUI//SP-TAX` marker matches.

## Risk Register

| ID | Severity | Risk | Evidence | Impact | Next safe move |
| --- | --- | --- | --- | --- | --- |
| R1 | Critical | ED validation claim is false in the local worktree. | `python3 -m pytest tests/test_fafsa_kb.py tests/test_isir_validation.py` failed 5 tests; output reported 2 passed and 40 failed dependent records. README still claims `42/42` in `README.md:31-33` and `README.md:53-57`. | Users may rely on incorrect financial-aid calculations; verification UI may create false assurance. | Reproduce the first three ISIR mismatches, decide whether parser or formula is wrong, and update either code or docs before any demo/deploy. |
| R2 | High | Public web endpoints have no visible auth, rate limit, abuse budget, or privacy gate. | Modal endpoints are declared in `app.py:432-488`; `DEPLOY.md:19-36` describes persistent public URLs and curl testing. | A public demo could collect sensitive financial facts, run paid LLM calls, and expose service cost/abuse risk. | Add explicit public-demo threat model, request limits, and provider opt-in before deploy. |
| R3 | High | LLM/user-derived content is rendered with `innerHTML`. | `app.py:311-320` interpolates field keys, citations, and reasoning into HTML; citations are requested as exact user quotes in `llm/openai_backend.py:23-30` and `llm/claude_backend.py:23-30`. | A malicious query or model output could inject HTML/script into the wizard. | Replace HTML interpolation with DOM text nodes or a sanitizer and add a regression test with HTML in the input query. |
| R4 | High | Reproducible installation is broken. | `uv run pytest tests` failed while generating package metadata: `relative path without a working directory: ../tensor-logic`; `test -d ../tensor-logic` exited 1 in this worktree; `uv.lock:263-291` omits the dependency. | New workers and CI cannot reliably install or test the repo from this isolated worktree. | Remove the unused local dependency or make it a real workspace/path dependency with the sibling present in every worker. |
| R5 | High | Deployment docs and implementation disagree. | `DEPLOY.md:25-35` documents `/sai`; `app.py:438-482` implements `/extract` and `/compute`; `DEPLOY.md:42-44` says `backend` can be passed in request JSON, but `app.py` ignores it and `llm/base.py:31` uses env vars. | Operators following docs will test the wrong endpoint or deploy a service that defaults to unavailable local Ollama. | Align endpoints and backend selection docs with code, or add the documented `/sai` facade. |
| R6 | Medium | Modal secret validation is too weak. | `app.py:40-42` sets `required_keys=[]`; deploy docs expect `ANTHROPIC_API_KEY` at `DEPLOY.md:46-48`. | Missing credentials become runtime failures instead of deployment-time failures. | Require keys for the configured backend or fail startup with a clear configuration error. |
| R7 | Medium | Sensitive-looking fixture data is tracked and shipped into the Modal image. | `git ls-files data/IDSA25OP-20240308.txt` confirms the data file is tracked; `app.py:35` copies `data` into the image; command observations found 178 `@test.com` and 174 `CUI//SP-TAX` markers. | Even test data may have handling requirements; shipping it in a public app image increases disclosure and compliance review burden. | Classify the fixture, document provenance/license, and exclude it from runtime images unless health/validation needs it. |
| R8 | Medium | Health check does not reflect correctness health. | `app.py:484-488` returns only `{"status": "ok"}` while local ISIR tests fail. | Monitoring can report green while the engine is mathematically untrustworthy. | Add a separate validation endpoint or startup check that reports cached ISIR validation status without exposing raw records. |
| R9 | Medium | Input validation is missing for the public API. | `app.py:464-472` accepts any `payload["facts"]`, filters known field names, casts to int, and instantiates the dataclass; `fafsa/kb.py:23-84` has no dataclass validation. | Negative values, impossible family sizes, huge integers, and malformed fields can yield misleading outputs or avoidable failures. | Add Pydantic request models with explicit ranges and user-facing validation errors. |
| R10 | Medium | Provider adapters log user-derived financial data. | `llm/ollama_backend.py:58-62`, `llm/openai_backend.py:42-46`, and `llm/claude_backend.py:39-43` print extracted values and citations. | Modal/local logs can retain sensitive user financial facts and exact query quotes. | Redact or disable extraction logging by default; make debug logging explicit. |
| R11 | Medium | Optional provider dependencies are not isolated in tests. | `python3 -m pytest tests` failed at collection with `ModuleNotFoundError: No module named 'anthropic'`, although `anthropic` is an optional extra in `pyproject.toml:11-14`. | Core tests cannot run in a minimal install; CI may fail before reaching deterministic FAFSA tests. | Mark provider tests with extras/skip gates or move provider SDK imports behind patches. |
| R12 | Medium | Financial formula scope is broader in code/docs than validation proves. | `fafsa/kb.py:1-2` says Formula A, B, and C; README validates dependent-student records; `tests/test_isir_validation.py` only covers Formula A dependent records. | Independent-student Formula B/C behavior may be unvalidated while presented as implemented. | Add independent-student fixtures/tests or state that Formula B/C are experimental. |
| R13 | Low | Unused/stale module surface can mislead follow-on agents. | `medicaid/kb.py` exists, README lists Medicaid/tax/clinical/visa as future domains in `README.md:76-84`, but `pyproject.toml:20-21` excludes `medicaid`. | Agents may implement against an unshipped module or assume a broader product boundary than exists. | Either package/test Medicaid as an example or move it to docs/examples with explicit non-production status. |
| R14 | Low | Heavy runtime dependency surface is unexplained. | `pyproject.toml:6` requires `torch`, while the inspected FAFSA core and LLM adapters do not import it; `uv.lock` contains many large torch wheels. | Installs are slower and larger, increasing CI/deploy friction and supply-chain exposure. | Audit whether `torch` is still needed; move it to an optional extra if only future tensor work uses it. |

## Validation Observations

Required validation command:

```bash
git status --short
```

Observed before report creation: exit 0, no output.

Expected after this report is written in this sandbox: exit 0 with `?? docs/` or the report path, because staging/committing is blocked by git index permissions. Ignored artifacts from validation attempts are visible only with `git status --short --ignored`.

Additional command candidates:

| Command | Observed status | Expected status before safe handoff |
| --- | --- | --- |
| `llm-tldr tree .` | Passed; showed repo structure. | Pass. |
| `git status --short --branch` | Passed; branch was `codex/goal-tensor-fafsa-engine-risk-register` and no tracked changes. | Pass. |
| `rtk pytest tests` | Failed as a useful runner; output said `Pytest: No tests collected`. | Should be replaced or documented; do not use as proof until it collects tests. |
| `uv run pytest tests` | Failed before tests due package metadata error for `tensor-logic @ file:../tensor-logic`. | Should pass metadata/install before CI depends on uv. |
| `python -m pytest tests` | Failed because `python` is not on PATH in this worktree shell. | Prefer `python3 -m pytest` locally or standardize the toolchain. |
| `python3 -m pytest tests` | Failed during collection because optional `anthropic` package is missing. | Core test collection should pass without optional provider SDKs. |
| `python3 -m pytest tests/test_fafsa_kb.py tests/test_isir_validation.py` | Failed: 9 passed, 5 failed; ISIR validation reported 2 passed and 40 failed dependent records. | Must pass before claiming ED validation. |
| `python3 -m compileall fafsa llm tests` | Passed. | Cheap syntax smoke test candidate; does not prove correctness. |
| `wc -l -c data/IDSA25OP-20240308.txt` | Passed; 103 lines and 793718 bytes. | Pass. |
| `rg -o "@test\\.com" data/IDSA25OP-20240308.txt | wc -l` | Passed; 178 matches. | Use only as data-handling signal, not correctness proof. |
| `rg -o "CUI//SP-TAX" data/IDSA25OP-20240308.txt | wc -l` | Passed; 174 matches. | Use only as data-handling signal, not correctness proof. |

## Next Safe Work

1. Repair or downgrade ED validation.
   - Acceptance criteria: `validate_isir_file()` agrees with the expected Formula A record count and has zero failures, or README/UI copy no longer claims `42/42`.
   - Validation: `python3 -m pytest tests/test_isir_validation.py tests/test_fafsa_kb.py::test_verify_returns_verified_when_engine_passes_isir_validation tests/test_fafsa_kb.py::test_verify_message_mentions_isir_count`.
   - Notes: Start from `fafsa/isir.py:105-107` and the first failing records reported by pytest.

2. Make install/test reproducible in an isolated worktree.
   - Acceptance criteria: `uv run pytest tests` reaches test collection without metadata failure; the lock and pyproject agree on local/workspace dependencies; optional provider tests skip cleanly when extras are absent.
   - Validation: `uv lock --check` and `uv run pytest tests`.
   - Notes: Decide whether `tensor-logic` is required. If not required, remove it. If required, make it a proper workspace dependency available to overnight workers.

3. Harden browser rendering and API schemas before any public demo.
   - Acceptance criteria: `/extract` and `/compute` use explicit schemas and range validation; the UI never injects user/model content through `innerHTML`; HTML-in-query regression test passes.
   - Validation: unit tests for malicious citation/reasoning strings plus a minimal FastAPI client test.
   - Notes: This can be done without deploying Modal.

4. Align Modal docs with implementation and backend configuration.
   - Acceptance criteria: docs list the actual endpoints, request/response shapes, configured default backend, required secrets, and known cost behavior; runtime fails early when the configured provider is missing.
   - Validation: local import/config tests, plus `modal serve` only after explicit approval because it touches external tooling.

5. Classify and isolate the ISIR fixture.
   - Acceptance criteria: provenance/license/handling guidance for `data/IDSA25OP-20240308.txt` is documented; runtime images do not include fixture data unless needed; validation code can still find fixtures in test context.
   - Validation: `git ls-files data/IDSA25OP-20240308.txt`, `rg "CUI//SP-TAX|@test\\.com" data/IDSA25OP-20240308.txt`, and an image-build review if deployment remains in scope.

6. Reduce privacy leakage in logs.
   - Acceptance criteria: provider adapters do not print extracted values or exact query quotes by default; debug mode is explicit and documented.
   - Validation: backend tests capture stdout and assert no user query fragments are emitted by default.

## Non-goals

- I did not change product code, tests, fixtures, dependencies, deployment config, secrets, or generated data.
- I did not deploy Modal, call provider APIs, pull models, push branches, open PRs, or mark external trackers done.
- I did not attempt to fix the failing FAFSA formula/ISIR validation; this queue item is read-only audit plus one report.
- I did not inspect external documentation or websites; all evidence above is local to this worktree and local command output.

## Unknowns

- Whether the bundled ISIR data file is exactly the intended official fixture revision or a newer/wider file than the parser expects.
- Whether `tensor-logic` is supposed to be present as a sibling repo in other worktrees; `../tensor-logic` was absent here.
- Whether production Modal deployments set `FAFSA_LLM=claude` or similar outside the repo; the local code defaults to Ollama.
- Whether the `CUI//SP-TAX` markers in the fixture are acceptable to ship in a public app image.
- Whether the independent-student Formula B/C code is intended to be production-supported or experimental.
- Whether the `torch` dependency is still needed by any uninspected future tensor integration.
