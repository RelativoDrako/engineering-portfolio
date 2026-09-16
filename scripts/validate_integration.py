"""Read the four latest project results without mutating persistent feedback."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from portfolio_operator.registry import load_registry
from portfolio_operator.runner import run_registered_action
from portfolio_operator.service import PortfolioService
from portfolio_operator.storage import OperatorStore


def main() -> int:
    registry = load_registry()
    service = PortfolioService(registry, OperatorStore())
    effective_port = os.environ.get("NP02_DB_PORT", "55433")
    preflight = run_registered_action(
        registry.project("NP02"), "preflight", env={"NP02_DB_PORT": effective_port}
    )
    print(f"NP02_PREFLIGHT: endpoint_port={effective_port}; status={preflight.status}; summary={preflight.result_summary}")
    for snapshot in service.all_snapshots(record=True):
        observation = snapshot.observation
        if observation is None:
            print(f"{snapshot.spec.project_id}: NO_LATEST_VALID_RUN")
            continue
        print(
            f"{observation.project_id}: run={observation.run_id}; status={observation.status}; "
            f"observation={observation.observation_id}; feedback=NOT_MUTATED"
        )
    print(f"OBSERVATIONS_REGISTERED={len(service.store.observations())}")
    print(f"FEEDBACK_REGISTERED={len(service.store.feedback())}; PERSISTENT_FEEDBACK_MUTATIONS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
