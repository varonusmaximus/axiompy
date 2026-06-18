# @!tooling

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

from axiompy.aal.config import load_config


def iter_source_files(
    root: Path,
    config: dict,
    *,
    only_files: list[Path] | None = None,
) -> Iterator[Path]:
    if only_files is not None:
        for path in only_files:
            p = path if path.is_absolute() else root / path
            if p.is_file():
                yield p
        return

    ignore = set(config.get("ignore_dirs", []))
    extensions = set(config.get("extensions", []))
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore]
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix in extensions:
                yield path


def read_file_for_parse(path: Path, config: dict) -> tuple[str, str]:
    ext = path.suffix
    text = path.read_text(encoding="utf-8", errors="strict")
    if config.get("scan_entire_file", True):
        return ext, text
    lines = text.splitlines(keepends=True)[: int(config.get("header_scan_lines", 50))]
    return ext, "".join(lines)
