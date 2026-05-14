---
name: code-style
description: Enforce AxiomPy code style and formatting conventions. Use when writing or reviewing Python code in axiompy projects, or when the user asks about formatting, imports, type hints, or file organization.
---

# AxiomPy Code Style

## Philosophy

**Readable, boring, explicit** code: types, import hygiene, and predictable structure beat shortcuts. **Public `axiompy/` and `examples/`** meet the **same** bar.

## When to use this skill

Formatting, **imports**, **line length**, **type hints**, **`match/case`**, **enums**, **HTTP client choice**, and **package layout**.

## Scope (this repository)

**axiompy** core: I/O (`axiompy.io`), servers (`axiompy.servers`), secrets (`axiompy.secrets`), validators, decorators, loggers, `axiompy.result` / `axiompy.web`, CLI, bundled Cursor skills. Data and agents live in sibling distributions (`axiompy-data`, `axiompy-agents`).

## Normative detail

See **[axiompy-style-reference.md](axiompy-style-reference.md)** for the full checklist.

## Workspace mirror

Cursor may also load **`.cursorrules`** (short reminder). Historical monolith: **`docs/ARCHIVED_AGENTS.md`**.
