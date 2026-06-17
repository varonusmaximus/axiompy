# @!code-style,testing

"""Resolve AAL domains to Cursor SKILL.md paths."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from axiompy.aal.bundle import load_manifest
from axiompy.aal.constants import DOMAINS_FILE, cursor_config_dir_name


def _parse_domains_yaml(text: str) -> dict[str, dict[str, Any]]:
    domains: dict[str, dict[str, Any]] = {}
    current: str | None = None
    in_skills = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "domains:":
            continue
        if line.endswith(":") and not line.startswith("-") and "skills" not in line:
            current = line[:-1]
            domains[current] = {"skills": []}
            in_skills = False
            continue
        if current and line == "skills:":
            in_skills = True
            continue
        if in_skills and line.startswith("- "):
            domains[current]["skills"].append(line[2:].strip().strip("\"'"))
    return domains


def _load_yaml_domains(text: str) -> dict[str, dict[str, Any]]:
    try:
        import yaml

        data = yaml.safe_load(text) or {}
        raw = data.get("domains", {})
        return raw if isinstance(raw, dict) else {}
    except ImportError:
        return _parse_domains_yaml(text)


def load_domains(root: Path) -> dict[str, dict[str, Any]]:
    cursor_dir = root / cursor_config_dir_name()
    domains: dict[str, dict[str, Any]] = {}

    primary = cursor_dir / DOMAINS_FILE
    if primary.exists():
        domains.update(_load_yaml_domains(primary.read_text(encoding="utf-8")))

    local = cursor_dir / "domains.local.yaml"
    if local.exists():
        domains.update(_load_yaml_domains(local.read_text(encoding="utf-8")))

    if domains:
        return domains

    manifest = load_manifest()
    return manifest.get("domains", {})


def domain_skill_paths(root: Path, domain: str) -> list[str]:
    domains = load_domains(root)
    entry = domains.get(domain)
    if not entry:
        return []
    skills = entry.get("skills")
    if skills:
        return list(skills)
    uri = entry.get("uri")
    return [uri] if uri else []


def resolve_read_target(root: Path, target: str) -> list[str]:
    """Resolve guard read target: domain name or explicit skill path."""
    if target.startswith(".cursor/"):
        return [target]
    if "/" in target and target.endswith(".md"):
        return [target if target.startswith(".") else f".cursor/skills/{target}"]
    return domain_skill_paths(root, target.split("/")[0])


def list_domain_names(root: Path) -> list[str]:
    return sorted(load_domains(root).keys())


def skill_path_for_domain(domain: str) -> str:
    return f"{cursor_config_dir_name()}/skills/{domain}/SKILL.md"
