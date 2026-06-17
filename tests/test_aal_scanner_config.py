# @!testing

"""Tests for AAL scanner and config loading."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from axiompy.aal.config import cursor_config_dir, load_config
from axiompy.aal.scanner import iter_source_files, read_file_for_parse
from tests.aal_helpers import setup_minimal_repo

_CURSOR_DIR = "_aal_cursor"


@pytest.fixture(autouse=True)
def _aal_cursor_dir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AXIOMPY_AAL_CURSOR_DIR", _CURSOR_DIR)


def test_iter_source_files_only_files(tmp_path: Path):
    root = tmp_path
    setup_minimal_repo(root)
    (root / "keep.py").write_text("x = 1\n", encoding="utf-8")
    (root / "skip.py").write_text("y = 2\n", encoding="utf-8")

    config = load_config(root)
    found = list(iter_source_files(root, config, only_files=[Path("keep.py")]))
    assert len(found) == 1
    assert found[0].name == "keep.py"


def test_read_file_for_parse_header_only(tmp_path: Path):
    root = tmp_path
    setup_minimal_repo(
        root,
        aal_config=(
            'version: "1.3"\n'
            "scan_entire_file: false\n"
            "header_scan_lines: 2\n"
            "extensions: [.py]\n"
            "ignore_dirs: [venv]\n"
        ),
    )
    path = root / "long.py"
    path.write_text("# line1\n# line2\n# line3\n", encoding="utf-8")
    config = load_config(root)

    _, content = read_file_for_parse(path, config)
    assert "line3" not in content


def test_load_config_merges_yaml(tmp_path: Path):
    root = tmp_path
    setup_minimal_repo(
        root,
        aal_config='version: "1.3"\nscan_entire_file: false\nheader_scan_lines: 10\n',
    )

    config = load_config(root)
    assert config["scan_entire_file"] is False
    assert config["header_scan_lines"] == 10
    assert cursor_config_dir(root).name == _CURSOR_DIR


def test_load_config_without_pyyaml_uses_defaults(tmp_path: Path, monkeypatch):
    import builtins

    root = tmp_path
    setup_minimal_repo(root)
    real_import = builtins.__import__

    def _block_yaml(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("blocked")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block_yaml)
    config = load_config(root)
    assert config["scan_entire_file"] is True
