---
name: tooling
description: CLI, skills sync, and AAL implementation. Use when editing axiompy.cli or aal.
---

# Tooling domain (axiompy)

Shared **code-style**, **design-patterns**, and **testing** load separately. This skill is **CLI/AAL-only** guidance.

## Scope

`axiompy/cli/**`, `external axiom-aal package`, `axiom-aal templates via `aal install``, `bundles/axiompy_skills/**`.

## Tooling-only rules

- CLI subcommands return `int` exit codes (0 = success).
- AAL modules avoid circular imports — keep `resolve` independent of hook middleware.
- Template paths must appear in `bundles/aal_templates/manifest.json`.
- New AAL behavior needs tests in `axiom-aal repo tests` (80% coverage gate).

## Sidecars (auto-included)

`aal-cli.md` — `axiompy-skills` commands and skills authoring workflow.

## Pointers

- `axiompy/cli/README.md`, `docs/aal/`
