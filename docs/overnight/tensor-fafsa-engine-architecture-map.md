# Overnight Architecture Map: tensor-fafsa-engine

Queue item: `tensor-fafsa-engine-architecture-map`
Branch: `codex/goal-tensor-fafsa-engine-architecture-map`
Repo: `tensor-fafsa-engine`
HEAD at audit time: `af625d0`

## Scope And Validation

This is a read-only architecture audit. The only repo change made by this
worker is this report file.

Required validation command:

```bash
git status --short
```

Initial dirty state: `git status --short` returned no output before the report
was written.

Final validation result after writing the report and removing the generated
`llm-tldr` cache:

```text
?? docs/
```

Exit code: 0. The only remaining dirty state is the report directory containing
this file.

Functional tests were not run because the queue item's required validation is
`git status --short` and this focus area is `architecture-map`, not
`validation-map`. Test files were inspected as evidence for available proof
surfaces.

## Commands Run

- `pwd`
- `git status --short`
- `git branch --show-current`
- `git rev-parse --short HEAD`
- `llm-tldr tree .`
- `rg --files -g ...`
- `rtk read README.md`
- `rtk read pyproject.toml`
- `rtk read fafsa/kb.py`
- `rtk read fafsa/isir.py`
- `rtk read fafsa/validate.py`
- `rtk read fafsa/wizard.py`
- `rtk read demo.py`
- `rtk read app.py`
- `rtk read llm/base.py`
- `rtk read llm/ollama_backend.py`
- `rtk read llm/claude_backend.py`
- `rtk read llm/openai_backend.py`
- `rtk read llm/mlx_backend.py`
- `rtk read medicaid/kb.py`
- `rtk read examples/counterfactual.py`
- `rtk read tests/test_fafsa_kb.py`
- `rtk read tests/test_isir_validation.py`
- `rtk read tests/test_llm_backends.py`
- `wc -l app.py demo.py fafsa/*.py llm/*.py medicaid/*.py tests/*.py examples/*.py README.md pyproject.toml DEPLOY.md`
- `rg -n "^(from|import) |^def |^class |@app\\.function|modal\\.|tensor_logic|verify|validate" .`
- `rg -n "tensor_logic|tensor-logic|prove_sai\\(|verify\\(|validate_isir_file\\(|@modal.fastapi_endpoint|POST /sai|/compute|/extract|health|medicaid|packages" ...`
- `rg --files -uu | sort | sed -n '1,240p'`
- `git ls-files`
- `du -sh data uv.lock .git 2>/dev/null`
- `nl -ba ...` for `README.md`, `pyproject.toml`, `fafsa/kb.py`,
  `fafsa/isir.py`, `fafsa/validate.py`, `llm/base.py`, `app.py`,
  `demo.py`, `DEPLOY.md`, and `fafsa/wizard.py`
- `llm-tldr context fafsa/kb.py prove_sai` and
  `llm-tldr calls fafsa/kb.py prove_sai` failed because this installed
  `llm-tldr` expects a symbol or project path, not `file function`.
- `llm-tldr context prove_sai --project . --depth 2`
- `llm-tldr calls .`
- `llm-tldr imports fafsa/kb.py`
- `llm-tldr imports demo.py`
- `llm-tldr imports app.py`
- `rm .tldr/cache/call_graph.json`
- `rmdir .tldr/cache .tldr`

## Repo Shape

The repo is small: 2,508 counted lines across Python, docs, and tests. Tracked
files are limited to `README.md`, `DEPLOY.md`, `pyproject.toml`, `uv.lock`,
the `fafsa/`, `llm/`, `medicaid/`, `tests/`, `examples/`, and `data/`
directories. No `.github/`, `docs/`, pytest config, Makefile, or project-level
agent instructions were present before this report.

Packaged modules are only `fafsa` and `llm` (`pyproject.toml:20-21`).
`medicaid` is tracked but not packaged.

Runtime dependencies are declared as `torch`, `requests`, and a sibling
path dependency `tensor-logic @ file:../tensor-logic`
(`pyproject.toml:5-9`). The inspected Python imports do not use `torch` or a
local `tensor_logic` module. The current deterministic engine implementation
is plain Python arithmetic in `fafsa/kb.py`.

## Entrypoints

- CLI LLM pipeline: `demo.py:17-87`. It calls `get_backend()`, extracts facts,
  asks for deterministic user confirmation, constructs `DependentFamily`,
  runs `prove_sai`, narrates, then calls `verify`.
- Interactive terminal questionnaire: `fafsa/wizard.py:214-404`. It collects
  dependent-student Formula A inputs directly and calls `prove_sai`.
- Modal web adapter: `app.py:432-488`. It exposes `index`, `extract`,
  `compute`, and `health` functions through Modal decorators.
