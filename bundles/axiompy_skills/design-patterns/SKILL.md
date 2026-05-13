---
name: design-patterns
description: AxiomPy design patterns for building classes, services, and modules. Use when creating new classes, factories, services, settings, error hierarchies, or modules in axiompy projects.
---

# AxiomPy Design Patterns (core)

## Installation

Install **`axiompy`** from your team index / PyPI. Optional stacks use extras in **`pyproject.toml`** (`databases`, `storage`, `servers`, `http`, `http-async`, etc.). Sibling wheels **`axiompy-data`** / **`axiompy-agents`** extend the `axiompy.*` namespace when installed.

## This repo’s surface

| Area | Entry points |
|------|----------------|
| I/O | `HTTPClientFactory`, database + object storage factories, `JSONRPCClient`, file helpers |
| Servers | `ServerFactory`, MCP / JSON-RPC integration in `axiompy.servers` |
| Secrets | `SecretsClientFactory`, settings per backend |
| Cross-cutting | `validators`, `decorators`, `LoggerFactory`, `Result` types |

## 1. Factory (required for multi-backend components)

Use **`match` / `case`** on an **`Enum`**, not `create_for_postgres()`-style helpers. Provide **`create_mock()`** for tests.

Submodules with many adapters (e.g. embedders, stores) should expose a **sub-factory** in their `__init__.py`; a top-level factory composes them.

## 2. Explicit configuration

- **Settings dataclasses** with `__post_init__` calling `axiompy.validators`
- Pass **Settings** into `Factory.create(...)` — no `create_from_env()` on factories (load env in a separate composition/helper if needed)

## 3. Fluent configuration APIs

Methods like `add_header` / `bearer_token` return **`self`** for chaining.

## 4. Errors, composition, mocks

- Small **exception hierarchies** (base + specific types)
- **Composition** over inheritance when the type is not a true subtype
- **Mock** classes beside real implementations; record calls for assertions

## 5. HTTP

Use **`HTTPClientFactory`** for synchronous HTTP. Raw **`requests`** only where documented (streaming, websockets, etc.).

## 6. Dispatch

Prefer **`match` / `case`** for routing on types or discrete string values.

## 7. Utilities

- **Validators:** let them raise; do not wrap/re-raise without adding value
- **Decorators:** `LogExecutionTime`, `Retry`, `CatchAndLog` from `axiompy.decorators`
- **Logging:** `LoggerFactory.create_logger(__name__)`

## 8. Secrets

Create clients only via **`SecretsClientFactory.create(type, settings)`** and inject where needed.

---

Layered apps, routing tables, caching, and search ports are **application** concerns — when you work on examples or services that use axiompy, follow the same separation rules documented in **`AGENTS.md`** (routes vs services vs domain).
