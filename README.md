# Daniel Franco Fajardo — Engineering Portfolio

**Principal Systems Architect | Critical & Intelligent Infrastructure**  
Governed Architecture · Resilient Operations · Applied AI

## Professional links

- [GitHub](https://github.com/RelativoDrako)
- [Professional landing](https://relativodrako.github.io/)
- [Contact](https://relativodrako.github.io/#contact)

This is a local learning, operating and feedback surface for four
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

Project repositories: [NP01](https://github.com/RelativoDrako/industrial-resilience-ot-lab), [NP02](https://github.com/RelativoDrako/governed-data-analytics), [NP03](https://github.com/RelativoDrako/governed-ai-assurance), and [NP04](https://github.com/RelativoDrako/architecture-decision-workbench).

The projects already produce traceable operational results. This root surface
collects small derived summaries so a reviewer can compare runs and provide
feedback. It does not replace any project's domain authority: project evidence
is read, never rewritten, and the local SQLite store contains only references,
bounded derived features, feedback and conceptual metadata.

## Quick start

On Windows, double-click:

```text
START_PORTFOLIO.cmd
```

The launcher checks or reuses the local root environment and opens the local
operator in the default browser at `http://127.0.0.1:8765`. The terminal stays
attached to the local service; use `Ctrl+C` or close it when finished. If a
browser cannot be opened, the launcher prints the exact local URL and keeps
serving it.

CLI fallback:

```text
START_PORTFOLIO.cmd --cli
```

Diagnostics:

```text
START_PORTFOLIO.cmd --diagnostics
```

The four projects remain independent repositories and can be run directly from
their own roots. The `engineering-portfolio` operator can also invoke their
registered actions from this root while preserving each project's working
directory and authority. There is intentionally no global root demo and no
global pytest collection.

### Manual fallback

Use this only if the Windows launcher is unavailable:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m portfolio_operator.bootstrap
```

The integration check is observational with respect to persistent feedback. It
uses the effective NP02 local port (`NP02_DB_PORT`, otherwise the project
default `55433`), discovers four `var/latest_valid.json` pointers and records
only idempotent observations. It does not run or alter project code and does
not create feedback records. Existing synthetic feedback is retained only for
inspection and remains labelled `SYNTHETIC_INTEGRATION_VALIDATION`.

The CLI operator first screen is:

```text
Engineering Portfolio - Local Operator
1 NP01 Industrial Resilience OT Lab
2 NP02 Governed Data & Analytics
3 NP03 Governed AI Assurance
4 NP04 Architecture Decision Workbench
5 Project status / preflight
6 Results / observations
7 Feedback
8 Learning concepts
0 Exit
```

Use a project view to read its purpose, check readiness and choose an
intentional registered action. Only actions present in `portfolio.toml` are
offered. A replay uses the registered project's latest run identifier; a new
project run is created by that project and the parent is not overwritten.
An execution detail page updates its status in place; refreshing or reopening
that page only reads its receipt and never starts the action again.
Destructive cleanup requires explicit confirmation. Feedback is labelled
`HUMAN` only when entered by an operator; the four existing integration
validation examples remain `SYNTHETIC_INTEGRATION_VALIDATION`.

## Local web surface

The optional browser view uses FastAPI, Uvicorn, Jinja2 and vanilla
HTML/CSS/JavaScript. Start it only when the root optional dependencies are
installed:

```powershell
.\.venv\Scripts\python.exe scripts\run_web.py
```

It binds to `127.0.0.1` by default. It exposes project explanations, latest
results, logical run/evidence views, feedback, learning concepts and bounded
registered actions. It does not accept arbitrary shell strings, expose private
filesystem paths, or bind to `0.0.0.0` by default.

## NP02 local port semantics

NP02's project default PostgreSQL port is `55433`. This workstation currently
uses `55540` as a validated local host override because `55433` is reserved.
The override is not a universal default. When needed locally, set
`NP02_DB_PORT=55540` before an NP02 action; diagnostics shows whether an
override is configured and whether its local listener responds.

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
