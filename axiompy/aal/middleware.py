# @!tooling

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from axiompy.aal.config import load_config
from axiompy.aal.domains import domain_skill_paths, resolve_read_target
from axiompy.aal.parser import effective_annotation_at_line, parse_aal_file
from axiompy.aal.resolve import resolve_edit
from axiompy.aal.scanner import read_file_for_parse


@dataclass
class EditIntent:
    file_path: str
    description: str = ""
    symbols_touched: list[str] = field(default_factory=list)
    imports_touched: list[str] = field(default_factory=list)
    target_line: int | None = None


@dataclass
class RequiredRead:
    uri: str
    domain: str
    reason: str


def _trigger_matches(kind: str, pattern: str, intent: EditIntent, file_path: str) -> bool:
    if kind == "always":
        return True
    if kind == "symbol":
        return any(s == pattern or fnmatch(s, pattern) for s in intent.symbols_touched)
    if kind == "import":
        return any(fnmatch(i, pattern) for i in intent.imports_touched)
    if kind == "path":
        return fnmatch(file_path, pattern)
    if kind == "keyword":
        return pattern.lower() in intent.description.lower()
    return False


def aal_pre_edit_hook(workspace: str, intent: EditIntent) -> list[RequiredRead]:
    root = Path(workspace).resolve()
    path = Path(intent.file_path)
    if not path.is_absolute():
        path = root / path
    config = load_config(root)
    ext, content = read_file_for_parse(path, config)
    aal = parse_aal_file(content, ext)
    required: dict[str, RequiredRead] = {}

    line = intent.target_line or len(content.splitlines())
    ann = effective_annotation_at_line(aal, line)
    if ann and ann.load:
        for domain in ann.domains:
            for skill in domain_skill_paths(root, domain):
                required[skill] = RequiredRead(uri=skill, domain=domain, reason=f"@!{domain}")

    rel_path = str(path.relative_to(root))
    for guard in aal.guards:
        if any(_trigger_matches(k, p, intent, rel_path) for k, p in guard.when):
            for _, target in guard.then:
                for skill in resolve_read_target(root, target):
                    domain = target.split("/")[0]
                    required[skill] = RequiredRead(
                        uri=skill, domain=domain, reason=f"guard:{target}"
                    )
    return list(required.values())


def aal_inject_on_edit(workspace: str, intent: EditIntent) -> dict:
    """Orchestrator API: resolve domains and return merged skill text."""
    return resolve_edit(
        Path(workspace).resolve(),
        intent.file_path,
        target_line=intent.target_line,
    )
