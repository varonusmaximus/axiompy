# CI & delivery (delivery domain)

## AAL gate workflow

- `.github/workflows/axiompy-aal-gate.yml` — scoped to changed paths in PRs.
- Requires committed `.cursor/domains.yaml` and `.cursor/skills/`.

## Local ship loop

1. `make test` or `pytest` with coverage gate.
2. `axiompy-skills verify-domains --strict` on touched files.
3. Commit with conventional message; open PR with test plan.

## Makefile

- Keep targets documented in root `README.md` when adding new developer commands.
