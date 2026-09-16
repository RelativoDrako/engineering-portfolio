"""Bounded, read-only readiness checks for registered portfolio projects."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any

from .evidence import load_latest, verify_sha256sums
from .registry import PortfolioRegistry, ProjectSpec


NP02_DEFAULT_PORT = 55433
NP02_VALIDATED_LOCAL_OVERRIDE = 55540


def _project_python_ready(spec: ProjectSpec) -> bool:
    return any(
        candidate.exists()
        for candidate in (spec.path / ".venv" / "Scripts" / "python.exe", spec.path / ".venv" / "bin" / "python")
    )


def _git_commit(path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "UNRESOLVED"
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "UNRESOLVED"


def _listener_state(port: int) -> str:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return "RESPONDING"
    except OSError:
        return "NOT_RESPONDING"


def _np02_port_state(spec: ProjectSpec) -> dict[str, Any]:
    default_port = spec.default_port or NP02_DEFAULT_PORT
    raw_override = os.environ.get("NP02_DB_PORT")
    if raw_override:
        try:
            effective_port = int(raw_override)
        except ValueError:
            return {
                "default_port": default_port,
                "effective_port": "INVALID",
                "port_semantics": "INVALID_OVERRIDE",
                "postgresql_readiness": "UNRESOLVED",
            }
        semantics = f"CONFIGURED_HOST_OVERRIDE:{effective_port}"
    else:
        effective_port = default_port
        semantics = f"PROJECT_DEFAULT:{default_port}"
    return {
        "default_port": default_port,
        "effective_port": effective_port,
        "port_semantics": semantics,
        "postgresql_readiness": _listener_state(effective_port),
        "validated_local_override": NP02_VALIDATED_LOCAL_OVERRIDE,
    }


def project_preflight(spec: ProjectSpec) -> dict[str, Any]:
    """Inspect only filesystem, Git, local listener and evidence references."""

    discovered = spec.path.exists() and spec.path.is_dir()
    current_commit = _git_commit(spec.path) if discovered else "UNRESOLVED"
    revision_status = (
        "VERIFIED_BASELINE"
        if spec.tested_commit and current_commit == spec.tested_commit
        else "UNVERIFIED_REVISION"
    )
    latest = load_latest(spec) if discovered else None
    verification = verify_sha256sums(latest) if latest else None
    result: dict[str, Any] = {
        "project_id": spec.project_id,
        "discovered": "YES" if discovered else "NO",
        "current_local_commit": current_commit,
        "tested_baseline_commit": spec.tested_commit or "UNREGISTERED",
        "revision_status": revision_status,
        "prerequisites": "READY" if _project_python_ready(spec) else "PROJECT_ENVIRONMENT_NOT_FOUND",
        "service_state": "NOT_REQUIRED",
        "latest_valid_run": latest.run_id if latest else "NOT_FOUND",
        "evidence_state": verification["status"] if verification else "NO_LATEST_RUN",
    }
    if spec.requires_docker:
        docker_available = shutil.which("docker") is not None
        result["docker"] = "AVAILABLE" if docker_available else "NOT_FOUND"
        result["service_state"] = "CHECK_DOCKER" if docker_available else "NEEDS_DOCKER"
    if spec.project_id == "NP02":
        result["np02_port"] = _np02_port_state(spec)
        if result["np02_port"]["postgresql_readiness"] == "RESPONDING":
            result["service_state"] = "POSTGRESQL_PORT_RESPONDING"
    return result


def portfolio_preflight(registry: PortfolioRegistry) -> dict[str, Any]:
    rows = [project_preflight(spec) for spec in registry.projects]
    return {
        "registry": "PASS",
        "projects_discovered": f"{sum(row['discovered'] == 'YES' for row in rows)}_OF_{len(rows)}",
        "web_binding": "127.0.0.1:8765",
        "projects": rows,
    }
