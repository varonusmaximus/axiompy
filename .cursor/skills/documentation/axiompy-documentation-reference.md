# AxiomPy documentation standards (normative summary)

Companion to **`documentation` / SKILL.md**.

## Docstrings (Google style)

Public functions, classes, and methods need a one-line summary, **`Args`**, **`Returns`**, **`Raises`**, and (when helpful) **`Example(s)`**.

## Module docstrings

Top of each module: purpose, main capabilities, pointers to area **`README.md`** and **`tests/`** for behavior.

## README files — layout (axiompy core repo)

### Root `README.md`

- Overview, **`pip install`**, optional extras, **local development**.
- **Install for Cursor agents:** state that **`pip install axiompy`** registers **`axiompy-skills`** on **`PATH`**; ordered steps to **sync skills** (`--project`, default sync, `--show-config`); pointer to **`AGENTS.md`** / **`docs/ARCHIVED_AGENTS.md`** for workspace vs history (not duplicate of full conventions).
- **Documentation index (agents):** table or list linking **`axiompy/README.md`**, every **`axiompy/<area>/README.md`**, and **`bundles/axiompy_skills/README.md`**. Optionally link **`examples/`** as a directory when the repo ships samples; keep the index focused on **`axiompy.*`** unless examples are strictly in-repo and on-topic.
- **Flat core modules:** a table (or equivalent) for single-file modules under **`axiompy/*.py`** (`validators`, `decorators`, `loggers`, `result`, `web`, `config`, `error`) with **source** and **test** links; complements the package hub.
- **Area table:** include a **Docs** column (or equivalent) pointing into the documentation index.
- CI, coverage pointers — not a full design spec (that lives in skills + module READMEs).

### Package hub `axiompy/README.md`

- Single entry for **flat** modules (files next to this README): short subsection each with purpose, main symbols, **read next** (subpackage README, tests, or skills).
- Table linking **`io`**, **`servers`**, **`secrets`**, **`cli`**, **`utils`** READMEs (and any future subpackages).

### Subpackage `axiompy/<area>/README.md`

- **Quick Start**, concepts, API tables (factories + key types), errors, testing command, cross-links.
- **Obligation:** adding a **new** Python subpackage under **`axiompy/`** requires adding **`axiompy/<name>/README.md`** in the same change (or immediately after) so agents can navigate without spelunking.

### Examples

- Subfolders under **`examples/`** may include a **README** for local demos. They are optional and not part of the core **`axiompy`** API unless code imports from **`axiompy.*`** only.
- **Example READMEs** (`examples/<name>/README.md`): how to run the example, dependencies/extras, and patterns demonstrated — kept in sync with example code.

### README co-update (required)

**Whenever you change code, packaging, or CI in an area, update the README(s) for that area in the same PR.** Do not merge behavior or install changes without matching documentation.

| If you change… | Update… |
|----------------|---------|
| `pyproject.toml` extras, core `dependencies`, or root install | `README.md` (repository root) |
| `axiompy/<area>/` (API, errors, install needs) | `axiompy/<area>/README.md` |
| `examples/<name>/` | `examples/<name>/README.md` |
| `.github/workflows/*.yml` | `.github/workflows/README.md` |
| `axiompy/web.py` or HTTP error types | root README + any example/server README that shows `ResultErrorHandler` or FastAPI/Flask routes |
| `axiompy/servers/` (factory, bridges, server types) | `axiompy/servers/README.md` + affected `examples/*/README.md` |

**Checklist before opening a PR:**

1. List directories touched under `axiompy/`, `examples/`, or `.github/workflows/`.
2. For each, confirm the matching `README.md` reflects new install extras, breaking changes, and public API names.
3. If you add or remove a `[project.optional-dependencies]` extra, update root README and any module README that listed the old extra name (e.g. do not document removed `[fastapi]` — use `[servers]`).

**Bundled copy:** keep [`SKILL.md`](SKILL.md) and [`bundles/axiompy_skills/documentation/SKILL.md`](../../../bundles/axiompy_skills/documentation/SKILL.md) in sync when editing skills in-repo (or run `axiompy-skills --project` after editing the bundle).

## Diagrams and figures

For **committed** long-lived markdown: prefer **linked images** (SVG/PNG) over embedded **Mermaid**, unless the doc is explicitly a short-lived draft. Use ASCII only sparingly.

## API naming in docs

Document **intent** (`execute_sql`, `query`), not internal engines or vendor-specific names.

## REST / HTTP in docs

Resource-oriented paths; nouns not verbs; soft delete with **`DELETE`** on the resource instance.

## Root README maintenance

When capabilities change, update feature lists, install snippets, skills install steps, **documentation index** links, and coverage/test pointers—or remove stale tables.
