# AAL & CLI (tooling domain)

## axiompy-skills commands

| Command | Purpose |
|---------|---------|
| `install --project --hooks` | Sync skills, domains, hooks, CI |
| `verify-domains --strict` | Validate annotations |
| `bootstrap suggest/apply/migrate` | Annotation rollout |
| `resolve --file --line --json` | Inject payload for hooks |

## Skills composition (no in-file includes)

AAL does **not** parse `@include` inside skill markdown. Composition happens in two places:

1. **`domains.yaml`** — lists `SKILL.md` paths to load per function domain (shared packages + domain folder).
2. **Sidecars** — other `*.md` files in the same folder as `SKILL.md` are **auto-merged** by `axiompy.aal.resolve.merge_skill_content`.

List only `…/SKILL.md` entries in `domains.yaml`. Do **not** list sidecar paths — that double-loads content.

## Authoring workflow

1. Edit `bundles/axiompy_skills/<name>/` (source of truth).
2. `rsync` to `.cursor/skills/<name>/` or run `axiompy-skills install --project --force`.
3. `make check-skills-parity` before commit.
4. Shared rules live in **packages** (`code-style`, `design-patterns`); domain folders hold **domain-only** rules + sidecars.

## Testing

- Coverage gate ≥ 80% on `axiompy/` — extend `tests/aal_helpers.py` for fixtures.
