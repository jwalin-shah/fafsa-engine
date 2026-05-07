# tensor-fafsa-engine dependency-surface audit

Queue item: `tensor-fafsa-engine-dependency-surface`  
Repo: `tensor-fafsa-engine`  
Branch: `codex/goal-tensor-fafsa-engine-dependency-surface`  
HEAD observed before report: `af625d0502548b76af5b7363366866592c504b82` (`af625d0 refactor: depend on shared tensor-logic`)  
Audit date: 2026-05-07

## Scope and non-goals

This is a read-only dependency-surface audit except for this report. I did not modify product code, generated data, secrets, deployment config, external services, sibling repos, branches, PRs, or trackers. I did not attempt `modal serve`, `modal deploy`, live LLM calls, `ollama pull`, API-key-backed Claude/OpenAI calls, or network-dependent dependency installation.

Unknowns left for a follow-up worker:

- Whether the real intended runtime is local `uv pip install -e .`, Modal deployment, direct source checkout execution, or all three.
- Whether `tensor-logic @ file:../tensor-logic` is intentionally replacing a copied `tensor_logic/` subtree or is a partial migration.
- Whether the bundled ED ISIR fixture changed, the parser regressed, or README validation claims are stale.
- Whether the default Python command should be `python`, `python3`, or `uv run python` on supported machines.

## Repo purpose and current state

The repo demonstrates a FAFSA Student Aid Index engine where LLM backends extract/narrate facts and `fafsa/kb.py` computes a deterministic proof trace. The dependency surface is larger than the core engine: pure-Python formula code, a local ED test fixture, LLM SDKs, local Ollama HTTP, MLX model loading, Modal deployment, and a sibling `tensor-logic` path dependency all appear in different entrypoints.

Observed state:

- `git branch --show-current` returned `codex/goal-tensor-fafsa-engine-dependency-surface`.
- Initial `git status --short` returned no output; the worktree was clean before this report.
- `git log -1 --oneline` returned `af625d0 refactor: depend on shared tensor-logic`.
- `llm-tldr tree .` showed a small repo with `fafsa/`, `llm/`, `medicaid/`, `tests/`, `data/IDSA25OP-20240308.txt`, `app.py`, `demo.py`, `DEPLOY.md`, `pyproject.toml`, and `uv.lock`.
- `fd --hidden --exclude .git --type f` found `.gitignore`, `pyproject.toml`, `uv.lock`, source files, tests, the ED data file, and no committed `docs/` directory before this audit.

## Dependency inventory

Declared packaging dependencies:

- `pyproject.toml:4` requires Python `>=3.11`.
- `pyproject.toml:5-9` declares core dependencies: `torch`, `requests`, and `tensor-logic @ file:../tensor-logic`.
- `pyproject.toml:11-14` declares optional extras: `claude = ["anthropic"]`, `openai = ["openai"]`, `mlx = ["mlx-lm"]`.
- `pyproject.toml:16-21` uses `setuptools>=61.0` and packages only `fafsa` and `llm`.

Lockfile observations:

- `uv.lock` records `fafsa-engine==0.1.0` as editable source.
- `uv.lock` package metadata lists `requests` and `torch` as base requirements plus optional `anthropic`, `openai`, and `mlx-lm`.
- The same `uv.lock` metadata did not list the `tensor-logic @ file:../tensor-logic` dependency visible in `pyproject.toml`, while `rg -n "tensor[-_]logic|tensor_logic|tensor-logic" .` found only `README.md:88` and `pyproject.toml:8`.
- `uv.lock` includes heavyweight optional MLX/transformers artifacts and platform wheels. `rg` found `mlx-lm` at `uv.lock:641`, `openai` at `uv.lock:903`, `requests` at `uv.lock:1231`, and `torch` at `uv.lock:1402`.

Runtime imports:

- `rg -n "^(import|from) " . --glob '*.py'` found no `torch` or `tensor_logic` imports in repo source.
- `fafsa/kb.py` imports only `math` and `dataclasses` for the core SAI formula.
- `fafsa/isir.py:14` hardcodes `_DEFAULT_ISIR_PATH` to `data/IDSA25OP-20240308.txt`; `fafsa/isir.py:133` opens that file directly.
- `llm/ollama_backend.py:4` imports `requests` and `llm/ollama_backend.py:8` reads `OLLAMA_URL`.
- `llm/claude_backend.py:3` imports `anthropic` at module import time.
- `llm/openai_backend.py:3` imports `OpenAI` at module import time.
- `llm/mlx_backend.py:57` lazily imports `mlx_lm.load`; `llm/mlx_backend.py:64` lazily imports `mlx_lm.generate`.
- `app.py:21` imports `modal`, but `modal` is not declared in `pyproject.toml`.

