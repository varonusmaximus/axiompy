# AAL Grill Session — Questions & Answers

Track all 18 staff-engineer grill questions. Use this file during HLD work and spec finalization.

**Legend:** ✅ Answered · ⏭ N/A · ⬜ Pending · 📝 Draft / needs HLD polish

---

## Round 1: The core bet

### Q1 — Scopes vs domains

**Question:** You claim fine-grained scopes are advisory, but agents still see them. Why include scopes at all?

**Status:** ✅ **Resolved (v1.3)**

**Answer:** Collapsed to **domain-only** vocabulary. One line: `# @!code-review`. No separate `scope=` labels. Domains map to skill files via `.cursor/domains.yaml`.

---

### Q2 — What actually enforces Tier B?

**Question:** In Cursor today, what *actually* enforces `@!load` / guards with no hooks configured?

**Status:** ✅ **Resolved (v1.3)**

**Answer:** **`preToolUse` inject hooks** (committed `.cursor/hooks/`). Rules alone are probabilistic. Default: `enforcement: inject` in `.cursor/aal.yaml`. Same validation via `axiompy-skills verify-domains`.

---

### Q3 — Behavior system or documentation sync?

**Question:** CI only verifies structure; agents can violate skills while pins are valid. Pick one.

**Status:** ✅ **Resolved (v1.3)**

**Answer:** **Both, split by layer:** inject = behavior at edit time; `verify-domains` = structural validation (local + CI on changed files). CI does not prove skill compliance — inject + code review do. Honest scope.

---

## Round 2: Hashes & ops

### Q4 — Skill edit workflow / hash churn

**Question:** You edit `code-review/SKILL.md` on Monday. How many files break? Command sequence?

**Status:** ⏭ **N/A (v1.3)** — no content hashes in source.

**Answer:** Edit skills in `.cursor/skills/` freely (or use `<domain>.override/SKILL.md`). No `freeze`. After package bump: `axiompy-skills upgrade` + commit.

---

### Q5 — Audit trail without inline hashes

**Question:** Six months later, security asks what skill text governed PR #847?

**Status:** ✅ **Resolved (v1.3)**

**Answer:** **Dual provenance:** (1) pinned `axiompy` version + wheel digest in CI/requirements, (2) git snapshot of `.cursor/skills/` (+ overrides) at merge commit. `skills_package_version` is a drift hint only.

---

### Q6 — CRLF / canonical hash normalization

**Question:** Windows contributor saves CRLF in skill doc — what breaks?

**Status:** ⏭ **N/A (v1.3)** — no hash gate on skill content.

**Answer:** Normal git/editor practices. Exclude `vendor/`, `generated/` via `ignore_dirs`.

---

### Q7 — Package upgrade / stale repo files

**Question:** `pip install -U` six months later — what updates automatically vs stays stale?

**Status:** ✅ **Resolved (v1.3)**

**Answer:** **`pip` updates tooling only.** Run **`axiompy-skills upgrade`** to replace all manifest paths from package. **`*.override.md`** and `domains.local.yaml` preserved. Commit `.cursor/` + `.cursor/` after upgrade. No selective merge — full overwrite of bundled assets.

---

### Q8 — `axiompy` vs `aal` on PATH

**Question:** Why two names? PATH collision?

**Status:** ✅ **Resolved (v1.3)**

**Answer:** Distribution name vs short CLI (normal Python packaging). Mitigate with `axiompy-skills doctor`, `python -m aal`, optional `axiompy` alias. Hooks use venv-safe invocation. **Implementation target:** axiompy / `axiompy-skills` (placeholders in spec docs).

---

## Round 3: Install & packaging

### Q9 — `.cursor/` blocked or ignored

**Question:** Fallback when `.cursor/` isn't available?

**Status:** ✅ **Resolved (v1.3)**

**Answer:** **Committed repo model** — `.cursor/` + `.cursor/` are part of the contract; do not gitignore. CI validates committed tree. Claude uses same skills via middleware (adapter gap, not spec gap). Global-only install not team default.

---

## Round 4: Guards & parsing

### Q10 — Guard DSL confusion

**Question:** Explain cross-domain guard; when wouldn't it fire?

**Status:** ✅ **Simplified (v1.3)**

**Answer:** **Primary model is `# @!domain` only.** Guards are **advanced optional** (§3). No mixed-concern guard examples in happy path. Imports belong in **skill files**, not guard predicates.

---

### Q11 — Header scan / buried annotations

**Question:** License + 40 imports before AAL block — what breaks?

**Status:** ✅ **Resolved (v1.3)**

**Answer:** **`scan_entire_file: true` (default)** — whole-file parse. File-level `# @!domain` **must be at top**; function-level overrides anywhere. CI verifies **changed files** in PR.

---

### Q12 — NL guards vs structured DSL

**Question:** Edit intent NL would catch but structured guards wouldn't?

**Status:** ⏭ **N/A (v1.3)**

**Answer:** NL guards out of core spec. Label scope with `# @!domain`; skills carry rules. No open issue.

---

## Round 5: Cursor vs Claude

### Q13 — What Cursor gets for free

**Question:** Three things Cursor gets free that Claude needs middleware for?

**Status:** ✅ **Reframed**

**Tactical answer:** `preToolUse` inject hooks; committed hook config; zero host code for Cursor vs middleware for Claude. Only inject matters for security.

**Strategic answer (primary):** AAL value = installable framework, mostly deterministic inject + CI, standardization **across all domains** — not security-only. See [AAL-project-todo.md](./AAL-project-todo.md) value prop section.

---

### Q14 — Rules are still out-of-band

