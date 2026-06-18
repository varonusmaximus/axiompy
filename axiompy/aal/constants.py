# @!tooling

from __future__ import annotations

import os
import re

DEFAULT_CONFIG = {
    "version": "1.3",
    "skills_package": "axiompy",
    "skills_package_version": "2.0.0",
    "scan_entire_file": True,
    "header_scan_lines": 50,
    "ignore_dirs": [".git", "node_modules", "__pycache__", "venv", "dist", "build", ".venv"],
    "extensions": [
        ".py",
        ".ts",
        ".js",
        ".go",
        ".rs",
        ".java",
        ".sql",
        ".vue",
        ".html",
        ".sh",
    ],
    "max_domains_per_annotation": 3,
}

COMMENT_STYLES: dict[str, tuple[list[str], str | None]] = {
    ".py": (["#"], None),
    ".rb": (["#"], None),
    ".sh": (["#"], None),
    ".yml": (["#"], None),
    ".yaml": (["#"], None),
    ".ts": (["//"], "/*"),
    ".js": (["//"], "/*"),
    ".go": (["//"], "/*"),
    ".java": (["//"], "/*"),
    ".rs": (["//"], "/*"),
    ".cpp": (["//"], "/*"),
    ".vue": (["//"], "/*"),
    ".sql": (["--"], None),
    ".clj": ([";;"], None),
    ".lisp": ([";;"], None),
    ".scm": ([";;"], None),
    ".html": ([], "<!--"),
    ".xml": ([], "<!--"),
}

RESERVED_COMPACT = frozenset(
    {"ref", "load", "guard", "domain", "aal", "ref-begin", "ref-end", "begin", "end"}
)

REF_ATTR_RE = re.compile(
    r"@!(?P<kind>ref|load)\s+"
    r'uri="(?P<uri>[^"]+)"\s+'
    r'hash="(?P<hash>[a-f0-9]{16}|DRAFT)"'
    r"(?:\s+scope=\[(?P<scope>.*?)\])?",
    re.IGNORECASE,
)
GUARD_RE = re.compile(
    r"@!guard\s+when=(?P<when>[^\s]+(?:\s+[^\s]+)*?)\s+then=(?P<then>.+)$",
    re.IGNORECASE,
)
REF_BEGIN_RE = re.compile(r"@!ref-begin\b", re.IGNORECASE)
REF_END_RE = re.compile(r"@!ref-end\b", re.IGNORECASE)
COMPACT_RE = re.compile(r"^@!(?P<body>[a-z][a-z0-9-]*(?:,[a-z0-9=-]+)*)$", re.IGNORECASE)
LOAD_MOD_RE = re.compile(r"^load=(none|guard|yes)$", re.IGNORECASE)
DOMAIN_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")

CURSOR_CONFIG_DIR = os.environ.get("AXIOMPY_AAL_CURSOR_DIR", ".cursor")


def cursor_config_dir_name() -> str:
    """Return the project-relative Cursor/AAL config directory name."""
    return os.environ.get("AXIOMPY_AAL_CURSOR_DIR", ".cursor")


DOMAINS_FILE = "domains.yaml"
AAL_CONFIG_FILE = "aal.yaml"
BOOTSTRAP_FILE = "bootstrap.yaml"
MANIFEST_FILE = ".axiompy-manifest.json"
