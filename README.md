# axiompy

**Core utilities for Python applications:** I/O (HTTP, database, object storage, files, JSON-RPC), servers (Flask/FastAPI, JSON-RPC, MCP), secrets, validation, logging, decorators, and `Result` helpers.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What is in this repository

Python package [`axiompy`](axiompy/):

| Area | Path | Notes |
|------|------|--------|
| HTTP | [`axiompy/io/http.py`](axiompy/io/http.py), [`axiompy/io/http_async.py`](axiompy/io/http_async.py) | Sync client + optional async batch transport |
| Database / object storage / files | [`axiompy/io/`](axiompy/io/) | CRUD abstractions, YAML/JSON helpers |
| JSON-RPC | [`axiompy/io/jsonrpc.py`](axiompy/io/jsonrpc.py) | Client + batch |
| Servers | [`axiompy/servers/`](axiompy/servers/) | `ServerFactory`, MCP, JSON-RPC |
| Secrets | [`axiompy/secrets/`](axiompy/secrets/) | Factory + Cerberus, AWS, Azure, local |
| Cross-cutting | [`axiompy/validators.py`](axiompy/validators.py), [`axiompy/decorators.py`](axiompy/decorators.py), [`axiompy/loggers.py`](axiompy/loggers.py), [`axiompy/result.py`](axiompy/result.py), [`axiompy/web.py`](axiompy/web.py) | |
| Cursor skills CLI | [`axiompy/cli/cursor_skills.py`](axiompy/cli/cursor_skills.py) | Syncs bundled skills to `~/.cursor/skills` |

**Not in this repo:** `axiompy.data` and `axiompy.agents` / `axiompy.reasoning` ship in sibling distributions (**axiompy-data**, **axiompy-agents**) with the same import namespace when those wheels are installed.

## Installation

```bash
pip install axiompy
```

Optional stacks use [extras in `pyproject.toml`](pyproject.toml) (see `[project.optional-dependencies]`):

```bash
pip install "axiompy[dev,servers,databases,storage,http,http-async]"
pip install "axiompy[data]"      # pulls axiompy-data from your index
pip install "axiompy[agents]"    # pulls axiompy-agents from your index
```

## Local development

```bash
pip install -r requirements-dev.txt
pip install -e ".[dev,servers,databases,storage,http,http-async]"
make test
make lint
```

See [`.github/workflows/README.md`](.github/workflows/README.md) for CI behavior and optional secrets.

## Cursor skills (`axiompy-skills`)

Bundled skills live in [`bundles/axiompy_skills/`](bundles/axiompy_skills/) (package `axiompy_skills`). Authoring copy for Cursor in-repo: [`.cursor/skills/`](.cursor/skills/).

```bash
axiompy-skills --list
axiompy-skills              # sync to ~/.cursor/skills/
axiompy-skills --project    # sync into ./.cursor/skills/
```

## Examples

- [`examples/api_template/`](examples/api_template/) — layered API template using `axiompy.servers`.
- [`examples/ecommerce_ai/`](examples/ecommerce_ai/) — requires **axiompy-agents** for `axiompy.reasoning` if you run the full demo.

## Related repositories

| Distribution | Role |
|--------------|------|
| **axiompy** (this repo) | Core I/O, servers, secrets, validators |
| **axiompy-data** | `axiompy.data` |
| **axiompy-agents** | `axiompy.agents`, `axiompy.reasoning` |

## License

MIT (see `pyproject.toml`).
