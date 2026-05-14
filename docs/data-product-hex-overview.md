# Data products, ports, and platform capabilities (overview)

This note **paraphrases** a hexagonal (ports-and-adapters) view of **autonomous data products** and **platform capabilities** without referencing any organization-specific systems or URLs. It informs how we talk about **cores**, **ports**, and **adapters** in skills and reviews.

## Core idea

- **Core (hexagon center):** Domain-owned **data + semantic meaning + contracts** (what the product *is* and *means*).
- **Ports:** **Stable interfaces** the core publishes so the outside world can discover, query, or invoke capabilities **without** reaching into storage or BI tools directly.
- **Adapters (platform):** Cross-cutting **capabilities** (search, graph reasoning, agents, notifications) that **consume** what cores publish through ports—swap or extend adapters without rewriting every core.

## Principles aligned with axiompy library style

- **Dependency direction:** High-level policies (business rules, public library APIs) **must not** depend on low-level I/O details at **compile/import** time; adapters depend on **ports** the core owns (same spirit as `SecretsClientFactory` + settings, `HTTPClientFactory`, and `Protocol`-backed seams in axiompy).
- **Defer irrelevant decisions:** Choose concrete DB, vendor SDK, or transport **after** port shapes exist—mirrors “database is an IO device” thinking ([A Little Architecture](https://blog.cleancoder.com/uncle-bob/2016/01/04/ALittleArchitecture.html))).
- **Non-symmetrical maturity:** Not every product must expose every capability day one; **progressive** exposure through the same port vocabulary reduces big-bang migrations.
- **Contracts at the port:** Structural and behavioral contracts (schemas, authz, privacy classing) are part of the **interface law**, not optional glue.

## Reading

- [Hexagonal architecture guide (ports/adapters)](https://devcookies.medium.com/a-detailed-guide-to-hexagonal-architecture-with-examples-042523acb1db)
- [A Little Architecture](https://blog.cleancoder.com/uncle-bob/2016/01/04/ALittleArchitecture.html)
