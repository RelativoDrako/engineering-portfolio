"""One-click bootstrap for the local engineering-portfolio operator surface."""

from __future__ import annotations

import argparse
import importlib.util
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from .config import BOOTSTRAP_LOG_PATH, DEFAULT_HOST, DEFAULT_PORT, ROOT_DIR, ROOT_VENV_DIR, ensure_runtime_dirs
from .preflight import portfolio_preflight
from .registry import load_registry
from .storage import OperatorStore


class BootstrapError(RuntimeError):
    """An actionable root-operator startup error."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class BootstrapStatus:
    action: str
    python: Path
    detail: str


def _venv_python(root: Path = ROOT_DIR) -> Path:
    return root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _write_log(text: str) -> None:
    ensure_runtime_dirs()
    BOOTSTRAP_LOG_PATH.write_text(text, encoding="utf-8")


def _dependency_probe(python: Path) -> bool:
    probe = "import fastapi, uvicorn, jinja2, portfolio_operator"
    try:
        result = subprocess.run([str(python), "-c", probe], cwd=ROOT_DIR, capture_output=True, text=True, check=False, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _require_current_python() -> None:
    if sys.version_info < (3, 12):
        raise BootstrapError("PYTHON_NOT_FOUND", "Python 3.12 or newer is required to prepare the local operator environment.")


def ensure_environment(*, root: Path = ROOT_DIR, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> BootstrapStatus:
    """Reuse a ready root venv; create or repair it only when required."""

    _require_current_python()
    python = _venv_python(root)
    if python.exists() and _dependency_probe(python):
        return BootstrapStatus("REUSE_EXISTING_ENVIRONMENT", python, "The local root environment is ready.")

    log: list[str] = []
    if not python.exists():
        create = runner([sys.executable, "-m", "venv", str(root / ".venv")], cwd=root, capture_output=True, text=True, check=False)
        log.extend([create.stdout or "", create.stderr or ""])
        if create.returncode != 0 or not python.exists():
            _write_log("\n".join(log))
            raise BootstrapError("VENV_CREATION_FAILED", "The root virtual environment could not be created. See var/bootstrap.log for technical details.")

    install = runner([str(python), "-m", "pip", "install", "-e", "."], cwd=root, capture_output=True, text=True, check=False)
    log.extend([install.stdout or "", install.stderr or ""])
    _write_log("\n".join(log))
    if install.returncode != 0 or not _dependency_probe(python):
        raise BootstrapError("DEPENDENCY_INSTALL_FAILED", "Root dependencies could not be prepared. Check your local Python package availability and var/bootstrap.log.")
    return BootstrapStatus("REPAIR_ROOT_ENVIRONMENT", python, "The local root environment was prepared.")


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((DEFAULT_HOST, port)) == 0


def _operator_is_responding(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://{DEFAULT_HOST}:{port}/", timeout=1.0) as response:
            return response.status == 200 and b"Engineering Portfolio" in response.read(4096)
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def select_web_port(requested: int = DEFAULT_PORT) -> tuple[int, str]:
    if _operator_is_responding(requested):
        return requested, "REUSE_EXISTING_SERVICE"
    if not _port_in_use(requested):
        return requested, "DEFAULT_PORT_AVAILABLE"
    for candidate in range(requested + 1, requested + 6):
        if not _port_in_use(candidate):
            return candidate, "ALTERNATE_LOCALHOST_PORT"
    raise BootstrapError("WEB_PORT_IN_USE", f"Local web port {requested} is occupied and no bounded alternative port is available.")


def diagnostics_report() -> str:
    try:
        registry = load_registry()
    except Exception as exc:  # registry parser errors are converted for operators
        raise BootstrapError("REGISTRY_INVALID", str(exc)) from exc
    report = portfolio_preflight(registry)
    store = OperatorStore()
    counts = store.feedback_counts()
    evidence_references = sum(item["evidence_state"] == "PASS" for item in report["projects"])
    lines = [
        "Engineering Portfolio Diagnostics",
        "",
        f"Root environment       READY",
        f"Registry               {report['registry']}",
        f"Projects discovered    {report['projects_discovered']}",
        f"Web binding            {report['web_binding']}",
        f"Observations            {len(store.observations())}",
        f"Evidence references     {evidence_references}/{len(report['projects'])} valid",
        f"Human feedback          {counts.get('HUMAN', 0)}",
        f"Synthetic feedback      {counts.get('SYNTHETIC_INTEGRATION_VALIDATION', 0)}",
    ]
    for item in report["projects"]:
        np02 = item.get("np02_port")
        suffix = ""
        if np02:
            suffix = f"; PostgreSQL {np02['port_semantics']}; listener={np02['postgresql_readiness']}"
        lines.append(
            f"{item['project_id']}                    {item['prerequisites']}; "
            f"latest={item['latest_valid_run']}; evidence={item['evidence_state']}; "
            f"revision={item['revision_status']}{suffix}"
        )
    return "\n".join(lines)


def _start_web(port: int, *, browser_open: Callable[[str], bool] = webbrowser.open) -> int:
    selected_port, port_state = select_web_port(port)
    url = f"http://{DEFAULT_HOST}:{selected_port}"
    if port_state == "REUSE_EXISTING_SERVICE":
        print(f"A local Engineering Portfolio surface is already available at: {url}")
        try:
            opened = browser_open(url)
        except Exception:
            opened = False
        print(f"WEB_BROWSER_OPEN={'PASS' if opened else 'DOCUMENTED_FALLBACK'}")
        return 0
    if port_state == "ALTERNATE_LOCALHOST_PORT":
        print(f"Local port {port} is in use by another process. Starting on bounded alternative: {url}")
    try:
        from .web import create_app
        import uvicorn
    except ImportError as exc:
        raise BootstrapError("WEB_START_FAILED", "The local web dependencies are unavailable after bootstrap.") from exc
    try:
        opened = browser_open(url)
    except Exception:
        opened = False
    print("Local operator environment is ready.")
    print(f"Opening: {url}")
    print(f"WEB_BROWSER_OPEN={'PASS' if opened else 'DOCUMENTED_FALLBACK'}")
    holder: dict[str, object] = {}
    app = create_app(stop_callback=lambda: setattr(holder["server"], "should_exit", True))
    server = uvicorn.Server(uvicorn.Config(app, host=DEFAULT_HOST, port=selected_port, log_level="warning", reload=False))
    holder["server"] = server
    server.run()
    return 0


def _run_in_root_environment(args: list[str], status: BootstrapStatus) -> int:
    current = Path(sys.executable).resolve()
    target = status.python.resolve()
    if current == target:
        return _dispatch(args)
    completed = subprocess.run([str(status.python), "-m", "portfolio_operator.bootstrap", *args], cwd=ROOT_DIR, check=False)
    return completed.returncode


def _dispatch(args: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Start the Engineering Portfolio local operator")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--cli", action="store_true", help="Open the root CLI operator")
    mode.add_argument("--diagnostics", action="store_true", help="Print bounded local diagnostics")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=argparse.SUPPRESS)
    parsed = parser.parse_args(args)
    if parsed.diagnostics:
        print(diagnostics_report())
        return 0
    if parsed.cli:
        from .cli import main as cli_main

        return cli_main([])
    return _start_web(parsed.port)


def main(argv: Iterable[str] | None = None) -> int:
    args = list(argv) if argv is not None else sys.argv[1:]
    try:
        status = ensure_environment()
        print(f"BOOTSTRAP_ACTION={status.action}")
        return _run_in_root_environment(args, status)
    except BootstrapError as exc:
        print("Portfolio could not start.")
        print(f"Reason: {exc.code}")
        print(f"Detail: {exc.detail}")
        print("Try START_PORTFOLIO.cmd --diagnostics or START_PORTFOLIO.cmd --cli.")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
