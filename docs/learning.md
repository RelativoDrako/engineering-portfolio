# Learning, feedback and evidence contract

The four projects produce the evidence. `engineering-portfolio` only
collects small derived observations, displays them and retains operator
feedback. It is an integration/operator surface, not a domain authority.

## Five layers

1. **Observed runs** — actual execution-derived observations imported through
   the four project adapters.
2. **Human feedback** — an explicit operator assessment of a known run.
3. **Deterministic analytics** — descriptive summaries, run-to-run deltas and
   bounded warning signals. This is the only active analysis today.
4. **Conceptual ML extensions** — a VAE representation/anomaly concept and a
   GAN synthetic-candidate concept. No model is trained.
5. **Future controlled operationalization** — a possible later stage, only
   after sufficient observations, a compatible feature schema, evaluation
   criteria, resource justification, bounded testing and human approval.

## Evidence boundaries

The four authorities remain separate:

| Project | Domain authority |
| --- | --- |
| NP01 | SQLite journal / PLC-edge execution state |
| NP02 | PostgreSQL structured authority |
| NP03 | Assurance evaluation artifacts |
| NP04 | SQLite decision-traceability state |

`PROJECT_EVIDENCE` means facts produced by an actual project execution.
`DERIVED_OBSERVATION` is a normalized representation for comparison and is
not domain authority. `MODEL_INFERENCE` is future statistical/ML
interpretation, not evidence. `SYNTHETIC_CANDIDATE` is a hypothetical future
scenario, never evidence. `HUMAN_FEEDBACK` is explicit assessment and is not
an automatic retraining signal.

In short:

```text
MODEL_INFERENCE != PROJECT_EVIDENCE
SYNTHETIC_CANDIDATE != PROJECT_EVIDENCE
DERIVED_OBSERVATION != DOMAIN_AUTHORITY
HUMAN_FEEDBACK != AUTOMATIC_RETRAINING_SIGNAL
```

## Observations and feedback

Every adapter emits `observation_id`, `project_id`, `run_id`, `run_type`,
`status`, `timestamp`, `source_commit`, `source_evidence_hash`,
`parent_run_id`, `features`, `labels` and `evidence_reference`. The
identifier is deterministic for a project/run/evidence-hash tuple, so reading
the same latest pointer twice is idempotent.

Feedback classifications are `EXPECTED`, `UNEXPECTED`,
`NEEDS_INVESTIGATION` and `KNOWN_TEST_SCENARIO`. Optional
`explanation_useful` values are `YES`, `PARTIAL` or `NO`, with an optional
note. Each record also declares its source:

* `HUMAN` — a future real operator assessment;
* `SYNTHETIC_INTEGRATION_VALIDATION` — the four existing bounded records from
  earlier integration validation.

Neither source changes project evidence or triggers retraining. Normal
integration validation is read-only with respect to persistent feedback and
does not recreate these records.

## Deterministic analysis

The active baseline is **DETERMINISTIC_DESCRIPTIVE**. It reports feature
counts, ranges, means, observed changes and bounded rule indications. It is
run-scoped and inspectable; it is not machine learning, prediction, diagnosis
or automated decision authority. The surface does not combine unrelated
cross-domain fields into one training vector.

## VAE concept (not trained)

A Variational Autoencoder could eventually learn what compatible historical
runs tend to look like within one domain and highlight a materially different
pattern. It would indicate “different from previously observed patterns”,
not “correct”, “incorrect”, “safe” or “unsafe”.

The one bounded example shown by the operator is NP02:

```text
NP02 historical observations
  -> compatible feature vectors (accepted/quarantined/rejected ratios,
     quality outcomes, lineage status, KPI status)
  -> VAE encoder -> latent representation -> reconstruction
  -> reconstruction difference -> anomaly signal -> human inspection
```

This is `EXAMPLE_ONLY`: no model was trained and no anomaly score is real.
Each project currently has one observed run, which is insufficient for
defensible representation learning. Readiness therefore remains
`INSUFFICIENT_DATA` for NP01, NP02, NP03 and NP04. A future training decision
would need more real bounded runs, a stable compatible schema, representative
variation, a train/evaluation split, evaluation criteria, resource
justification and human approval. No arbitrary minimum row count is claimed.

## GAN concept (not trained)

A future generative model could propose a new synthetic candidate scenario.
The one bounded example shown is NP01: bounded sensor fluctuation,
communication delay and an abnormal tank-level sequence. The candidate must
be labelled `SYNTHETIC_CANDIDATE` and follow this path:

```text
synthetic candidate -> schema validation -> domain constraint validation
  -> human review -> explicit human approval -> NP01 execution
  -> actual validation -> evidence bundle
```

GAN output authority is `NONE`. Auto-execution, promotion to a test fixture,
automatic evidence creation and automatic feedback acceptance are all `NO`.
Operational GAN training readiness is not evaluated in this surface and no
candidate fixture is executed.

## Model metadata

The model page exposes two conceptual interfaces (`VAE_NP02_CONCEPT` and
`GAN_NP01_CONCEPT`) with state `CONCEPT_DEMONSTRATION`, `trained=false`,
`active=false` and no artifact hash. They are extension contracts, not model
artifacts. The registered model table remains available for a future,
explicitly approved lifecycle; it currently contains no trained models.

## Project-specific learning explanations

* **NP01** observes faults, state transitions, recovery, validation and
  replay. A future VAE could highlight unusual run patterns; a future GAN
  could propose synthetic fault scenarios for human-reviewed testing.
* **NP02** observes accepted/quarantined/rejected records, quality, lineage
  and KPIs. A future VAE could highlight unusual pipeline profiles; a future
  GAN could propose bounded synthetic source-data scenarios.
* **NP03** observes `SUPPORTED`, `HUMAN_REVIEW_REQUIRED`, `ABSTAIN`,
  false-support behavior and replay. A future VAE could highlight unusual
  assurance-run patterns; a future GAN could propose bounded synthetic
  evaluation cases, with no generated answer becoming evidence.
* **NP04** observes requirements, fit-gap, traceability, preferred option and
  sensitivity changes. A future VAE could highlight unusual decision-analysis
  configurations; a future GAN could propose bounded assumption/scenario
  combinations for human review.

These possibilities are domain-specific; not every project would benefit
equally from either approach.
