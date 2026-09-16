from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .evidence import RunEvidence
from .registry import ProjectSpec


@dataclass(frozen=True)
class ObservationEnvelope:
    observation_id: str
    project_id: str
    run_id: str
    run_type: str
    status: str
    timestamp: str
    source_commit: str
    source_evidence_hash: str
    parent_run_id: str | None
    features: dict[str, int | float | bool | None]
    labels: dict[str, str]
    evidence_reference: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "run_type": self.run_type,
            "status": self.status,
            "timestamp": self.timestamp,
            "source_commit": self.source_commit,
            "source_evidence_hash": self.source_evidence_hash,
            "parent_run_id": self.parent_run_id,
            "features": self.features,
            "labels": self.labels,
            "evidence_reference": self.evidence_reference,
        }


def _value_string(value: object, fallback: str = "UNKNOWN") -> str:
    return value if isinstance(value, str) and value else fallback


def _source_commit(run: RunEvidence) -> str:
    version = run.manifest.get("code_version", {})
    if isinstance(version, dict):
        return _value_string(version.get("commit"))
    return _value_string(version)


def _base(spec: ProjectSpec, run: RunEvidence) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = run.manifest
    result = run.result
    status = _value_string(result.get("status", manifest.get("status")))
    scenario = _value_string(manifest.get("scenario", result.get("scenario")))
    run_type = "replay" if manifest.get("parent_run_id") else "canonical"
    source_hash = _value_string(manifest.get("evidence_hash", run.pointer.get("evidence_hash")))
    token = f"{spec.project_id}|{run.run_id}|{source_hash}".encode("utf-8")
    observation_id = "obs-" + hashlib.sha256(token).hexdigest()[:20]
    timestamp = _value_string(manifest.get("completed_at", manifest.get("started_at")), datetime.now(timezone.utc).isoformat())
    common = {
        "observation_id": observation_id,
        "project_id": spec.project_id,
        "run_id": run.run_id,
        "run_type": run_type,
        "status": status,
        "timestamp": timestamp,
        "source_commit": _source_commit(run),
        "source_evidence_hash": source_hash,
        "parent_run_id": manifest.get("parent_run_id") if isinstance(manifest.get("parent_run_id"), str) else None,
        "evidence_reference": str(run.run_root),
    }
    return common, {"scenario": scenario, "result": result.get("result_summary", {})}


def _finish(common: dict[str, Any], features: dict[str, Any], labels: dict[str, str]) -> ObservationEnvelope:
    clean_features: dict[str, int | float | bool | None] = {}
    for key, value in features.items():
        if isinstance(value, (int, float, bool)) or value is None:
            clean_features[key] = value
    return ObservationEnvelope(features=clean_features, labels=labels, **common)


def adapt_np01(spec: ProjectSpec, run: RunEvidence) -> ObservationEnvelope:
    common, data = _base(spec, run)
    summary = data["result"] if isinstance(data["result"], dict) else {}
    trace = summary.get("state_trace") if isinstance(summary.get("state_trace"), list) else []
    faults = summary.get("faults") if isinstance(summary.get("faults"), list) else []
    replay = summary.get("replay_digest")
    features = {
        "fault_count": len(faults),
        "state_transition_count": max(len(trace) - 1, 0),
        "validation_count": summary.get("validation_checks") if isinstance(summary.get("validation_checks"), int) else None,
        "replay_present": bool(replay),
    }
    labels = {
        "scenario": str(data["scenario"]),
        "recovery_status": "OBSERVED" if "RECOVERY" in trace else "UNKNOWN",
        "replay_result": "PASS" if replay else "UNKNOWN",
    }
    return _finish(common, features, labels)


