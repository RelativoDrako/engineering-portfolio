# Operator surface architecture

The surface is an adapter, not a fifth domain runtime.

```text
NP01 SQLite journal / PLC-edge state ─┐
NP02 PostgreSQL structured authority ─┤
NP03 assurance evaluation artifacts ──┼─> read-only adapters
NP04 SQLite decision traceability ────┘          │
                                                v
                              ObservationEnvelope + evidence references
                                                │
                             operator SQLite (observations/feedback/models)
                                                │
                  CLI / localhost web UI / deterministic descriptive learning
                                                │
                         conceptual VAE/GAN extension points
```

`portfolio.toml` is the only project registry. A project path is resolved
under the portfolio parent and an action is executable only when its fixed
argument array appears in the registry. Python entrypoints execute with an
explicit project working directory and `shell=False` (the default used by
`subprocess.run`). Browser POSTs select one of those registered actions; they
cannot submit a command string.

`START_PORTFOLIO.cmd` is a thin Windows entrypoint. It delegates environment
reuse/repair, port handling and UI startup to `portfolio_operator.bootstrap`.
It does not implement project orchestration or domain logic. The root
preflight reads project paths, local revisions, environment presence, local
service listeners and latest evidence without executing a domain scenario.

The root database contains references, run metadata and bounded features. It
does not copy source records, PLC state, PostgreSQL rows or assurance corpus
content. Evidence verification follows each project's existing `SHA256SUMS`
manifest without rewriting it.

The learning surface has five explicit layers: observed project runs, human
feedback, deterministic analytics, conceptual ML extensions and future
controlled operationalization. A derived observation is never a domain
authority, model inference is never project evidence, and a synthetic
candidate can never become evidence without a separately validated,
human-approved project execution.

### Operator lifecycle

1. Load and validate the registry.
2. Resolve a project's latest-valid pointer inside its own evidence root.
3. Read `run_manifest.json`, `result.json`, `validation.json` and hashes.
4. Adapt the domain result into a normalized observation envelope.
5. Persist the envelope idempotently in the operator store.
6. Let a human run a registered action or record feedback.

The four existing integration-validation feedback rows are marked
`SYNTHETIC_INTEGRATION_VALIDATION`; future operator entries are marked
`HUMAN`. Normal integration validation does not create persistent feedback.
Neither source triggers automatic retraining.

Actions that may remove runtime resources are confirmation-gated. Failed
subprocesses are reported with stage, exit status, stdout/stderr and the
bounded evidence reference; the root surface never rolls back a project run.
