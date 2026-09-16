from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from statistics import mean
from typing import Any, Protocol, Sequence

from .adapters import ObservationEnvelope
from .storage import OperatorStore


PROJECT_IDS = ("NP01", "NP02", "NP03", "NP04")

LEARNING_LAYERS = (
    {
        "number": 1,
        "name": "Observed runs",
        "kind": "PROJECT_EVIDENCE",
        "description": "Actual execution-derived observations imported through the four project adapters.",
    },
    {
        "number": 2,
        "name": "Human feedback",
        "kind": "HUMAN_FEEDBACK",
        "description": "Explicit operator assessment of a known run; it never retrains a model automatically.",
    },
    {
        "number": 3,
        "name": "Deterministic analytics",
        "kind": "DETERMINISTIC_ANALYSIS",
        "description": "Inspectable summaries, run-to-run deltas and bounded descriptive warnings.",
    },
    {
        "number": 4,
        "name": "Conceptual ML extensions",
        "kind": "MODEL_INFERENCE",
        "description": "VAE representation/anomaly concepts and GAN synthetic-candidate concepts only.",
    },
    {
        "number": 5,
        "name": "Future controlled operationalization",
        "kind": "FUTURE_CONTROLLED_OPERATIONALIZATION",
        "description": "A future stage requiring sufficient observations, evaluation criteria, resources and human approval.",
    },
)

PROJECT_AUTHORITIES = {
    "NP01": "SQLite journal / PLC-edge execution state",
    "NP02": "PostgreSQL structured authority",
    "NP03": "assurance evaluation artifacts",
    "NP04": "SQLite decision-traceability state",
}

VAE_CONCEPT_EXAMPLE = {
    "label": "EXAMPLE_ONLY",
    "domain": "NP02",
    "flow": [
        "NP02 historical observations",
        "compatible feature vectors",
        "VAE encoder",
        "latent representation",
        "reconstruction",
        "reconstruction difference",
        "anomaly signal",
        "human inspection",
    ],
    "features": [
        "accepted ratio",
        "quarantined ratio",
        "rejected ratio",
        "quality outcomes",
        "lineage status",
        "KPI status",
    ],
    "interpretation": "This run differs materially from previously observed NP02 patterns; the largest differences could be rejection ratio and referential-integrity failures.",
    "boundary": "An anomaly signal is not a diagnosis and does not establish correct, incorrect, safe or unsafe behavior.",
    "no_model_was_trained": True,
    "no_anomaly_score_is_real": True,
}

GAN_CONCEPT_EXAMPLE = {
    "label": "EXAMPLE_ONLY",
    "domain": "NP01",
    "candidate": {
        "sensor_fluctuation": "bounded synthetic variation",
        "communication_delay": "bounded synthetic delay",
        "tank_level_sequence": "abnormal but schema-valid sequence",
    },
    "flow": [
        "SYNTHETIC_CANDIDATE",
        "schema validation",
        "domain constraint validation",
        "human review",
        "explicit human approval",
        "NP01 execution",
        "actual run",
        "actual validation",
        "evidence bundle",
    ],
    "authority": "NONE",
    "auto_execution": False,
    "auto_promotion_to_fixture": False,
    "auto_evidence_creation": False,
}


def conceptual_model_metadata() -> list[dict[str, Any]]:
    """Return non-trained extension points without registering model artifacts."""

    return [
        {
            "model_id": "VAE_NP02_CONCEPT",
            "model_type": "VAE",
            "domain": "NP02",
            "state": "CONCEPT_DEMONSTRATION",
            "trained": False,
            "active": False,
            "artifact_hash": None,
            "purpose": "Future representation/anomaly signal for compatible NP02 run patterns.",
            "limitations": "No model is trained; data readiness is currently insufficient.",
        },
        {
            "model_id": "GAN_NP01_CONCEPT",
            "model_type": "GAN",
            "domain": "NP01",
            "state": "CONCEPT_DEMONSTRATION",
            "trained": False,
            "active": False,
            "artifact_hash": None,
            "purpose": "Future proposal of bounded synthetic NP01 fault scenarios.",
            "limitations": "Candidates are not evidence and require validation plus human approval before execution.",
        },
    ]