**Question:** You ship `.cursor/rules/aal.mdc` and `CLAUDE.md` — still out-of-band. Defend in one sentence.

**Status:** ✅ **Resolved (v1.3)**

**Answer:** AAL replaces **undifferentiated global lore** with **in-band scope labels** (`# @!domain`) and **mechanical inject** from committed skills; `.cursor/rules/aal.mdc` and `CLAUDE.md` are **host-specific glue** for AAL workflow — not policy — while hooks and CI enforce the contract.

**Three-layer model (for HLD):**

| Layer | Artifact | Role | Enforcement |
|-------|----------|------|-------------|
| **Contract** | `# @!code-review` in source | In-band scope declaration — *where* policy applies | Hook + CI |
| **Policy** | `.cursor/skills/` | Authoritative skill text — *what* applies | Injected on edit |
| **Host glue** | `.cursor/rules/aal.mdc`, `CLAUDE.md` | Tooling-specific workflow — *how* this host participates | Advisory |

**Who connects what:**

| Connection | Mechanism |
|------------|-----------|
| Skills → edits | **Hooks** (`preToolUse` → `axiompy-skills resolve` → inject) |
| Agent workflow → AAL | **Rules / CLAUDE.md** (don't strip `# @!`, trust inject, run verify) |

**One-sentence defense (canonical):** *`.cursor/rules/aal.mdc` and `CLAUDE.md` are host-specific glue for AAL workflow — not policy — while `# @!domain` and committed skills are the in-band contract hooks and CI enforce.*

---

### Q15 — Week one: local install or local + CI?

**Original grill wording:** "Rules, hooks, or CI — pick one." **Reframed (v1.3):** `axiompy-skills install --hooks` ships **hooks + host glue + skills + registry** as one committed bootstrap. Real fork:

| Option | What you ship |
|--------|----------------|
| **A — Local install** | `axiompy-skills install --hooks` → commit `.cursor/` + `.cursor/` → annotate P0 → verify inject |
| **B — Local install + CI/CD** | Same + pin package + `aal-gate.yml` |

**Answer:** **A first**, CI week two.

**One-sentence defense:** *Ship the full local bootstrap in week one — hooks and rules glue install together — and add CI in week two once the committed contract exists.*

---

## Round 6: Kill shot

### Q16 — "Comment syntax cosplaying as dependency management"

**Question (skeptic):** CODEOWNERS, GitHub permissions, path rules — why AAL?

**Status:** ✅ **Resolved (v1.3)**

**Category error:** AAL has **nothing to do with** merge approval or permissions. AAL links annotated regions to **domain practice documents** and enforces at edit time (inject) and/or CI (`verify-domains`).

**One-sentence defense:** *AAL doesn't govern who edits code — it links annotated regions to domain practice documents and enforces that link at edit time (inject) and in CI (`verify-domains`).*

---

### Q17 — Organizational failure mode

**Question:** Biggest **non-technical** reason adoption fails in six months?

**Status:** ✅ **Resolved (v1.3)**

**Answer (ranked risks):**

1. **Maintenance of the package and skills** — highest risk.
2. **Adoption / coverage** — existing code never annotated; inject has nothing to resolve.

**Mitigations:** Named steward; bootstrap workflow; future skill severity for progressive fixes.

**One-sentence defense:** *AAL fails when skill maintenance and upgrade ownership disappear — adoption stalls second when existing code never gets annotated.*

---

### Q18 — Cut half the spec for MVP

**Question:** What stays and what goes for MVP next week?

**Status:** ✅ **Resolved (v1.3)**

**Answer:** Ship the **minimum loop**: install → annotate (bootstrap phase 1) → inject → verify on PR. Cut guards, directory defaults, diagnostics, Claude middleware, and bootstrap phase 2.

**MVP — ship:**

| Category | Items |
|----------|-------|
| **Syntax** | `# @!domain`; multi-domain max **3**; file + function placement; warnings for >1 domain / incompatible pairs |
| **Registry** | `domains.yaml`, overrides, `bootstrap.yaml` |
| **Lifecycle** | `install --hooks`, `upgrade`, `uninstall`, `doctor --strict` |
| **Behavior** | `resolve` + inject hook + host glue |
| **Validation** | `verify-domains --strict --files` |
| **Bootstrap phase 1** | `bootstrap suggest`, `bootstrap apply --level file`, `annotate` (file-level), `axiompy-skills init` (new files) |
| **CI** | Workflow template on changed files |
| **Host** | Cursor only |

**Post-MVP — defer:**

| Category | Items |
|----------|-------|
| Bootstrap phase 2 | `bootstrap refine`, `annotate --function`, `report --mixed`, `coverage report` |
| Advanced | Guards (§3), `.aal-dir.yaml` directory defaults |
| Diagnostics | `explain`, `impact`, `graph` |
| Integrations | Claude middleware implementation |
| Quality | Skill-import alignment; skill severity (`error`/`warning`/`info`) |
| Nice-to-have | `refresh --check`; AST placement |

**One-sentence defense:** *MVP is install, phase-1 bootstrap annotations, inject, and CI on changed files — everything else is post-MVP polish.*

**Canonical reference:** [AAL-v1.3.0.md](./AAL-v1.3.0.md) §8.2 · [AAL-project-todo.md](./AAL-project-todo.md) MVP scope

---

## Summary

| Status | Count | Questions |
|--------|-------|-----------|
| ✅ Answered | 15 | Q1–3, Q5, Q7–11, Q13–18 |
| ⏭ N/A | 3 | Q4, Q6, Q12 |
| ⬜ Pending | 0 | — |

**Grill session complete.** HLD delivered: [AAL-HLD.md](./AAL-HLD.md).
