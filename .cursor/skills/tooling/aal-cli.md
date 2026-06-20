# AAL & CLI (tooling domain)

## axiompy-skills commands

| Command | Purpose |
|---------|---------|
| `install --project --hooks` | Sync skills, domains, hooks, CI |
| `verify-domains --strict` | Validate annotations |
| `bootstrap suggest/apply/migrate` | Annotation rollout |
| `resolve --file --line --json` | Inject payload (debug) |
| `resolve --file --line --log` | Resolve + append JSONL audit log |
| `hook cursor-pretooluse` | Cursor preToolUse adapter (stdin JSON → stdout permission JSON) |
| `doctor --strict` | Registry, skills, and hook smoke test |

## Cursor inject hook

`.cursor/hooks/aal-inject.sh` delegates to `aal hook cursor-pretooluse`:

1. Read **stdin JSON** (`tool_name`, `tool_input`, `workspace_roots`).
2. Resolve domains via `resolve_edit()` for `Write` / `StrReplace`.
3. Append audit record to `.cursor/logs/aal-inject.jsonl`.
4. Write **stdout JSON**: `permission` + optional `agent_message` (inject text).

**Fail closed:** resolve errors return `permission: deny` with fix instructions.

`hooks.json` uses `matcher: Write|StrReplace` and `failClosed: true`.

Manual smoke:

```bash
echo '{"tool_name":"Write","tool_input":{"file_path":"PATH"},"workspace_roots":["'$(pwd)'"]}' \
  | aal hook cursor-pretooluse
```

## Skills composition (no in-file includes)

AAL does **not** parse `@include` inside skill markdown. Composition happens in two places:

1. **`domains.yaml`** — lists `SKILL.md` paths to load per function domain (shared packages + domain folder).
2. **Sidecars** — other `*.md` files in the same folder as `SKILL.md` are **auto-merged** by `aal.resolve.merge_skill_content`.

List only `…/SKILL.md` entries in `domains.yaml`. Do **not** list sidecar paths — that double-loads content.

## Authoring workflow

1. Edit `bundles/axiompy_skills/<name>/` (source of truth).
2. `rsync` to `.cursor/skills/<name>/` or run `aal install --project --force`.
3. `make check-skills-parity` before commit.
4. Shared rules live in **packages** (`code-style`, `design-patterns`); domain folders hold **domain-only** rules + sidecars.

## Testing

- Coverage gate ≥ 80% on `axiompy/` — extend `tests/aal_helpers.py` for fixtures.
- Hook tests: `tests/test_aal_cursor_hook.py`.

## Inject log

Hook and `resolve --log` append to **`.cursor/logs/aal-inject.jsonl`** (override with `inject_log` in `.cursor/aal.yaml`).

```bash
tail -5 .cursor/logs/aal-inject.jsonl
```
