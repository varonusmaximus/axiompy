# Plan: Core `axiompy.web` (Pydantic yes, FastAPI no)

Implementation plan for this repository. **Phase 2** (axiompy-data CI/docs) lives in the sibling [axiompy-data](https://github.com/varonusmaximus/axiompy-data) repo after this merges.

## Decisions (locked)

| Topic | Decision |
|-------|----------|
| **Pydantic** | **Core dependency** — `dependencies = ["pydantic>=2.0,<3.0"]` in `pyproject.toml`. Keep existing `web.py` uses of `BaseModel`, `ValidationError`, `model_dump`. |
| **FastAPI in `web.py`** | **Remove** — no `from fastapi import HTTPException`. `ResultErrorHandler` raises `HttpResponseError` instead. |
| **`axiompy[web]` extra** | **Do not add** — `web` ships with base install. |
| **`axiompy[fastapi]` extra** | **Remove** — FastAPI/uvicorn stay only under **`[servers]`**. |
| **Optional aggregates** | **`io`**, **`servers`**, **`all`** (capability names, not vendors). |

## Problem today

`axiompy/__init__.py` imports `axiompy.web`, and `web.py` imports FastAPI. Any `import axiompy.data...` (from axiompy-data) forces a FastAPI install even though data code never uses web helpers.

After this plan: base `pip install axiompy` pulls **Pydantic** only; FastAPI is needed only for **`[servers]`** or explicit FastAPI apps.

## Checklist (Phase 1 — this repo)

- [ ] **pyproject.toml** — `dependencies = ["pydantic>=2.0,<3.0"]`; remove `fastapi` extra; add `io` aggregate; expand `all`
- [ ] **axiompy/web.py** — define `HttpResponseError`; drop FastAPI import; raise it in `ResultErrorHandler.handle_error`
- [ ] **axiompy/servers/fastapi_web.py** — `raise_fastapi_http_exception()` + `register_fastapi_http_response_handler()` (lazy FastAPI; lives with `[servers]`)
- [ ] **tests/test_web.py** — `pytest.raises(HttpResponseError)`; no FastAPI import
- [ ] **examples/api_template/** — use bridge or catch `HttpResponseError`
- [ ] **README.md**, **requirements-dev.txt**, **.github/workflows/python-ci.yml** — no `[fastapi]`; document `[io]`, `[servers]`
- [ ] **CHANGELOG** — note breaking change for `handle_error` exception type
- [ ] **Verify** — `pip install -e .` then `pytest tests/test_web.py` with **no** `fastapi` installed

## Implementation detail

### 1. Core dependency — `pyproject.toml`

```toml
dependencies = ["pydantic>=2.0,<3.0"]
```

- Mirror in `[tool.poetry.dependencies]` if that section is kept in sync.
- Remove **`fastapi`** from `[project.optional-dependencies]` (deps remain under **`servers`** only).

### 2. Decouple `web.py` from FastAPI

**Edit** `axiompy/web.py` only (no separate `web_errors.py` — one small exception class belongs next to `ResultErrorHandler`):

- Add `HttpResponseError` at module top (framework-agnostic stand-in for `HTTPException`).
- Delete `from fastapi import HTTPException`.
- Keep `from pydantic import BaseModel, ValidationError`.
- In `ResultErrorHandler.handle_error`: `raise HttpResponseError(status_code=..., detail=error_detail)`.

**Export** `HttpResponseError` from `axiompy` via `axiompy/__init__.py` if desired (`from axiompy.web import HttpResponseError`).

### 3. FastAPI bridge (`[servers]` consumers) — `axiompy/servers/fastapi_web.py`

Not in `web.py` so `import axiompy.web` never touches FastAPI. Colocate with `FastAPIServer` under **`[servers]`**. Lazy-import FastAPI inside functions; import `HttpResponseError` from `axiompy.web`.

- `raise_fastapi_http_exception(err)` — manual try/except in routes
- `register_fastapi_http_response_handler(app)` — register once on the FastAPI app (preferred for `api_template`)

Export from `axiompy.servers` `__init__.py` for discoverability.

### 4. Extras cleanup

| Extra | Action |
|-------|--------|
| `fastapi` | **Delete** |
| `web` | **Do not add** |
| `io` | **Add** — aggregate `http`, `http-async`, `databases`, `storage`, `yaml` |
| `servers` | **Keep** — `flask`, `fastapi`, `uvicorn`, `httpx` |
| `all` | **Expand** — `io` + `servers` runtime deps + `axiompy-data` + `axiompy-agents` |

### 5. `axiompy/__init__.py`

Keep exporting `ResultValidator`, `ResultConverter`, etc. from `web` once FastAPI is removed from the import chain.

## API note (breaking, minor)

`ResultErrorHandler.handle_error` raises **`HttpResponseError`**, not **`fastapi.HTTPException`**.

FastAPI apps (after `pip install "axiompy[servers]"`):

```python
from axiompy.servers import register_fastapi_http_response_handler

register_fastapi_http_response_handler(app)  # once at startup
# routes may call ResultErrorHandler.handle_error(result) without try/except
```

## Phase 2 — axiompy-data (after merge)

Update sibling repo [axiompy-data](https://github.com/varonusmaximus/axiompy-data):

- `.github/workflows/python-ci.yml` — `pip install "axiompy[io] @ git+https://github.com/varonusmaximus/axiompy.git@<merge-commit>"` (no `[fastapi]`)
- `README.md` — same
- Optional `docs/CORE_AXIOMPY_EXTRAS.md` pointing here

No code changes under `axiompy/data/*` in axiompy-data.

## How to execute (workflow)

```bash
cd /path/to/axiompy
git checkout main && git pull
git checkout -b varona-core-web-extras   # or use existing branch with this plan
# implement checklist above
pip install -e .
python -m pytest tests/test_web.py -v
python -m pytest tests/ -v               # full suite with [dev,io,servers] if needed
make lint                                # or: ruff check . && ruff format --check .
git add -A && git commit -m "Make web core with pydantic; drop fastapi extra from web"
git push -u origin varona-core-web-extras
gh pr create --title "Core web module: pydantic required, FastAPI optional" --body "See docs/CORE_WEB_AND_EXTRAS_PLAN.md"
```

Then in **axiompy-data**, branch off `main`, pin CI to the axiompy merge commit, and open a small follow-up PR.

## Out of scope (Phase 1)

- Removing FastAPI from `axiompy.servers` (stays in `[servers]`).
- PyPI publish of axiompy 2.x.
- **Tornado** server backend (see below — separate effort).

## Flask (already supported)

`axiompy.servers` already supports **Flask** via `ServerType.FLASK` / `FlaskServer` in [`axiompy/servers/server.py`](axiompy/servers/server.py). It is included in the **`[servers]`** extra (`flask>=2.3.0`).

For this plan’s `HttpResponseError` change: add **`axiompy/servers/flask_web.py`** (mirror of `fastapi_web.py`) with `@app.errorhandler(HttpResponseError)` returning `jsonify(exc.detail), exc.status_code` — only needed if routes call `ResultErrorHandler.handle_error()` without catching. Flask’s existing `(dict, status_code)` tuple returns already work for manual errors.

## Future: Tornado support (not Phase 1)

Tornado is **not** implemented today. Adding it would be a **separate PR** (~medium scope), not bundled with the pydantic/FastAPI decoupling unless you explicitly expand scope.

### What to build

| Area | Work |
|------|------|
| **Enum + factory** | `ServerType.TORNADO = "tornado"`; `TornadoServer(Server)` in `server.py` (or `tornado_server.py`); register in `ServerFactory._server_map` |
| **Packaging** | `tornado = ["tornado>=6.0"]` optional extra; add to **`[servers]`** aggregate in `pyproject.toml` |
| **`TornadoServer`** | Implement `route`, `add_middleware`, `run`, `get_app` against `tornado.web.Application` + `HTTPServer` — map axiompy’s decorator style to Tornado handlers (path regex / `RequestHandler` adapter; handle dict/list JSON returns like `FlaskServer`) |
| **`HttpResponseError` bridge** | `axiompy/servers/tornado_web.py` — e.g. `register_tornado_http_response_handler(app)` using `app.add_handlers` / custom `RequestHandler` `write_error` or middleware that catches `HttpResponseError` |
| **Tests** | `tests/test_server.py` — init, route registration, JSON response, `importorskip("tornado")` (mirror Flask/FastAPI test blocks) |
| **Docs** | [`axiompy/servers/README.md`](axiompy/servers/README.md), root README `[servers]` list |

### Design friction (why it is not trivial)

- Tornado is **handler-class** and **regex-path** oriented; Flask/FastAPI use WSGI/ASGI decorators with `<param>` paths. The shared `Server.route()` API needs a **compatibility shim** (wrapper `RequestHandler` or dynamic handler generation).
- `run()` typically uses `tornado.ioloop.IOLoop` + `HTTPServer.listen()` — different from Flask `app.run()` and FastAPI+uvicorn.
- Async handlers: decide whether `Server.route` wrappers are sync-only (like today) or support coroutine handlers.

### Suggested order

1. Ship Phase 1 (pydantic core, `HttpResponseError`, `fastapi_web` + `flask_web`).
2. Follow-up PR: `TornadoServer` + `tornado` extra + tests + `tornado_web` bridge.