PROJECT_LEARNING_EXPLANATIONS = {
    "NP01": {
        "observed_today": "faults, state transitions, recovery, validation and replay",
        "vae": "A future compatible history could highlight unusual NP01 run patterns.",
        "gan": "A future generator could propose synthetic fault scenarios for human-reviewed testing.",
    },
    "NP02": {
        "observed_today": "accepted, quarantined and rejected records, quality, lineage and KPIs",
        "vae": "A future compatible history could highlight unusual pipeline/run profiles.",
        "gan": "A future generator could propose bounded synthetic source-data scenarios.",
    },
    "NP03": {
        "observed_today": "SUPPORTED, HUMAN_REVIEW_REQUIRED, ABSTAIN, false-support behavior and replay",
        "vae": "A future compatible history could highlight unusual assurance-run patterns.",
        "gan": "A future generator could propose bounded synthetic evaluation cases; generated answers would not be evidence.",
    },
    "NP04": {
        "observed_today": "requirements, fit-gap, traceability, preferred option and sensitivity changes",
        "vae": "A future compatible history could highlight unusual decision-analysis configurations.",
        "gan": "A future generator could propose synthetic bounded assumption/scenario combinations for human review.",
    },
}


class VAEWorker(Protocol):
    def evaluate(self, observations: Sequence[ObservationEnvelope], *, namespace: str) -> dict[str, Any]: ...


class GANScenarioGenerator(Protocol):
    def propose(self, *, namespace: str, feature_schema_version: str = "v1") -> dict[str, Any]: ...


@dataclass(frozen=True)
class DeterministicVAEWorker:
    minimum_observations: int = 5

    def evaluate(self, observations: Sequence[ObservationEnvelope], *, namespace: str) -> dict[str, Any]:
        return {
            "status": "CONCEPT_DEMONSTRATION",
            "namespace": namespace,
            "observations_available": len(observations),
            "data_readiness": "READY_FOR_REVIEW" if len(observations) >= self.minimum_observations else "INSUFFICIENT_DATA",
            "trained": False,
            "active": False,
            "reason": "No VAE is trained; the interface demonstrates where a future compatible representation-learning extension could fit without fabricating rows.",
            "required_before_training": [
                "more real bounded runs",
                "stable compatible feature schema",
                "representative variation",
                "train/evaluation split",
                "evaluation criteria",
                "resource justification",
                "human approval",
            ],
        }


@dataclass(frozen=True)
class DeterministicGANGenerator:
    def propose(self, *, namespace: str, feature_schema_version: str = "v1") -> dict[str, Any]:
        seed = hashlib.sha256(f"{namespace}|{feature_schema_version}".encode("utf-8")).hexdigest()[:16]
        return {
            "status": "SYNTHETIC_CANDIDATE",
            "candidate_id": f"candidate-{seed}",
            "namespace": namespace,
            "feature_schema_version": feature_schema_version,
            "requires_schema_validation": True,
            "requires_human_approval": True,
            "evidence": False,
            "executed": False,
        }


def numeric_features(observations: Sequence[dict[str, Any]]) -> dict[str, dict[str, float | int | None]]:
    values: dict[str, list[float]] = {}
    for observation in observations:
        for key, value in (observation.get("features") or {}).items():
            if isinstance(value, bool):
                values.setdefault(key, []).append(float(value))
            elif isinstance(value, (int, float)):
                values.setdefault(key, []).append(float(value))
    return {
        key: {
            "count": len(items),
            "min": min(items) if items else None,
            "max": max(items) if items else None,
            "mean": round(mean(items), 6) if items else None,
        }
        for key, items in sorted(values.items())
    }


