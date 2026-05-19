# Changelog

## 2.0.0

**Breaking (packaging):** The library is split into three installable distributions while keeping import paths stable:

- **`axiompy`** — core (`axiompy.io`, `axiompy.servers`, `axiompy.secrets`, validators, logging, `axiompy-skills`, …).
- **`axiompy-data`** — `axiompy.data` (big-data / data-engineering); depends on `axiompy`.
- **`axiompy-agents`** — `axiompy.reasoning` and `axiompy.agents`; depends on `axiompy` with HTTP/server extras.

`pip install axiompy` alone no longer installs data or agents; add `axiompy-data` and/or `axiompy-agents`, or use extras `pip install "axiompy[data]"`, `"axiompy[agents]"`, or `"axiompy[all]"` when installing from an index that hosts all three wheels.

**Breaking (web):** `ResultErrorHandler.handle_error` now raises `HttpResponseError` instead of `fastapi.HTTPException`. FastAPI apps should call `register_fastapi_http_response_handler(app)` from `axiompy.servers` (requires `[servers]`).

**Packaging:** Pydantic is a core dependency. The `[fastapi]` extra is removed (use `[servers]`). New `[io]` aggregate extra for HTTP, databases, storage, and YAML. `[all]` includes `io` and `servers` runtime dependencies plus sibling wheels.

Repository layout: **`axiompy`**, **`axiompy-data`**, and **`axiompy-agents`** are maintained as **separate Git repositories** (same `axiompy.*` import paths; install the wheels you need from your index).
