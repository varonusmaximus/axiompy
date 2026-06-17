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

## Bundled domains

Domain names match existing skill folder names in `bundles/axiompy_skills/`:

| Annotation | Skill path |
|------------|------------|
| `# @!code-review` | `.cursor/skills/code-review/SKILL.md` |
| `# @!code-style` | `.cursor/skills/code-style/SKILL.md` |
| `# @!design-patterns` | `.cursor/skills/design-patterns/SKILL.md` |
| `# @!documentation` | `.cursor/skills/documentation/SKILL.md` |
| `# @!ship-it` | `.cursor/skills/ship-it/SKILL.md` |
| `# @!testing` | `.cursor/skills/testing/SKILL.md` |

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
