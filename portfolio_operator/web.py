from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from .config import DEFAULT_HOST, DEFAULT_PORT, STATIC_DIR, TEMPLATES_DIR
from .learning import (
    conceptual_model_metadata,
    deterministic_baseline,
    learning_summary,
    project_learning_explanation,
    readiness_by_project,
)
from .registry import DESTRUCTIVE_ACTIONS, load_registry
from .runner import run_registered_action
from .service import PortfolioService
from .storage import OperatorStore, StorageError

try:
    from starlette.requests import Request as _Request
except ImportError:  # pragma: no cover - web factory reports the dependency
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


def _safe_evidence_reference(spec: Any, run_id: str | None) -> str:
    """Expose a logical repository-relative reference, never a private path."""

    if not run_id:
        return f"{spec.evidence_location.rstrip('/')}/<run_id>"
    return f"{spec.evidence_location.rstrip('/')}/{run_id}"


def create_app(service: PortfolioService | None = None):
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
        from fastapi.staticfiles import StaticFiles
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except ImportError as exc:  # pragma: no cover - exercised when optional web deps are absent
        raise RuntimeError("Web surface requires fastapi, uvicorn and Jinja2; install the root optional dependencies.") from exc

    app = FastAPI(title="Engineering Portfolio - Local Operator")
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=select_autoescape(["html", "xml"]))
    operator = service or PortfolioService(load_registry(), OperatorStore())

    def render(name: str, **context: Any) -> HTMLResponse:
        template = templates.get_template(name)
        return HTMLResponse(template.render(**context))

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        snapshots = operator.all_snapshots()
        return render("index.html", title="Engineering Portfolio - Local Operator", projects=snapshots)

    @app.get("/projects/{project_id}", response_class=HTMLResponse)
    async def project(project_id: str) -> HTMLResponse:
        try:
            snapshot = operator.snapshot(project_id)
        except (KeyError, ValueError) as exc:
            return PlainTextResponse(str(exc), status_code=404)
        return render(
            "project.html",
            title=snapshot.spec.name,
            snapshot=snapshot,
            learning=project_learning_explanation(project_id),
        )

    @app.get("/projects/{project_id}/learn", response_class=HTMLResponse)
    async def project_learn(project_id: str) -> HTMLResponse:
        try:
            snapshot = operator.snapshot(project_id)
        except (KeyError, ValueError) as exc:
            return PlainTextResponse(str(exc), status_code=404)
        baseline = deterministic_baseline(operator.store, project_id)
        readiness = readiness_by_project(operator.store).get(project_id)
        return render(
            "learn.html",
            title=f"Learning - {snapshot.spec.name}",
            snapshot=snapshot,
            baseline=baseline,
            readiness=readiness,
            summary=learning_summary(operator.store),
            project_learning=project_learning_explanation(project_id),
            conceptual_models=conceptual_model_metadata(),
            feedback=operator.store.feedback(project_id),
        )

    @app.get("/projects/{project_id}/runs", response_class=HTMLResponse)
    async def project_runs(project_id: str) -> HTMLResponse:
        try:
            snapshot = operator.snapshot(project_id)
            runs = operator.run_ids(project_id)
        except (KeyError, ValueError) as exc:
            return PlainTextResponse(str(exc), status_code=404)
        return render("runs.html", title=f"Runs - {snapshot.spec.name}", snapshot=snapshot, runs=runs)

    @app.get("/projects/{project_id}/runs/{run_id}", response_class=HTMLResponse)
    async def project_run(project_id: str, run_id: str) -> HTMLResponse:
        try:
            spec = operator.registry.project(project_id)
            run = next((item for item in operator.run_ids(project_id) if item == run_id), None)
            if run is None:
                return PlainTextResponse("run not found", status_code=404)
            from .evidence import load_latest

            # The run route is bounded to the registered evidence root. It does not
            # accept a filesystem path from the browser.
            run_root = (spec.evidence_root / run_id).resolve()
            if not run_root.is_relative_to(spec.evidence_root.resolve()):
                return PlainTextResponse("invalid run path", status_code=400)
            latest = load_latest(spec)
            if latest is None or latest.run_id != run_id:
                # Read the same bounded schema for a non-latest run.
                from .evidence import _read_json, RunEvidence

                latest = RunEvidence(
                    project_id, run_id, run_root,
                    _read_json(run_root / "run_manifest.json"),
                    _read_json(run_root / "result.json"),
                    _read_json(run_root / "validation.json"),
                    {"run_id": run_id},
                )
            verification = __import__("portfolio_operator.evidence", fromlist=["verify_sha256sums"]).verify_sha256sums(latest)
            return render(
                "run.html",
                title=f"Run {run_id}",
                run=latest,
                verification=verification,
                safe_evidence_reference=_safe_evidence_reference(spec, run_id),
            )
        except (KeyError, ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
            return PlainTextResponse(str(exc), status_code=404)

    @app.post("/projects/{project_id}/operate")
    async def operate(project_id: str, request: _Request):
        payload = _payload_from_body(await request.body())
        action = str(payload.get("action", "")).strip()
        try:
            spec = operator.registry.project(project_id)
            if action not in spec.supported_actions:
                return JSONResponse({"status": "REJECTED", "reason": "action is not registered"}, status_code=400)
            result = run_registered_action(spec, action, confirm=_bool(payload.get("confirm")))
            return JSONResponse(
                {
                    "project_id": result.project_id,
                    "action": result.action,
                    "status": result.status,
                    "working_directory": spec.relative_path,
                    "prerequisite_state": result.prerequisite_state,
                    "current_stage": result.current_stage,
                    "exit_status": result.exit_status,
                    "result_summary": result.result_summary,
                    "evidence_reference": _safe_evidence_reference(spec, None),
                }
            )
        except KeyError:
            return JSONResponse({"status": "NOT_FOUND"}, status_code=404)

    @app.post("/projects/{project_id}/feedback")
    async def feedback(project_id: str, request: _Request):
        payload = _payload_from_body(await request.body())
        try:
            snapshot = operator.snapshot(project_id)
            if snapshot.latest is None:
                return JSONResponse({"status": "REJECTED", "reason": "no run available"}, status_code=409)
            classification = str(payload.get("classification", "")).upper()
            note = str(payload.get("note", "")) or None
            useful = str(payload.get("explanation_useful", "")).upper() or None
            import hashlib

            feedback_id = "fb-" + hashlib.sha256(f"{project_id}|{snapshot.latest.run_id}|{classification}|{note or ''}".encode()).hexdigest()[:20]
            inserted = operator.store.record_feedback(
                feedback_id=feedback_id, project_id=project_id, run_id=snapshot.latest.run_id,
                classification=classification, explanation_useful=useful, note=note,
                source="HUMAN",
            )
            return JSONResponse({"status": "RECORDED" if inserted else "ALREADY_RECORDED", "feedback_id": feedback_id, "source": "HUMAN"})
        except (KeyError, StorageError) as exc:
            return JSONResponse({"status": "REJECTED", "reason": str(exc)}, status_code=400)

    @app.get("/learning", response_class=HTMLResponse)
    async def learning() -> HTMLResponse:
        return render(
            "learn.html",
            title="Cross-project learning",
            snapshot=None,
            baseline=deterministic_baseline(operator.store),
            readiness=readiness_by_project(operator.store),
            summary=learning_summary(operator.store),
            project_learning=None,
            conceptual_models=conceptual_model_metadata(),
            feedback=operator.store.feedback(),
        )

    @app.get("/models", response_class=HTMLResponse)
    async def models() -> HTMLResponse:
        return render(
            "models.html",
            title="Model concepts and metadata",
            models=operator.store.models(),
            conceptual_models=conceptual_model_metadata(),
        )

    return app


def main() -> int:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("Install the root optional dependencies before starting the web surface.") from exc
    uvicorn.run("portfolio_operator.web:create_app", host=DEFAULT_HOST, port=DEFAULT_PORT, factory=True)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
