---
name: servers
description: Inbound application servers — web factories, hexagonal entrypoints. Use when editing axiompy.servers (except MCP modules).
---

# Servers domain (axiompy)

Shared packages load separately. This skill is **inbound server-only** guidance (not MCP — see **mcp** domain).

## Scope

`axiompy/servers/server.py`, `fastapi_web.py`, `servers/__init__.py`.

## APIs

- `ServerFactory` — Flask/FastAPI adapter switching.

## Sidecars (auto-included)

`inbound.md` — route layering, handler thinness.

## Pointers

- `axiompy/servers/README.md`
- Install: `pip install "axiompy[servers]"`.
