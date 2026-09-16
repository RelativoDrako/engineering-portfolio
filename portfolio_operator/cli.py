from __future__ import annotations

import argparse
import hashlib
import sys
from typing import Iterable

from .learning import (
    GAN_CONCEPT_EXAMPLE,
    LEARNING_LAYERS,
    PROJECT_AUTHORITIES,
    VAE_CONCEPT_EXAMPLE,
    deterministic_baseline,
    learning_summary,
    project_learning_explanation,
    readiness_by_project,
)
from .preflight import portfolio_preflight, project_preflight
from .registry import load_registry
from .runner import ActionResult, run_registered_action
from .service import PortfolioService
from .storage import OperatorStore, StorageError


def _print_action(result: ActionResult) -> None:
    print(f"PROJECT: {result.project_id}")
    print(f"ACTION: {result.action}")
    print(f"WORKING_DIRECTORY: {result.working_directory}")
    print(f"PREREQUISITE_STATE: {result.prerequisite_state}")
    print(f"STARTED_AT: {result.started_at}")
    print(f"CURRENT_STAGE: {result.current_stage}")
    print(f"EXIT_STATUS: {result.exit_status}")
    print(f"STATUS: {result.status}")
    print(f"RESULT_SUMMARY: {result.result_summary}")
    print(f"EVIDENCE_REFERENCE: {result.evidence_reference or 'NONE'}")
    if result.stdout:
        print("RAW_LOG (expandable in web UI):")
        print(result.stdout[-2000:])
    if result.stderr:
        print("RAW_ERROR:")
        print(result.stderr[-2000:])


def _show_project(service: PortfolioService, project_id: str) -> None:
    snapshot = service.snapshot(project_id)
    spec = snapshot.spec
    print(f"\n{spec.name} ({spec.project_id})")
    print(f"WHAT THIS DEMONSTRATES: {spec.plain_language_description}")
    print(f"DOMAIN: {spec.domain}")
    readiness = project_preflight(spec)
    print(f"READINESS: {readiness['prerequisites']}; evidence={readiness['evidence_state']}; revision={readiness['revision_status']}")
    print("PREREQUISITES:")
    for item in spec.prerequisites:
        print(f"- {item}")
    if snapshot.latest:
        summary = snapshot.latest.result.get("result_summary", {})
        print(f"LATEST RESULT: run_id={snapshot.latest.run_id}; status={snapshot.latest.result.get('status', 'UNKNOWN')}; summary={summary}")
        print(f"EVIDENCE: {snapshot.latest.run_root}")
        print(f"DOMAIN AUTHORITY: {PROJECT_AUTHORITIES.get(project_id, 'UNKNOWN')}")
    else:
        print("LATEST RESULT: no latest valid run discovered")
    learning = project_learning_explanation(project_id)
    print(f"LEARNING OBSERVED TODAY: {learning['observed_today']}")
    print(f"FUTURE VAE POSSIBILITY: {learning['vae']}")
    print(f"FUTURE GAN POSSIBILITY: {learning['gan']}")
    print("GUIDED OPERATE FLOW: Understand -> Check -> Prepare -> Execute -> Review -> Verify -> Replay / Explore")
    print("Registered actions run from this root surface with the project's own working directory.")
    print("SUPPORTED ACTIONS:")
    for index, action in enumerate(spec.supported_actions, start=1):
        print(f"{index}. {action}")
    print("0. Back")
    try:
        choice = input("Select action: ").strip()
    except EOFError:
        return
    if choice == "0" or not choice:
        return
    try:
        action = spec.supported_actions[int(choice) - 1]
    except (ValueError, IndexError):
        print("Unknown action.")
        return
    if action == "feedback":
        _capture_feedback(service, project_id)
        return
    confirm = False
    if action == "cleanup":
        confirm = input("Cleanup removes project runtime volumes. Type CONFIRM to continue: ").strip() == "CONFIRM"
    result = run_registered_action(spec, action, confirm=confirm)
    _print_action(result)


def _capture_feedback(service: PortfolioService, project_id: str) -> None:
    latest = service.snapshot(project_id).latest
    if latest is None:
        print("No run is available for feedback.")
        return
    print("Classification: EXPECTED, UNEXPECTED, NEEDS_INVESTIGATION, KNOWN_TEST_SCENARIO")
    classification = input("Classification: ").strip().upper()
    useful = input("Was the explanation useful? YES/PARTIAL/NO (optional): ").strip().upper() or None
    note = input("Note (optional): ").strip() or None
    feedback_id = "fb-" + hashlib.sha256(f"{project_id}|{latest.run_id}|{classification}|{note or ''}".encode()).hexdigest()[:20]
    try:
        inserted = service.store.record_feedback(
            feedback_id=feedback_id, project_id=project_id, run_id=latest.run_id,
            classification=classification, explanation_useful=useful, note=note,
            source="HUMAN",
        )
        print(f"FEEDBACK_STATUS: {'RECORDED' if inserted else 'ALREADY_RECORDED'}; feedback_id={feedback_id}; source=HUMAN")
    except StorageError as exc:
        print(f"FEEDBACK_STATUS: REJECTED; {exc}")


