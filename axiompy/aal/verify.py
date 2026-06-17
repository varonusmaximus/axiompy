from __future__ import annotations

import json
from pathlib import Path

from axiompy.aal.config import load_config
from axiompy.aal.domains import domain_skill_paths, load_domains, resolve_read_target
from axiompy.aal.parser import parse_aal_file
from axiompy.aal.scanner import iter_source_files, read_file_for_parse


def _read_file_content(path: Path, config: dict) -> tuple[str, str]:
    return read_file_for_parse(path, config)


def collect_domain_usages(root: Path, config: dict) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    for path in iter_source_files(root, config):
        rel = str(path.relative_to(root))
        ext, content = _read_file_content(path, config)
        try:
            aal = parse_aal_file(content, ext)
        except ValueError:
            continue
        names: set[str] = set()
        for ann in aal.compact:
            names.update(ann.domains)
        for guard in aal.guards:
            for _, target in guard.then:
                names.add(target.split("/")[0])
        for name in names:
            graph.setdefault(name, []).append(rel)
    return graph


def cmd_verify_domains(
    root: Path,
    strict: bool,
    *,
    files: list[str] | None = None,
) -> int:
    config = load_config(root)
    domains = load_domains(root)
    if not domains:
        print("ERROR: no domains defined — run: axiompy-skills install --project --hooks")
        return 1

    max_domains = int(config.get("max_domains_per_annotation", 3))
    violations = 0
    checked = 0
    referenced: set[str] = set()

    only_paths: list[Path] | None = None
    if files:
        only_paths = [Path(f) for f in files]

    print("[AAL] Verifying domain annotations...")
    for path in iter_source_files(root, config, only_files=only_paths):
        checked += 1
        rel = path.relative_to(root)
        try:
            ext, content = _read_file_content(path, config)
            aal = parse_aal_file(content, ext)
        except UnicodeDecodeError:
            continue
        except ValueError as exc:
            print(f"ERROR: {rel}: {exc}")
            violations += 1
            continue

        if not aal.compact and not aal.guards and not aal.refs:
            continue

        for ann in aal.compact:
            if len(ann.domains) > max_domains:
                print(
                    f"ERROR: {rel}:{ann.line_no} has {len(ann.domains)} domains (max {max_domains})"
                )
                violations += 1
            if len(ann.domains) > 1:
                print(
                    f"WARN: {rel}:{ann.line_no} multiple domains "
                    f"({', '.join(ann.domains)}) — review mixed concerns"
                )
            for domain in ann.domains:
                referenced.add(domain)
                if domain not in domains:
                    print(f"ERROR: {rel}:{ann.line_no} unknown domain {domain!r}")
                    violations += 1
                    continue
                for skill in domain_skill_paths(root, domain):
                    if not (root / skill).is_file():
                        print(f"ERROR: {rel}:{ann.line_no} missing skill {skill}")
                        violations += 1

        for guard in aal.guards:
            for _, target in guard.then:
                for skill in resolve_read_target(root, target):
                    referenced.add(target.split("/")[0])
                    if not (root / skill).is_file():
                        print(f"ERROR: {rel}:{guard.line_no} guard target missing {skill}")
                        violations += 1
                    domain_key = target.split("/")[0]
                    if domain_key not in domains and not target.startswith(".cursor/"):
                        print(f"ERROR: {rel}:{guard.line_no} unknown domain {domain_key!r}")
                        violations += 1

    if only_paths is None:
        for domain, entry in domains.items():
            skills = entry.get("skills") or ([entry["uri"]] if entry.get("uri") else [])
            for skill in skills:
                if not (root / skill).is_file():
                    print(f"ERROR: domain {domain!r} skill missing: {skill}")
                    violations += 1

    pkg_version = config.get("skills_package_version")
    if strict and pkg_version:
        try:
            from axiompy import __version__ as axiompy_version

            installed = axiompy_version
        except Exception:
            installed = "unknown"
        if pkg_version != installed:
            print(
                f"WARN: .cursor/aal.yaml records skills_package_version={pkg_version!r} "
                f"but installed axiompy is {installed!r} — run: axiompy-skills upgrade"
            )
            violations += 1

    print(f"[AAL] Audited {checked} files, {len(referenced)} domain(s) referenced.")
    if violations:
        print(f"[AAL] Verification failed ({violations} issue(s)).")
        return 1
    print("[AAL] All domain annotations valid.")
    return 0
