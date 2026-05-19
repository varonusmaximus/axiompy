---
name: ship-it
description: >-
  Runs AxiomPy local CI (make ci-local), fixes failures up to 5 retries, then
  commits and pushes when there are changes. Use for /ship-it, ship it, run
  automation, ci-local, commit and push, merge ready, green CI, or pre-push
  checks. AxiomPy repo only; never commits on main; does not push when the
  working tree is clean after checks.
---

# Ship it (`/ship-it`)

End-to-end **local CI → commit → push** for the **axiompy** repository only. Do not run this workflow in sibling repos (axiompy-data, axiompy-agents, etc.).

## Quick workflow

1. **Scope** — Confirm cwd is the axiompy repo root (has `Makefile`, `axiompy/`, `pyproject.toml`). Stop if not.
2. **Branch** — If on `main`, stop. Create or switch to a feature branch (`<owner>-<topic>`) before continuing.
3. **Skills parity** — If `.cursor/skills/` or `bundles/axiompy_skills/` has local changes, run `make check-skills-parity` and fix mismatches before CI.
4. **Venv** — If no venv is detected (`venv`, `.ci-venv`, etc.), run `make venv`, then continue.
5. **CI** — Run `make ci-local`. On failure: diagnose, fix, re-run (max **5** full attempts). See [reference.md](reference.md).
6. **Git status** — If the working tree is **clean** (no staged/unstaged changes after CI): **stop. Do not push.** Report success and any unpushed commits only if the user asks.
7. **Untracked files** — If there are **untracked** files, **ask the user** which paths to include before `git add`. Do not stage all untracked files by default.
8. **Commit** — Stage only agreed paths plus other modified files the user confirmed. Draft a 1–2 sentence commit message from the diff (repo style). Commit (hooks may run; use full permissions if needed).
9. **Push** — `git push -u origin HEAD`.

## Rules

| Topic | Rule |
|-------|------|
| Repo | **axiompy only** |
| `main` | Never commit on `main` |
| Clean tree after CI | **Do not push** |
| Untracked | **Ask** before staging |
| Retries | Max **5** `make ci-local` runs |
| Push | `git push -u origin HEAD` when a new commit was created |
| Secrets | Never commit `.env`, keys, or credentials |

## Normative detail

Step-by-step checks, failure handling, and git edge cases: **[reference.md](reference.md)**.

## Related

- **`testing`** — coverage and pytest patterns when CI fails on tests
- **`code-style`** — Ruff/format when lint fails
- **`documentation`** — README/skills parity when docs change
