from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
PORTFOLIO_PARENT = ROOT_DIR.parent
REGISTRY_PATH = ROOT_DIR / "portfolio.toml"
VAR_DIR = ROOT_DIR / "var"
DATABASE_PATH = VAR_DIR / "portfolio_operator.sqlite3"
TEMPLATES_DIR = ROOT_DIR / "templates"
STATIC_DIR = ROOT_DIR / "static"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def ensure_runtime_dirs() -> None:
    """Create only the operator's own runtime directory."""

    VAR_DIR.mkdir(parents=True, exist_ok=True)
