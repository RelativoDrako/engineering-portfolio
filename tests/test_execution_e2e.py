from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from portfolio_operator.executions import ExecutionManager
from portfolio_operator.registry import load_registry
from portfolio_operator.service import PortfolioService
from portfolio_operator.storage import OperatorStore
from portfolio_operator.web import create_app


def test_registered_read_only_action_is_normalized_and_receipted(tmp_path):
    store = OperatorStore(tmp_path / "operator.sqlite3")
    manager = ExecutionManager(store, tmp_path / "operator_runs")
    app = create_app(PortfolioService(load_registry(), store), execution_manager=manager)
    with TestClient(app) as client:
        response = client.post("/projects/NP01/actions/latest", data={}, follow_redirects=False)
        assert response.status_code == 303
        execution_id = response.headers["location"].rsplit("/", 1)[-1]
        for _ in range(80):
            result = client.get(f"/api/executions/{execution_id}").json()
            if result["status"] not in {"READY", "RUNNING"}:
                break
            time.sleep(0.02)
        assert result["status"] in {"PASS", "FAIL", "BLOCKED", "UNKNOWN_ERROR"}
        assert result["reason_code"] is None or result["reason_code"]
        assert result["execution_id"] == execution_id
        assert result["receipt_integrity"] == "PASS"
        assert client.get(f"/executions/{execution_id}").status_code == 200


def test_invalid_action_never_reaches_runner(tmp_path):
    store = OperatorStore(tmp_path / "operator.sqlite3")
    app = create_app(PortfolioService(load_registry(), store), execution_manager=ExecutionManager(store, tmp_path / "operator_runs"))
    with TestClient(app) as client:
        response = client.post("/projects/NP01/actions/not-registered", data={})
    assert response.status_code == 400
    assert response.json()["reason_code"] == "ACTION_NOT_REGISTERED"


def test_root_pages_have_identity_theme_and_no_naked_unknown(tmp_path):
    store = OperatorStore(tmp_path / "operator.sqlite3")
    app = create_app(PortfolioService(load_registry(), store), execution_manager=ExecutionManager(store, tmp_path / "operator_runs"))
    with TestClient(app) as client:
        for path in ("/", "/operate", "/evidence", "/about"):
            body = client.get(path).text
            assert "Daniel Franco Fajardo" in body
            assert "theme-select" in body
            assert "UNKNOWN" not in body


def test_project_forms_are_action_specific_and_links_are_trusted_metadata(tmp_path):
    store = OperatorStore(tmp_path / "operator.sqlite3")
    app = create_app(PortfolioService(load_registry(), store), execution_manager=ExecutionManager(store, tmp_path / "operator_runs"))
    with TestClient(app) as client:
        body = client.get("/projects/NP01").text
    assert 'action="/projects/NP01/actions/latest"' in body
    assert 'name="action"' not in body
    assert 'https://github.com/RelativoDrako/industrial-resilience-ot-lab' in body
    assert 'target="_blank"' in body and 'noopener noreferrer' in body


def test_post_redirect_get_refresh_does_not_reexecute(tmp_path):
    store = OperatorStore(tmp_path / "operator.sqlite3")
    app = create_app(PortfolioService(load_registry(), store), execution_manager=ExecutionManager(store, tmp_path / "operator_runs"))
    with TestClient(app) as client:
        response = client.post("/projects/NP03/actions/latest", follow_redirects=False)
        assert response.status_code == 303
        destination = response.headers["location"]
        before = len(store.executions("NP03"))
        assert client.get(destination).status_code == 200
        assert client.get(destination).status_code == 200
        assert len(store.executions("NP03")) == before


def test_execution_page_is_explicitly_marked_for_scoped_status_polling(tmp_path):
    store = OperatorStore(tmp_path / "operator.sqlite3")
    app = create_app(PortfolioService(load_registry(), store), execution_manager=ExecutionManager(store, tmp_path / "operator_runs"))
    with TestClient(app) as client:
        response = client.post("/projects/NP04/actions/latest", follow_redirects=False)
        destination = response.headers["location"]
        body = client.get(destination).text
        home = client.get("/").text
    assert 'data-page="execution"' in body
    assert 'data-execution-id="op-' in body
    assert 'data-page="execution"' not in home


def test_browser_script_never_reloads_documents_and_scopes_polling_to_execution_page():
    root = Path(__file__).resolve().parents[1]
    script = (root / "static" / "app.js").read_text(encoding="utf-8")
    assert "window.location.reload" not in script
    assert "document.body.dataset.page === 'execution'" in script
    assert "window.addEventListener('pagehide', stop" in script
    assert "terminal.has(record.status)" in script


def test_normal_web_runtime_explicitly_disables_server_reload():
    root = Path(__file__).resolve().parents[1]
    assert "reload=False" in (root / "portfolio_operator" / "bootstrap.py").read_text(encoding="utf-8")
    assert "reload=False" in (root / "portfolio_operator" / "web.py").read_text(encoding="utf-8")


def test_navigation_has_fixed_professional_links_and_no_root_repository_claim(tmp_path):
    store = OperatorStore(tmp_path / "operator.sqlite3")
    app = create_app(PortfolioService(load_registry(), store), execution_manager=ExecutionManager(store, tmp_path / "operator_runs"))
    with TestClient(app) as client:
        body = client.get("/").text
    for url in ("https://github.com/RelativoDrako", "https://relativodrako.github.io/", "https://relativodrako.github.io/#contact"):
        assert url in body
    assert "RelativoDrako/engineering-portfolio" not in body


def test_rendered_action_matrix_matches_registered_actions(tmp_path):
    store = OperatorStore(tmp_path / "operator.sqlite3")
    registry = load_registry()
    app = create_app(PortfolioService(registry, store), execution_manager=ExecutionManager(store, tmp_path / "operator_runs"))
    with TestClient(app) as client:
        for spec in registry.projects:
            body = client.get(f"/projects/{spec.project_id}").text
            for action in spec.supported_actions:
                assert f'/projects/{spec.project_id}/actions/{action}' in body
