---
name: delivery
description: Ship workflow — Makefile, CI workflows, release hygiene. Use when editing .github or root Makefile.
---

# Delivery domain (axiompy)

**code-style**, **ship-it**, and **testing** load separately. This skill is **CI/Makefile-only** guidance.

## Scope

`Makefile`, `.github/workflows/**`, release scripts.

## Delivery-only rules

- AAL gate workflow validates changed files — keep `.cursor/domains.yaml` and `.cursor/skills/` committed.
- Workflow behavior changes require `.github/workflows/README.md` updates.

## Sidecars (auto-included)

`ci.md` — AAL gate, pre-commit vs CI split.

## Related

Use **ship-it** skill (composed via registry) for local `make ci-local` → commit → push.
