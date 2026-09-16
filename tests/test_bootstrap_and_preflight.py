from __future__ import annotations

import subprocess
from pathlib import Path

from portfolio_operator import bootstrap
from portfolio_operator.config import DEFAULT_HOST, DEFAULT_PORT, ROOT_DIR
from portfolio_operator.preflight import NP02_DEFAULT_PORT, NP02_VALIDATED_LOCAL_OVERRIDE, portfolio_preflight, project_preflight
from portfolio_operator.registry import load_registry


def test_windows_launcher_routes_default_cli_and_diagnostics_without_domain_logic():
    launcher = (ROOT_DIR / "START_PORTFOLIO.cmd").read_text(encoding="utf-8")
    assert "-m portfolio_operator.bootstrap %*" in launcher
    assert "PORTFOLIO_ROOT=%~dp0" in launcher
    assert "scripts\\" not in launcher
    assert "pause" in launcher


def test_bootstrap_reuses_existing_root_environment():
    status = bootstrap.ensure_environment()
    assert status.action == "REUSE_EXISTING_ENVIRONMENT"
    assert status.python.exists()


def test_bootstrap_repairs_only_a_missing_root_environment(tmp_path: Path, monkeypatch):
    calls: list[list[str]] = []

    def fake_probe(path: Path) -> bool:
        return path.exists()

    def fake_runner(args, **kwargs):
        calls.append(list(args))
        if args[1:3] == ["-m", "venv"]:
            python = tmp_path / ".venv" / "Scripts" / "python.exe"
            python.parent.mkdir(parents=True)
            python.touch()
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(bootstrap, "_dependency_probe", fake_probe)
    monkeypatch.setattr(bootstrap, "_write_log", lambda text: None)
    status = bootstrap.ensure_environment(root=tmp_path, runner=fake_runner)
    assert status.action == "REPAIR_ROOT_ENVIRONMENT"
    assert any("venv" in call for call in calls)
    assert any("pip" in call for call in calls)


def test_port_selection_reuses_registered_service(monkeypatch):
    monkeypatch.setattr(bootstrap, "_operator_is_responding", lambda port: port == DEFAULT_PORT)
    monkeypatch.setattr(bootstrap, "_port_in_use", lambda port: True)
    assert bootstrap.select_web_port() == (DEFAULT_PORT, "REUSE_EXISTING_SERVICE")


def test_port_selection_uses_bounded_local_alternative(monkeypatch):
    monkeypatch.setattr(bootstrap, "_operator_is_responding", lambda port: False)
    monkeypatch.setattr(bootstrap, "_port_in_use", lambda port: port in {DEFAULT_PORT, DEFAULT_PORT + 1})
    assert bootstrap.select_web_port() == (DEFAULT_PORT + 2, "ALTERNATE_LOCALHOST_PORT")


def test_existing_service_browser_failure_has_documented_fallback(monkeypatch, capsys):
    monkeypatch.setattr(bootstrap, "select_web_port", lambda port: (port, "REUSE_EXISTING_SERVICE"))
    assert bootstrap._start_web(DEFAULT_PORT, browser_open=lambda url: False) == 0
    assert "DOCUMENTED_FALLBACK" in capsys.readouterr().out


def test_preflight_discovers_four_projects_and_current_baselines():
    report = portfolio_preflight(load_registry())
    assert report["registry"] == "PASS"
    assert report["projects_discovered"] == "4_OF_4"
    assert report["web_binding"] == f"{DEFAULT_HOST}:{DEFAULT_PORT}"
    assert {item["revision_status"] for item in report["projects"]} == {"VERIFIED_BASELINE"}


def test_np02_default_and_host_override_semantics(monkeypatch):
    spec = load_registry().project("NP02")
    monkeypatch.delenv("NP02_DB_PORT", raising=False)
    default = project_preflight(spec)["np02_port"]
    assert default["default_port"] == NP02_DEFAULT_PORT == 55433
    assert default["effective_port"] == 55433
    assert default["port_semantics"] == "PROJECT_DEFAULT:55433"
    monkeypatch.setenv("NP02_DB_PORT", str(NP02_VALIDATED_LOCAL_OVERRIDE))
    override = project_preflight(spec)["np02_port"]
    assert override["effective_port"] == 55540
    assert override["port_semantics"] == "CONFIGURED_HOST_OVERRIDE:55540"


def test_diagnostics_is_read_only_and_does_not_run_project_actions(monkeypatch):
    calls: list[object] = []

    def fake_preflight(registry):
        calls.append(registry)
        return {"registry": "PASS", "projects_discovered": "4_OF_4", "web_binding": "127.0.0.1:8765", "projects": []}

    monkeypatch.setattr(bootstrap, "portfolio_preflight", fake_preflight)
    text = bootstrap.diagnostics_report()
    assert "Projects discovered    4_OF_4" in text
    assert len(calls) == 1


def test_validation_script_does_not_record_persistent_feedback():
    source = (ROOT_DIR / "scripts" / "validate_integration.py").read_text(encoding="utf-8")
    assert "record_feedback(" not in source
    assert "PERSISTENT_FEEDBACK_MUTATIONS=0" in source


def test_no_ml_runtime_dependencies_are_declared():
    package = (ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8").lower()
    for forbidden in ("torch", "tensorflow", "jax", "cuda"):
        assert forbidden not in package
