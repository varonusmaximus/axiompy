# @!code-style,testing

from __future__ import annotations

import re

from axiompy.aal.constants import (
    COMMENT_STYLES,
    COMPACT_RE,
    DOMAIN_NAME_RE,
    GUARD_RE,
    LOAD_MOD_RE,
    REF_ATTR_RE,
    REF_BEGIN_RE,
    REF_END_RE,
    RESERVED_COMPACT,
)
from axiompy.aal.models import AALFile, CompactAnnotation, GuardDirective, RefDirective


def parse_scope(scope_str: str | None) -> list[str]:
    if not scope_str or not scope_str.strip():
        return []
    return [s.strip().strip("\"'") for s in scope_str.split(",") if s.strip()]


def strip_comment(line: str, ext: str) -> str | None:
    styles = COMMENT_STYLES.get(ext, (["//", "#", "--", ";;"], "/*"))
    singles, block = styles
    stripped = line.strip()
    for prefix in singles:
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip()
    if block == "<!--" and stripped.startswith("<!--") and stripped.endswith("-->"):
        return stripped[4:-3].strip()
    if block == "/*" and stripped.startswith("/*") and stripped.endswith("*/"):
        return stripped[2:-2].strip()
    return None


def parse_compact(body: str, line_no: int) -> CompactAnnotation:
    parts = [p.strip().lower() for p in body.split(",") if p.strip()]
    domains: list[str] = []
    load = True
    for part in parts:
        if LOAD_MOD_RE.match(part):
            load = part.split("=", 1)[1] not in ("none", "guard")
            continue
        if not DOMAIN_NAME_RE.match(part):
            raise ValueError(f"invalid domain name {part!r}")
        if part in RESERVED_COMPACT:
            raise ValueError(f"reserved name {part!r}")
        domains.append(part)
    if not domains:
        raise ValueError("compact annotation requires at least one domain")
    return CompactAnnotation(domains=domains, load=load, line_no=line_no, raw_line=f"@!{body}")


def split_guard_segments(text: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    in_quote = False
    for ch in text:
        if ch == '"':
            in_quote = not in_quote
            current.append(ch)
        elif ch == "," and not in_quote:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


def parse_guard_then(then_part: str) -> list[tuple[str, str]]:
    actions: list[tuple[str, str]] = []
    for segment in split_guard_segments(then_part):
        segment = segment.strip()
        m = re.match(r'read:("([^"]+)"|([a-z][a-z0-9-/]*))', segment, re.IGNORECASE)
        if not m:
            raise ValueError(f"invalid guard action: {segment!r}")
        target = m.group(2) or m.group(3)
        actions.append(("read", target))
    return actions


def parse_guard_when(when_part: str) -> list[tuple[str, str]]:
    triggers: list[tuple[str, str]] = []
    allowed = {"symbol", "import", "path", "keyword", "always"}
    for segment in split_guard_segments(when_part):
        segment = segment.strip()
        if ":" not in segment:
            raise ValueError(f"invalid guard trigger: {segment!r}")
        kind, pattern = segment.split(":", 1)
        kind = kind.strip().lower()
        pattern = pattern.strip()
        if kind not in allowed:
            raise ValueError(f"unknown trigger kind: {kind!r}")
        triggers.append((kind, pattern or "*"))
    if not triggers:
        raise ValueError("guard must contain at least one trigger")
    return triggers


def parse_aal_file(content: str, ext: str, max_lines: int | None = None) -> AALFile:
    """Parse v1.3 compact annotations and legacy directives."""
    result = AALFile()
    lines = content.splitlines()
    limit = len(lines) if max_lines is None else min(len(lines), max_lines)

    for idx in range(limit):
        line_no = idx + 1
        body = strip_comment(lines[idx], ext)
        if not body or not body.startswith("@!"):
            continue

        guard_match = GUARD_RE.search(body)
        if guard_match:
            when = parse_guard_when(guard_match.group("when"))
            then = parse_guard_then(guard_match.group("then"))
            result.guards.append(
                GuardDirective(when=when, then=then, line_no=line_no, raw_line=body)
            )
            continue

        ref_match = REF_ATTR_RE.search(body)
        if ref_match:
            directive = RefDirective(
                kind=ref_match.group("kind").lower(),
                uri=ref_match.group("uri"),
                hash=ref_match.group("hash").lower(),
                scope=parse_scope(ref_match.group("scope")),
                line_no=line_no,
                raw_line=body,
            )
            if directive.kind == "load":
                result.loads.append(directive)
            else:
                result.refs.append(directive)
            continue

        if REF_BEGIN_RE.search(body) or REF_END_RE.search(body):
            continue

        compact_match = COMPACT_RE.match(body)
        if compact_match:
            result.compact.append(parse_compact(compact_match.group("body"), line_no))

    return result


def parse_header(content: str, ext: str, max_lines: int = 50) -> AALFile:
    return parse_aal_file(content, ext, max_lines)


def effective_annotation_at_line(aal: AALFile, line_no: int) -> CompactAnnotation | None:
    """Innermost compact annotation at or before line_no (function-level override)."""
    candidate: CompactAnnotation | None = None
    for ann in aal.compact:
        if ann.line_no <= line_no:
            candidate = ann
        else:
            break
    return candidate
