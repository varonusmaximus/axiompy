# `axiompy` package

Agent-oriented map of the **core** `axiompy` distribution (this repo). Deeper API and patterns live in subpackage READMEs and tests; **conventions** (factories, style, testing) live in **Cursor skills** installed via `axiompy-skills` (see repo root [README.md](../README.md)).

## Subpackages (each has its own README)

| Area | Documentation |
|------|----------------|
| I/O (HTTP, DB, storage, files, JSON-RPC) | [io/README.md](io/README.md) |
| Servers (Flask/FastAPI, MCP, JSON-RPC) | [servers/README.md](servers/README.md) |
| Secrets (factory, AWS, local) | [secrets/README.md](secrets/README.md) |
| CLI (`axiompy-skills`, entrypoints) | [cli/README.md](cli/README.md) |
| Utilities (reserved / thin helpers) | [utils/README.md](utils/README.md) |

## Top-level modules (flat layout)

These live as `.py` files next to this README; use docstrings and `tests/` for behavior.

| Module | Role | Read next |
|--------|------|-----------|
| `validators` | Input validation helpers at API boundaries | [tests/test_validators.py](../tests/test_validators.py) |
| `decorators` | Cross-cutting decorators (logging, retry, etc.) | [tests/test_decorators.py](../tests/test_decorators.py) |
| `loggers` | `LoggerFactory` and logging helpers | [tests/test_loggers.py](../tests/test_loggers.py) |
| `result` | `Result` / `Ok` / `Err` and helpers (re-exported from `axiompy`) | [tests/test_result.py](../tests/test_result.py) |
| `web` | Web-layer helpers (`ResultConverter`, pagination, etc.) | [tests/test_web.py](../tests/test_web.py) |
| `config` | Reserved | — |
| `error` | Reserved | — |
