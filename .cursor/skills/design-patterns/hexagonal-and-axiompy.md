# Hexagonal thinking in axiompy-shaped code

Read this with the **`design-patterns`** skill. For the ecosystem metaphor (data products, ports, adapters), see **`docs/data-product-hex-overview.md`** at the axiompy **repository root** when you have a source checkout (that file is not part of the `axiompy_skills` wheel).

## Why these links

- [A Detailed Guide to Hexagonal Architecture with Examples](https://devcookies.medium.com/a-detailed-guide-to-hexagonal-architecture-with-examples-042523acb1db) — **Domain** vs **ports** (inbound/outbound) vs **adapters**; test the core without real DB/UI.
- [A Little Architecture](https://blog.cleancoder.com/uncle-bob/2016/01/04/ALittleArchitecture.html) — **Defer** database/framework decisions; **invert dependencies** so business rules do not *compile-depend* on I/O; narrow interfaces (**Interface Segregation**) owned by the caller’s policy.

## How that maps to axiompy (library code)

| Hex concept | axiompy habit |
|-------------|----------------|
| **Domain / core** | Public types and orchestration that express **intent** (`execute_sql`, `get_secret`, HTTP use-case) without importing vendor SDKs in the middle of rules. |
| **Outbound port** | `Protocol` or small ABC + **Settings** dataclass describing the seam (e.g. credential provider, HTTP client boundary). |
| **Adapter** | Concrete client (`HTTPClientFactory.create(...)`, `SecretsClientFactory.create(...)`, DB adapter) lives at the **edge**; swapped via **enum** + factory `match`. |
| **Deferral** | No `create_from_env()` on factories—**compose** at the app root with explicit settings so tests do not need the real network or env. |

## Simplicity north star

Prefer designs where **readers see fewer names** and **fewer directions of dependency**. If a change forces many unrelated files to recompile for a one-line policy tweak, revisit port boundaries.
