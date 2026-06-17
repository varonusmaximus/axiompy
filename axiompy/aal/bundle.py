# @!code-style,testing

from __future__ import annotations

import importlib.resources
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_BUNDLE_PACKAGE = "axiompy_aal_templates"


@lru_cache(maxsize=1)
def bundled_root() -> Path:
    ref = importlib.resources.files(_BUNDLE_PACKAGE)
    path = Path(str(ref))
    if not path.is_dir():
        raise FileNotFoundError(f"AAL templates bundle not found at {path}")
    return path


def load_manifest() -> dict[str, Any]:
    path = bundled_root() / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def bundled_file(relative: str) -> Path:
    return bundled_root() / relative


def list_bundled_domains() -> list[str]:
    manifest = load_manifest()
    return list(manifest.get("domains", {}).keys())
