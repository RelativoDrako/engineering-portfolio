import pytest

from portfolio_operator.config import DEFAULT_HOST
from portfolio_operator.registry import load_registry
from portfolio_operator.runner import build_command, run_registered_action


def test_commands_use_project_working_directory_and_no_shell_string():
    spec = load_registry().project("NP01")
    command = build_command(spec, "operate")
    assert command[0].endswith("python.exe") or command[0].endswith("python")
    assert command[-1] == "scripts/run_operational.py"
    result = run_registered_action(spec, "cleanup", confirm=False)
    assert result.status == "ABORTED"
    assert result.prerequisite_state == "CONFIRMATION_REQUIRED"


def test_web_default_binding_is_localhost():
    assert DEFAULT_HOST == "127.0.0.1"


def test_web_evidence_reference_is_logical_and_not_private_path():
    from portfolio_operator.web import _safe_evidence_reference

    spec = load_registry().project("NP01")
    reference = _safe_evidence_reference(spec, "run-1")
    assert reference == "var/runs/run-1"
    assert "_nsambi_" not in reference


def test_web_factory_is_available_or_reports_dependency():
    from portfolio_operator import web

    try:
        app = web.create_app()
    except RuntimeError as exc:
        assert "fastapi" in str(exc).lower()
    else:
        assert any(getattr(route, "path", "") == "/" for route in app.routes)
