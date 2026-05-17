---
name: documentation
description: AxiomPy documentation standards for docstrings, module docs, and READMEs. Use when writing docstrings, module documentation, README files, or when the user asks about documentation format.
---

# AxiomPy Documentation Standards

## Docstrings (Google style)

Public functions, classes, and methods need a one-line summary, `Args`, `Returns`, `Raises`, and (when helpful) a short `Example` or `Examples` block.

## Module docstrings

Top of each module: purpose, main capabilities, and pointers to `README.md` under the same folder or to `tests/` for behavior.

## README files

**Root `README.md`:** short overview, install, dev commands, links to CI docs and sibling repos — not a full design spec.

**Package READMEs** (`axiompy/<area>/README.md`): Quick Start, concepts, API table for factories and key types, errors, testing command, cross-links to related modules.

**Example READMEs** (`examples/<name>/README.md`): how to run the example, dependencies/extras, and patterns demonstrated — kept in sync with example code.

Use ASCII diagrams sparingly; prefer **linked images** for complex figures (see code-review skill: avoid Mermaid in committed docs unless agreed).

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

Bundled copy: keep [`bundles/axiompy_skills/documentation/SKILL.md`](../../bundles/axiompy_skills/documentation/SKILL.md) in sync with this file when editing skills in-repo (or run `axiompy-skills --project` after editing the bundle).

## API naming in docs

Document **intent** (`execute_sql`, `query`), not internal engines (`execute_arrow`, vendor-specific names). Implementation details belong in architecture or adapter sections.

## REST / HTTP docs (when you document APIs)

Resource-oriented paths; nouns not verbs; soft delete with `DELETE` on the resource instance. Align examples with **`AGENTS.md`**.

## When the root README changes

Update feature lists and install snippets when you add or remove top-level capabilities; keep coverage / test pointers accurate or remove stale tables. Then apply the **README co-update** table above for every subdirectory whose behavior changed.