def deterministic_baseline(store: OperatorStore, project_id: str | None = None) -> dict[str, Any]:
    observations = store.observations(project_id)
    # Keep feature semantics domain-scoped.  A cross-project view reports one
    # summary per project rather than treating unlike counts as one vector.
    summaries_by_project = (
        {project_id: numeric_features(observations)}
        if project_id
        else {
            item: numeric_features(store.observations(item))
            for item in PROJECT_IDS
        }
    )
    summary = summaries_by_project.get(project_id, {}) if project_id else {}
    warnings: list[str] = []
    for namespace, namespace_summary in summaries_by_project.items():
        for key, stats in namespace_summary.items():
            if stats["min"] is not None and stats["max"] is not None and stats["min"] != stats["max"]:
                warnings.append(f"{namespace}.{key}: observed change from {stats['min']} to {stats['max']}")
    return {
        "observations": len(observations),
        "feature_summary": summary,
        "feature_summary_by_project": summaries_by_project,
        "change_indicators": warnings,
        "analysis_type": "DETERMINISTIC_DESCRIPTIVE",
        "interpretation": "Descriptive run-scoped analysis; not predictive intelligence, model inference, diagnosis or decision authority.",
        "project_evidence": False,
        "domain_scoped": True,
    }


def readiness_by_project(store: OperatorStore) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for project_id in PROJECT_IDS:
        rows = store.observations(project_id)
        envelopes = []
        for row in rows:
            envelopes.append(
                ObservationEnvelope(
                    observation_id=row["observation_id"], project_id=row["project_id"], run_id=row["run_id"],
                    run_type=row["run_type"], status=row["status"], timestamp=row["timestamp"],
                    source_commit=row["source_commit"], source_evidence_hash=row["source_evidence_hash"],
                    parent_run_id=row["parent_run_id"], features=row["features"], labels=row["labels"],
                    evidence_reference=row["evidence_reference"],
                )
            )
        vae = DeterministicVAEWorker().evaluate(envelopes, namespace=project_id)
        result[project_id] = {
            "observations_available": len(rows),
            "vae": vae,
            "gan": {
                "status": "CONCEPT_DEMONSTRATION",
                "candidate_status": "SYNTHETIC_CANDIDATE",
                "generated": False,
                "requires_schema_validation": True,
                "requires_human_approval": True,
                "authority": "NONE",
                "evidence": False,
                "executed": False,
            },
        }
    return result


def project_learning_explanation(project_id: str) -> dict[str, str]:
    return PROJECT_LEARNING_EXPLANATIONS.get(
        project_id,
        {
            "observed_today": "No project-specific observation explanation is registered.",
            "vae": "No VAE concept is registered for this project.",
            "gan": "No GAN concept is registered for this project.",
        },
    )


def learning_summary(store: OperatorStore) -> dict[str, Any]:
    observations = store.observations()
    feedback_counts = store.feedback_counts()
    return {
        "observed_runs": len(observations),
        "human_feedback": feedback_counts.get("HUMAN", 0),
        "synthetic_validation_feedback": feedback_counts.get("SYNTHETIC_INTEGRATION_VALIDATION", 0),
        "active_analysis": "DETERMINISTIC_DESCRIPTIVE",
        "trained_models": 0,
        "active_models": 0,
        "generated_evidence": 0,
        "layers": list(LEARNING_LAYERS),
        "project_authorities": dict(PROJECT_AUTHORITIES),
        "vae": {
            "role": "CONCEPT_DEMONSTRATION",
            "status": "CONCEPT_DEMONSTRATION",
            "trained": False,
            "data_readiness_by_project": {
                project_id: (
                    "READY_FOR_REVIEW"
                    if len(store.observations(project_id)) >= DeterministicVAEWorker.minimum_observations
                    else "INSUFFICIENT_DATA"
                )
                for project_id in PROJECT_IDS
            },
        },
        "gan": {
            "role": "CONCEPT_DEMONSTRATION",
            "status": "CONCEPT_DEMONSTRATION",
            "training_readiness": "NOT_EVALUATED_OPERATIONAL_TRAINING_OUT_OF_SCOPE",
            "trained": False,
            "generated_evidence": 0,
        },
        "boundaries": {
            "model_inference_is_project_evidence": False,
            "synthetic_candidate_is_project_evidence": False,
            "derived_observation_is_domain_authority": False,
            "human_feedback_triggers_automatic_retraining": False,
        },
    }
