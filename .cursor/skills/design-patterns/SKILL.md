---
name: design-patterns
description: AxiomPy design patterns for building classes, services, and modules. Use when creating new classes, factories, services, settings, error hierarchies, or modules in axiompy projects.
---

# AxiomPy Design Patterns (core)

## Philosophy

- **Simplicity first:** fewer dependencies and clearer boundaries beat clever abstractions.
- **Ports and adapters:** keep **policy** (rules, public APIs) independent of **I/O mechanisms** (HTTP SDK, DB, secrets backend). See [hexagonal-and-axiompy.md](hexagonal-and-axiompy.md).
- **Public `axiompy/` + `examples/`** share the **same** architectural bar; keep internals pragmatic only where they are not part of the published surface.

## When to use this skill

Factories, **Settings** + validation, **explicit DI**, fluent configuration, **errors**, **composition vs inheritance**, **mocks**, **HTTP** and **secrets** construction, and **dispatch** style (`match` / `case`).

## This repo’s surface (entry points)

| Area | Entry points |
|------|----------------|
| I/O | `HTTPClientFactory`, database + object storage factories, `JSONRPCClient`, file helpers |
| Servers | `ServerFactory`, MCP / JSON-RPC in `axiompy.servers` |
| Secrets | `SecretsClientFactory`, settings per backend |
| Cross-cutting | `validators`, `decorators`, `LoggerFactory`, `Result` types |

## Normative detail (read next)

- **[axiompy-patterns.md](axiompy-patterns.md)** — condensed rules (factories, settings, HTTP, secrets, rule of three, layers).
- **[hexagonal-and-axiompy.md](hexagonal-and-axiompy.md)** — how hexagonal maps to axiompy + external anchors:
  - [Hexagonal architecture (ports & adapters)](https://devcookies.medium.com/a-detailed-guide-to-hexagonal-architecture-with-examples-042523acb1db)
  - [A Little Architecture](https://blog.cleancoder.com/uncle-bob/2016/01/04/ALittleArchitecture.html)

## Ecosystem-scale metaphor (optional)

If you design **data platforms** with autonomous products and pluggable capabilities, read **`docs/data-product-hex-overview.md`** in a source checkout (sanitized overview; no org-specific links).

## Installation

Install **axiompy** and optional extras from **`pyproject.toml`** (`databases`, `storage`, `servers`, `http`, `http-async`, etc.). Sibling wheels **axiompy-data** / **axiompy-agents** extend the `axiompy.*` namespace when installed.
