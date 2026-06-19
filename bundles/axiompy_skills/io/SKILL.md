---
name: io
description: Outbound and local transport — HTTP clients, file I/O, serialization, web helpers. Use when editing axiompy.io or axiompy.web.
---

# I/O domain (axiompy)

Shared **code-style** and **design-patterns** load separately via `domains.yaml`. This skill is **transport-only** guidance.

> **FIXME (interim):** Broad domain — HTTP, files, serialization, and `web.py` share `# @!io` until split into `http`, `file`, and `serialization`.

## Scope

`axiompy/io/http.py`, `http_async.py`, `file.py`, `serialization.py`, `web.py`, `io/__init__.py`.

## APIs (entry points)

| Concern | Types |
|---------|--------|
| Sync HTTP | `HTTPClientFactory`, `RetryConfig` |
| Async HTTP | factories in `http_async.py` |
| Files | `read_text`, `read_json`, `read_csv`, write helpers |
| Serialization | `serialization.py` format helpers |
| Web helpers | `axiompy.web` — framework-agnostic HTTP utilities |

## Sidecars (auto-included)

- `http.md` — sync/async HTTP specifics
- `file.md` — local file I/O
- `serialization.md` — format boundaries

## Pointers

- `axiompy/io/README.md` — install extras `[io]`, `[http]`, `[http-async]`.
