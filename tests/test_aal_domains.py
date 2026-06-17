# @!testing

"""Tests for AAL domain registry resolution."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from axiompy.aal.domains import (
    _DomainsYamlLineKind,
    _classify_domains_yaml_line,
    _load_yaml_domains,
    _parse_domains_yaml,
    domain_skill_paths,
    list_domain_names,
    load_domains,
    resolve_read_target,
    skill_path_for_domain,
)

_CURSOR_DIR = "_aal_cursor"


@pytest.fixture(autouse=True)
def _aal_cursor_dir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AXIOMPY_AAL_CURSOR_DIR", _CURSOR_DIR)


def _cursor(root: Path) -> Path:
    return root / os.environ.get("AXIOMPY_AAL_CURSOR_DIR", _CURSOR_DIR)


SAMPLE_DOMAINS_YAML = """\
domains:
  testing:
    skills:
      - .cursor/skills/testing/SKILL.md
  code-style:
    skills:
      - '.cursor/skills/code-style/SKILL.md'
# comment
  documentation:
    skills:
      - .cursor/skills/documentation/SKILL.md
"""


def test_classify_domains_yaml_line():
    assert (
        _classify_domains_yaml_line("", current=None, in_skills=False) == _DomainsYamlLineKind.SKIP
    )
    assert _classify_domains_yaml_line("# note", current=None, in_skills=False) == (
        _DomainsYamlLineKind.SKIP
    )
    assert _classify_domains_yaml_line("domains:", current=None, in_skills=False) == (
        _DomainsYamlLineKind.SKIP
    )
    assert _classify_domains_yaml_line("testing:", current=None, in_skills=False) == (
        _DomainsYamlLineKind.DOMAIN_HEADER
    )
    assert _classify_domains_yaml_line("skills:", current="testing", in_skills=False) == (
        _DomainsYamlLineKind.SKILLS_HEADER
    )
    assert _classify_domains_yaml_line("- path.md", current="testing", in_skills=True) == (
        _DomainsYamlLineKind.SKILL_ITEM
    )


def test_parse_domains_yaml_fallback():
    parsed = _parse_domains_yaml(SAMPLE_DOMAINS_YAML)
    assert set(parsed) == {"testing", "code-style", "documentation"}
    assert parsed["testing"]["skills"] == [".cursor/skills/testing/SKILL.md"]
    assert parsed["code-style"]["skills"] == [".cursor/skills/code-style/SKILL.md"]


def test_load_yaml_domains_uses_fallback_without_pyyaml(monkeypatch: pytest.MonkeyPatch):
    import builtins

    real_import = builtins.__import__

    def _block_yaml(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block_yaml)
    loaded = _load_yaml_domains(SAMPLE_DOMAINS_YAML)
    assert loaded["testing"]["skills"] == [".cursor/skills/testing/SKILL.md"]


def test_load_domains_merges_local_overlay(tmp_path: Path):
    root = tmp_path
    cursor = _cursor(root)
    cursor.mkdir()
    (cursor / "domains.yaml").write_text(
        "domains:\n  testing:\n    skills:\n      - .cursor/skills/testing/SKILL.md\n",
        encoding="utf-8",
    )
    (cursor / "domains.local.yaml").write_text(
        "domains:\n  code-style:\n    skills:\n      - .cursor/skills/code-style/SKILL.md\n",
        encoding="utf-8",
    )

    names = list_domain_names(root)
    assert names == ["code-style", "testing"]


def test_domain_skill_paths_skills_and_uri(tmp_path: Path):
    root = tmp_path
    cursor = _cursor(root)
    cursor.mkdir()
    (cursor / "domains.yaml").write_text(
        "domains:\n"
        "  testing:\n"
        "    skills:\n"
        "      - .cursor/skills/testing/SKILL.md\n"
        "  legacy:\n"
        "    uri: .cursor/skills/legacy/SKILL.md\n",
        encoding="utf-8",
    )

    assert domain_skill_paths(root, "testing") == [".cursor/skills/testing/SKILL.md"]
    assert domain_skill_paths(root, "legacy") == [".cursor/skills/legacy/SKILL.md"]
    assert domain_skill_paths(root, "missing") == []


def test_resolve_read_target_dispatch(tmp_path: Path):
    root = tmp_path
    cursor = _cursor(root)
    cursor.mkdir()
    (cursor / "domains.yaml").write_text(
        "domains:\n  testing:\n    skills:\n      - .cursor/skills/testing/SKILL.md\n",
        encoding="utf-8",
    )

    assert resolve_read_target(root, ".cursor/skills/testing/SKILL.md") == [
        ".cursor/skills/testing/SKILL.md"
    ]
    assert resolve_read_target(root, "testing/extra.md") == [".cursor/skills/testing/extra.md"]
    assert resolve_read_target(root, "testing") == [".cursor/skills/testing/SKILL.md"]


def test_skill_path_for_domain():
    assert skill_path_for_domain("testing") == f"{_CURSOR_DIR}/skills/testing/SKILL.md"


def test_load_domains_reads_primary_file(tmp_path: Path):
    root = tmp_path
    cursor = _cursor(root)
    cursor.mkdir()
    (cursor / "domains.yaml").write_text(
        "domains:\n  ship-it:\n    skills:\n      - .cursor/skills/ship-it/SKILL.md\n",
        encoding="utf-8",
    )

    loaded = load_domains(root)
    assert loaded["ship-it"]["skills"] == [".cursor/skills/ship-it/SKILL.md"]
