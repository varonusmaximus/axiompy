# Ship-it reference

## What `make ci-local` runs

Matches `.github/workflows/python-ci.yml`:

1. Ruff check + format check
2. Mypy on `axiompy/`
3. `pre-commit run --all-files`
4. Pytest + coverage (fail under 80%)
5. Bandit + pip-audit

Requires a venv (`make venv` if missing).

## Skills bundle parity

Before `make ci-local`, when **either** tree has edits:

- `.cursor/skills/`
- `bundles/axiompy_skills/`

Run:

```bash
make check-skills-parity
```

If parity fails, sync authoring → bundle (e.g. `rsync -a --delete .cursor/skills/<skill>/ bundles/axiompy_skills/<skill>/` per skill) and re-run until green.

## CI failure loop (max 5 attempts)

For each failure:

1. Read the failing step output (Ruff, mypy, pre-commit, pytest/coverage, security).
2. Apply the smallest fix (prefer auto-fix for format/lint when safe).
3. Re-run `make ci-local`.
4. Stop after **5** full runs and report remaining errors if still red.

Common fixes:

| Failure | Action |
|---------|--------|
| Ruff / format | Fix reported paths; re-run |
| Mypy / pre-commit mypy | Types, stubs, or `additional_dependencies` in `.pre-commit-config.yaml` |
| Coverage &lt; 80% | Add focused tests for new modules |
| Pre-commit hooks | Fix hook output; ensure venv has `pre-commit` |
| pip-audit | Upgrade vulnerable deps or document exception |

Use **`all`** permissions for shell when pre-commit or git hooks need `os.sysconf` / network.

## Git: clean tree — no push

After `make ci-local` succeeds:

```bash
git status --porcelain
```

If empty: report **"CI passed; nothing to commit; not pushing."** Do **not** run `git push` unless the user explicitly asks to push existing commits.

## Git: untracked files — ask first

If `git status` shows untracked files (`??`):

1. List them for the user.
2. Ask which paths to include in the commit (or to leave untracked).
3. Only `git add` paths the user confirms.

Modified tracked files: mention in the same prompt if the user should include them (default: include modified tracked files unless user says otherwise).

## Git: commit message

- 1–2 sentences, focus on **why**
- Match recent repo commits (`git log -5 --oneline`)
- Use a HEREDOC for `git commit -m "$(cat <<'EOF' ... EOF)"`
- Do not amend unless user rules allow (hook auto-fix on a commit you just made)

## Git: push

Only after a **new commit** in this run:

```bash
git push -u origin HEAD
```

Pre-push hooks may run (`pip-audit`, etc.); use full permissions if needed.

## PR Summary in chat

After **CI passes**, produce a PR Summary in the **assistant message** (never write `PR_SUMMARY.md` or similar unless the user asks). The user copies it into GitHub or `gh pr create --body-file -`.

### When to emit

| Situation | Emit PR Summary? |
|-----------|------------------|
| New commit pushed this run | **Yes** |
| Clean tree, branch ahead of `origin/main` | **Yes** (remind user to push first if not up to date) |
| Clean tree, branch matches remote, no commits vs `main` | Optional one-liner: nothing to PR |
| CI failed | **No** |

### Gather context

```bash
git branch --show-current
git fetch origin main 2>/dev/null || true
git log origin/main..HEAD --oneline
git diff origin/main...HEAD --stat
```

Use `main` as base unless the repo’s default branch differs. Infer a **title** from commits (imperative, ~72 chars).

### Template (copy exactly this structure)

Output a fenced **markdown** block the user can copy as-is:

~~~markdown
## Summary

- <bullet: what changed and why — 1–3 bullets, complete sentences>
- <bullet: user-visible or architectural impact if relevant>

## Test plan

- [ ] `make ci-local` (or note it already passed on this branch)
- [ ] <specific manual check tied to the change>
- [ ] <another check if needed; remove unused bullets>
~~~

### Quality bar

- **Summary**: focus on *why*, not file lists; no raw `git diff` dumps.
- **Test plan**: actionable checkboxes; include `make ci-local` when code changed.
- **Title line** (optional, above the fence): suggest one line for the PR title, e.g. `**Suggested title:** Add ship-it skill for local CI workflow`
- Do **not** run `gh pr create` unless the user explicitly asks.

### Example snippet (format only)

**Suggested title:** Add ship-it Cursor skill for local CI and push workflow

~~~markdown
## Summary

- Adds a bundled `ship-it` skill so agents run `make ci-local`, commit, and push with branch guards and untracked-file prompts.
- Syncs authoring and `bundles/axiompy_skills/` and updates cursor skills sync tests.

## Test plan

- [ ] `make ci-local` on the feature branch
- [ ] `axiompy-skills --list` shows `ship-it`
- [ ] `axiompy-skills --dry-run --project` previews sync without error
~~~

## Out of scope

- Sibling repositories (axiompy-data, axiompy-agents)
- Force push, `git push --force`, or committing on `main`
- Creating empty commits when there are no changes
- Writing PR summary files to disk (chat output only)
