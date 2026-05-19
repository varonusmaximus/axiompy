---
name: testing
description: AxiomPy testing standards and patterns. Use when writing tests, test fixtures, mock clients, or when the user asks about testing conventions or coverage requirements.
---

# AxiomPy Testing Standards

## Philosophy

**Unit-heavy, boundary-aware:** prove behavior with small tests first; use **integration** where ports touch the outside world and risk is real.

## When to use this skill

**pytest** layout, **coverage**, **factory mocks**, **unit vs port-boundary integration**, and patching external systems.

## Normative detail

See **[axiompy-testing-reference.md](axiompy-testing-reference.md)**.

## Running tests

```bash
pytest tests/ -v --cov=axiompy --cov-report=term-missing
```

## Historical reference

Older expanded examples: **`docs/ARCHIVED_AGENTS.md`** (Testing section).
