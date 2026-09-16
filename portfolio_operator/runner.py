from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from .evidence import load_latest
from .registry import DESTRUCTIVE_ACTIONS, ProjectSpec


@dataclass(frozen=True)
class ActionResult:
    project_id: str
    action: str
    working_directory: str
    command: tuple[str, ...] | None
    prerequisite_state: str
    started_at: str
    completed_at: str
    exit_status: int | None
    status: str
    result_summary: str
    evidence_reference: str | None
    stdout: str = ""
    stderr: str = ""
    current_stage: str = "completed"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _built_in(spec: ProjectSpec, action: str) -> ActionResult | None:
    if action == "explain":
        return ActionResult(spec.project_id, action, str(spec.path), None, "NOT_REQUIRED", _now(), _now(), 0, "PASS", spec.plain_language_description, None)
    if action == "setup":
        guidance = "Check readiness first. If this independent project environment is missing, use its README setup once; the root operator does not alter project environments automatically."
        return ActionResult(spec.project_id, action, str(spec.path), None, "GUIDANCE_ONLY", _now(), _now(), 0, "PASS", guidance, None)
    if action == "latest":
        latest = load_latest(spec)
        summary = "No latest valid run is available." if latest is None else f"Latest valid run: {latest.run_id} ({latest.result.get('status', 'UNKNOWN')}); evidence={latest.run_root}"
        return ActionResult(spec.project_id, action, str(spec.path), None, "READ_ONLY", _now(), _now(), 0, "PASS", summary, str(latest.run_root) if latest else None)
    return None


def _project_python(spec: ProjectSpec) -> str:
    """Prefer the project's own environment so dependencies stay isolated."""

    candidates = (
        spec.path / ".venv" / "Scripts" / "python.exe",
        spec.path / ".venv" / "bin" / "python",
    )
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _validate_command_paths(spec: ProjectSpec, tokens: list[str]) -> None:
    """Registry command paths must resolve inside the registered project root."""

    root = spec.path.resolve()
    for token in tokens:
        if token.startswith("-") or not ("/" in token or "\\" in token or token.endswith(".py")):
            continue
        candidate = (root / token).resolve()
        if not candidate.is_relative_to(root):
            raise ValueError(f"registered command path escapes {spec.project_id} root")


def build_command(spec: ProjectSpec, action: str) -> tuple[str, ...]:
    if action not in spec.actions:
        raise ValueError(f"action {action} is not registered for {spec.project_id}")
    tokens = list(spec.actions[action])
    _validate_command_paths(spec, tokens)
    if tokens and tokens[0].endswith(".py"):
        return (_project_python(spec), *tokens)
    if tokens and tokens[0] == "-m":
        return (_project_python(spec), *tokens)
    return tuple(tokens)


def run_registered_action(
    spec: ProjectSpec,
    action: str,
    *,
    confirm: bool = False,
    env: Mapping[str, str] | None = None,
    timeout_seconds: int = 300,
) -> ActionResult:
    builtin = _built_in(spec, action)
    if builtin is not None:
        return builtin
    if action == "verify":
        latest = load_latest(spec)
        if latest is None:
            return ActionResult(spec.project_id, action, str(spec.path), None, "READ_ONLY", _now(), _now(), 1, "FAIL", "No latest valid run is available.", None)
        from .evidence import verify_sha256sums

        check = verify_sha256sums(latest)
        status = "PASS" if check["status"] == "PASS" else "FAIL"
        return ActionResult(spec.project_id, action, str(spec.path), None, "READ_ONLY", _now(), _now(), 0 if status == "PASS" else 1, status, f"SHA256SUMS: {check['checked']} checked; mismatches={len(check['mismatches'])}", str(latest.run_root))
    if action == "runs":
        return ActionResult(spec.project_id, action, str(spec.path), None, "READ_ONLY", _now(), _now(), 0, "PASS", "Run listing is available through the service.", str(spec.evidence_root))
    if action == "feedback":
        return ActionResult(spec.project_id, action, str(spec.path), None, "REQUIRES_INPUT", _now(), _now(), 0, "PASS", "Use the feedback form with an explicit classification.", None)
    if action not in spec.actions:
        raise ValueError(f"action {action} is not registered for {spec.project_id}")
    if action in DESTRUCTIVE_ACTIONS and not confirm:
        return ActionResult(spec.project_id, action, str(spec.path), build_command(spec, action), "CONFIRMATION_REQUIRED", _now(), _now(), None, "ABORTED", "Explicit confirmation is required; no command was executed.", None)
    command = build_command(spec, action)
    if action == "replay":
        latest = load_latest(spec)
        if latest is None:
            return ActionResult(spec.project_id, action, str(spec.path), command, "NO_LATEST_RUN", _now(), _now(), 1, "FAIL", "No latest valid run is available to replay.", None)
        command = (*command, latest.run_id)
        if spec.replay_change:
            command = (*command, "--change", spec.replay_change)
    started = _now()
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    try:
        completed = subprocess.run(
            list(command),
            cwd=spec.path,
            env=process_env,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
        status = "PASS" if completed.returncode == 0 else "FAIL"
        output = (completed.stdout or "").strip().splitlines()
        summary = output[-1] if output else (completed.stderr or "").strip().splitlines()[-1] if completed.stderr else status
        return ActionResult(spec.project_id, action, str(spec.path), tuple(command), "EXECUTED", started, _now(), completed.returncode, status, summary, str(spec.evidence_root), completed.stdout or "", completed.stderr or "")
    except subprocess.TimeoutExpired as exc:
        return ActionResult(spec.project_id, action, str(spec.path), tuple(command), "EXECUTED", started, _now(), None, "ABORTED", f"timeout after {timeout_seconds}s", str(spec.evidence_root), str(exc.stdout or ""), str(exc.stderr or ""))
    except OSError as exc:
        return ActionResult(spec.project_id, action, str(spec.path), tuple(command), "EXECUTED", started, _now(), None, "FAIL", f"execution error: {exc}", str(spec.evidence_root), "", str(exc))
