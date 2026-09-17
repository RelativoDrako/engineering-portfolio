from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import parse_qs

from .config import DEFAULT_HOST, DEFAULT_PORT, STATIC_DIR, TEMPLATES_DIR
from .executions import ExecutionManager
from .learning import conceptual_model_metadata, deterministic_baseline, learning_summary, project_learning_explanation, readiness_by_project
from .preflight import portfolio_preflight, project_preflight
from .registry import load_registry
from .service import PortfolioService
from .storage import OperatorStore, StorageError

try:
    from starlette.requests import Request as _Request
except ImportError:  # pragma: no cover
    _Request = Any  # type: ignore[assignment,misc]


def _payload_from_body(body: bytes) -> dict[str, Any]:
    if not body:
        return {}
    try:
        parsed = json.loads(body.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        values = parse_qs(body.decode("utf-8", errors="replace"))
        return {key: item[-1] for key, item in values.items()}


def _bool(value: Any) -> bool:
    return value is True or str(value).lower() in {"1", "true", "yes", "on", "confirm"}


def _display(value: Any) -> str:
    """Never expose a bare unknown state in the human UI."""
    text = str(value or "NOT_CHECKED")
    return "NOT_CHECKED" if text in {"UNKNOWN", "UNRESOLVED", ""} else text


def _safe_evidence_reference(spec: Any, run_id: str | None) -> str:
    return f"{spec.evidence_location.rstrip('/')}/{run_id or '<run_id>'}"


def _safe_technical_text(value: str) -> str:
    import re
    return re.sub(r"(?i)[a-z]:[\\/][^\s\"']+", "<local path>", value)[-4000:]


def create_app(service: PortfolioService | None = None, stop_callback: Any | None = None, execution_manager: ExecutionManager | None = None):
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
        from fastapi.staticfiles import StaticFiles
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Web surface requires fastapi, uvicorn and Jinja2; install the root optional dependencies.") from exc

    app = FastAPI(title="Daniel Franco Fajardo | Engineering Portfolio")
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=select_autoescape(["html", "xml"]))
    operator = service or PortfolioService(load_registry(), OperatorStore())
    executions = execution_manager or ExecutionManager(operator.store)

    def render(name: str, **context: Any) -> HTMLResponse:
        return HTMLResponse(templates.get_template(name).render(display_status=_display, registry=operator.registry, **context))

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        snapshots = operator.all_snapshots(record=False)
        readiness = {row["project_id"]: row for row in portfolio_preflight(operator.registry)["projects"]}
        return render("index.html", title="Daniel Franco Fajardo | Engineering Portfolio", projects=snapshots, readiness=readiness, counts=operator.store.feedback_counts())

    @app.get("/operate", response_class=HTMLResponse)
    async def operate_overview() -> HTMLResponse:
        return render("operate.html", title="Operate | Engineering Portfolio", projects=operator.all_snapshots(record=False))

    @app.get("/evidence", response_class=HTMLResponse)
    async def evidence_overview() -> HTMLResponse:
        return render("evidence.html", title="Evidence | Engineering Portfolio", projects=operator.all_snapshots(record=False), executions=operator.store.executions())

    @app.get("/about", response_class=HTMLResponse)
    async def about() -> HTMLResponse:
        return render("about.html", title="About | Daniel Franco Fajardo")

    @app.get("/projects/{project_id}", response_class=HTMLResponse)
    async def project(project_id: str) -> HTMLResponse:
        try:
            snapshot = operator.snapshot(project_id, record=False)
        except (KeyError, ValueError) as exc:
            return PlainTextResponse(str(exc), status_code=404)
        return render("project.html", title=snapshot.spec.name, snapshot=snapshot, learning=project_learning_explanation(project_id), preflight=project_preflight(snapshot.spec))

    @app.get("/projects/{project_id}/learn", response_class=HTMLResponse)
    async def project_learn(project_id: str) -> HTMLResponse:
        try:
            snapshot = operator.snapshot(project_id, record=False)
        except (KeyError, ValueError) as exc:
            return PlainTextResponse(str(exc), status_code=404)
        return render("learn.html", title=f"Learning - {snapshot.spec.name}", snapshot=snapshot, baseline=deterministic_baseline(operator.store, project_id), readiness=readiness_by_project(operator.store).get(project_id), summary=learning_summary(operator.store), project_learning=project_learning_explanation(project_id), conceptual_models=conceptual_model_metadata(), feedback=operator.store.feedback(project_id))

    @app.get("/projects/{project_id}/runs", response_class=HTMLResponse)
    async def project_runs(project_id: str) -> HTMLResponse:
        try:
            snapshot = operator.snapshot(project_id, record=False)
            runs = operator.run_ids(project_id)
        except (KeyError, ValueError) as exc:
            return PlainTextResponse(str(exc), status_code=404)
        return render("runs.html", title=f"Runs - {snapshot.spec.name}", snapshot=snapshot, runs=runs)

    def _start_execution(project_id: str, action: str, confirm: bool = False) -> dict[str, Any]:
        return executions.start(operator.registry.project(project_id), action, confirm=confirm)

    @app.post("/projects/{project_id}/actions/{action_id}")
    async def action_post(project_id: str, action_id: str, request: _Request):
        """Progressive-enhancement endpoint: HTML POST redirects; JS requests JSON."""
        from fastapi.responses import RedirectResponse
        payload = _payload_from_body(await request.body())
        try:
            record = _start_execution(project_id, action_id, _bool(payload.get("confirm")))
            if "application/json" in request.headers.get("accept", ""):
                return JSONResponse(record, status_code=202)
            return RedirectResponse(f"/executions/{record['execution_id']}", status_code=303)
        except KeyError:
            return JSONResponse({"status": "BLOCKED", "reason_code": "PROJECT_NOT_FOUND", "human_message": "The registered project could not be found."}, status_code=404)
        except ValueError:
            return JSONResponse({"status": "BLOCKED", "reason_code": "ACTION_NOT_REGISTERED", "human_message": "This action is not registered for the project."}, status_code=400)

    @app.post("/projects/{project_id}/operate")
    async def legacy_operate(project_id: str, request: _Request):
        """Compatibility API; browser forms use the action-specific PRG route."""
        payload = _payload_from_body(await request.body())
        action = str(payload.get("action_id", payload.get("action", ""))).strip()
        try:
            return JSONResponse(_start_execution(project_id, action, _bool(payload.get("confirm"))), status_code=202)
        except (KeyError, ValueError):
            return JSONResponse({"status": "BLOCKED", "reason_code": "ACTION_NOT_REGISTERED", "human_message": "This action is not registered for the project."}, status_code=400)

    @app.get("/api/executions/{execution_id}")
    async def execution_api(execution_id: str):
        record = executions.view(execution_id)
        if record is None:
            return JSONResponse({"status": "BLOCKED", "reason_code": "RESULT_NOT_FOUND", "human_message": "The requested execution receipt was not found."}, status_code=404)
        return JSONResponse(record)

    @app.get("/executions/{execution_id}", response_class=HTMLResponse)
    async def execution_view(execution_id: str) -> HTMLResponse:
        record = executions.view(execution_id)
        return render("execution.html", title=f"Execution {execution_id}", execution=record) if record else PlainTextResponse("execution receipt not found", status_code=404)

    @app.post("/projects/{project_id}/feedback")
    async def feedback(project_id: str, request: _Request):
        payload = _payload_from_body(await request.body())
        try:
            snapshot = operator.snapshot(project_id, record=False)
            execution_id = str(payload.get("execution_id", "")).strip() or None
            run_id = snapshot.latest.run_id if snapshot.latest else "NO_PROJECT_RUN"
            classification, note = str(payload.get("classification", "")).upper(), str(payload.get("note", "")) or None
            useful = str(payload.get("explanation_useful", "")).upper() or None
            import hashlib
            feedback_id = "fb-" + hashlib.sha256(f"{project_id}|{run_id}|{execution_id}|{classification}|{note or ''}".encode()).hexdigest()[:20]
            inserted = operator.store.record_feedback(feedback_id=feedback_id, project_id=project_id, run_id=run_id, classification=classification, explanation_useful=useful, note=note, source="HUMAN", execution_id=execution_id)
            return JSONResponse({"status": "RECORDED" if inserted else "ALREADY_RECORDED", "feedback_id": feedback_id, "source": "HUMAN"})
        except (KeyError, StorageError) as exc:
            return JSONResponse({"status": "BLOCKED", "reason_code": "INPUT_INVALID", "human_message": str(exc)}, status_code=400)

    @app.get("/learning", response_class=HTMLResponse)
    async def learning() -> HTMLResponse:
        return render("learn.html", title="Learning | Engineering Portfolio", snapshot=None, baseline=deterministic_baseline(operator.store), readiness=readiness_by_project(operator.store), summary=learning_summary(operator.store), project_learning=None, conceptual_models=conceptual_model_metadata(), feedback=operator.store.feedback())

    @app.get("/feedback", response_class=HTMLResponse)
    async def feedback_overview() -> HTMLResponse:
        return render("feedback.html", title="Feedback | Engineering Portfolio", feedback=operator.store.feedback(), counts=operator.store.feedback_counts())

    @app.get("/diagnostics")
    async def diagnostics() -> JSONResponse:
        return JSONResponse(portfolio_preflight(operator.registry))

    @app.post("/operator/stop")
    async def stop_operator() -> JSONResponse:
        if not callable(stop_callback):
            return JSONResponse({"status": "NOT_APPLICABLE", "reason_code": "LAUNCHER_NOT_OWNING_PROCESS", "human_message": "This web process is not launcher-owned."}, status_code=409)
        asyncio.get_running_loop().call_later(0.2, stop_callback)
        return JSONResponse({"status": "PASS", "human_message": "The local operator is stopping. Project services are unchanged."})

    @app.get("/models", response_class=HTMLResponse)
    async def models() -> HTMLResponse:
        return render("models.html", title="Learning concepts", models=operator.store.models(), conceptual_models=conceptual_model_metadata())
    return app


def main() -> int:
    import uvicorn
    uvicorn.run("portfolio_operator.web:create_app", host=DEFAULT_HOST, port=DEFAULT_PORT, factory=True)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
