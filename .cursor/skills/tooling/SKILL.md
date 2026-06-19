---
name: tooling
description: CLI, skills sync, and AAL implementation. Use when editing axiompy.cli or axiompy.aal.
---

# Tooling domain (axiompy)

Shared **code-style**, **design-patterns**, and **testing** load separately. This skill is **CLI/AAL-only** guidance.

## Scope

`axiompy/cli/**`, `axiompy/aal/**`, `bundles/axiompy_aal_templates/**`, `bundles/axiompy_skills/**`.

## Tooling-only rules

- CLI subcommands return `int` exit codes (0 = success).
- AAL modules avoid circular imports — keep `resolve` independent of hook middleware.
- Template paths must appear in `bundles/axiompy_aal_templates/manifest.json`.
- New AAL behavior needs tests in `tests/test_aal_*.py` (80% coverage gate).

## Sidecars (auto-included)

`aal-cli.md` — `axiompy-skills` commands and skills authoring workflow.

## Pointers

- `axiompy/cli/README.md`, `docs/aal/`
