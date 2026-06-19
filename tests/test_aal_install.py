# @!testing

"""Tests for axiompy-skills install --hooks."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from axiompy.aal.install import InstallOptions, cmd_install, cmd_upgrade

_CURSOR_DIR = "_aal_cursor"


@pytest.fixture(autouse=True)
def _aal_cursor_dir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AXIOMPY_AAL_CURSOR_DIR", _CURSOR_DIR)


def _cursor(root: Path) -> Path:
    return root / os.environ.get("AXIOMPY_AAL_CURSOR_DIR", _CURSOR_DIR)


def test_install_hooks_dry_run(tmp_path: Path):
    root = tmp_path
    code = cmd_install(
        InstallOptions(root=root, project=True, hooks=True, ci=True, dry_run=True),
        skills_dest=_cursor(root) / "skills",
    )
    assert code == 0
    assert not (_cursor(root) / "domains.yaml").exists()
    assert not (_cursor(root) / "hooks.json").exists()


def test_install_hooks_writes_registry(tmp_path: Path):
    root = tmp_path
    skills_dest = _cursor(root) / "skills"
    code = cmd_install(
        InstallOptions(root=root, project=True, hooks=True, ci=False, dry_run=False),
        skills_dest=skills_dest,
    )
    assert code == 0
    domains_text = (_cursor(root) / "domains.yaml").read_text(encoding="utf-8")
    assert "tooling:" in domains_text
    assert "design-patterns" in domains_text
    assert "sql.md" not in domains_text
    assert (_cursor(root) / "aal.yaml").is_file()
    assert (_cursor(root) / "bootstrap.yaml").is_file()
    assert (skills_dest / "testing" / "SKILL.md").is_file()
    assert (_cursor(root) / "hooks/aal-inject.sh").is_file()


def test_upgrade_requires_manifest(tmp_path: Path, capsys):
    root = tmp_path
    assert cmd_upgrade(root) == 1
    assert "missing" in capsys.readouterr().out.lower()
