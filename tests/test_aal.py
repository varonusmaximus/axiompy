# @!testing

"""Tests for AAL parser and verify-domains."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from axiompy.aal.parser import effective_annotation_at_line, parse_aal_file, parse_header
from axiompy.aal.verify import cmd_verify_domains

_CURSOR_DIR = "_aal_cursor"


@pytest.fixture(autouse=True)
def _aal_cursor_dir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AXIOMPY_AAL_CURSOR_DIR", _CURSOR_DIR)


def _cursor(root: Path) -> Path:
    return root / os.environ.get("AXIOMPY_AAL_CURSOR_DIR", _CURSOR_DIR)


def test_parse_compact_annotation():
    content = "# @!testing\n\ndef test_foo():\n    pass\n"
    aal = parse_aal_file(content, ".py")
    assert len(aal.compact) == 1
    assert aal.compact[0].domains == ["testing"]


def test_parse_multi_domain():
    content = "# @!code-style,testing\n"
    aal = parse_header(content, ".py")
    assert aal.compact[0].domains == ["code-style", "testing"]


def test_effective_annotation_function_override():
    content = (
        "# @!code-style\n\ndef outer():\n    pass\n\n# @!testing\ndef test_inner():\n    pass\n"
    )
    aal = parse_aal_file(content, ".py")
    assert effective_annotation_at_line(aal, 2).domains == ["code-style"]
    assert effective_annotation_at_line(aal, 8).domains == ["testing"]


def test_verify_domains_valid_fixture(tmp_path: Path):
    root = tmp_path
    cursor = _cursor(root)
    cursor.mkdir()
    (cursor / "skills/testing").mkdir(parents=True)
    (cursor / "skills/testing/SKILL.md").write_text("# Testing skill\n", encoding="utf-8")
    (cursor / "domains.yaml").write_text(
        f"domains:\n  testing:\n    skills:\n      - {_CURSOR_DIR}/skills/testing/SKILL.md\n",
        encoding="utf-8",
    )
    src = root / "module.py"
    src.write_text("# @!testing\nx = 1\n", encoding="utf-8")

    assert cmd_verify_domains(root, strict=False) == 0


def test_verify_domains_unknown_domain(tmp_path: Path):
    root = tmp_path
    cursor = _cursor(root)
    cursor.mkdir()
    (cursor / "domains.yaml").write_text("domains:\n  testing:\n    skills: []\n", encoding="utf-8")
    (root / "module.py").write_text("# @!unknown\n", encoding="utf-8")

    assert cmd_verify_domains(root, strict=False) == 1


def test_verify_domains_max_three(tmp_path: Path):
    root = tmp_path
    cursor = _cursor(root)
    cursor.mkdir()
    for name in ("a", "b", "c", "d"):
        (cursor / "skills" / name).mkdir(parents=True)
        (cursor / "skills" / name / "SKILL.md").write_text("x", encoding="utf-8")
    (cursor / "domains.yaml").write_text(
        "domains:\n"
        f"  a:\n    skills: [{_CURSOR_DIR}/skills/a/SKILL.md]\n"
        f"  b:\n    skills: [{_CURSOR_DIR}/skills/b/SKILL.md]\n"
        f"  c:\n    skills: [{_CURSOR_DIR}/skills/c/SKILL.md]\n"
        f"  d:\n    skills: [{_CURSOR_DIR}/skills/d/SKILL.md]\n",
        encoding="utf-8",
    )
    (root / "module.py").write_text("# @!a,b,c,d\n", encoding="utf-8")

    assert cmd_verify_domains(root, strict=False) == 1
