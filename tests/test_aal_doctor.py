# @!testing

"""Tests for AAL doctor command."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from axiompy.aal.doctor import cmd_doctor
from tests.aal_helpers import cursor_dir, setup_minimal_repo

_CURSOR_DIR = "_aal_cursor"


@pytest.fixture(autouse=True)
def _aal_cursor_dir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AXIOMPY_AAL_CURSOR_DIR", _CURSOR_DIR)


def test_doctor_passes_for_complete_install(tmp_path: Path, capsys):
    root = tmp_path
    setup_minimal_repo(
        root,
        manifest='{"version":"1.0","managed_paths":[]}\n',
    )

    assert cmd_doctor(root, strict=True) == 0
    out = capsys.readouterr().out
    assert "all required components present" in out


def test_doctor_reports_missing_cursor(tmp_path: Path, capsys):
    root = tmp_path

    assert cmd_doctor(root, strict=True) == 1
    assert "MISSING: .cursor/" in capsys.readouterr().out


def test_doctor_non_strict_allows_optional_manifest(tmp_path: Path, capsys):
    root = tmp_path
    setup_minimal_repo(root, manifest=None)

    assert cmd_doctor(root, strict=False) == 0
    out = capsys.readouterr().out
    assert "OPTIONAL" in out or "MISSING" not in out
