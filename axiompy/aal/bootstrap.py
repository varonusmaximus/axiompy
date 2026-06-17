# @!code-style,testing

from __future__ import annotations

import re
from pathlib import Path

from axiompy.aal.config import cursor_config_dir, load_config
from axiompy.aal.constants import BOOTSTRAP_FILE, COMMENT_STYLES
from axiompy.aal.domains import list_domain_names
from axiompy.aal.parser import parse_aal_file
from axiompy.aal.scanner import iter_source_files, read_file_for_parse


def _glob_to_regex(pattern: str) -> str:
    """Translate a repo-relative glob (with ``**``) into a full-match regex."""
    parts: list[str] = ["^"]
    index = 0
    while index < len(pattern):
        if pattern[index : index + 3] == "**/":
            parts.append("(?:.*/)?")
            index += 3
            continue
        if pattern[index : index + 2] == "**":
            parts.append(".*")
            index += 2
            continue
        char = pattern[index]
        if char == "*":
            parts.append("[^/]*")
            index += 1
            continue
        if char == "?":
            parts.append("[^/]")
            index += 1
            continue
        end = index
        while end < len(pattern) and pattern[end] not in {"*", "?"}:
            end += 1
        parts.append(re.escape(pattern[index:end]))
        index = end
    parts.append("$")
    return "".join(parts)


def _path_matches_glob(rel_path: str, pattern: str) -> bool:
    """Match repo-relative paths using glob semantics (supports ``**``)."""
    return re.fullmatch(_glob_to_regex(pattern), rel_path) is not None


def _load_bootstrap(root: Path) -> dict:
    path = cursor_config_dir(root) / BOOTSTRAP_FILE
    if not path.is_file():
        return {}
    try:
        import yaml

        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except ImportError:
        return {}


def _match_hint(rel_path: str, hints: list[dict]) -> dict | None:
    best: tuple[int, dict] | None = None
    for hint in hints:
        glob = hint.get("glob", "")
        if _path_matches_glob(rel_path, glob):
            score = len(glob)
            if best is None or score > best[0]:
                best = (score, hint)
    return best[1] if best else None


def _domains_from_hint(hint: dict) -> list[str]:
    if "domains" in hint:
        return list(hint["domains"])[:3]
    if "domain" in hint:
        return [hint["domain"]]
    return []


def _warn_incompatible(domains: list[str], pairs: list[list[str]]) -> list[str]:
    warnings: list[str] = []
    domain_set = set(domains)
    for pair in pairs:
        if len(pair) == 2 and pair[0] in domain_set and pair[1] in domain_set:
            warnings.append(f"incompatible pair: {pair[0]} + {pair[1]}")
    return warnings


def suggest_annotations(root: Path) -> list[dict]:
    bootstrap = _load_bootstrap(root)
    config = load_config(root)
    p0_globs = bootstrap.get("p0_globs", ["**/*.py"])
    hints = bootstrap.get("path_hints", [])
    default_domain = bootstrap.get("default_domain", "code-style")
    incompatible = bootstrap.get("incompatible_pairs", [])
    known = set(list_domain_names(root))

    suggestions: list[dict] = []
    for path in iter_source_files(root, config):
        rel = str(path.relative_to(root))
        if not any(_path_matches_glob(rel, g) for g in p0_globs):
            continue

        ext, content = read_file_for_parse(path, config)
        aal = parse_aal_file(content, ext)
        if aal.compact:
            continue

        hint = _match_hint(rel, hints)
        domains = _domains_from_hint(hint) if hint else [default_domain]
        domains = [d for d in domains if d in known][:3]
        if not domains:
            domains = [default_domain] if default_domain in known else []

        warnings = _warn_incompatible(domains, incompatible)
        if len(domains) > 1:
            warnings.append("multiple domains on file-level annotation")

        suggestions.append(
            {
                "file": rel,
                "domains": domains,
                "warnings": warnings,
            }
        )
    return suggestions


def cmd_bootstrap_suggest(root: Path) -> int:
    suggestions = suggest_annotations(root)
    if not suggestions:
        print("[AAL] No bootstrap suggestions (all P0 files annotated or none matched).")
        return 0
    print(f"[AAL] Bootstrap suggestions ({len(suggestions)} files):")
    for item in suggestions:
        domains = ",".join(item["domains"])
        print(f"  {item['file']}  →  @!{domains}")
        for warn in item["warnings"]:
            print(f"    WARN: {warn}")
    return 0


def comment_prefix(ext: str) -> str:
    match ext:
        case ".sql":
            return "--"
        case ".ts" | ".js" | ".go" | ".java" | ".rs" | ".vue" | ".cpp":
            return "//"
        case _:
            singles = COMMENT_STYLES.get(ext, (["#"], None))[0]
            return singles[0] if singles else "#"


def cmd_bootstrap_apply(root: Path, *, level: str, dry_run: bool = True) -> int:
    if level != "file":
        print("ERROR: only --level file is supported in MVP")
        return 1

    suggestions = suggest_annotations(root)
    applied = 0
    for item in suggestions:
        path = root / item["file"]
        ext = path.suffix
        prefix = comment_prefix(ext)
        domains = ",".join(item["domains"])
        line = f"{prefix} @!{domains}\n"

        if dry_run:
            print(f"  would annotate: {item['file']}  @!{domains}")
            applied += 1
            continue

        content = path.read_text(encoding="utf-8")
        if "@!" in content.splitlines()[0] if content else "":
            continue
        path.write_text(line + "\n" + content, encoding="utf-8")
        print(f"  annotated: {item['file']}  @!{domains}")
        applied += 1

    label = "would annotate" if dry_run else "annotated"
    print(f"\n[AAL] {label} {applied} file(s).")
    if dry_run:
        print("Re-run with --apply to write annotations.")
    return 0


def cmd_annotate(root: Path, file_path: str, domain: str, *, dry_run: bool = False) -> int:
    path = Path(file_path)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        print(f"ERROR: file not found: {file_path}")
        return 1

    known = set(list_domain_names(root))
    if domain not in known:
        print(f"ERROR: unknown domain {domain!r}. Available: {', '.join(sorted(known))}")
        return 1

    ext = path.suffix
    config = load_config(root)
    _, content = read_file_for_parse(path, config)
    aal = parse_aal_file(content, ext)
    if aal.compact:
        print(
            f"OK: {path.relative_to(root)} already has annotation @!{','.join(aal.compact[0].domains)}"
        )
        return 0

    prefix = comment_prefix(ext)
    line = f"{prefix} @!{domain}\n"
    if dry_run:
        print(f"would annotate: {path.relative_to(root)}  @!{domain}")
        return 0

    path.write_text(line + "\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"annotated: {path.relative_to(root)}  @!{domain}")
    return 0
