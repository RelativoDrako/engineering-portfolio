from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .adapters import ObservationEnvelope, adapt_run
from .evidence import RunEvidence, compact_run_summary, load_latest, list_runs, verify_sha256sums
from .registry import PortfolioRegistry, ProjectSpec
from .storage import OperatorStore


@dataclass(frozen=True)
class ProjectSnapshot:
    spec: ProjectSpec
    latest: RunEvidence | None
    observation: ObservationEnvelope | None
    evidence_verification: dict[str, Any] | None


class PortfolioService:
    def __init__(self, registry: PortfolioRegistry, store: OperatorStore | None = None):
        self.registry = registry
        self.store = store or OperatorStore()

    def snapshot(self, project_id: str, *, record: bool = True) -> ProjectSnapshot:
        spec = self.registry.project(project_id)
        latest = load_latest(spec)
        observation = adapt_run(spec, latest) if latest else None
        if observation and record:
            self.store.record_observation(observation)
        verification = verify_sha256sums(latest) if latest else None
        return ProjectSnapshot(spec, latest, observation, verification)

    def all_snapshots(self, *, record: bool = True) -> list[ProjectSnapshot]:
        return [self.snapshot(spec.project_id, record=record) for spec in self.registry.projects]

    def compact_latest(self, project_id: str) -> dict[str, Any] | None:
        latest = self.snapshot(project_id).latest
        return compact_run_summary(latest) if latest else None

    def run_ids(self, project_id: str) -> list[str]:
        return list_runs(self.registry.project(project_id))
