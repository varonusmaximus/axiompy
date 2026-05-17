---
name: code-review
description: Review code for quality, security, and maintainability following AxiomPy standards. Use when reviewing pull requests, code changes, or when the user asks for a code review. Covers SOLID principles, anti-patterns, and code smells.
---

# AxiomPy Code Review

## Principles (short)

- **Rule of three:** no premature abstractions.
- **HTTP-first:** prefer `axiompy.io.http` over ad hoc `requests` in runtime code unless justified.
- **SOLID:** SRP, DIP (factories + injection), prefer **Protocols** over bad inheritance (LSP).
- **Thin HTTP layer:** parse/validate → delegate to services; no business logic or DB commits in route handlers.
- **Resilient demos/CLI:** use `CatchAndLog` / structured logging so one failed external step does not kill the whole run when that is the product intent.
- **Docs diagrams:** prefer linked **images** (SVG/PNG) over embedded Mermaid in committed repo docs unless explicitly a draft.

## Anti-patterns (severity)

| Pattern | Level | Notes |
|---------|-------|--------|
| God class | ERROR | Very large classes with many unrelated responsibilities |
| Speculative ABC | WARNING | One implementation only |
| Inappropriate intimacy | WARNING | Reaching into `_private` state |
| Singleton / global mutable | WARNING | Prefer factories + DI |

## Smells (fix)

Long methods (>~50 lines), deep nesting (>4 levels), magic numbers, copy-paste, dead code, hardcoded secrets (**CRITICAL**), bare `except`, `**kwargs` hiding parameters, long parameter lists (prefer Settings/dataclasses).

## Checklist (core repo)

- [ ] Factories: `create` + `create_mock`; **enum**-based dispatch where multiple backends exist
- [ ] **Settings** dataclass with `__post_init__` validation (`axiompy.validators`)
- [ ] **Typed** public APIs; Google-style docstrings for public surface
- [ ] **Logging** via `LoggerFactory` where appropriate
- [ ] **Secrets:** `SecretsClientFactory` — no ad hoc env reads scattered in library code
- [ ] **REST / HTTP APIs** (when applicable): resource-oriented paths; soft delete via `DELETE`; avoid verb-shaped URLs — align with **`AGENTS.md`**
- [ ] No Mermaid blocks in long-lived markdown docs (use images)
- [ ] **README co-update:** every touched `axiompy/<area>/`, `examples/<name>/`, or workflow has matching `README.md` updates (install extras, breaking API, CI) — see **documentation** skill

## More examples

See [reference.md](reference.md) for short before/after snippets; deep detail lives in **`AGENTS.md`**.
