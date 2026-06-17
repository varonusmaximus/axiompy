# axiompy

**Core utilities for Python applications:** I/O (HTTP, database, object storage, files, JSON-RPC), servers (Flask/FastAPI, JSON-RPC, MCP), secrets, validation, logging, decorators, and `Result` helpers.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What is in this repository

Python package [`axiompy`](axiompy/):

| Area | Path | Notes | Docs |
|------|------|--------|------|
| HTTP | [`axiompy/io/http.py`](axiompy/io/http.py), [`axiompy/io/http_async.py`](axiompy/io/http_async.py) | Sync client + optional async batch transport | [I/O README](axiompy/io/README.md) |
| Database / object storage / files | [`axiompy/io/`](axiompy/io/) | CRUD abstractions, YAML/JSON helpers | [I/O README](axiompy/io/README.md) |
| JSON-RPC | [`axiompy/io/jsonrpc.py`](axiompy/io/jsonrpc.py) | Client + batch | [I/O README](axiompy/io/README.md) |
| Servers | [`axiompy/servers/`](axiompy/servers/) | `ServerFactory`, MCP, JSON-RPC | [Servers README](axiompy/servers/README.md) |
| Secrets | [`axiompy/secrets/`](axiompy/secrets/) | Factory + AWS (Secrets Manager, KMS), local `.env` | [Secrets README](axiompy/secrets/README.md) |
| Cross-cutting | [`axiompy/validators.py`](axiompy/validators.py), [`axiompy/decorators.py`](axiompy/decorators.py), [`axiompy/loggers.py`](axiompy/loggers.py), [`axiompy/result.py`](axiompy/result.py), [`axiompy/web.py`](axiompy/web.py) (`HttpResponseError`; FastAPI bridge in [`axiompy/servers`](axiompy/servers/)) | | [Package hub](axiompy/README.md) |
| Cursor skills CLI | [`axiompy/cli/cursor_skills.py`](axiompy/cli/cursor_skills.py) | Installs bundled **SKILL.md trees** to one resolved directory (see below) | [CLI README](axiompy/cli/README.md) |

**Not in this repo:** `axiompy.data` and `axiompy.agents` / `axiompy.reasoning` ship in sibling distributions (**axiompy-data**, **axiompy-agents**) with the same import namespace when those wheels are installed.

## Installation

```bash
pip install axiompy
```

Base install includes **Pydantic** and framework-agnostic helpers (`axiompy.web`, `axiompy.result`, validators, logging). FastAPI and Flask are optional via **`[servers]`**.

Optional stacks use [extras in `pyproject.toml`](pyproject.toml) (see `[project.optional-dependencies]`):

```bash
pip install "axiompy[io]"        # HTTP, databases, object storage, YAML
pip install "axiompy[servers]"   # Flask, FastAPI, uvicorn, httpx
pip install "axiompy[dev,io,servers]"
pip install "axiompy[data]"      # pulls axiompy-data from your index
pip install "axiompy[agents]"    # pulls axiompy-agents from your index
pip install "axiompy[all]"       # io + servers + data + agents wheels
```

### Install for Cursor agents (library + skills)

