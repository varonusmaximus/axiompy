# AxiomPy ↔ AAL mapping

Bridge document between the portable AAL spec and this repository's implementation.

## Package and CLI

| AAL concept | AxiomPy implementation |
|-------------|------------------------|
| `pip install agentic-aal` | `pip install axiompy` |
| `aal` CLI | `axiompy-skills` (extended with AAL subcommands) |
| `aal install --hooks` | `axiompy-skills install --project --hooks` |
| `aal upgrade` | `axiompy-skills upgrade --force` |
| `aal verify-domains` | `axiompy-skills verify-domains --strict` |
| `aal resolve` | `axiompy-skills resolve --file PATH --line N --json` |
| `aal bootstrap suggest` | `axiompy-skills bootstrap suggest` |
| `aal bootstrap apply --level file` | `axiompy-skills bootstrap apply --level file --apply` |
| `aal bootstrap migrate` | `axiompy-skills bootstrap migrate --apply` |
| `aal annotate FILE --domain D` | `axiompy-skills annotate FILE --domain D` |
| `aal doctor --strict` | `axiompy-skills doctor --strict` |

Python API: `axiompy.aal` (`parser`, `verify`, `resolve`, `middleware`, `bootstrap`).

## Registry layout (`.cursor/` first)

| AAL spec path | AxiomPy path |
|---------------|--------------|
| `.agent/domains.yaml` | `.cursor/domains.yaml` |
| `.agent/domains.local.yaml` | `.cursor/domains.local.yaml` |
| `.agent/aal.yaml` | `.cursor/aal.yaml` |
| `.agent/bootstrap.yaml` | `.cursor/bootstrap.yaml` |
| `.agent/.aal-manifest.json` | `.cursor/.axiompy-manifest.json` |
| `.agent/skills/*.md` | `.cursor/skills/<domain>/SKILL.md` |
| `{stem}.override.md` | `.cursor/skills/<domain>.override/SKILL.md` |

## Function domains vs skill packages

Annotations use **function domain** names (what the code does). Inject composes **shared packages** and **domain skill folders** — there is no `@include` syntax inside markdown.

| Layer | Path | Role |
|-------|------|------|
| Shared packages | `.cursor/skills/code-style/`, `design-patterns/`, … | Cross-cutting practice (formatting, factories, security review) |
| Domain skills | `.cursor/skills/storage/`, `io/`, `secrets/`, … | Domain-only rules in `SKILL.md` |
| Sidecars | Same folder as domain `SKILL.md` (e.g. `mcp/tools-sessions.md`) | Auto-merged by `merge_skill_content` at inject |
| Registry | `.cursor/domains.yaml` | Lists `SKILL.md` paths only — **not** sidecar paths |

### How composition works

1. `# @!storage` on a file selects the **storage** domain.
2. `domains.yaml` lists shared packages plus `.cursor/skills/storage/SKILL.md`.
3. Resolve loads each listed `SKILL.md` and **automatically appends** other `*.md` files in that folder (sidecars).
4. Domain skill text should be **domain-only** — shared factory/settings rules live in `design-patterns`, not repeated in domain files.

Example registry entry:

```yaml
storage:
  skills:
    - .cursor/skills/code-style/SKILL.md
    - .cursor/skills/design-patterns/SKILL.md
    - .cursor/skills/storage/SKILL.md   # sql.md sidecar auto-included
```

Injected paths for `# @!storage` on `axiompy/io/database.py`:

```
.cursor/skills/code-style/SKILL.md
.cursor/skills/design-patterns/SKILL.md
.cursor/skills/storage/SKILL.md  (+ storage/sql.md merged inside)
```

### Domain → composition matrix

| Domain | Shared packages | Domain folder |
|--------|-----------------|---------------|
| `core` | code-style | `core/` |
| `io` | code-style, design-patterns | `io/` |
| `storage` | code-style, design-patterns | `storage/` |
| `object` | code-style, design-patterns | `object/` |
| `rpc` | code-style, design-patterns | `rpc/` |
| `servers` | code-style, design-patterns | `servers/` |
| `mcp` | code-style, design-patterns, code-review | `mcp/` |
| `secrets` | code-style, design-patterns, code-review | `secrets/` |
| `tooling` | code-style, design-patterns, testing | `tooling/` |
| `testing` | code-style | `testing/` |
| `documentation` | code-style | `documentation/` |
| `delivery` | code-style, ship-it, testing | `delivery/` |

> **FIXME:** `io` is intentionally broad (HTTP, files, serialization, web). Split into `http`, `file`, and `serialization` domains later.

Source of truth: `bundles/axiompy_skills/` (synced to `.cursor/skills/` on install).

## Templates package

AAL install templates ship in `bundles/axiompy_aal_templates/` (wheel-bundled as `axiompy_aal_templates`).

## Open decisions resolved

1. **Registry host:** `.cursor/` first; future host-agnostic `.axiompy/` extraction documented in [HLD.md](./HLD.md) §7.
2. **Skills format:** Cursor `SKILL.md` folder trees (not flat `.md` files).
3. **CLI surface:** Extend `axiompy-skills` rather than a separate `axiompy-aal` entry point.
4. **Composition:** `domains.yaml` playlists shared + domain `SKILL.md` paths; sidecars auto-merge — no in-file includes.

## Source of truth

| Layer | File |
|-------|------|
| Narrative / onboarding | [HLD.md](./HLD.md) |
| Normative spec | [spec.md](./spec.md) |
| Runbooks | [deployment.md](./deployment.md) |
| Behavior | `axiompy/aal/` + `axiompy/cli/cursor_skills.py` |

If code and docs disagree after MVP, **code wins** — update `spec.md` in the same PR.
