---
name: documentation
description: AxiomPy documentation standards for docstrings, module docs, and READMEs. Use when writing docstrings, module documentation, README files, or when the user asks about documentation format.
---

# AxiomPy Documentation Standards

## Philosophy

Docs should let a **new contributor** ship correct changes without reading the whole codebase—**accurate**, **scannable**, and **aligned** with the real public API.

## When to use this skill

**Docstrings**, **module docs**, **README** structure, **API naming in docs**, **diagrams** in committed markdown, and **where to put agent-facing repo navigation**.

## Repository documentation map (agents)

In the **axiompy** core repository, agents should navigate **README links** in this order:

1. **Root `README.md`** — project overview, **`pip install axiompy`**, optional extras, **local dev**, and an explicit **library + skills** flow: installing the package puts **`axiompy-skills` on `PATH`**; run **`axiompy-skills --project`** in a clone for `./.cursor/skills/`, or **`axiompy-skills`** for the resolved default; **`axiompy-skills --show-config`** to inspect resolution without writing files. Include a **flat core modules** subsection (`validators`, `decorators`, `loggers`, `result`, `web`, `config`, `error`) with links to **source** and **tests** (no per-file README for those).
2. **`axiompy/README.md`** — **package hub**: map of every subpackage README plus short sections for **flat** top-level modules with pointers to tests and subpackage docs.
3. **`axiompy/<subpackage>/README.md`** — every **code subdirectory** under `axiompy/` (`io`, `servers`, `secrets`, `cli`, `utils`, …) must have its own README for deep API and usage; **do not** leave a new subpackage without a README when you add one.
4. **`examples/`** — optional sample scripts in this repo; not required for core `axiompy` use. A root README may link the directory without listing sibling distributions.
5. **Conventions** (factories, HTTP, style, tests, review triage) — use the other bundled skills (**`design-patterns`**, **`code-style`**, **`testing`**, **`code-review`**); do not duplicate long normative lists in READMEs.

## Normative detail

See **[axiompy-documentation-reference.md](axiompy-documentation-reference.md)** (README layout rules, diagram / Mermaid policy, REST-in-docs rules).

## Historical reference

Older expanded examples live in **`docs/ARCHIVED_AGENTS.md`** (Documentation section) for archaeology only.
