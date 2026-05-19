# `axiompy.cli`

Command-line entrypoints kept **outside** the heavy import path so `import axiompy` does not load CLI machinery unless you run a command.

## `axiompy-skills`

The **`axiompy-skills`** script ([`cursor_skills.py`](cursor_skills.py)) syncs bundled Cursor **skill trees** from package `axiompy_skills` (wheel content under `bundles/axiompy_skills/` in source) into a resolved parent directory (for example `~/.cursor/skills` or `<repo>/.cursor/skills`).

- **Behavior and flags:** see repo root [README.md](../../README.md) (Cursor skills section) and [bundles/axiompy_skills/README.md](../../bundles/axiompy_skills/README.md).
- **Module entry:** `python -m axiompy.cli` may be wired for future CLIs; today the published console script is **`axiompy-skills`** ([`pyproject.toml`](../../pyproject.toml) `[project.scripts]`).
