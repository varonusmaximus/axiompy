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

Use ASCII diagrams sparingly; prefer **linked images** for complex figures (see code-review skill: avoid Mermaid in committed docs unless agreed).

## API naming in docs

Document **intent** (`execute_sql`, `query`), not internal engines (`execute_arrow`, vendor-specific names). Implementation details belong in architecture or adapter sections.

## REST / HTTP docs (when you document APIs)

Resource-oriented paths; nouns not verbs; soft delete with `DELETE` on the resource instance. Align examples with **`AGENTS.md`**.

## When the root README changes

Update feature lists and install snippets when you add or remove top-level capabilities; keep coverage / test pointers accurate or remove stale tables.
