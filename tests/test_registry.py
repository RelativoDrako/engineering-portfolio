from pathlib import Path

import pytest

from portfolio_operator.config import REGISTRY_PATH, ROOT_DIR
from portfolio_operator.registry import ProjectSpec, RegistryError, load_registry


def test_registry_loads_four_projects_and_fixed_actions():
    registry = load_registry()
    assert [item.project_id for item in registry.projects] == ["NP01", "NP02", "NP03", "NP04"]
    assert "operate" in registry.project("NP01").supported_actions
    assert "preflight" in registry.project("NP02").supported_actions
    assert "cleanup" not in registry.project("NP03").supported_actions


def test_registry_paths_are_contained_under_portfolio_parent():
    registry = load_registry()
    parent = ROOT_DIR.parent.resolve()
    for item in registry.projects:
        assert item.path.is_relative_to(parent)
        assert item.path != ROOT_DIR.resolve()


def test_registry_rejects_path_escape(tmp_path: Path):
    spec = ProjectSpec("BAD", "Bad", "../../", "x", "x", (), "var/runs", "var/latest_valid.json", {})
    with pytest.raises(RegistryError):
        _ = spec.path


def test_registry_rejects_shell_syntax(tmp_path: Path):
    registry_text = """
version = 1
portfolio_id = 'test'
[[projects]]
project_id = 'X'
name = 'X'
relative_path = '..'
plain_language_description = 'x'
domain = 'x'
prerequisites = []
evidence_location = 'var/runs'
latest_valid_location = 'var/latest_valid.json'
[projects.actions]
demo = ['scripts/demo.py && whoami']
"""
    path = tmp_path / "portfolio.toml"
    path.write_text(registry_text, encoding="utf-8")
    with pytest.raises(RegistryError):
        load_registry(path)
