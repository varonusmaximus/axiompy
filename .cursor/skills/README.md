# AxiomPy bundled Cursor skills (`axiompy_skills`)

This package ships Cursor **skill directories** (each folder contains `SKILL.md` and optional sidecar `.md` files). The [`axiompy-skills`](../../axiompy/cli/cursor_skills.py) CLI copies those trees into **one resolved parent directory** (for example `.cursor/skills/`).

## Two layers

| Layer | Folders | Annotate? |
|-------|---------|-----------|
| **Shared packages** | `code-style/`, `design-patterns/`, `code-review/`, `testing/`, `documentation/`, `ship-it/` | No — composed via `domains.yaml` |
| **Domain skills** | `core/`, `io/`, `storage/`, `object/`, `rpc/`, `servers/`, `mcp/`, `secrets/`, `tooling/`, `delivery/` | No — referenced by function domain in `domains.yaml` |

File annotations use **function domain** names (`# @!storage`, `# @!io`). `.cursor/domains.yaml` lists shared packages **and** domain `SKILL.md` paths for each domain.

## Sidecars (companion docs)

A **sidecar** is any `*.md` file in the same folder as `SKILL.md` (for example `mcp/tools-sessions.md`). When inject loads a skill path, `merge_skill_content` automatically appends all sidecars in that folder.

**Registry rule:** list only `…/SKILL.md` paths in `domains.yaml`. Do not list sidecar paths separately — that duplicates content at inject time.

## Composition (not includes)

There is no `@include` syntax inside skill files. To compose skills:

1. Add shared package paths to the domain in `domains.yaml`.
2. Put domain-specific detail in the domain folder (`SKILL.md` + sidecars).

## Guidance layers (what the installer does *not* touch)

| Artifact | Role | Installed by `axiompy-skills`? |
|----------|------|--------------------------------|
| [`.cursorrules`](../../.cursorrules) | Workspace rules Cursor loads for a repo | No |
| [`AGENTS.md`](../../AGENTS.md) | Short stub (skills + archive pointer); not the normative ruleset | No |
| `…/skills/<name>/SKILL.md` | Routed playbooks from this bundle | Yes (only these trees) |

## Authoring vs shipped copy (this repository)

- **Authoring:** [`.cursor/skills/`](../../.cursor/skills/) — edit skills here during axiompy development.
- **Shipped:** this directory under `bundles/axiompy_skills/` — must match authoring; CI runs `make check-skills-parity` (or `pytest tests/test_skills_bundle_parity.py`).

Workflow:

1. Edit **`bundles/axiompy_skills/<skill>/`** or `.cursor/skills/<skill>/` (keep in sync).
2. Run **`make check-skills-parity`** before committing.
3. Run **`axiompy-skills install --project --force`** to refresh `.cursor/domains.yaml` from templates when registry changes.

## `SKILL.md` conventions (bundled skills)

- **YAML frontmatter:** `name` (kebab-case, matches folder) and `description` (third-person, when to use — primary routing hint for agents).
- **Body:** domain-only rules; **do not repeat** factory/settings guidance already in `design-patterns` or `code-style`.
- **Sidecars:** focused topic files in the same folder; auto-merged on inject.
- **One skill per folder**; no secrets, hostnames, or org-specific IDs in public skills.

## Configuring the install destination

Precedence (highest first): `--dest` → `--project` → `AXIOMPY_SKILLS_DEST` → `[tool.axiompy.skills]` in the **nearest** `pyproject.toml` walking upward from the current working directory → default `~/.cursor/skills`.

Inspect resolution without writing:

```bash
axiompy-skills --show-config
```