def _cross_project(service: PortfolioService) -> None:
    print("\nCross-project observations (references plus bounded derived features only)")
    for snapshot in service.all_snapshots():
        if snapshot.observation:
            print(f"{snapshot.spec.project_id}: run={snapshot.observation.run_id}; status={snapshot.observation.status}; features={snapshot.observation.features}; labels={snapshot.observation.labels}")
        else:
            print(f"{snapshot.spec.project_id}: no latest valid run")


def _print_diagnostics(service: PortfolioService) -> None:
    report = portfolio_preflight(service.registry)
    print("\nEngineering Portfolio Diagnostics")
    print(f"REGISTRY: {report['registry']}")
    print(f"PROJECTS_DISCOVERED: {report['projects_discovered']}")
    print(f"WEB_BINDING: {report['web_binding']}")
    for item in report["projects"]:
        np02 = item.get("np02_port")
        port = "" if not np02 else f"; PostgreSQL={np02['port_semantics']}; listener={np02['postgresql_readiness']}"
        print(
            f"{item['project_id']}: prerequisites={item['prerequisites']}; latest={item['latest_valid_run']}; "
            f"evidence={item['evidence_state']}; revision={item['revision_status']}{port}"
        )


def _feedback_overview(service: PortfolioService) -> None:
    counts = service.store.feedback_counts()
    print("\nFeedback")
    print(f"HUMAN_FEEDBACK: {counts.get('HUMAN', 0)}")
    print(f"SYNTHETIC_VALIDATION_FEEDBACK: {counts.get('SYNTHETIC_INTEGRATION_VALIDATION', 0)}")
    print("Feedback is an operator assessment, not project evidence or an automatic retraining signal.")
    for item in service.store.feedback():
        print(
            f"{item['project_id']}: run={item['run_id']}; classification={item['classification']}; "
            f"source={item.get('source', 'HUMAN')}; useful={item.get('explanation_useful') or 'NONE'}"
        )


def _print_learning_overview(service: PortfolioService) -> None:
    summary = learning_summary(service.store)
    print("\nHow this system learns today")
    print(f"OBSERVED_RUNS: {summary['observed_runs']}")
    print(f"HUMAN_FEEDBACK: {summary['human_feedback']}")
    print(f"SYNTHETIC_VALIDATION_FEEDBACK: {summary['synthetic_validation_feedback']}")
    print(f"ACTIVE_ANALYSIS: {summary['active_analysis']}")
    print("PROJECT_EVIDENCE: facts produced by actual NP01-NP04 executions")
    print("DERIVED_OBSERVATION: normalized representation for comparison")
    print("MODEL_INFERENCE: future statistical/ML interpretation, not current evidence")
    print("SYNTHETIC_CANDIDATE: future generated scenario, never evidence")
    print("HUMAN_FEEDBACK: explicit operator assessment; no automatic retraining")
    print("LAYERS:")
    for layer in LEARNING_LAYERS:
        print(f"  {layer['number']}. {layer['name']} ({layer['kind']})")


def _print_vae_concept(service: PortfolioService) -> None:
    summary = learning_summary(service.store)
    print("\nVAE concept")
    print("ROLE: CONCEPT_DEMONSTRATION")
    print("STATUS: CONCEPT_DEMONSTRATION")
    print("TRAINED_MODEL: NO")
    print("WHY: Insufficient compatible historical observations for defensible representation learning.")
    print("DATA_READINESS_BY_PROJECT: " + str(summary["vae"]["data_readiness_by_project"]))
    print("A future VAE could highlight patterns that differ from a compatible domain history; it would not diagnose or decide.")
    print("EXAMPLE_ONLY (NP02):")
    print("FEATURES: " + ", ".join(VAE_CONCEPT_EXAMPLE["features"]))
    print("FLOW: " + " -> ".join(VAE_CONCEPT_EXAMPLE["flow"]))
    print("INTERPRETATION: " + VAE_CONCEPT_EXAMPLE["interpretation"])
    print("BOUNDARY: " + VAE_CONCEPT_EXAMPLE["boundary"])
    print("NO_MODEL_WAS_TRAINED: YES")
    print("NO_ANOMALY_SCORE_IS_REAL: YES")
    print("REQUIRED_BEFORE_TRAINING: more real bounded runs; stable feature schema; representative variation; evaluation criteria; resource justification; human approval")


