# AxiomPy design patterns (condensed normative reference)

Companion to **`design-patterns` / SKILL.md**. **Simplicity** and **explicit seams** beat cleverness.

## 1. Factory (required for instantiable classes)

- Every major service/client has a **Factory** with `create(...)` and **`create_mock()`** for tests.
- **Enum-based** `match` / `case` dispatch for multiple backends—**no** `create_for_postgres()`-style proliferation.
- **Sub-factories** live next to adapter families (e.g. embedders, vector stores); the top factory **composes** them instead of inline helpers.

## 2. Explicit configuration

- **Settings** dataclasses with **`__post_init__`** calling `axiompy.validators` (let validators raise).
- Pass **Settings** into `Factory.create`—**no** `create_from_env()` hiding dependencies (optional separate `load_*_from_env()` helpers at the composition root only).

## 3. Fluent configuration APIs

- Methods that configure a client return **`self`** for chaining (`add_header`, `bearer_token`, …).

## 4. Errors, composition, mocks

- Small **exception hierarchies** (base + specific).
- **Composition** over inheritance when there is no true subtype relationship.
- **Mock** implementations beside real ones; record calls where useful for assertions.

## 5. HTTP

- **`HTTPClientFactory`** for synchronous outbound HTTP; raw **`requests`** only where documented (streaming, websockets, etc.).

## 6. Dispatch

- Prefer **`match` / `case`** for routing on enums or discrete string states (not long `if` / `elif` chains).

## 7. Utilities

- **Validators:** use at boundaries; do not wrap/re-raise without adding information.
- **Decorators:** `LogExecutionTime`, `Retry`, `CatchAndLog` from `axiompy.decorators` where appropriate.
- **Logging:** `LoggerFactory.create_logger(__name__)`.

## 8. Secrets

- **`SecretsClientFactory.create(type, settings)`** only; inject clients—no scattered `os.environ` reads inside library modules.

## 9. Rule of three

- Do not invent ABCs/Protocols until **multiple** real implementations justify the seam.

## 10. Layered HTTP / servers

- Routes or thin entrypoints: **parse/validate → delegate**; **no** business rules or persistence commits inlined in handlers (see servers / examples templates in-repo).

## Further reading (external)

- [Hexagonal architecture (ports & adapters)](https://devcookies.medium.com/a-detailed-guide-to-hexagonal-architecture-with-examples-042523acb1db)
- [A Little Architecture (DIP, deferral)](https://blog.cleancoder.com/uncle-bob/2016/01/04/ALittleArchitecture.html)
