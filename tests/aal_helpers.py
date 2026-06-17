# @!testing

"""Shared fixtures for AAL package tests."""

from __future__ import annotations

import os
from pathlib import Path


_CURSOR_DIR = "_aal_cursor"


def cursor_dir(root: Path) -> Path:
    return root / os.environ.get("AXIOMPY_AAL_CURSOR_DIR", _CURSOR_DIR)


def write_domains(cursor: Path, yaml_text: str) -> None:
    cursor.mkdir(parents=True, exist_ok=True)
    (cursor / "domains.yaml").write_text(yaml_text, encoding="utf-8")


def write_skill(
    cursor: Path, domain: str, body: str = "# Skill\n", *, sidecar: str | None = None
) -> Path:
    skill_dir = cursor / "skills" / domain
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text(body, encoding="utf-8")
    if sidecar:
        (skill_dir / sidecar).write_text(f"# {sidecar}\n", encoding="utf-8")
    return skill_path


def setup_minimal_repo(
    root: Path,
    *,
    domains: dict[str, list[str]] | None = None,
    bootstrap: str | None = None,
    aal_config: str | None = None,
    manifest: str | None = None,
) -> Path:
    cursor = cursor_dir(root)
    cursor.mkdir(parents=True, exist_ok=True)

    domain_lines = ["domains:"]
    domain_map = domains or {"testing": [f"{_CURSOR_DIR}/skills/testing/SKILL.md"]}
    for name, skills in domain_map.items():
        domain_lines.append(f"  {name}:")
        domain_lines.append("    skills:")
        for skill in skills:
            domain_lines.append(f"      - {skill}")
    write_domains(cursor, "\n".join(domain_lines) + "\n")

    for name in domain_map:
        rel = domain_map[name][0]
        domain = rel.split("/skills/")[-1].split("/")[0]
        write_skill(cursor, domain)

    (cursor / "bootstrap.yaml").write_text(
        bootstrap
        or (
            "p0_globs:\n  - '*.py'\n"
            "default_domain: testing\n"
            "path_hints:\n  - glob: 'tests/**'\n    domain: testing\n"
        ),
        encoding="utf-8",
    )
    (cursor / "aal.yaml").write_text(
        aal_config
        or (
            'version: "1.3"\n'
            "skills_package: axiompy\n"
            'skills_package_version: "2.0.0"\n'
            "scan_entire_file: true\n"
            "ignore_dirs: [.git, venv]\n"
            "extensions: [.py]\n"
        ),
        encoding="utf-8",
    )
    if manifest is not None:
        (cursor / ".axiompy-manifest.json").write_text(manifest, encoding="utf-8")

    (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (root / ".github/workflows/axiompy-aal-gate.yml").write_text("name: gate\n", encoding="utf-8")
    (cursor / "rules").mkdir(exist_ok=True)
    (cursor / "rules/aal.mdc").write_text("# AAL\n", encoding="utf-8")
    return cursor