Deployment dependencies:

- `app.py:25-35` builds a Modal image with `fastapi[standard]`, `anthropic`, `openai`, and `requests`, then copies `fafsa`, `llm`, and `data` into `/root`.
- `app.py:40-42` references Modal secret `fafsa-llm-keys` with `required_keys=[]`.
- `app.py:432-486` exposes Modal FastAPI endpoints for `/`, extraction, computation, and health.
- `DEPLOY.md:8-10` instructs installing Modal, authenticating in browser, and creating `fafsa-llm-keys` with `ANTHROPIC_API_KEY`.
- `DEPLOY.md:44` documents `POST /sai`, but `app.py` exposes separate `extract` and `compute` function endpoints rather than a visible `sai` function.

Environment variables and secrets:

- `llm/base.py:31-32` reads `FAFSA_LLM` and `FAFSA_LLM_MODEL`; default backend is Ollama and default model is `qwen3.5:4b` unless overridden.
- `llm/base.py:19-22` sets explicit defaults for Ollama and MLX.
- `llm/ollama_backend.py:8` reads `OLLAMA_URL`, defaulting to `http://localhost:11434`.
- `README.md:68-72` documents `FAFSA_LLM=mlx`, `FAFSA_LLM=claude`, `FAFSA_LLM=openai`, and `FAFSA_LLM_MODEL`.
- `DEPLOY.md:48` says the Modal secret should contain `ANTHROPIC_API_KEY` and optionally `OPENAI_API_KEY`.
- `.gitignore` ignores `.env`, `.venv/`, `dist/`, `*.egg-info/`, `*.pyc`, and `__pycache__/`.

Data, generated artifacts, and local-only state:

- `wc -l data/IDSA25OP-20240308.txt` returned `103`.
- `du -ah .` observed the repo at about `1.2M`, with `data/IDSA25OP-20240308.txt` about `776K`, `uv.lock` about `272K`, `fafsa/` about `56K`, and `llm/` about `28K`.
- `tests/test_isir_validation.py:19` points tests at the same ED fixture path.
- `python3 -m py_compile ...` initially created ignored `__pycache__` directories; `python3 -m pytest ...` created `.pytest_cache`; `env UV_CACHE_DIR=.uv-cache uv tree --locked` created `.uv-cache`. I removed those generated caches before writing this report.
- No committed generated artifacts beyond `uv.lock` and the ED fixture were observed.

## Validation observations

Commands run and observed status:

- `python3 --version` returned `Python 3.12.8`.
- `uv --version` returned `uv 0.11.5 (Homebrew 2026-04-08 aarch64-apple-darwin)`.
- `python -m py_compile ...` failed because `python` was not on PATH.
- `python3 -m py_compile app.py demo.py examples/counterfactual.py fafsa/kb.py fafsa/isir.py fafsa/validate.py fafsa/wizard.py llm/base.py llm/ollama_backend.py llm/claude_backend.py llm/openai_backend.py llm/mlx_backend.py medicaid/kb.py` passed.
- `python3 -c "from fafsa.isir import validate_isir_file; r=validate_isir_file(); print(r)"` ran and returned `ISIRReport(total=103, passed=2, failed=40, skipped=0, failures=[...])`.
- `python3 -m pytest tests/test_fafsa_kb.py tests/test_isir_validation.py -q` failed: `9 passed`, `5 failed`. Failures all traced to the ISIR validation mismatch and README/test expectation of `42/42`.
- `python3 -m pytest tests/test_llm_backends.py -q` failed during collection with `ModuleNotFoundError: No module named 'anthropic'`.
- `uv tree --locked` failed against the default uv cache with `Operation not permitted` under `/Users/jwalinshah/.cache/uv`.
- `env UV_CACHE_DIR=.uv-cache uv tree --locked` avoided the cache permission failure but then failed to fetch `setuptools>=61.0` because network/DNS was unavailable.
- `rtk pytest tests/test_fafsa_kb.py tests/test_isir_validation.py` returned `Pytest: No tests collected`; raw `python3 -m pytest` was more reliable for this repo.

Validation command candidates for future work:

- Required queue validation: `git status --short`. Expected after this report: one untracked report path until committed, or clean after a scoped docs commit.
- Syntax-only proof: the `python3 -m py_compile ...` command above. Expected current status: pass.
- Pure core tests: `python3 -m pytest tests/test_fafsa_kb.py tests/test_isir_validation.py -q`. Expected current status: fail until ISIR validation/data/parser claims are reconciled.
- LLM mock tests: `python3 -m pytest tests/test_llm_backends.py -q`. Expected current status in bare environment: fail at collection unless optional `anthropic` and `openai` SDKs are installed or tests avoid import-time optional dependencies.
- Dependency graph: `env UV_CACHE_DIR=.uv-cache uv tree --locked`. Expected current status in restricted network sandbox: fail unless build requirements are already cached or uv can access PyPI.

