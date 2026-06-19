---
name: core
description: Cross-cutting axiompy library primitives — validators, decorators, loggers, Result, config, errors, utils. Use when editing non-I/O core modules.
---

# Core domain (axiompy)

Cross-cutting rules (formatting, types) load from **code-style**; this skill is **core-only** guidance.

## Scope

`axiompy/validators.py`, `decorators.py`, `loggers.py`, `result.py`, `config.py`, `error.py`, `utils/**`.

## Core-only rules

- **No upward imports** — core utilities must not import `axiompy.io`, `axiompy.servers`, or `axiompy.secrets`.
- **Validators at boundaries** — public functions and Settings `__post_init__`; do not re-wrap validator exceptions without context.
- **Result types** for composable error paths in library code (see sidecar).

## Sidecars (auto-included)

`primitives.md` — validators, decorators, Result, logging patterns for this domain.

## Pointers

- `docs/ARCHIVED_AGENTS.md` — historical patterns only.
