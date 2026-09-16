from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .registry import ProjectSpec


class EvidenceError(ValueError):
    """Raised when a project evidence reference cannot be safely followed."""


@dataclass(frozen=True)
class RunEvidence:
    project_id: str
    run_id: str
    run_root: Path
    manifest: dict[str, Any]
    result: dict[str, Any]
    validation: dict[str, Any]
    pointer: dict[str, Any]


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise EvidenceError(f"expected JSON object: {path}")
    return value


def load_latest(spec: ProjectSpec) -> RunEvidence | None:
    pointer_path = spec.latest_pointer
    if not pointer_path.exists():
        return None
    pointer = _read_json(pointer_path)
    run_id = pointer.get("run_id")
    if not isinstance(run_id, str) or not run_id or Path(run_id).name != run_id:
        raise EvidenceError(f"invalid run_id in latest pointer for {spec.project_id}")
    run_root = (spec.evidence_root / run_id).resolve()
    if not run_root.is_relative_to(spec.evidence_root.resolve()):
        raise EvidenceError("latest pointer escapes evidence root")
    manifest_path = run_root / "run_manifest.json"
    result_path = run_root / "result.json"
    validation_path = run_root / "validation.json"
    if not all(path.exists() for path in (manifest_path, result_path, validation_path)):
        raise EvidenceError(f"incomplete run bundle: {run_root}")
    manifest = _read_json(manifest_path)
    result = _read_json(result_path)
    validation = _read_json(validation_path)
    return RunEvidence(spec.project_id, run_id, run_root, manifest, result, validation, pointer)


def list_runs(spec: ProjectSpec) -> list[str]:
    root = spec.evidence_root
    if not root.exists():
        return []
    return sorted(
        (item.name for item in root.iterdir() if item.is_dir() and (item / "run_manifest.json").exists()),
        reverse=True,
    )


def verify_sha256sums(run: RunEvidence) -> dict[str, Any]:
    sums_path = run.run_root / "SHA256SUMS"
    if not sums_path.exists():
        return {"status": "FAIL", "checked": 0, "mismatches": ["SHA256SUMS missing"]}
    checked = 0
    mismatches: list[str] = []
    for raw_line in sums_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            expected, relative = line.split(maxsplit=1)
        except ValueError:
            mismatches.append(f"malformed line: {line}")
            continue
        relative = relative.lstrip(" *")
        target = (run.run_root / relative).resolve()
        if not target.is_relative_to(run.run_root.resolve()) or not target.is_file():
            mismatches.append(relative)
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        checked += 1
        if digest.lower() != expected.lower():
            mismatches.append(relative)
    return {"status": "PASS" if not mismatches and checked > 0 else "FAIL", "checked": checked, "mismatches": mismatches}


def compact_run_summary(run: RunEvidence) -> dict[str, Any]:
    summary = run.result.get("result_summary")
    if not isinstance(summary, dict):
        summary = {}
    return {
        "project_id": run.project_id,
        "run_id": run.run_id,
        "status": run.result.get("status", run.manifest.get("status", "UNKNOWN")),
        "scenario": run.result.get("scenario", run.manifest.get("scenario", "UNKNOWN")),
        "domain_authority": run.result.get("domain_authority", run.manifest.get("domain_authority", "UNKNOWN")),
        "result_summary": summary,
        "validation_summary": run.validation,
        "evidence_path": str(run.run_root),
        "evidence_hash": run.manifest.get("evidence_hash", run.pointer.get("evidence_hash")),
        "replay_command": run.manifest.get("replay_command"),
    }
