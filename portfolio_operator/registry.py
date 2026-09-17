from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.12 is required
    tomllib = None  # type: ignore[assignment]

from .config import PORTFOLIO_PARENT, REGISTRY_PATH, ROOT_DIR


BUILTIN_ACTIONS = frozenset(
    {"explain", "setup", "latest", "verify", "feedback", "runs"}
)
REGISTERED_ACTIONS = frozenset(
    {
        "preflight",
        "start_services",
        "demo",
        "tests",
        "operate",
        "latest",
        "verify",
        "replay",
        "cleanup",
    }
)
DESTRUCTIVE_ACTIONS = frozenset({"cleanup"})
_FORBIDDEN_SHELL_TOKENS = frozenset({";", "&&", "||", "|", ">", "<"})


class RegistryError(ValueError):
    """Raised when the declarative registry is unsafe or incomplete."""


def _safe_command(tokens: object, *, project_id: str, action: str) -> tuple[str, ...]:
    if not isinstance(tokens, list) or not tokens or not all(isinstance(t, str) for t in tokens):
        raise RegistryError(f"{project_id}.{action} must be a non-empty string array")
    values = tuple(tokens)
    if any(
        "\n" in t
        or "\r" in t
        or any(forbidden in t for forbidden in _FORBIDDEN_SHELL_TOKENS)
        for t in values
    ):
        raise RegistryError(f"{project_id}.{action} contains shell syntax")
    return values


@dataclass(frozen=True)
class ProjectSpec:
    project_id: str
    name: str
    relative_path: str
    plain_language_description: str
    domain: str
    prerequisites: tuple[str, ...]
    evidence_location: str
    latest_valid_location: str
    actions: Mapping[str, tuple[str, ...]]
    replay_change: str | None = None
    tested_commit: str | None = None
    requires_docker: bool = False
    default_port: int | None = None
    repository_url: str | None = None

    @property
    def path(self) -> Path:
        candidate = (ROOT_DIR / self.relative_path).resolve()
        portfolio_parent = PORTFOLIO_PARENT.resolve()
        if candidate == ROOT_DIR.resolve() or not candidate.is_relative_to(portfolio_parent):
            raise RegistryError(f"{self.project_id} path escapes the portfolio parent")
        return candidate

    @property
    def evidence_root(self) -> Path:
        root = (self.path / self.evidence_location).resolve()
        if not root.is_relative_to(self.path.resolve()):
            raise RegistryError(f"{self.project_id} evidence location escapes project root")
        return root

    @property
    def latest_pointer(self) -> Path:
        pointer = (self.path / self.latest_valid_location).resolve()
        if not pointer.is_relative_to(self.path.resolve()):
            raise RegistryError(f"{self.project_id} latest location escapes project root")
        return pointer

    @property
    def supported_actions(self) -> tuple[str, ...]:
        registered = set(self.actions) | set(BUILTIN_ACTIONS)
        return tuple(
            action
            for action in (
                "explain",
                "setup",
                "preflight",
                "start_services",
                "demo",
                "tests",
                "operate",
                "latest",
                "verify",
                "replay",
                "runs",
                "feedback",
                "cleanup",
            )
            if action in registered
        )


@dataclass(frozen=True)
class PortfolioRegistry:
    version: int
    portfolio_id: str
    projects: tuple[ProjectSpec, ...]
    root_repository_url: str | None = None

    def project(self, project_id: str) -> ProjectSpec:
        for item in self.projects:
            if item.project_id == project_id:
                return item
        raise KeyError(project_id)


def load_registry(path: Path = REGISTRY_PATH) -> PortfolioRegistry:
    if tomllib is None:  # pragma: no cover
        raise RegistryError("Python 3.11+ tomllib is required")
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    projects_raw = raw.get("projects")
    if not isinstance(projects_raw, list) or not projects_raw:
        raise RegistryError("registry must contain at least one project")
    specs: list[ProjectSpec] = []
    seen: set[str] = set()
    for item in projects_raw:
        if not isinstance(item, dict):
            raise RegistryError("each project entry must be a table")
        required = (
            "project_id",
            "name",
            "relative_path",
            "plain_language_description",
            "domain",
            "prerequisites",
            "evidence_location",
            "latest_valid_location",
        )
        missing = [key for key in required if key not in item]
        if missing:
            raise RegistryError(f"project entry missing {missing}")
        project_id = str(item["project_id"])
        if project_id in seen:
            raise RegistryError(f"duplicate project_id {project_id}")
        seen.add(project_id)
        prerequisites = item["prerequisites"]
        if not isinstance(prerequisites, list) or not all(isinstance(p, str) for p in prerequisites):
            raise RegistryError(f"{project_id}.prerequisites must be a string array")
        actions_raw = item.get("actions", {})
        if not isinstance(actions_raw, dict):
            raise RegistryError(f"{project_id}.actions must be a table")
        actions: dict[str, tuple[str, ...]] = {}
        for action, command in actions_raw.items():
            if action not in REGISTERED_ACTIONS:
                raise RegistryError(f"unregistered action {project_id}.{action}")
            actions[action] = _safe_command(command, project_id=project_id, action=action)
        spec = ProjectSpec(
            project_id=project_id,
            name=str(item["name"]),
            relative_path=str(item["relative_path"]),
            plain_language_description=str(item["plain_language_description"]),
            domain=str(item["domain"]),
            prerequisites=tuple(prerequisites),
            evidence_location=str(item["evidence_location"]),
            latest_valid_location=str(item["latest_valid_location"]),
            actions=actions,
            replay_change=str(item["replay_change"]) if item.get("replay_change") else None,
            tested_commit=str(item["tested_commit"]) if item.get("tested_commit") else None,
            requires_docker=bool(item.get("requires_docker", False)),
            default_port=int(item["default_port"]) if item.get("default_port") is not None else None,
            repository_url=str(item["repository_url"]) if item.get("repository_url") else None,
        )
        # Resolve during loading so an unsafe registry fails before any action.
        _ = spec.path
        _ = spec.evidence_root
        _ = spec.latest_pointer
        specs.append(spec)
    return PortfolioRegistry(
        version=int(raw.get("version", 1)),
        portfolio_id=str(raw.get("portfolio_id", "engineering-portfolio")),
        projects=tuple(specs),
        root_repository_url=str(raw["root_repository_url"]) if raw.get("root_repository_url") else None,
    )
