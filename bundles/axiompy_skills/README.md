# AxiomPy bundled Cursor skills (`axiompy_skills`)

This package ships **only** Cursor **skill directories** (each folder contains `SKILL.md` and optional files such as `reference.md`). The [`axiompy-skills`](../../axiompy/cli/cursor_skills.py) CLI copies those trees into **one resolved parent directory** (for example `~/.cursor/skills`), where each skill is a subfolder (`code-review/`, `testing/`, …).

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

1. Edit **`.cursor/skills/<skill>/`** (`SKILL.md` and optional sidecars).
2. Copy into the bundle package tree, e.g.
   `rsync -a --delete .cursor/skills/<skill>/ bundles/axiompy_skills/<skill>/`
3. Run **`make check-skills-parity`** (or `pytest tests/test_skills_bundle_parity.py`) before committing.

## `SKILL.md` conventions (bundled skills)

- **YAML frontmatter:** `name` (kebab-case, matches folder) and `description` (third-person, when to use — primary routing hint for agents).
- **Body:** short; checklists and pointers to **sidecar** `.md` files in the same folder (e.g. `reference.md`, `axiompy-patterns.md`). For historical prose only, mention **`docs/ARCHIVED_AGENTS.md`** — do not defer to root `AGENTS.md` as authority.
- **One skill per folder**; no secrets, hostnames, or org-specific IDs in public skills.
- **Renaming** a skill folder is breaking for anyone scripting paths; note in changelog.

## Configuring the install destination

Precedence (highest first): `--dest` → `--project` → `AXIOMPY_SKILLS_DEST` → `[tool.axiompy.skills]` in the **nearest** `pyproject.toml` walking upward from the current working directory → default `~/.cursor/skills`.

`[tool.axiompy.skills]` example:

```toml
[tool.axiompy.skills]
destination = "project"   # or "global" or an absolute path string
```

Inspect resolution without writing:

```bash
axiompy-skills --show-config
```