def _print_gan_concept() -> None:
    print("\nGAN concept")
    print("ROLE: CONCEPT_DEMONSTRATION")
    print("STATUS: CONCEPT_DEMONSTRATION")
    print("TRAINING_READINESS: NOT_EVALUATED_OPERATIONAL_TRAINING_OUT_OF_SCOPE")
    print("TRAINED_MODEL: NO")
    print("EXAMPLE_ONLY (NP01): a future generator might propose bounded sensor fluctuation, communication delay and an abnormal tank-level sequence.")
    print("LABEL: SYNTHETIC_CANDIDATE")
    print("FLOW: " + " -> ".join(GAN_CONCEPT_EXAMPLE["flow"]))
    print("GAN_OUTPUT_AUTHORITY: NONE")
    print("AUTO_EXECUTION: NO")
    print("AUTO_PROMOTION_TO_TEST_FIXTURE: NO")
    print("AUTO_EVIDENCE_CREATION: NO")
    print("NO_GENERATED_EVIDENCE: YES")


def _print_authority_boundaries() -> None:
    print("\nEvidence and authority boundaries")
    for project_id, authority in PROJECT_AUTHORITIES.items():
        print(f"{project_id}: {authority}")
    print("engineering-portfolio: integration and operator surface only")
    print("PROJECT_EVIDENCE != DERIVED_OBSERVATION")
    print("MODEL_INFERENCE != PROJECT_EVIDENCE")
    print("SYNTHETIC_CANDIDATE != PROJECT_EVIDENCE")
    print("DERIVED_OBSERVATION != DOMAIN_AUTHORITY")
    print("HUMAN_FEEDBACK != AUTOMATIC_RETRAINING_SIGNAL")


def _learning_menu(service: PortfolioService) -> None:
    print("\nLearning concepts")
    print("1. How this system learns today")
    print("2. VAE concept")
    print("3. GAN concept")
    print("4. Data/model readiness")
    print("5. Evidence and authority boundaries")
    print("0. Back")
    try:
        choice = input("Select: ").strip()
    except EOFError:
        return
    if choice == "1":
        _print_learning_overview(service)
    elif choice == "2":
        _print_vae_concept(service)
    elif choice == "3":
        _print_gan_concept()
    elif choice == "4":
        print("\nData/model readiness")
        print("VAE: CONCEPT_DEMONSTRATION; trained=NO; data readiness=" + str(learning_summary(service.store)["vae"]["data_readiness_by_project"]))
        print("GAN: CONCEPT_DEMONSTRATION; training readiness=NOT_EVALUATED_OPERATIONAL_TRAINING_OUT_OF_SCOPE")
        print("TRAINED_MODELS=0; ACTIVE_MODELS=0; GENERATED_EVIDENCE=0")
        for project_id, state in readiness_by_project(service.store).items():
            print(f"{project_id}: observations={state['observations_available']}; VAE={state['vae']['status']}; data={state['vae']['data_readiness']}; GAN={state['gan']['status']}")
    elif choice == "5":
        _print_authority_boundaries()


def _learning(service: PortfolioService) -> None:
    _print_learning_overview(service)
    print("Use option 7 from the main menu for VAE/GAN concepts and readiness details.")


def interactive(service: PortfolioService) -> int:
    print("Engineering Portfolio - Local Operator")
    print("1 NP01 Industrial Resilience OT Lab")
    print("2 NP02 Governed Data & Analytics")
    print("3 NP03 Governed AI Assurance")
    print("4 NP04 Architecture Decision Workbench")
    print("5 Project status / preflight")
    print("6 Results / observations")
    print("7 Feedback")
    print("8 Learning concepts")
    print("0 Exit")
    try:
        choice = input("Select: ").strip()
    except EOFError:
        return 0
    if choice in {"1", "2", "3", "4"}:
        _show_project(service, f"NP0{choice}")
    elif choice == "5":
        _print_diagnostics(service)
    elif choice == "6":
        _cross_project(service)
    elif choice == "7":
        _feedback_overview(service)
    elif choice == "8":
        _learning_menu(service)
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Engineering portfolio local operator")
    parser.add_argument("--project", choices=["NP01", "NP02", "NP03", "NP04"])
    parser.add_argument("--action")
    parser.add_argument("--diagnostics", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    registry = load_registry()
    service = PortfolioService(registry, OperatorStore())
    if args.diagnostics:
        _print_diagnostics(service)
        return 0
    if args.project and args.action:
        spec = registry.project(args.project)
        result = run_registered_action(spec, args.action)
        _print_action(result)
        return 0 if result.status == "PASS" else 1
    return interactive(service)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
