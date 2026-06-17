# @!testing

"""Tests for AAL verify-domains extended paths."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from axiompy.aal.verify import cmd_verify_domains, collect_domain_usages
from axiompy.aal.config import load_config
from tests.aal_helpers import setup_minimal_repo

_CURSOR_DIR = "_aal_cursor"


@pytest.fixture(autouse=True)
def _aal_cursor_dir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AXIOMPY_AAL_CURSOR_DIR", _CURSOR_DIR)


def test_collect_domain_usages(tmp_path: Path):
    root = tmp_path
    setup_minimal_repo(root)
    (root / "a.py").write_text("# @!testing\n", encoding="utf-8")
    (root / "b.py").write_text(
        "# @!guard when=always then=read:testing\n",
        encoding="utf-8",
    )

    graph = collect_domain_usages(root, load_config(root))
    assert "testing" in graph
    assert "a.py" in graph["testing"]


def test_verify_domains_guard_and_files_filter(tmp_path: Path, capsys):
    root = tmp_path
    setup_minimal_repo(root)
    (root / "good.py").write_text("# @!testing\n", encoding="utf-8")
    (root / "bad.py").write_text("# @!not-a-domain\n", encoding="utf-8")

    assert cmd_verify_domains(root, strict=False, files=["good.py"]) == 0
    assert "All domain annotations valid" in capsys.readouterr().out

    assert cmd_verify_domains(root, strict=False, files=["bad.py"]) == 1


def test_verify_domains_missing_registry_skill(tmp_path: Path, capsys):
    root = tmp_path
    setup_minimal_repo(
        root,
        domains={"testing": [f"{_CURSOR_DIR}/skills/testing/SKILL.md"]},
    )
    skill = root / _CURSOR_DIR / "skills/testing/SKILL.md"
    skill.unlink()

    assert cmd_verify_domains(root, strict=False) == 1
    assert "skill missing" in capsys.readouterr().out


def test_verify_domains_strict_version_mismatch(tmp_path: Path, capsys):
    root = tmp_path
    setup_minimal_repo(
        root,
        aal_config=(
            'version: "1.3"\n'
            "skills_package: axiompy\n"
            'skills_package_version: "0.0.0"\n'
            "extensions: [.py]\n"
            "ignore_dirs: [venv]\n"
        ),
    )
    (root / "app.py").write_text("# @!testing\n", encoding="utf-8")

    assert cmd_verify_domains(root, strict=True) == 1
    assert "skills_package_version" in capsys.readouterr().out


def test_verify_domains_parse_error(tmp_path: Path, capsys):
    root = tmp_path
    setup_minimal_repo(root)
    (root / "broken.py").write_text("# @!testing,load=bad\n", encoding="utf-8")

    assert cmd_verify_domains(root, strict=False, files=["broken.py"]) == 1
    assert "ERROR" in capsys.readouterr().out


def test_verify_domains_no_registry(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("axiompy.aal.verify.load_domains", lambda _root: {})
    assert cmd_verify_domains(tmp_path, strict=False) == 1
    assert "no domains defined" in capsys.readouterr().out
