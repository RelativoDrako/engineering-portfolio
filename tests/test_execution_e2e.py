from __future__ import annotations

import time

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
        response = client.post("/projects/NP01/operate", data={"action": "latest"})
        assert response.status_code == 202
        execution_id = response.json()["execution_id"]
        for _ in range(80):
            result = client.get(f"/executions/{execution_id}").json()
            if result["status"] not in {"READY", "RUNNING"}:
                break
            time.sleep(0.02)
        assert result["status"] in {"PASS", "FAIL", "BLOCKED", "UNKNOWN_ERROR"}
        assert result["reason_code"] is None or result["reason_code"]
        assert result["execution_id"] == execution_id
        assert result["receipt_integrity"] == "PASS"
        assert client.get(f"/executions/{execution_id}/view").status_code == 200


def test_invalid_action_never_reaches_runner(tmp_path):
    store = OperatorStore(tmp_path / "operator.sqlite3")
    app = create_app(PortfolioService(load_registry(), store), execution_manager=ExecutionManager(store, tmp_path / "operator_runs"))
    with TestClient(app) as client:
        response = client.post("/projects/NP01/operate", data={"action": "not-registered"})
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
