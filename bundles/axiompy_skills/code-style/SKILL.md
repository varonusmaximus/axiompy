---
name: code-style
description: Enforce AxiomPy code style and formatting conventions. Use when writing or reviewing Python code in axiompy projects, or when the user asks about formatting, imports, type hints, or file organization.
---

# AxiomPy Code Style

## Scope (this repository)

**axiompy** core: I/O (`axiompy.io`), servers (`axiompy.servers`), secrets (`axiompy.secrets`), validators, decorators, loggers, `axiompy.result` / `axiompy.web`, CLI, and bundled Cursor skills. Data and agents live in sibling distributions (`axiompy-data`, `axiompy-agents`).

## General

- Python 3.12+
- Format with **black**, lint with **ruff** (line length 100 per `pyproject.toml`)
- Type hints on **all** parameters and return types; use `from __future__ import annotations` when needed
- Prefer **`match` / `case`** over long `if` / `elif` chains for dispatch
- Use **`Enum` / `str, Enum`** for constrained states instead of raw string literals in internal logic
- Public names should be **intent-based**, not backend-specific (e.g. `execute_sql`, not `execute_arrow`)

## Imports

Group: stdlib, third-party, local (blank lines between). **Absolute** imports from `axiompy.*`. Import specific symbols, not star imports.

## HTTP clients

Prefer **`axiompy.io.http`** (`HTTPClientFactory`, `RetryConfig`) for outbound HTTP. Avoid new direct **`requests`** usage in application code unless documented (streaming, websockets, etc.).

## Layout

Package code under `axiompy/<area>/` with `__init__.py` exporting the public API; optional `README.md` per area. Factories and settings dataclasses live next to the code they construct.

For full project rules, see **`AGENTS.md`** and **`.cursorrules`**.
