# AxiomPy code style (normative summary)

Companion to **`code-style` / SKILL.md**.

## General

- **Python 3.12+**
- **black** + **ruff**; line length **100** (`pyproject.toml`)
- **Type hints** on all parameters and returns; `from __future__ import annotations` when needed
- Prefer **`match` / `case`** over long `if` / `elif` for dispatch
- **`Enum` / `str, Enum`** for constrained states instead of raw string literals in internal logic
- **Intent-based public names** (`execute_sql`, not `execute_arrow`)

## Imports

- Order: **stdlib**, **third party**, **local** — blank lines between groups
- **Absolute** imports from `axiompy.*`
- Import **specific** symbols; **no** `from module import *`

## HTTP

- Prefer **`axiompy.io.http`** (`HTTPClientFactory`, `RetryConfig`) for outbound HTTP
- Avoid new raw **`requests`** in library/application code unless documented (streaming, websockets, etc.)

## Layout

- Package code under `axiompy/<area>/` with `__init__.py` exporting the public API
- Optional `README.md` per area; factories and settings live next to the code they construct