## Risks and stale assumptions

1. Packaging and lock metadata appear inconsistent. `pyproject.toml` declares `tensor-logic @ file:../tensor-logic`, but `uv.lock` metadata for `fafsa-engine` lists only `requests` and `torch` as base dependencies. A fresh install may not match the committed lock or may require sibling repo layout not captured by the lock.

2. `tensor-logic` is declared and documented but unused in local source. `rg` found no import of `tensor_logic`, and `fafsa/kb.py` is pure Python arithmetic. The README claim at `README.md:88` that the derivation substrate is `tensor_logic/` is not supported by current code in this repo.

3. Core validation claims are stale or broken locally. README lines `30-33` and `50-57` claim `42/42` ED ISIR validation, but direct execution of `validate_isir_file()` returned only `2` passing dependent records with `40` failures out of a `103` line fixture.

4. Optional SDK imports are eager enough to break tests. `tests/test_llm_backends.py` imports `ClaudeBackend` and `OpenAIBackend` at module top level, so a developer without optional extras cannot collect even mocked LLM tests.

5. The local quick start uses `python`, but the observed machine only had `python3`. README lines `6`, `43`, `67`, and the demo usage in `demo.py` all use `python`, which may fail on supported macOS environments unless `uv run python` or `python3` is standardized.

6. Modal deployment has a separate dependency universe. `app.py` requires local `modal` just to import, but `pyproject.toml` does not declare `modal` or `fastapi`; the Modal image installs FastAPI and LLM SDKs independently, bypassing local package metadata and the `tensor-logic` dependency.

7. Modal secrets are permissive at declaration time. `app.py:40-42` uses `required_keys=[]`, so a Modal deployment can start without either `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`, then fail only at request time depending on `FAFSA_LLM`.

8. `medicaid/` is local source but not packaged. `pyproject.toml:20-21` packages only `fafsa` and `llm`; `medicaid/kb.py` exists and reuses FAFSA trace types, but editable/package installs will omit it unless packaging is expanded.

9. The ED data file is a hidden runtime dependency of validation and verification. The package config includes only packages, not explicit package data; installed wheels may omit `data/IDSA25OP-20240308.txt`, breaking `fafsa/isir.py` outside source checkouts.

10. Sibling path dependencies create handoff fragility. `repos.json` says `tensor-fafsa-engine` and `tensor-logic` are sibling tensor repos, but isolated worktrees under `.agent-stack-worktrees/.../tensor-fafsa-engine-dependency-surface` may not have the same relative `../tensor-logic` layout expected by `pyproject.toml`.

## Sibling repo overlap

Because this repo is small, I checked related tensor repos from `/Users/jwalinshah/projects/agent-stack/repos.json` read-only:

- `repos.json` lists tensor siblings: `tensor-experiments`, `tensor-fafsa-engine`, `tensor-quicksilver-zk`, `tensor-taxes`, and `tensor-logic`.
- `llm-tldr tree /Users/jwalinshah/projects/tensor/tensor-logic` shows a full `tensor_logic/` package, many `experiments/exp80_*` files, and tests including `tests/test_exp80.py`.
- `tensor-logic/docs/superpowers/plans/2026-04-28-fafsa-engine.md` planned a standalone `fafsa-engine` repo with copied `tensor_logic/` source, `torch` and `requests` dependencies, optional Claude/OpenAI, and mock-based tests.
- `tensor-logic/docs/superpowers/specs/2026-04-28-fafsa-engine-design.md` says verification should check a prevalidated `1015`-family synthetic dataset; the current repo instead uses an ED ISIR fixture and fails many local ISIR comparisons.
- `llm-tldr tree /Users/jwalinshah/projects/tensor/taxes` shows a similar domain-specific proof repo with `taxes/`, `llm/`, `tests/`, `demo.py`, `pyproject.toml`, and `uv.lock`.
- `/Users/jwalinshah/projects/tensor/taxes/pyproject.toml` has `dependencies = []`, optional `claude`, and `dev = ["pytest", "hypothesis"]`, suggesting `tensor-fafsa-engine` could also separate core runtime dependencies from dev/test and LLM extras.
- `/Users/jwalinshah/projects/tensor/taxes/llm/base.py` mirrors the `LLMBackend` pattern but uses `TAX_LLM`, showing duplication of backend factory structure across domain repos.

