---
name: code-review
description: Review code for quality, security, and maintainability following AxiomPy standards. Use when reviewing pull requests, code changes, or when the user asks for a code review. Covers SOLID principles, anti-patterns, and code smells.
---

# AxiomPy Code Review

## Philosophy

Reviews protect **correctness**, **boundaries**, and **long-term simplicity** — not personal taste. Prefer **small, explicit** designs over clever layers.

## When to use this skill

PR review, pre-merge checklist, **security** pass, **architecture** / coupling questions, and **test strategy** sanity checks.

## Normative detail

See **[reference.md](reference.md)** for triage order, hexagonal links, security, and pointers to **`design-patterns`** sidecars.

## Companion skills

- **`design-patterns`** — factories, settings, HTTP, hexagonal mapping
- **`code-style`** — formatting, imports, types
- **`testing`** — unit-heavy vs port-boundary integration
- **`documentation`** — public API docs

## Historical reference

**`docs/ARCHIVED_AGENTS.md`** — archived monolith for archaeology only.
