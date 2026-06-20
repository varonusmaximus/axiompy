# AxiomPy (Cursor workspace)

## Where the rules live

1. **Cursor skills** — Install or refresh with `axiompy-skills --project`. **AAL** (hooks, verify, inject) uses the separate `axiom-aal` package: `pip install axiom-aal` then `aal install --project --hooks --force`. from repo root so `./.cursor/skills/` matches the shipped bundle. **Canonical** depth for design, review, style, docs, and testing is in those `SKILL.md` files and their sidecars.
2. **`.cursor/rules/*.mdc`** — Workflow and repo gates only (e.g. branch-first). Not a duplicate of the full style guide.
3. **History** — [`docs/ARCHIVED_AGENTS.md`](docs/ARCHIVED_AGENTS.md) holds the old monolithic ruleset for reference only.

## Quick constraints

- **Python 3.12+**; **black** + **ruff**; line length **100** (see `pyproject.toml`).
- **Branch-first:** do not commit directly to `main` (see [`.cursor/rules/branch-first-workflow.mdc`](.cursor/rules/branch-first-workflow.mdc)).
- **Public `axiompy/` + `examples/`** — same architectural bar: explicit factories/settings, `axiompy.io.http` for outbound HTTP where applicable, validators at boundaries, no hardcoded secrets.

For anything beyond this blurb, open the relevant skill under `.cursor/skills/<name>/SKILL.md` after syncing.
