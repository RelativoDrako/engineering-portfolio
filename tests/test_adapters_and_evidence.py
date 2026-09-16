import json
from pathlib import Path

from portfolio_operator.adapters import adapt_run
from portfolio_operator.evidence import load_latest, verify_sha256sums
from portfolio_operator.registry import load_registry


def test_adapters_parse_current_latest_runs():
    registry = load_registry()
    expected = {"NP01": "fault_count", "NP02": "accepted", "NP03": "case_count", "NP04": "requirements"}
    for project_id, feature in expected.items():
        spec = registry.project(project_id)
        run = load_latest(spec)
        assert run is not None
        envelope = adapt_run(spec, run)
        assert envelope.project_id == project_id
        assert envelope.run_id == run.run_id
        assert feature in envelope.features
        assert Path(envelope.evidence_reference).is_relative_to(spec.evidence_root)
        assert verify_sha256sums(run)["status"] == "PASS"


def test_unknown_schema_fails_safe(tmp_path: Path):
    registry = load_registry()
    spec = registry.project("NP03")
    run_root = tmp_path / "run"
    run_root.mkdir()
    for filename, value in {
        "run_manifest.json": {"run_id": "unknown", "status": "PASS", "evidence_hash": "x"},
        "result.json": {"status": "PASS", "result_summary": "not-an-object"},
        "validation.json": {"status": "PASS"},
    }.items():
        (run_root / filename).write_text(json.dumps(value), encoding="utf-8")
    from portfolio_operator.evidence import RunEvidence

    run = RunEvidence("NP03", "unknown", run_root, json.loads((run_root / "run_manifest.json").read_text()), json.loads((run_root / "result.json").read_text()), json.loads((run_root / "validation.json").read_text()), {})
    envelope = adapt_run(spec, run)
    assert envelope.labels["schema_status"] == "UNKNOWN_SCHEMA"