Handoff risk: current `tensor-fafsa-engine` appears to have evolved from the tensor-logic exp80 plan, then partially migrated from copied `tensor_logic/` to a path dependency, while README/docs/test claims still mix the synthetic-dataset plan and ED-ISIR validation reality.

## Independently grabbable next tasks

1. Reconcile `tensor-logic` dependency strategy.

Acceptance criteria:
- Decide whether FAFSA should import/use `tensor_logic`, copy no `tensor_logic` code, or remove the dependency entirely.
- Make `pyproject.toml`, `uv.lock`, README engine wording, and import surface agree.
- Document whether isolated worktrees need a sibling `../tensor-logic`.

Validation:
- `rg -n "tensor[-_]logic|tensor_logic|tensor-logic" .`
- `env UV_CACHE_DIR=.uv-cache uv lock --check` or equivalent once network/cache is available.
- `python3 -m pytest tests/test_fafsa_kb.py -q`

2. Fix optional LLM dependency isolation.

Acceptance criteria:
- A base install can collect and run non-live tests without `anthropic`, `openai`, `mlx-lm`, Ollama, Modal, or API keys.
- Mock-based backend tests either install declared test extras or skip/patch optional SDK imports cleanly.
- README quick start states the exact install command for base, LLM extras, and dev/test dependencies.

Validation:
- Fresh environment: `python3 -m pytest tests/test_llm_backends.py -q` should pass or skip optional SDK-specific tests with explicit reasons.
- `python3 -m pytest tests/test_fafsa_kb.py -q`

3. Reconcile validation claims with the ED fixture.

Acceptance criteria:
- `README.md`, `fafsa/validate.py`, `tests/test_isir_validation.py`, and `data/IDSA25OP-20240308.txt` agree on the number and meaning of validated cases.
- If ED ISIR validation is the source of truth, fix parser/formula gaps or weaken claims until tests reflect real coverage.
- If synthetic validation is still intended, separate it from ED ISIR tests and state which one drives user-facing verification.

Validation:
- `python3 -c "from fafsa.isir import validate_isir_file; print(validate_isir_file())"`
- `python3 -m pytest tests/test_isir_validation.py tests/test_fafsa_kb.py -q`

4. Align Modal deployment with package metadata.

Acceptance criteria:
- `app.py`, `DEPLOY.md`, and `pyproject.toml` agree on deployment dependencies (`modal`, `fastapi`, LLM SDKs, data packaging).
- Modal endpoint names in docs match actual Modal functions/endpoints.
- Missing API-key behavior is explicit before request-time backend failure.

Validation:
- Syntax: `python3 -m py_compile app.py`
- Import check in a dev env with deploy extras: `python3 -c "import app; print('modal app import ok')"`
- Docs grep: `rg -n "sai|extract|compute|health|modal|fastapi|fafsa-llm-keys" app.py DEPLOY.md pyproject.toml`

5. Package runtime data and non-FAFSA modules intentionally.

Acceptance criteria:
- Decide whether `data/IDSA25OP-20240308.txt` is source-only test data or package runtime data.
- Decide whether `medicaid/` is demo source, package source, or should move to examples/sibling repo.
- Update package config and tests to assert intended distribution contents.

Validation:
- `python3 -m pytest tests/test_isir_validation.py -q`
- Build/install check once build deps are available: `env UV_CACHE_DIR=.uv-cache uv build` and inspect wheel contents.

## Final audit notes

The core arithmetic module has a small dependency footprint, but the repo-level dependency surface is not small: lockfile drift, optional SDK import behavior, deployment-specific packages, the ED fixture, a local sibling path dependency, and README/test claims all affect whether another worker can reproduce or trust the project. The safest next work is documentation/packaging reconciliation before changing formula logic.

## Handoff

Files changed:

- `docs/overnight/tensor-fafsa-engine-dependency-surface.md`

Validation:

- Required command: `git status --short`
- Observed after writing this report: `?? docs/`
- Interpretation: command runs successfully; the only dirty state is this required untracked report path.

Commit and PR:

- Report commit was attempted but blocked by sandbox permissions: `git add docs/overnight/tensor-fafsa-engine-dependency-surface.md` failed with `fatal: Unable to create '/Users/jwalinshah/projects/tensor/fafsa-engine/.git/worktrees/tensor-fafsa-engine-dependency-surface/index.lock': Operation not permitted`.
- Current HEAD remains `af625d0502548b76af5b7363366866592c504b82`; that SHA does not include this report.
- No PR was created; PR creation is out of scope for this queue item.
