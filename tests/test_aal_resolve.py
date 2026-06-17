# @!testing

"""Tests for AAL resolve, merge, and middleware."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from axiompy.aal.middleware import EditIntent, aal_inject_on_edit, aal_pre_edit_hook
from axiompy.aal.resolve import cmd_resolve, merge_skill_content, resolve_edit
from tests.aal_helpers import cursor_dir, setup_minimal_repo

_CURSOR_DIR = "_aal_cursor"


@pytest.fixture(autouse=True)
def _aal_cursor_dir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AXIOMPY_AAL_CURSOR_DIR", _CURSOR_DIR)


def test_merge_skill_content_with_sidecar_and_override(tmp_path: Path):
    root = tmp_path
    cursor = setup_minimal_repo(root)
    (cursor / "skills/testing/reference.md").write_text("# Ref\n", encoding="utf-8")
    override = cursor / "skills/testing.override"
    override.mkdir()
    (override / "SKILL.md").write_text("# Override\n", encoding="utf-8")

    merged = merge_skill_content(root, f"{_CURSOR_DIR}/skills/testing/SKILL.md")
    assert "# Skill" in merged
    assert "reference" in merged
    assert "Override" in merged


def test_resolve_edit_returns_domains_and_content(tmp_path: Path):
    root = tmp_path
    setup_minimal_repo(root)
    src = root / "app.py"
    src.write_text("# @!testing\n\ndef run():\n    pass\n", encoding="utf-8")

    payload = resolve_edit(root, "app.py", target_line=3)
    assert payload["domains"] == ["testing"]
    assert payload["skills"][0]["path"].endswith("SKILL.md")
    assert "Domain: testing" in payload["content"]


def test_resolve_edit_no_annotation(tmp_path: Path):
    root = tmp_path
    setup_minimal_repo(root)
    src = root / "plain.py"
    src.write_text("x = 1\n", encoding="utf-8")

    payload = resolve_edit(root, "plain.py")
    assert payload["domains"] == []
    assert payload["content"] == ""


def test_resolve_edit_errors(tmp_path: Path):
    root = tmp_path
    setup_minimal_repo(root)
    with pytest.raises(FileNotFoundError):
        resolve_edit(root, "missing.py")

    src = root / "bad.py"
    src.write_text("# @!missing\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown domain"):
        resolve_edit(root, "bad.py")


def test_cmd_resolve_json_and_text(tmp_path: Path, capsys):
    root = tmp_path
    setup_minimal_repo(root)
    src = root / "app.py"
    src.write_text("# @!testing\n", encoding="utf-8")

    assert cmd_resolve(root, "app.py", as_json=True) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["domains"] == ["testing"]

    assert cmd_resolve(root, "app.py", as_json=False) == 0
    assert "domains: testing" in capsys.readouterr().out

    assert cmd_resolve(root, "missing.py") == 1


def test_middleware_pre_edit_and_inject(tmp_path: Path):
    root = tmp_path
    setup_minimal_repo(root)
    src = root / "svc.py"
    src.write_text(
        "# @!testing\n# @!guard when=symbol:save then=read:testing\n\ndef save():\n    pass\n",
        encoding="utf-8",
    )

    intent = EditIntent(
        file_path="svc.py",
        description="update save",
        symbols_touched=["save"],
        target_line=5,
    )
    reads = aal_pre_edit_hook(str(root), intent)
    assert any(r.domain == "testing" for r in reads)

    injected = aal_inject_on_edit(str(root), intent)
    assert injected["domains"] == ["testing"]
