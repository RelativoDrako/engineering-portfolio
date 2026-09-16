from pathlib import Path

import pytest

from portfolio_operator.adapters import ObservationEnvelope
from portfolio_operator.learning import (
    DeterministicGANGenerator,
    DeterministicVAEWorker,
    conceptual_model_metadata,
    deterministic_baseline,
    learning_summary,
    readiness_by_project,
)
from portfolio_operator.storage import FEEDBACK_SOURCES, OperatorStore, StorageError


def envelope(project_id: str = "NP01", run_id: str = "r1") -> ObservationEnvelope:
    return ObservationEnvelope(
        observation_id=f"obs-{project_id}-{run_id}", project_id=project_id, run_id=run_id,
        run_type="canonical", status="PASS", timestamp="2026-09-16T00:00:00Z",
        source_commit="abc", source_evidence_hash="hash", parent_run_id=None,
        features={"count": 3}, labels={"state": "PASS"}, evidence_reference="var/runs/r1",
    )


def test_observation_persistence_is_idempotent(tmp_path: Path):
    store = OperatorStore(tmp_path / "operator.sqlite3")
    item = envelope()
    assert store.record_observation(item) is True
    assert store.record_observation(item) is False
    assert len(store.observations()) == 1


def test_feedback_contract_and_persistence(tmp_path: Path):
    store = OperatorStore(tmp_path / "operator.sqlite3")
    assert store.record_feedback(feedback_id="fb-1", project_id="NP01", run_id="r1", classification="EXPECTED", explanation_useful="YES")
    assert not store.record_feedback(feedback_id="fb-1", project_id="NP01", run_id="r1", classification="EXPECTED", explanation_useful="YES")
    assert store.feedback()[0]["source"] == "HUMAN"
    assert store.feedback_counts() == {"HUMAN": 1}
    with pytest.raises(StorageError):
        store.record_feedback(feedback_id="fb-2", project_id="NP01", run_id="r1", classification="INVALID")
    with pytest.raises(StorageError):
        store.record_feedback(feedback_id="fb-3", project_id="NP01", run_id="r1", classification="EXPECTED", source="OTHER")
    assert FEEDBACK_SOURCES == {"HUMAN", "SYNTHETIC_INTEGRATION_VALIDATION"}


def test_legacy_integration_feedback_is_classified_on_schema_upgrade(tmp_path: Path):
    import sqlite3

    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE feedback (
                feedback_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                classification TEXT NOT NULL,
                explanation_useful TEXT,
                note TEXT,
                timestamp TEXT NOT NULL,
                UNIQUE(project_id, run_id, classification, note)
            )
            """
        )
        connection.execute(
            "INSERT INTO feedback VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("fb-old", "NP01", "r1", "KNOWN_TEST_SCENARIO", "YES", "Synthetic local integration review.", "2026-09-16T00:00:00Z"),
        )
    store = OperatorStore(path)
    assert store.feedback()[0]["source"] == "SYNTHETIC_INTEGRATION_VALIDATION"


def test_descriptive_baseline_and_vae_insufficient_data(tmp_path: Path):
    store = OperatorStore(tmp_path / "operator.sqlite3")
    store.record_observation(envelope())
    baseline = deterministic_baseline(store, "NP01")
    assert baseline["observations"] == 1
    assert "not predictive" in baseline["interpretation"].lower()
    rows = store.observations("NP01")
    from portfolio_operator.adapters import ObservationEnvelope as Envelope

    envs = [Envelope(observation_id=row["observation_id"], project_id=row["project_id"], run_id=row["run_id"], run_type=row["run_type"], status=row["status"], timestamp=row["timestamp"], source_commit=row["source_commit"], source_evidence_hash=row["source_evidence_hash"], parent_run_id=row["parent_run_id"], features=row["features"], labels=row["labels"], evidence_reference=row["evidence_reference"]) for row in rows]
    vae = DeterministicVAEWorker().evaluate(envs, namespace="NP01")
    assert vae["status"] == "CONCEPT_DEMONSTRATION"
    assert vae["data_readiness"] == "INSUFFICIENT_DATA"
    assert vae["trained"] is False
    assert learning_summary(store)["trained_models"] == 0
    assert learning_summary(store)["vae"]["status"] == "CONCEPT_DEMONSTRATION"
    cross_project = deterministic_baseline(store)
    assert cross_project["domain_scoped"] is True
    assert set(cross_project["feature_summary_by_project"]) == {"NP01", "NP02", "NP03", "NP04"}


def test_gan_candidate_is_not_evidence_and_needs_approval():
    candidate = DeterministicGANGenerator().propose(namespace="NP01")
    assert candidate["status"] == "SYNTHETIC_CANDIDATE"
    assert candidate["evidence"] is False
    assert candidate["requires_human_approval"] is True


def test_conceptual_model_metadata_is_untrained_and_non_authoritative():
    metadata = conceptual_model_metadata()
    assert {item["model_type"] for item in metadata} == {"VAE", "GAN"}
    assert all(item["state"] == "CONCEPT_DEMONSTRATION" for item in metadata)
    assert all(item["trained"] is False and item["active"] is False for item in metadata)
    assert all(item["artifact_hash"] is None for item in metadata)


def test_readiness_uses_concept_status_and_preserves_project_scope(tmp_path: Path):
    store = OperatorStore(tmp_path / "operator.sqlite3")
    states = readiness_by_project(store)
    assert set(states) == {"NP01", "NP02", "NP03", "NP04"}
    assert all(state["vae"]["status"] == "CONCEPT_DEMONSTRATION" for state in states.values())
    assert all(state["vae"]["data_readiness"] == "INSUFFICIENT_DATA" for state in states.values())
    assert all(state["gan"]["status"] == "CONCEPT_DEMONSTRATION" for state in states.values())


def test_model_lifecycle_requires_explicit_human_approval(tmp_path: Path):
    store = OperatorStore(tmp_path / "operator.sqlite3")
    store.register_model({
        "model_id": "vae-np01-v1",
        "model_type": "VAE",
        "project_domain": "NP01",
        "training_observations": 0,
        "feature_schema_version": "v1",
        "training_configuration": {"namespace": "NP01"},
        "evaluation_result": {"status": "INSUFFICIENT_DATA"},
        "state": "NOT_TRAINED",
    })
    with pytest.raises(StorageError):
        store.promote_model("vae-np01-v1", "ACTIVE")
    store.promote_model("vae-np01-v1", "CANDIDATE")
    store.promote_model("vae-np01-v1", "ACTIVE", human_approved=True)
    assert store.models()[0]["state"] == "ACTIVE"
