from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .adapters import ObservationEnvelope
from .config import DATABASE_PATH, ensure_runtime_dirs


FEEDBACK_CLASSIFICATIONS = frozenset({"EXPECTED", "UNEXPECTED", "NEEDS_INVESTIGATION", "KNOWN_TEST_SCENARIO"})
EXPLANATION_VALUES = frozenset({"YES", "PARTIAL", "NO"})
FEEDBACK_SOURCES = frozenset({"HUMAN", "SYNTHETIC_INTEGRATION_VALIDATION"})
MODEL_STATES = frozenset({"NOT_TRAINED", "CANDIDATE", "VALIDATED", "ACTIVE", "RETIRED"})


class StorageError(ValueError):
    pass


class OperatorStore:
    """SQLite store for integration-surface state, never domain authority."""

    def __init__(self, path: Path = DATABASE_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _init_schema(self) -> None:
        ensure_runtime_dirs()
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS observations (
                    observation_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    run_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source_commit TEXT NOT NULL,
                    source_evidence_hash TEXT NOT NULL,
                    parent_run_id TEXT,
                    features_json TEXT NOT NULL,
                    labels_json TEXT NOT NULL,
                    evidence_reference TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(project_id, run_id)
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    explanation_useful TEXT,
                    note TEXT,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'HUMAN',
                    UNIQUE(project_id, run_id, classification, note)
                );
                CREATE TABLE IF NOT EXISTS operator_sessions (
                    session_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    metadata_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS model_metadata (
                    model_id TEXT PRIMARY KEY,
                    model_type TEXT NOT NULL,
                    project_domain TEXT NOT NULL,
                    training_observations INTEGER NOT NULL,
                    feature_schema_version TEXT NOT NULL,
                    training_configuration TEXT NOT NULL,
                    artifact_hash TEXT,
                    evaluation_result TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            # The four existing integration records predate source tracking.
            # Backfill only their distinctive validation note; unknown legacy
            # rows retain the safe HUMAN default.
            columns = {row[1] for row in connection.execute("PRAGMA table_info(feedback)")}
            if "source" not in columns:
                connection.execute("ALTER TABLE feedback ADD COLUMN source TEXT NOT NULL DEFAULT 'HUMAN'")
            connection.execute(
                """
                UPDATE feedback
                   SET source = 'SYNTHETIC_INTEGRATION_VALIDATION'
                 WHERE lower(coalesce(note, '')) LIKE 'synthetic local integration review%'
                """
            )

    def record_observation(self, envelope: ObservationEnvelope) -> bool:
        created = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO observations
                (observation_id, project_id, run_id, run_type, status, timestamp,
                 source_commit, source_evidence_hash, parent_run_id, features_json,
                 labels_json, evidence_reference, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    envelope.observation_id,
                    envelope.project_id,
                    envelope.run_id,
                    envelope.run_type,
                    envelope.status,
                    envelope.timestamp,
                    envelope.source_commit,
                    envelope.source_evidence_hash,
                    envelope.parent_run_id,
                    json.dumps(envelope.features, sort_keys=True),
                    json.dumps(envelope.labels, sort_keys=True),
                    envelope.evidence_reference,
                    created,
                ),
            )
            return cursor.rowcount == 1

    def observations(self, project_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM observations"
        params: tuple[Any, ...] = ()
        if project_id:
            query += " WHERE project_id = ?"
            params = (project_id,)
        query += " ORDER BY timestamp, observation_id"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["features"] = json.loads(item.pop("features_json"))
            item["labels"] = json.loads(item.pop("labels_json"))
            result.append(item)
        return result

    def record_feedback(
        self,
        *,
        feedback_id: str,
        project_id: str,
        run_id: str,
        classification: str,
        explanation_useful: str | None = None,
        note: str | None = None,
        timestamp: str | None = None,
        source: str = "HUMAN",
    ) -> bool:
        if classification not in FEEDBACK_CLASSIFICATIONS:
            raise StorageError(f"invalid feedback classification: {classification}")
        if explanation_useful is not None and explanation_useful not in EXPLANATION_VALUES:
            raise StorageError(f"invalid explanation_useful: {explanation_useful}")
        if source not in FEEDBACK_SOURCES:
            raise StorageError(f"invalid feedback source: {source}")
        stamp = timestamp or datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO feedback
                (feedback_id, project_id, run_id, classification, explanation_useful, note, timestamp, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (feedback_id, project_id, run_id, classification, explanation_useful, note, stamp, source),
            )
            return cursor.rowcount == 1

    def feedback(self, project_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM feedback"
        params: tuple[Any, ...] = ()
        if project_id:
            query += " WHERE project_id = ?"
            params = (project_id,)
        query += " ORDER BY timestamp, feedback_id"
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(query, params).fetchall()]

    def feedback_counts(self) -> dict[str, int]:
        """Count feedback by declared source; feedback is not project evidence."""

        with self._connect() as connection:
            rows = connection.execute("SELECT source, COUNT(*) AS count FROM feedback GROUP BY source").fetchall()
        return {str(row[0]): int(row[1]) for row in rows}

    def register_model(self, metadata: dict[str, Any]) -> None:
        state = str(metadata.get("state", "NOT_TRAINED"))
        if state not in MODEL_STATES:
            raise StorageError(f"invalid model state: {state}")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO model_metadata
                (model_id, model_type, project_domain, training_observations,
                 feature_schema_version, training_configuration, artifact_hash,
                 evaluation_result, state, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(model_id) DO UPDATE SET
                  evaluation_result=excluded.evaluation_result,
                  artifact_hash=excluded.artifact_hash,
                  state=excluded.state
                """,
                (
                    str(metadata["model_id"]),
                    str(metadata["model_type"]),
                    str(metadata["project_domain"]),
                    int(metadata.get("training_observations", 0)),
                    str(metadata.get("feature_schema_version", "v1")),
                    json.dumps(metadata.get("training_configuration", {}), sort_keys=True),
                    metadata.get("artifact_hash"),
                    json.dumps(metadata.get("evaluation_result", {}), sort_keys=True),
                    state,
                    str(metadata.get("created_at", datetime.now(timezone.utc).isoformat())),
                ),
            )

    def promote_model(self, model_id: str, target_state: str, *, human_approved: bool = False) -> None:
        if target_state not in MODEL_STATES:
            raise StorageError(f"invalid model state: {target_state}")
        if target_state == "ACTIVE" and not human_approved:
            raise StorageError("ACTIVE promotion requires explicit human approval")
        with self._connect() as connection:
            row = connection.execute("SELECT state FROM model_metadata WHERE model_id = ?", (model_id,)).fetchone()
            if row is None:
                raise StorageError(f"unknown model: {model_id}")
            connection.execute("UPDATE model_metadata SET state = ? WHERE model_id = ?", (target_state, model_id))

    def models(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM model_metadata ORDER BY created_at, model_id").fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["training_configuration"] = json.loads(item["training_configuration"])
            item["evaluation_result"] = json.loads(item["evaluation_result"])
            result.append(item)
        return result
