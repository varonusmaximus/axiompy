# @!testing

"""Tests for AAL bootstrap and annotate commands."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from axiompy.aal.bootstrap import (
    _domains_from_hint,
    _match_hint,
    _path_matches_glob,
    _warn_incompatible,
    cmd_annotate,
    cmd_bootstrap_apply,
    cmd_bootstrap_migrate,
    cmd_bootstrap_suggest,
    comment_prefix,
    migrate_annotations,
    suggest_annotations,
)
from tests.aal_helpers import cursor_dir, setup_minimal_repo

_CURSOR_DIR = "_aal_cursor"


@pytest.fixture(autouse=True)
def _aal_cursor_dir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AXIOMPY_AAL_CURSOR_DIR", _CURSOR_DIR)


def test_path_matches_glob_supports_double_star():
    assert _path_matches_glob("axiompy/aal/domains.py", "axiompy/**")
    assert _path_matches_glob("tests/test_aal.py", "tests/**")
    assert not _path_matches_glob("docs/aal/spec.md", "axiompy/**")


def test_match_hint_prefers_longest_glob():
    hints = [
        {"glob": "tests/**", "domain": "testing"},
        {"glob": "tests/test_aal*.py", "domains": ["code-style", "testing"]},
    ]
    hint = _match_hint("tests/test_aal_bootstrap.py", hints)
    assert hint is not None
    assert _domains_from_hint(hint) == ["code-style", "testing"]


def test_warn_incompatible_pairs():
    warnings = _warn_incompatible(["code-review", "testing"], [["code-review", "testing"]])
    assert "incompatible pair" in warnings[0]


def test_comment_prefix_by_extension():
    assert comment_prefix(".sql") == "--"
    assert comment_prefix(".ts") == "//"
    assert comment_prefix(".py") == "#"


def test_suggest_annotations_for_unannotated_file(tmp_path: Path):
    root = tmp_path
    setup_minimal_repo(root)
    target = root / "module.py"
    target.write_text("x = 1\n", encoding="utf-8")

    suggestions = suggest_annotations(root)
    assert len(suggestions) == 1
    assert suggestions[0]["domains"] == ["testing"]


def test_cmd_bootstrap_suggest_and_apply(tmp_path: Path, capsys):
    root = tmp_path
    setup_minimal_repo(root)
    (root / "foo.py").write_text("pass\n", encoding="utf-8")

    assert cmd_bootstrap_suggest(root) == 0
    out = capsys.readouterr().out
    assert "foo.py" in out

    assert cmd_bootstrap_apply(root, level="file", dry_run=True) == 0
    assert "would annotate" in capsys.readouterr().out

    assert cmd_bootstrap_apply(root, level="file", dry_run=False) == 0
    assert (root / "foo.py").read_text(encoding="utf-8").startswith("# @!testing")


def test_cmd_bootstrap_apply_rejects_non_file_level(tmp_path: Path, capsys):
    assert cmd_bootstrap_apply(tmp_path, level="function", dry_run=True) == 1
    assert "only --level file" in capsys.readouterr().out


def test_migrate_annotations_replaces_skill_names(tmp_path: Path):
    root = tmp_path
    setup_minimal_repo(
        root,
        domains={
            "tooling": [
                f"{_CURSOR_DIR}/skills/code-style/SKILL.md",
                f"{_CURSOR_DIR}/skills/testing/SKILL.md",
            ],
            "testing": [f"{_CURSOR_DIR}/skills/testing/SKILL.md"],
        },
        bootstrap=(
            "p0_globs:\n  - '**/*.py'\n"
            "default_domain: tooling\n"
            "path_hints:\n  - glob: 'aal/**'\n    domain: tooling\n"
            "  - glob: 'tests/**'\n    domain: testing\n"
        ),
    )
    aal_file = root / "aal" / "install.py"
    aal_file.parent.mkdir(parents=True)
    aal_file.write_text("# @!code-style,testing\nx = 1\n", encoding="utf-8")

    migrations = migrate_annotations(root)
    assert len(migrations) == 1
    assert migrations[0]["old_domains"] == ["code-style", "testing"]
    assert migrations[0]["domains"] == ["tooling"]


def test_cmd_bootstrap_migrate_apply(tmp_path: Path, capsys):
    root = tmp_path
    setup_minimal_repo(
        root,
        domains={
            "tooling": [f"{_CURSOR_DIR}/skills/testing/SKILL.md"],
            "testing": [f"{_CURSOR_DIR}/skills/testing/SKILL.md"],
        },
        bootstrap=(
            "p0_globs:\n  - '*.py'\n"
            "default_domain: tooling\n"
            "path_hints:\n  - glob: 'foo.py'\n    domain: tooling\n"
        ),
    )
    path = root / "foo.py"
    path.write_text("# @!testing\npass\n", encoding="utf-8")

    assert cmd_bootstrap_migrate(root, dry_run=True) == 0
    assert "would migrate" in capsys.readouterr().out

    assert cmd_bootstrap_migrate(root, dry_run=False) == 0
    assert path.read_text(encoding="utf-8").startswith("# @!tooling")


def test_cmd_annotate_paths(tmp_path: Path, capsys):
    root = tmp_path
    setup_minimal_repo(root)
    path = root / "new.py"
    path.write_text("x = 1\n", encoding="utf-8")

    assert cmd_annotate(root, "missing.py", "testing") == 1
    assert cmd_annotate(root, "new.py", "unknown") == 1

    assert cmd_annotate(root, "new.py", "testing", dry_run=True) == 0
    assert "would annotate" in capsys.readouterr().out

    assert cmd_annotate(root, "new.py", "testing") == 0
    assert path.read_text(encoding="utf-8").startswith("# @!testing")

    assert cmd_annotate(root, "new.py", "testing") == 0
    assert "already has annotation" in capsys.readouterr().out
