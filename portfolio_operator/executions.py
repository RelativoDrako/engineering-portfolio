"""Local, typed execution records for the root operator surface.

This module observes registered project actions.  It never becomes a project
authority: each receipt references, rather than copies, project evidence.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from .config import ROOT_DIR, VAR_DIR
from .evidence import load_latest, verify_sha256sums
from .registry import DESTRUCTIVE_ACTIONS, ProjectSpec
from .runner import ActionResult, run_registered_action
from .storage import OperatorStore

STATUS_VALUES = frozenset({"NOT_CHECKED", "READY", "RUNNING", "PASS", "FAIL", "BLOCKED", "NOT_APPLICABLE", "CANCELLED", "UNKNOWN_ERROR"})
READ_ONLY_ACTIONS = frozenset({"latest", "verify", "runs", "explain", "setup", "preflight"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _execution_id(project_id: str, action: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    suffix = hashlib.sha256(f"{stamp}|{project_id}|{action}".encode()).hexdigest()[:8]
    return f"op-{stamp}-{project_id.lower()}-{suffix}"


def _commit(path: Path) -> str:
    try:
        completed = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return "UNRESOLVED"
    return completed.stdout.strip() if completed.returncode == 0 and completed.stdout.strip() else "UNRESOLVED"


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except ValueError:
        return path.name


def _sanitize(value: str) -> str:
    # Absolute local paths and common secret-shaped values must not reach receipts/UI.
    import re
    value = re.sub(r"(?i)[a-z]:[\\/][^\s\"']+", "<local path>", value)
    value = re.sub(r"(?i)(password|token|secret|api[_-]?key)\s*[=:]\s*[^\s]+", r"\1=<redacted>", value)
    return value[-8000:]


def _reason(result: ActionResult) -> str | None:
    text = f"{result.result_summary}\n{result.stderr}".lower()
    if result.status == "PASS":
        return None
    if result.status == "ABORTED":
        return "OPERATION_TIMEOUT" if "timeout" in text else "DESTRUCTIVE_CONFIRMATION_REQUIRED"
    if "no latest valid run" in text:
        return "RESULT_NOT_FOUND"
    if "execution error" in text:
        return "PROCESS_START_FAILED"
    if "connection" in text or "postgres" in text or "docker" in text or "service" in text:
        return "SERVICE_NOT_READY"
    return "PROCESS_EXIT_NONZERO"


def _typed_status(result: ActionResult) -> str:
    if result.status == "PASS":
        return "PASS"
    if result.status == "ABORTED":
        return "BLOCKED" if "timeout" not in result.result_summary.lower() else "FAIL"
    return "FAIL"


def _human_projection(spec: ProjectSpec, action: str, result: ActionResult, latest: Any | None) -> tuple[str, str]:
    if result.status != "PASS":
        return (
            "The registered action did not complete successfully. Review the stated reason before retrying.",
            _sanitize(result.result_summary or "The process returned a non-success status."),
        )
    if action == "verify":
        return ("The latest project evidence manifest was checked for integrity.", _sanitize(result.result_summary))
    if action == "latest":
        if latest is None:
            return ("No latest valid project run is currently available.", "No project result could be interpreted.")
        values = latest.result if isinstance(latest.result, dict) else {}
        if spec.project_id == "NP01":
            return ("The latest industrial scenario is available with its recorded control-state, fault, recovery and validation evidence.", "NP01 result fields were read from the latest project result.")
        if spec.project_id == "NP02":
            return ("The latest data lifecycle result is available, including its recorded disposition, quality, lineage and KPI evidence.", "NP02 result fields were read from the latest project result.")
        if spec.project_id == "NP03":
            return ("The latest assurance evaluation is available with supported, human-review and abstention outcomes.", "NP03 result fields were read from the latest project result.")
        if spec.project_id == "NP04":
            return ("The latest architecture decision result is available with requirements, fit-gap, traceability and sensitivity evidence.", "NP04 result fields were read from the latest project result.")
        return ("The latest registered project result is available.", json.dumps(values, sort_keys=True)[:1000])
    return ("The registered project action completed. Its result and evidence references are recorded below.", _sanitize(result.result_summary))


class ExecutionManager:
    """One in-process execution owner with project-local concurrency locks."""

    def __init__(self, store: OperatorStore, receipts_root: Path | None = None):
        self.store = store
        self.receipts_root = receipts_root or (VAR_DIR / "operator_runs")
        self.receipts_root.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def _lock(self, project_id: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(project_id, threading.Lock())

    def start(self, spec: ProjectSpec, action: str, *, confirm: bool = False) -> dict[str, Any]:
        if action not in spec.supported_actions:
            raise ValueError("ACTION_NOT_REGISTERED")
        execution_id = _execution_id(spec.project_id, action)
        started = _utc_now()
        record = {
            "execution_id": execution_id, "project_id": spec.project_id, "action_id": action,
            "status": "READY", "reason_code": None, "started_at": started, "completed_at": None,
            "duration_ms": None, "source_commit": _commit(spec.path), "cwd_relative": spec.relative_path,
            "sanitized_argv_json": json.dumps(["registered", action]), "exit_code": None,
            "human_summary": "The registered action is queued for this independent project.",
            "technical_summary": "Awaiting local execution.", "project_run_id": None,
            "evidence_hash": None, "evidence_reference": None, "operator_result_hash": None,
            "stage_json": json.dumps([{"stage": "Starting", "status": "READY", "at": started}]),
            "receipt_reference": None,
        }
        self.store.record_execution(record)
        thread = threading.Thread(target=self._execute, args=(execution_id, spec, action, confirm), daemon=True)
        thread.start()
        return self.view(execution_id) or record

    def _append_stage(self, record: dict[str, Any], stage: str, status: str) -> None:
        stages = record["stages"] if "stages" in record else json.loads(record["stage_json"])
        stages.append({"stage": stage, "status": status, "at": _utc_now()})
        record["stages"] = stages
        record["stage_json"] = json.dumps(stages)

    def _persist(self, record: dict[str, Any]) -> None:
        copy = dict(record)
        copy["sanitized_argv_json"] = json.dumps(copy.get("sanitized_argv", json.loads(copy.get("sanitized_argv_json", "[]"))))
        copy["stage_json"] = json.dumps(copy.get("stages", json.loads(copy.get("stage_json", "[]"))))
        self.store.record_execution(copy)

    def _execute(self, execution_id: str, spec: ProjectSpec, action: str, confirm: bool) -> None:
        record = self.store.execution(execution_id)
        if record is None:
            return
        record["status"] = "RUNNING"
        self._append_stage(record, "Launching registered action", "RUNNING")
        self._persist(record)
        lock = self._lock(spec.project_id)
        mutating = action not in READ_ONLY_ACTIONS
        acquired = lock.acquire(blocking=not mutating)
        if not acquired:
            record.update({"status": "BLOCKED", "reason_code": "PROJECT_ACTION_IN_PROGRESS", "completed_at": _utc_now(), "human_summary": "Another mutable action is already running for this project.", "technical_summary": "Per-project execution ownership prevents concurrent mutable actions."})
            self._append_stage(record, "Completed", "BLOCKED")
            self._finalize(record, "", "")
            return
        began = perf_counter()
        try:
            self._append_stage(record, "Running", "RUNNING")
            self._persist(record)
            result = run_registered_action(spec, action, confirm=confirm)
            latest = load_latest(spec)
            status = _typed_status(result)
            reason = _reason(result)
            human, technical = _human_projection(spec, action, result, latest)
            evidence_hash = None
            project_run_id = latest.run_id if latest else None
            evidence_ref = f"{spec.evidence_location}/{project_run_id}" if project_run_id else None
            if latest:
                verification = verify_sha256sums(latest)
                evidence_hash = str(verification.get("manifest_hash") or "") or None
                if action in {"latest", "verify"}:
                    self._append_stage(record, "Verifying evidence", "RUNNING")
            argv = ["registered", action] if result.command is None else [Path(token).name if index == 0 else token for index, token in enumerate(result.command)]
            record.update({
                "status": status, "reason_code": reason, "completed_at": _utc_now(),
                "duration_ms": int((perf_counter() - began) * 1000), "sanitized_argv": argv,
                "exit_code": result.exit_status, "human_summary": human, "technical_summary": technical,
                "project_run_id": project_run_id, "evidence_hash": evidence_hash,
                "evidence_reference": evidence_ref,
            })
            self._append_stage(record, "Completed", status)
            self._finalize(record, _sanitize(result.stdout), _sanitize(result.stderr))
        except Exception as exc:  # defensive boundary: never render a naked unknown
            record.update({"status": "UNKNOWN_ERROR", "reason_code": "INTERNAL_ERROR", "completed_at": _utc_now(), "human_summary": "The operator could not complete this action because of an internal error.", "technical_summary": _sanitize(str(exc)), "duration_ms": int((perf_counter() - began) * 1000)})
            self._append_stage(record, "Completed", "UNKNOWN_ERROR")
            self._finalize(record, "", _sanitize(repr(exc)))
        finally:
            lock.release()

    def _finalize(self, record: dict[str, Any], stdout: str, stderr: str) -> None:
        receipt = self._write_receipt(record, stdout, stderr)
        record["receipt_reference"] = receipt["reference"]
        record["operator_result_hash"] = receipt["hash"]
        self._persist(record)

    def _write_receipt(self, record: dict[str, Any], stdout: str, stderr: str) -> dict[str, str]:
        root = self.receipts_root / str(record["execution_id"])
        root.mkdir(parents=True, exist_ok=False)
        receipt = {
            "authority_boundary": "operator receipt; not project evidence",
            "execution": {key: record.get(key) for key in ("execution_id", "project_id", "action_id", "status", "reason_code", "started_at", "completed_at", "duration_ms", "source_commit", "cwd_relative", "sanitized_argv", "exit_code", "human_summary", "technical_summary", "project_run_id", "evidence_hash", "evidence_reference")},
        }
        receipt_path = root / "receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (root / "technical.log").write_text(f"stdout:\n{stdout}\n\nstderr:\n{stderr}\n", encoding="utf-8")
        entries = []
        for path in (receipt_path, root / "technical.log"):
            entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
        (root / "SHA256SUMS").write_text("\n".join(entries) + "\n", encoding="utf-8")
        digest = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        return {"reference": f"var/operator_runs/{record['execution_id']}", "hash": digest}

    def view(self, execution_id: str) -> dict[str, Any] | None:
        record = self.store.execution(execution_id)
        if record is None:
            return None
        return {
            "execution_id": record["execution_id"], "project_id": record["project_id"], "action": record["action_id"],
            "status": record["status"], "reason_code": record["reason_code"], "started_at": record["started_at"],
            "completed_at": record["completed_at"], "duration_ms": record["duration_ms"],
            "human_summary": record["human_summary"], "technical_summary": record["technical_summary"],
            "exit_code": record["exit_code"], "result_reference": record["project_run_id"],
            "evidence_reference": record["evidence_reference"], "receipt_reference": record["receipt_reference"],
            "receipt_integrity": self.verify_receipt(record), "stages": record["stages"],
            "technical_trace": {"source_commit": record["source_commit"], "cwd_relative": record["cwd_relative"], "sanitized_argv": record["sanitized_argv"], "operator_result_hash": record["operator_result_hash"]},
        }

    def verify_receipt(self, record: dict[str, Any]) -> str:
        reference = record.get("receipt_reference")
        if not reference:
            return "NOT_CHECKED"
        local_root = self.receipts_root / str(record["execution_id"])
        root = local_root if local_root.exists() else ROOT_DIR / reference
        manifest = root / "SHA256SUMS"
        if not manifest.exists():
            return "FAIL"
        try:
            for line in manifest.read_text(encoding="utf-8").splitlines():
                digest, name = line.split("  ", 1)
                if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
                    return "FAIL"
        except (OSError, ValueError):
            return "FAIL"
        return "PASS"
