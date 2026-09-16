# Engineering Portfolio - Local Operator

This is a small local learning, operating and feedback surface for four
independent engineering projects. It helps a reviewer understand each project,
check prerequisites, run an existing registered entrypoint, inspect the latest
result, verify evidence, replay a run and leave structured feedback.

The projects remain separate repositories and remain independently runnable:

* NP01 demonstrates a synthetic industrial cell detecting faults and
  recovering its control state.
* NP02 checks imperfect records before producing trusted quality, lineage and
  analytical results.
* NP03 tests whether retrieved evidence supports a conclusion, requires human
  review, or should be declined.
* NP04 compares architecture alternatives against requirements, assumptions,
  risks, costs and verification needs.

The projects already produce traceable operational results. This root surface
collects small derived summaries so a reviewer can compare runs and provide
feedback. It does not replace any project's domain authority: project evidence
is read, never rewritten, and the local SQLite store contains only references,
bounded derived features, feedback and conceptual metadata.

## Quick start

Run these commands from this directory. The four projects are independent
repositories, so the root intentionally has no global demo or global pytest
suite; operate a project from that project's repository root.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe scripts\validate_integration.py
.\.venv\Scripts\python.exe -m portfolio_operator
```

The integration check performs the NP02 PostgreSQL preflight using the
effective local port (`NP02_DB_PORT`, defaulting to the documented `55540`),
discovers the four existing `var/latest_valid.json` pointers, records one
observation per available latest run, and submits one synthetic
`KNOWN_TEST_SCENARIO` feedback record per project. It does not run or alter
project code. The operator console's first screen is:

```text
Engineering Portfolio - Local Operator
1 NP01 Industrial Resilience OT Lab
2 NP02 Governed Data & Analytics
3 NP03 Governed AI Assurance
4 NP04 Architecture Decision Workbench
5 Cross-project observations
6 Feedback
7 Learning concepts
0 Exit
```

Use a project view to read the plain-language explanation, prerequisites and
latest result. Only actions present in `portfolio.toml` are offered. A replay
uses the registered project's latest run identifier; a new project run is
created by that project and the parent is not overwritten. Destructive cleanup
requires an explicit `CONFIRM` in the CLI or a confirmed POST in the web
surface. Feedback is labelled `HUMAN` when entered by an operator; the four
records created by integration validation are labelled
`SYNTHETIC_INTEGRATION_VALIDATION`.

## Local web surface

The optional browser view uses FastAPI, Uvicorn, Jinja2 and vanilla
HTML/CSS/JavaScript. Start it only when the root optional dependencies are
installed:

```powershell
.\.venv\Scripts\python.exe scripts\run_web.py
```

It binds to `127.0.0.1` by default. It exposes project explanations, latest
results, logical run/evidence views, learning concepts, model metadata and
bounded POST actions. It does not accept arbitrary shell strings, expose
private filesystem paths, or bind to `0.0.0.0` by default.

## Evidence and authority

The registry follows the existing project pointers without copying run
bundles:

| Project | Domain authority | Evidence reference |
| --- | --- | --- |
| NP01 | SQLite journal / PLC-edge execution state | `var/runs/<run_id>/` in NP01 |
| NP02 | PostgreSQL structured authority | `var/runs/<run_id>/` in NP02 |
| NP03 | Assurance evaluation artifacts | `var/runs/<run_id>/` in NP03 |
| NP04 | SQLite decision-traceability state | `var/runs/<run_id>/` in NP04 |

For each observed run the operator stores an `ObservationEnvelope` containing
the run identifier, source commit and evidence hash, status, a small numeric
feature set, labels and the evidence path. The adapter returns an explicit
unknown-schema observation instead of guessing when a project result changes.
`SHA256SUMS` verification is read-only.

## Learning today and future concepts

The active analysis is `DETERMINISTIC_DESCRIPTIVE`: feature summaries,
run-to-run differences and bounded rule indications. It is inspectable and
run-scoped, not machine learning, prediction, diagnosis or automated decision
authority.

The operator presents five layers: observed project runs, human feedback,
deterministic analytics, conceptual ML extensions, and future controlled
operationalization. VAE and GAN are `CONCEPT_DEMONSTRATION` interfaces only.
Each project currently has one observation, so VAE data readiness is
`INSUFFICIENT_DATA` for all four projects and no model is trained. A VAE could
eventually highlight an unusual pattern within one compatible domain; a GAN
could propose a `SYNTHETIC_CANDIDATE` scenario. A candidate requires schema and
domain validation plus explicit human approval before execution and can never
become evidence automatically.

For the one bounded examples and the full evidence/authority contract, see
[`docs/learning.md`](docs/learning.md) or use the Learning concepts menu.

## Out of scope

This surface is not NP05, a central runtime, a replacement database, a
monorepo, a cloud service, an autonomous decision system, a model-training
pipeline or a publication pipeline. It does not claim production control,
production-scale data engineering, generalized AI quality, procurement
authority or functional-safety certification. No model is trained or
operationalized here; remote repository creation and pushes are intentionally
outside this workunit.
The root environment intentionally adds no PyTorch, TensorFlow, JAX, CUDA or
GPU-specific dependency.

## Layout

* `portfolio.toml` — declarative project registry and fixed action arrays.
* `portfolio_operator/` — registry, evidence readers, adapters, storage,
  runner, CLI and optional web app.
* `scripts/validate_integration.py` — bounded four-project observation and
  feedback check.
* `tests/` — integration-surface contract tests only.
* `docs/` — concise architecture and learning boundaries.
* `var/` — ignored local operator SQLite state.
