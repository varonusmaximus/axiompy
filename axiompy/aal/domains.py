# @!code-style,testing

"""Resolve AAL domains to Cursor SKILL.md paths."""

from __future__ import annotations

from enum import Enum, auto
from pathlib import Path
from typing import Any

from axiompy.aal.bundle import load_manifest
from axiompy.aal.constants import DOMAINS_FILE, cursor_config_dir_name


class _DomainsYamlLineKind(Enum):
    SKIP = auto()
    DOMAIN_HEADER = auto()
    SKILLS_HEADER = auto()
    SKILL_ITEM = auto()


def _classify_domains_yaml_line(
    line: str,
    *,
    current: str | None,
    in_skills: bool,
) -> _DomainsYamlLineKind:
    match (line, current, in_skills):
        case ("", _, _) | (_, _, _) if line.startswith("#"):
            return _DomainsYamlLineKind.SKIP
        case ("domains:", _, _):
            return _DomainsYamlLineKind.SKIP
        case (domain_line, _, _) if (
            domain_line.endswith(":")
            and not domain_line.startswith("-")
            and "skills" not in domain_line
        ):
            return _DomainsYamlLineKind.DOMAIN_HEADER
        case ("skills:", name, _) if name is not None:
            return _DomainsYamlLineKind.SKILLS_HEADER
        case (item, name, True) if item.startswith("- ") and name is not None:
            return _DomainsYamlLineKind.SKILL_ITEM
        case _:
            return _DomainsYamlLineKind.SKIP


def _parse_domains_yaml(text: str) -> dict[str, dict[str, Any]]:
    domains: dict[str, dict[str, Any]] = {}
    current: str | None = None
    in_skills = False
    for raw in text.splitlines():
        line = raw.strip()
        match _classify_domains_yaml_line(line, current=current, in_skills=in_skills):
            case _DomainsYamlLineKind.SKIP:
                continue
            case _DomainsYamlLineKind.DOMAIN_HEADER:
                current = line[:-1]
                domains[current] = {"skills": []}
                in_skills = False
            case _DomainsYamlLineKind.SKILLS_HEADER:
                in_skills = True
            case _DomainsYamlLineKind.SKILL_ITEM:
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
    match entry:
        case {"skills": skills} if skills:
            return list(skills)
        case {"uri": uri} if uri:
            return [uri]
        case _:
            return []


def resolve_read_target(root: Path, target: str) -> list[str]:
    """Resolve guard read target: domain name or explicit skill path."""
    match target:
        case t if t.startswith(".cursor/"):
            return [t]
        case t if "/" in t and t.endswith(".md"):
            return [t if t.startswith(".") else f".cursor/skills/{t}"]
        case _:
            return domain_skill_paths(root, target.split("/")[0])


def list_domain_names(root: Path) -> list[str]:
    return sorted(load_domains(root).keys())


def skill_path_for_domain(domain: str) -> str:
    return f"{cursor_config_dir_name()}/skills/{domain}/SKILL.md"
