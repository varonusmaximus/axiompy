# AAL Implementation Backlog

Maps [spec.md](./spec.md) to code in `axiompy/aal/`. **Documentation is authoritative; implementation follows.**

> **Status (branch `varona/aal-v1.3-merge`):** MVP shipped — parser, domains, verify, resolve, install, bootstrap, doctor, inject hook templates, CI gate, and dogfood annotations on this repo.

**MVP scope:** [spec.md §8.2](./spec.md) · [design-review.md](./design-review.md) Q18

---

## Phase 1 — Parser and registry (MVP)

| Spec section | Module | Deliverable |
|--------------|--------|-------------|
| §2 Compact syntax | `parser.py` | `COMPACT_RE`; domain list; multi-domain max 3 |
| §4 Precedence | `parser.py` | `effective_annotation_at_line()` |
| §4.5 Scanning | `scanner.py` | `scan_entire_file: true` default; whole-file annotation discovery |
| §5 Registry | `domains.py` | Load `domains.yaml` + `domains.local.yaml`; `domain_skill_paths()` |
| §5.1 Overrides | `overrides.py` | Glob `**/*.override.md`; frontmatter validation; append/replace merge |
| §5.2 Bootstrap | `bootstrap.py` | Load `bootstrap.yaml`; path hint resolution; incompatible pair warnings |

**Tests:** parse examples from [AAL-examples.md](./AAL-examples.md); precedence; override discovery; multi-domain cap.

---

## Phase 2 — CLI (MVP)

| Command | Module | Notes |
|---------|--------|-------|
| `install --hooks` | `install.py` | Project-scoped manifest paths; `.cursor/` + `.cursor/` + CI template |
| `upgrade [--force]` | `install.py` | Replace manifest paths; preserve `*.override.md`, `domains.local.yaml` |
| `uninstall` | `install.py` | Delete manifest paths only |
| `init` | `scanner.py` | Create **new** file with `# @!{domain}\n\n` |
| `annotate` | `scanner.py` | Add file-level `# @!domain` to existing file (idempotent) — **MVP** |
| `bootstrap suggest` | `bootstrap.py` | P0 scan + path hints → per-file domain(s) + warnings — **MVP** |
| `bootstrap apply --level file` | `bootstrap.py` | Phase 1: bulk file-level only — **MVP** |
| `resolve` | `resolve.py` | JSON for hooks: domains, skills, merged content |
| `verify-domains` | `verify.py` | Placement rules (`--strict`); `--files` for CI; max 3 domains; warnings |
| **Shared validator** | `verify.py` | Single `validate_workspace()` used by `verify-domains`, `resolve`, hook |
| `doctor [--strict]` | `doctor.py` | Package version vs `aal.yaml`; wrong `aal` on PATH |
| `override init` | `overrides.py` | Scaffold `{target}.override.md` |

**Post-MVP CLI:** `bootstrap refine`, `annotate --function`, `bootstrap report --mixed`, `coverage report`, `explain`, `impact`, `graph`, `refresh --check`

**Remove or deprecate:** `freeze`, hash logic in `check`, `refresh --plan` merge tiers.

---

## Phase 3 — Inject-on-edit (MVP)

| Spec section | Module | Deliverable |
|--------------|--------|-------------|
| §7 Inject | `middleware.py` | `aal_inject_on_edit()`, `EditIntent` |
| §6.1 Modes | `middleware.py` | `inject` / `cache` / `deny` from `aal.yaml` |
| Session cache | `session.py` | `.cursor/.aal-session.json`; mtime invalidation (optional MVP) |

**Bundled hook:** `.cursor/hooks/aal-inject.sh` → `python -m aal resolve --json` (venv-safe).

---

## Phase 4 — Templates (bundled, committed on install) — MVP

| Template | Path in repo after `install` |
|----------|------------------------------|
| Cursor rules (host glue) | `.cursor/rules/aal.mdc` — workflow glue, not policy |
| Inject hook | `.cursor/hooks.json` + `aal-inject.sh` |
| CI | `.github/workflows/aal-gate.yml` → `doctor --strict` + `verify-domains --strict --files <changed>` |
| Manifest | `.cursor/.axiompy-manifest.json` |
| Bootstrap config scaffold | `.cursor/bootstrap.yaml` (example path hints; repo-owned) |

**Post-MVP templates:** Pre-commit optional; Claude `CLAUDE.md` snippet

---

## Phase 5 — Package layout

```text
src/aal/
  parser.py, domains.py, overrides.py, bootstrap.py, resolve.py, verify.py
  middleware.py, session.py, install.py, cli.py
  bundled/
    manifest.json
    skills/
    templates/
```

---

## Non-goals (v1.3 MVP)

- Content hashes in source annotations
- `freeze` / `DRAFT` workflow
- In-place edits to bundled skills (use overrides)
- Guards (§3) in MVP parser surface
- `.aal-dir.yaml` directory defaults
- `explain` / `impact` / `graph`
- Bootstrap phase 2 (function-level bulk)
- Claude middleware implementation
- Skill severity levels; skill-import alignment
- CI running `axiompy-skills install` instead of validating committed tree

## Future (post-MVP)

- **Bootstrap phase 2** — `bootstrap refine`, `annotate --function`, `report --mixed`, `coverage report`
- **Skill severity** — `error` | `warning` | `info`; `--min-severity` on verify/bootstrap
- Skill–code import alignment checks
- Extended guard triggers (`symbol:`, `import:`, `path:`)
- Directory defaults (`.aal-dir.yaml`)
- AST placement resolver

---

## Suggested build order

1. `domains.yaml` + `bootstrap.yaml` + compact parser + override discovery + `verify-domains`
2. `install` / `upgrade` / manifest + bundled skills + committed templates
3. `resolve` + inject middleware + Cursor hook template
4. **Bootstrap phase 1:** `bootstrap suggest`, `bootstrap apply --level file`, `annotate`
5. `doctor --strict` + CI workflow template + `init`
6. Post-MVP: bootstrap phase 2, guards, `explain`, Claude adapter
