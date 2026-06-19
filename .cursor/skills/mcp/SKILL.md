---
name: mcp
description: MCP services, reasoning hooks, and validators — security-sensitive agent surfaces. Use when editing axiompy.servers.mcp*.
---

# MCP domain (axiompy)

Shared **code-style**, **design-patterns**, and **code-review** load separately. This skill is **MCP-only** guidance.

## Scope

`axiompy/servers/mcp.py`, `mcp_service.py`, `mcp_reasoning.py`.

## MCP-only rules

- Register tools with explicit name, handler, description, and input validation.
- Fail closed on authorization; validate arguments before side effects.
- Keep `mcp_reasoning` hooks separate from basic tool dispatch — avoid circular imports between MCP modules.

## Sidecars (auto-included)

`tools-sessions.md` — tool lifecycle, sessions, validators.

## Pointers

- `axiompy/servers/README.md` — MCP sections.
- `examples/servers/mcp_*.py`
