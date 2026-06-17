# @!code-style,testing

from __future__ import annotations

import json
from pathlib import Path

from axiompy.aal.config import load_config
from axiompy.aal.domains import domain_skill_paths, load_domains
from axiompy.aal.middleware import EditIntent, aal_pre_edit_hook
from axiompy.aal.parser import effective_annotation_at_line, parse_aal_file
from axiompy.aal.scanner import read_file_for_parse


def merge_skill_content(root: Path, skill_rel: str) -> str:
    """Read SKILL.md and markdown sidecars in the same skill directory."""
    skill_path = root / skill_rel
    if not skill_path.is_file():
        raise FileNotFoundError(skill_rel)

    parts: list[str] = [skill_path.read_text(encoding="utf-8")]
    skill_dir = skill_path.parent
    for sidecar in sorted(skill_dir.glob("*.md")):
        if sidecar.name == "SKILL.md":
            continue
        parts.append(f"\n\n---\n\n## {sidecar.stem}\n\n")
        parts.append(sidecar.read_text(encoding="utf-8"))

    override_dir = skill_dir.parent / f"{skill_dir.name}.override"
    override_skill = override_dir / "SKILL.md"
    if override_skill.is_file():
        parts.append("\n\n---\n\n## Override\n\n")
        parts.append(override_skill.read_text(encoding="utf-8"))

    return "".join(parts)


def resolve_edit(
    root: Path,
    file_path: str,
    *,
    target_line: int | None = None,
) -> dict:
    """Resolve effective domains and skill content for an edit."""
    path = Path(file_path)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        raise FileNotFoundError(file_path)

    config = load_config(root)
    domains_registry = load_domains(root)
    ext, content = read_file_for_parse(path, config)
    aal = parse_aal_file(content, ext)

    line = target_line or len(content.splitlines()) or 1
    ann = effective_annotation_at_line(aal, line)
    if ann is None or not ann.load:
        return {
            "file": str(path.relative_to(root)),
            "line": line,
            "domains": [],
            "skills": [],
            "content": "",
        }

    if len(ann.domains) > int(config.get("max_domains_per_annotation", 3)):
        raise ValueError(f"too many domains at line {line}")

    skills_payload: list[dict] = []
    merged_parts: list[str] = []
    for domain in ann.domains:
        if domain not in domains_registry:
            raise ValueError(f"unknown domain {domain!r}")
        for skill_rel in domain_skill_paths(root, domain):
            if not (root / skill_rel).is_file():
                raise FileNotFoundError(skill_rel)
            text = merge_skill_content(root, skill_rel)
            skills_payload.append({"domain": domain, "path": skill_rel, "content": text})
            merged_parts.append(f"# Domain: {domain}\n\n{text}")

    return {
        "file": str(path.relative_to(root)),
        "line": line,
        "domains": ann.domains,
        "skills": skills_payload,
        "content": "\n\n---\n\n".join(merged_parts),
    }


def cmd_resolve(
    root: Path,
    file_path: str,
    *,
    line: int | None = None,
    as_json: bool = False,
) -> int:
    try:
        payload = resolve_edit(root, file_path, target_line=line)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        return 1

    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"file: {payload['file']}  line: {payload['line']}")
        print(f"domains: {', '.join(payload['domains']) or '(none)'}")
        for skill in payload["skills"]:
            print(f"  {skill['domain']} → {skill['path']}")
    return 0