- Counterfactual script: `examples/counterfactual.py:8-15`. It sweeps parent
  AGI and calls `prove_sai`.
- Test entrypoints: `tests/test_fafsa_kb.py`, `tests/test_isir_validation.py`,
  and `tests/test_llm_backends.py`.

## Module Ownership Map

### `fafsa.kb`

This is the core deterministic rule module. Its public interface is centered
on `prove_sai(family) -> SAITrace` (`fafsa/kb.py:181-184`). It owns:

- Input records: `DependentFamily` (`fafsa/kb.py:23-59`) and
  `IndependentFamily` (`fafsa/kb.py:62-84`).
- Trace records: `CitedValue` and `SAITrace` (`fafsa/kb.py:87-100`).
- Formula constants and helper arithmetic (`fafsa/kb.py:107-174`).
- Formula A dependent calculation (`fafsa/kb.py:187-235`).
- Formula B/C independent calculation (`fafsa/kb.py:238-275`).
- Small convenience functions `prove_sai_counterfactual` and `fmt_trace`
  (`fafsa/kb.py:278-287`).

The module is deep enough to earn its interface: callers hand it a family
record and receive a trace with cited derivation steps. `llm-tldr context`
reported `prove_sai` as a low-complexity dispatch into dependent and
independent formula implementations, with tests, app, demo, wizard, validation,
and examples crossing this same interface.

The interface is also broad. Callers must know many raw field names in
`DependentFamily`, and the Modal app, CLI demo, wizard, LLM prompts, tests, and
ISIR reconstruction each couple directly to those names.

### `fafsa.isir`

`fafsa/isir.py` owns fixed-width ED test ISIR parsing and reconstruction into
`DependentFamily`. It defines field slices (`fafsa/isir.py:17-45`),
`ISIRReport` (`fafsa/isir.py:48-59`), reconstructs a family
(`fafsa/isir.py:72-122`), filters Formula A records (`fafsa/isir.py:125-126`),
and validates computed SAI values against ED targets
(`fafsa/isir.py:129-170`).

This is a validation adapter over the deterministic engine, not part of the
core formula interface. It imports `_aai_to_parent_contribution` but does not
use it (`fafsa/isir.py:11`), which suggests either stale coupling or a missing
component-level validation seam.

### `fafsa.validate`

`fafsa/validate.py` owns user-facing verification status. It caches an
`ISIRReport` lazily (`fafsa/validate.py:102-110`) and converts it to a
`VerificationResult` message (`fafsa/validate.py:113-150`).

The docstring says validation happens "at import time" (`fafsa/validate.py:3-5`),
but the implementation runs it only on first `verify()` through
`_get_isir_report()`. That is a stale assumption in the module contract.

### `llm`

`llm/base.py` defines a real seam: `LLMBackend` has `extract_facts` and
`narrate_proof` (`llm/base.py:7-16`), and `get_backend()` selects concrete
adapters from `FAFSA_LLM` and `FAFSA_LLM_MODEL` (`llm/base.py:25-45`).
There are four adapters: Ollama, Claude, OpenAI, and MLX.

This seam is justified because there are multiple adapters. The shallow part is
the fact schema: each backend carries its own `_FIELDS_HINT` string, so the
schema presented to models can drift from `DependentFamily`.

### `app.py`

`app.py` is a deployment adapter and an embedded web UI in one 488-line module.
It builds a Modal image (`app.py:25-36`), declares a Modal app and secret
(`app.py:38-43`), embeds the full HTML/JS UI (`app.py:45-414`), serializes
traces (`app.py:416-430`), and exposes endpoints (`app.py:432-488`).

This module should be treated as an adapter over `fafsa.kb` and `llm`, not as
part of the rule engine. Its `compute` endpoint intentionally defaults to
`DependentFamily` only (`app.py:466-472`), so the web path currently does not
exercise the `IndependentFamily` half of `prove_sai`.

### `medicaid`

`medicaid/kb.py` is a proof-pattern demo using a `Household` input and
`prove_medicaid` (`medicaid/kb.py:16-68`). It imports `CitedValue` and
`SAITrace` from `fafsa.kb` for "demo consistency" (`medicaid/kb.py:12`), and
stores eligibility as `SAITrace.sai` (`medicaid/kb.py:68`).

This is the clearest ownership leak: a non-FAFSA domain depends on FAFSA-named
trace types. The repo wants a reusable proof trace abstraction, but the current
shared type is named after FAFSA's Student Aid Index.

## Stale Assumptions And Architectural Friction

1. README names a `tensor_logic/` derivation substrate that is not present in
   this repo. The claim appears at `README.md:86-88`; the only related package
   evidence is the sibling dependency in `pyproject.toml:5-9`. The actual
   rule module says Python arithmetic implements the formula
   (`fafsa/kb.py:4-8`).

