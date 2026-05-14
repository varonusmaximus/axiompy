# AxiomPy code review reference (normative summary)

Companion to **`code-review` / SKILL.md**.

## Architecture and coupling

- **Hexagonal / ports-and-adapters:** [Hexagonal architecture (guide)](https://devcookies.medium.com/a-detailed-guide-to-hexagonal-architecture-with-examples-042523acb1db); [Uncle Bob — *A Little Architecture*](https://blog.cleancoder.com/uncle-bob/2016/01/04/ALittleArchitecture.html). Repo overview (sanitized): **`docs/data-product-hex-overview.md`**. AxiomPy mapping: **`design-patterns` / hexagonal-and-axiompy.md`** (bundle) or **`.cursor/skills/design-patterns/hexagonal-and-axiompy.md`**.
- **Dependency rule:** domain and application **do not** import infrastructure; adapters depend inward. Prefer **composition** and **factories** over deep inheritance trees.
- **HTTP:** prefer **`axiompy.io.http`**; avoid new raw **`requests`** in library code without justification.

## AxiomPy patterns (factories, settings, errors)

Condensed checklist: **`design-patterns` / axiompy-patterns.md`** (bundle) or **`.cursor/skills/design-patterns/axiompy-patterns.md`**.

## Security and reliability

- **No secrets** in source; use **`axiompy.secrets`** or env — never commit keys/passwords.
- **Validate** inputs at boundaries (`axiompy.validators`); **log** via **`LoggerFactory`**; avoid bare `except` and silent failure.

## Review triage (simplicity-first)

1. **Correctness and invariants** — wrong behavior beats style.
2. **Coupling and boundaries** — domain vs adapters; hidden globals; **YAGNI** / speculative layers.
3. **Testability** — can behavior be proven with **units**; is integration only at **ports**?
4. **Security and observability** — secrets, validation, logging, error paths.
5. **Style nits** — last; defer to **`code-style`** unless they block readability.

## Historical reference

Older expanded narrative: **`docs/ARCHIVED_AGENTS.md`** (for archaeology only).