def adapt_np02(spec: ProjectSpec, run: RunEvidence) -> ObservationEnvelope:
    common, data = _base(spec, run)
    summary = data["result"] if isinstance(data["result"], dict) else {}
    quality = summary.get("quality") if isinstance(summary.get("quality"), dict) else {}
    features = {
        "accepted": summary.get("accepted") if isinstance(summary.get("accepted"), int) else None,
        "quarantined": summary.get("quarantined") if isinstance(summary.get("quarantined"), int) else None,
        "rejected": summary.get("rejected") if isinstance(summary.get("rejected"), int) else None,
        "lineage_links": summary.get("lineage_link_count") if isinstance(summary.get("lineage_link_count"), int) else None,
        "kpi_count": len(summary.get("kpis", {})) if isinstance(summary.get("kpis"), dict) else 0,
    }
    labels = {
        "scenario": str(data["scenario"]),
        "quality_status": _value_string(summary.get("quality_status")),
        "lineage_status": _value_string(summary.get("lineage_status")),
        "kpi_status": _value_string(summary.get("kpi_status")),
        "quality_rules": str(len(quality)),
    }
    return _finish(common, features, labels)


def adapt_np03(spec: ProjectSpec, run: RunEvidence) -> ObservationEnvelope:
    common, data = _base(spec, run)
    summary = data["result"] if isinstance(data["result"], dict) else {}
    outcomes = summary.get("outcomes") if isinstance(summary.get("outcomes"), dict) else {}
    features = {
        "case_count": summary.get("case_count") if isinstance(summary.get("case_count"), int) else None,
        "supported": outcomes.get("SUPPORTED") if isinstance(outcomes.get("SUPPORTED"), int) else 0,
        "human_review_required": outcomes.get("HUMAN_REVIEW_REQUIRED") if isinstance(outcomes.get("HUMAN_REVIEW_REQUIRED"), int) else 0,
        "abstain": outcomes.get("ABSTAIN") if isinstance(outcomes.get("ABSTAIN"), int) else 0,
        "false_support": summary.get("false_support") if isinstance(summary.get("false_support"), int) else None,
        "replay_present": bool(summary.get("replay_digest")),
    }
    labels = {
        "scenario": str(data["scenario"]),
        "replay_idempotence": "PASS" if summary.get("replay_digest") else "UNKNOWN",
    }
    return _finish(common, features, labels)


def adapt_np04(spec: ProjectSpec, run: RunEvidence) -> ObservationEnvelope:
    common, data = _base(spec, run)
    summary = data["result"] if isinstance(data["result"], dict) else {}
    sensitivity = summary.get("sensitivity") if isinstance(summary.get("sensitivity"), list) else []
    changed = [item for item in sensitivity if isinstance(item, dict) and item.get("result") == "DECISION_CHANGED"]
    changed_assumption = str(changed[0].get("changed_assumption")) if changed else "NONE"
    decision_after = str(changed[0].get("replayed_decision")) if changed else _value_string(summary.get("preferred_option"))
    features = {
        "requirements": summary.get("requirements") if isinstance(summary.get("requirements"), int) else None,
        "fit_gap_rows": summary.get("fit_gap_rows") if isinstance(summary.get("fit_gap_rows"), int) else None,
        "traceability_rows": summary.get("traceability_rows") if isinstance(summary.get("traceability_rows"), int) else None,
        "sensitivity_cases": len(sensitivity),
        "decision_changed_cases": len(changed),
    }
    labels = {
        "scenario": str(data["scenario"]),
        "preferred_option": _value_string(summary.get("preferred_option")),
        "changed_assumption": changed_assumption,
        "decision_after": decision_after,
    }
    return _finish(common, features, labels)


def adapt_run(spec: ProjectSpec, run: RunEvidence) -> ObservationEnvelope:
    if not isinstance(run.result.get("result_summary"), dict):
        common, data = _base(spec, run)
        return _finish(common, {}, {"schema_status": "UNKNOWN_SCHEMA", "scenario": str(data["scenario"])})
    try:
        if spec.project_id == "NP01":
            return adapt_np01(spec, run)
        if spec.project_id == "NP02":
            return adapt_np02(spec, run)
        if spec.project_id == "NP03":
            return adapt_np03(spec, run)
        if spec.project_id == "NP04":
            return adapt_np04(spec, run)
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        pass
    common, data = _base(spec, run)
    return _finish(common, {}, {"schema_status": "UNKNOWN_SCHEMA", "scenario": str(data["scenario"])})