2. `medicaid` is described in the README as the same engine with a different
   rule file (`README.md:76-84`), and a `medicaid/kb.py` module exists, but it
   is not packaged (`pyproject.toml:20-21`) and it reuses FAFSA-specific
   `SAITrace` (`medicaid/kb.py:12`, `medicaid/kb.py:68`).

3. The Modal health endpoint contract is stale. The module docstring says
   `GET /health` returns liveness plus ED ISIR validation status
   (`app.py:9-13`), but the implementation returns only `{"status": "ok"}`
   (`app.py:484-488`).

4. `DEPLOY.md` describes `POST /sai` and backend selection in the payload
   (`DEPLOY.md:42-44`), while the actual Modal endpoints are `/extract` and
   `/compute` with backend selection delegated to environment variables
   (`app.py:438-482`, `llm/base.py:31-45`).

5. `fafsa/wizard.py` has presentation labels that no longer match trace labels.
   It explains `parent_medicare_allowance` and `parent_oasdi_allowance`
   (`fafsa/wizard.py:60-69`) and groups those labels in the parent phase
   (`fafsa/wizard.py:130-135`), but `fafsa.kb` emits a combined
   `parent_payroll_tax` step (`fafsa/kb.py:201-203`). The student phase has the
   same split-label assumption (`fafsa/wizard.py:144-148`) while `fafsa.kb`
   emits `student_payroll_tax` (`fafsa/kb.py:221`).

6. `DependentFamily.max_pell_eligible` exists (`fafsa/kb.py:59`) but is not
   used by `prove_sai` or observed callers. That is likely either future state
   or a stale input field.

7. There is a real LLM seam, but its fact schema is duplicated in each adapter.
   The durable schema is `DependentFamily`; the model-facing schema is repeated
   strings in the backends and can drift silently.

## Architecture Decisions Observed

- The engine intentionally keeps computation deterministic and LLMs outside
  the math path. README states this at `README.md:55-61`, and the call graph
  backs it up: LLM adapters extract facts and narrate, while `prove_sai`
  computes the trace.
- The main external seam is `LLMBackend`. This is a real seam because it has
  multiple adapters.
- The formula internals are not split into many public modules. That is a
  reasonable choice for now: the formula interface is easier to validate when
  tests cross `prove_sai` instead of many shallow helper interfaces.
- The validation oracle is local data plus deterministic reconstruction, not
  an external service. The ED data file is tracked under `data/` and
  `fafsa.isir` reads it directly.

## Next Safe Work

1. Reconcile the proof-substrate story.
   Acceptance criteria: either remove the unsupported `tensor_logic/` README
   claim and unused sibling dependency, or introduce a real proof-trace module
   with callers crossing that interface. Validation: `uv run pytest
   tests/test_fafsa_kb.py tests/test_isir_validation.py`.

2. Extract a domain-neutral trace type before expanding Medicaid or other rule
   domains.
   Acceptance criteria: `medicaid` no longer imports `SAITrace` from
   `fafsa.kb`; FAFSA still exposes an SAI-specific result where needed; existing
   FAFSA and Medicaid formatting still works. Validation: `uv run pytest
   tests/test_fafsa_kb.py` plus a new Medicaid trace smoke test.

3. Centralize the FAFSA input field schema.
   Acceptance criteria: LLM backends, `demo.py`, and `app.py` derive accepted
   field names from one source, ideally `DependentFamily` metadata; duplicated
   `_FIELDS_HINT` strings are removed or generated; tests cover at least one
   adapter prompt/schema path. Validation: `uv run pytest tests/test_llm_backends.py`.

4. Separate Modal transport from embedded UI and refresh endpoint contracts.
   Acceptance criteria: docs and `app.py` agree on `/extract`, `/compute`, and
   `/health`; health either reports validation status or stops claiming it; UI
   code is isolated enough that endpoint logic can be reviewed without a
   370-line HTML string. Validation: `uv run pytest` for unit coverage plus a
   Modal smoke command only when credentials are intentionally available.

5. Decide whether `IndependentFamily` is supported or experimental.
   Acceptance criteria: docs and entrypoints explicitly state whether Formula
   B/C are supported; web and CLI paths either route independent inputs or avoid
   claiming support. Validation: focused tests for `prove_sai(IndependentFamily)`
   and any public entrypoint that claims independent-student support.

## Handoff

Changed files:

- `docs/overnight/tensor-fafsa-engine-architecture-map.md`

PR URL: not created; PR creation is out of scope for this Goal Pack item.

External trackers: not updated.

Blockers: none for writing the report. Functional validation was not run beyond
the required `git status --short` command because this queue item specified
that command as validation and requested a read-only architecture-map report.
