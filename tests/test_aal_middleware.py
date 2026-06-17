# @!testing

"""Tests for AAL middleware trigger matching."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from axiompy.aal.middleware import EditIntent, _trigger_matches
from tests.aal_helpers import setup_minimal_repo

_CURSOR_DIR = "_aal_cursor"


@pytest.fixture(autouse=True)
def _aal_cursor_dir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AXIOMPY_AAL_CURSOR_DIR", _CURSOR_DIR)


def test_trigger_matches_kinds():
    intent = EditIntent(
        file_path="pkg/mod.py",
        description="Fix SQL injection keyword",
        symbols_touched=["save_user"],
        imports_touched=["sqlalchemy.orm"],
    )
    assert _trigger_matches("always", "*", intent, "pkg/mod.py")
    assert _trigger_matches("symbol", "save_user", intent, "pkg/mod.py")
    assert _trigger_matches("import", "sqlalchemy.*", intent, "pkg/mod.py")
    assert _trigger_matches("path", "pkg/*.py", intent, "pkg/mod.py")
    assert _trigger_matches("keyword", "sql", intent, "pkg/mod.py")
    assert not _trigger_matches("symbol", "other", intent, "pkg/mod.py")
    assert not _trigger_matches("bogus", "x", intent, "pkg/mod.py")
