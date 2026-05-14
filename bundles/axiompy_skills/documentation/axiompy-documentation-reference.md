# AxiomPy documentation standards (normative summary)

Companion to **`documentation` / SKILL.md**.

## Docstrings (Google style)

Public functions, classes, and methods need a one-line summary, **`Args`**, **`Returns`**, **`Raises`**, and (when helpful) **`Example(s)`**.

## Module docstrings

Top of each module: purpose, main capabilities, pointers to area **`README.md`** and **`tests/`** for behavior.

## README files

- **Root `README.md`:** overview, install, dev commands, links to CI and sibling repos — not a full design spec.
- **Package READMEs** (`axiompy/<area>/README.md`): Quick Start, concepts, API table (factories + key types), errors, testing command, cross-links.

## Diagrams and figures

For **committed** long-lived markdown: prefer **linked images** (SVG/PNG) over embedded **Mermaid**, unless the doc is explicitly a short-lived draft. Use ASCII only sparingly.

## API naming in docs

Document **intent** (`execute_sql`, `query`), not internal engines or vendor-specific names.

## REST / HTTP in docs

Resource-oriented paths; nouns not verbs; soft delete with **`DELETE`** on the resource instance.

## Root README maintenance

When capabilities change, update feature lists, install snippets, and coverage/test pointers—or remove stale tables.
