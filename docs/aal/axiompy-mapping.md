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

Annotations use **function domain** names (what the code does). Each domain maps to one or more **skill packages** injected at edit time:

| Domain | Skills injected |
|--------|-----------------|
| `core` | code-style |
| `io` | code-style, design-patterns |
| `storage` | code-style, design-patterns |
| `object` | code-style, design-patterns |
| `rpc` | code-style, design-patterns |
| `servers` | code-style, design-patterns |
| `mcp` | code-style, design-patterns, code-review |
| `secrets` | code-style, design-patterns, code-review |
| `tooling` | code-style, design-patterns, testing |
| `testing` | code-style, testing |
| `documentation` | code-style, documentation |
| `delivery` | code-style, ship-it, testing |

Example: `# @!tooling` on `axiompy/aal/install.py` injects code-style + design-patterns + testing skills.

> **FIXME:** `io` is intentionally broad (HTTP, files, serialization, web). Split into `http`, `file`, and `serialization` domains later.

Skill packages live under `.cursor/skills/<name>/SKILL.md` (ingredients, not annotation targets).

## Templates package

AAL install templates ship in `bundles/axiompy_aal_templates/` (wheel-bundled as `axiompy_aal_templates`).

## Open decisions resolved

1. **Registry host:** `.cursor/` first; future host-agnostic `.axiompy/` extraction documented in [HLD.md](./HLD.md) §7.
2. **Skills format:** Cursor `SKILL.md` folder trees (not flat `.md` files).
3. **CLI surface:** Extend `axiompy-skills` rather than a separate `axiompy-aal` entry point.

## Source of truth

| Layer | File |
|-------|------|
| Narrative / onboarding | [HLD.md](./HLD.md) |
| Normative spec | [spec.md](./spec.md) |
| Runbooks | [deployment.md](./deployment.md) |
| Behavior | `axiompy/aal/` + `axiompy/cli/cursor_skills.py` |

If code and docs disagree after MVP, **code wins** — update `spec.md` in the same PR.