1. **`pip install axiompy`** (or an editable install from [Local development](#local-development)) installs the library and registers **`axiompy-skills` on your `PATH`** (see [`pyproject.toml`](pyproject.toml) `[project.scripts]`).
2. **Sync skills:** from a repository working tree run **`axiompy-skills --project`** to install under `<cwd>/.cursor/skills/`; run **`axiompy-skills`** alone to sync to the resolved default (often `~/.cursor/skills`). Use **`axiompy-skills --show-config`** to print the resolved parent and config source without writing files.
3. **Conventions** (review, style, design patterns, testing) live in those skill trees. [`AGENTS.md`](AGENTS.md) is a short workspace pointer; historical prose is in [`docs/ARCHIVED_AGENTS.md`](docs/ARCHIVED_AGENTS.md).
4. **AAL (domain annotations + inject):** see [`docs/aal/HLD.md`](docs/aal/HLD.md) and run `axiompy-skills install --project --hooks` to provision registry, hooks, and CI templates.

### Documentation index (agents)

Use this list to jump to the README for the area you are changing.

| Topic | README |
|-------|--------|
| **AAL** (annotations, inject, CI) | [`docs/aal/HLD.md`](docs/aal/HLD.md) · [`docs/aal/README.md`](docs/aal/README.md) |
| Package map (flat modules + links to subpackages) | [`axiompy/README.md`](axiompy/README.md) |
| I/O | [`axiompy/io/README.md`](axiompy/io/README.md) |
| Servers | [`axiompy/servers/README.md`](axiompy/servers/README.md) |
| Secrets | [`axiompy/secrets/README.md`](axiompy/secrets/README.md) |
| CLI / `axiompy-skills` | [`axiompy/cli/README.md`](axiompy/cli/README.md) |
| Utils | [`axiompy/utils/README.md`](axiompy/utils/README.md) |
| Bundled skills (authoring, destinations) | [`bundles/axiompy_skills/README.md`](bundles/axiompy_skills/README.md) |

### Flat core modules (`axiompy/*.py`)

These modules live as **single `.py` files** under [`axiompy/`](axiompy/) (not separate subfolders). They do **not** each have their own `README.md`; use this table, the [package hub](axiompy/README.md), **module docstrings**, and **tests** for full detail.

| Module | Source | Tests | Role |
|--------|--------|-------|------|
| `validators` | [`axiompy/validators.py`](axiompy/validators.py) | [`tests/test_validators.py`](tests/test_validators.py) | Input validation at public boundaries (`axiompy.validators`). |
| `decorators` | [`axiompy/decorators.py`](axiompy/decorators.py) | [`tests/test_decorators.py`](tests/test_decorators.py) | Cross-cutting decorators (logging, retry, timing, etc.). |
| `loggers` | [`axiompy/loggers.py`](axiompy/loggers.py) | [`tests/test_loggers.py`](tests/test_loggers.py) | `LoggerFactory` and logging helpers. |
| `result` | [`axiompy/result.py`](axiompy/result.py) | [`tests/test_result.py`](tests/test_result.py) | `Result`, `Ok`, `Err`, and related helpers (re-exported from [`axiompy/__init__.py`](axiompy/__init__.py)). |
| `web` | [`axiompy/web.py`](axiompy/web.py) | [`tests/test_web.py`](tests/test_web.py) | Web-oriented helpers (`ResultConverter`, pagination, adapters). |
| `config` | [`axiompy/config.py`](axiompy/config.py) | — | Reserved placeholder (no public API yet). |
| `error` | [`axiompy/error.py`](axiompy/error.py) | — | Reserved placeholder (no public API yet). |

## Local development

Requires **Python 3.12+**. On macOS, run **`brew install python@3.12`** once; `make venv` uses that keg automatically (see `scripts/resolve_python312.sh`). No `export` needed if Homebrew is installed.

```bash
pip install -r requirements-dev.txt
pip install -e ".[dev,io,servers]"
make test
make lint
```

See [`.github/workflows/README.md`](.github/workflows/README.md) for CI behavior and optional secrets.

## Cursor skills (`axiompy-skills`)

The CLI installs **only** bundled **SKILL.md trees** (subfolders under one parent directory such as `~/.cursor/skills`). It does **not** copy [`AGENTS.md`](AGENTS.md) or [`.cursorrules`](.cursorrules).

### How guidance fits together

| Artifact | Role | Installed by `axiompy-skills`? |
|----------|------|--------------------------------|
| [`.cursorrules`](.cursorrules) | Workspace rules for Cursor in this repo | No |
| [`AGENTS.md`](AGENTS.md) | Short stub: where skills and `.cursor/rules` live; points to archive | No |
| `…/skills/<name>/SKILL.md` | Routed playbooks from the `axiompy_skills` package | Yes |

### Repo layout (authoring vs wheel)

- **Shipped bundle:** [`bundles/axiompy_skills/`](bundles/axiompy_skills/) (package `axiompy_skills` on the wheel).
- **Authoring mirror:** [`.cursor/skills/`](.cursor/skills/) — must match the bundle; CI enforces parity (`make check-skills-parity` or `pytest tests/test_skills_bundle_parity.py`).

Maintainer notes: [bundles/axiompy_skills/README.md](bundles/axiompy_skills/README.md) (conventions, workflow, destination rules).

### Where skills are installed (one parent directory per run)

Precedence (highest first):

1. `--dest <path>` — parent directory that will contain `code-review/`, `testing/`, etc.
2. `--project` — `<cwd>/.cursor/skills/`
3. Environment variable `AXIOMPY_SKILLS_DEST` — same parent directory semantics
4. `[tool.axiompy.skills]` in the **nearest** `pyproject.toml` (walk upward from `cwd`) — key `destination`: `global`, `project`, or an absolute path string
5. Default: `~/.cursor/skills`

Example `pyproject.toml` fragment:

```toml
[tool.axiompy.skills]
destination = "project"
```

Commands:

```bash
axiompy-skills --show-config   # print resolved parent + config source; no files written
axiompy-skills --list
axiompy-skills                 # sync using resolved destination
axiompy-skills --project       # force <cwd>/.cursor/skills/
```

## License

MIT (see `pyproject.toml`).
