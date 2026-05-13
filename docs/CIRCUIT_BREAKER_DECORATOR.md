# AxiomPy `CircuitBreaker` decorator — design

This document specifies the AxiomPy circuit-breaker decorator: public API, runtime semantics, how it composes with `@Retry`, async limitations, and the test matrix for implementation. It aligns with existing decorator style (`LoggerFactory`, `@Retry`, `@CatchAndLog` in `axiompy.decorators`).

## Scope

**In scope**

- Specification for a library decorator factory, dedicated open-circuit exception type, optional `pybreaker` dependency, exports, tests, and packaging (see implementation checklist in the repo).

**Out of scope (v1)**

- Changes to downstream consumers (e.g. other repos) unless they opt in.
- Distributed / Redis-backed breaker — noted as a possible future extension.
- FastAPI route-level usage — prefer adapters, HTTP clients, and services (see design patterns §13 on explicit routing vs handler decorators).

## Recommended public API

### Factory

`CircuitBreaker(logger, *, fail_max, reset_timeout_seconds, name=None, …)` returns a decorator (callable that wraps a function), matching the parameterized-factory pattern used by `Retry` and `CatchAndLog`.

Suggested keyword parameters (names may be adjusted slightly to match `pybreaker` where wired 1:1):

| Parameter | Role |
|-----------|------|
| `logger` | AxiomPy / stdlib `Logger`; drives state-transition and optional debug logs. |
| `fail_max` | Consecutive counted failures before **open**. |
| `reset_timeout_seconds` | Seconds before transition from **open** to **half-open** (probe). |
| `name` | Logical breaker name (logging, `CircuitOpenError` context); default derived from wrapped function if omitted. |
| `exceptions` | Tuple of exception types that count as failures when raised (same idea as `Retry.exceptions`). |
| `failure_predicate` | Optional `(exc: BaseException) -> bool`; when set, only failures for which this returns `True` increment the breaker (refines `exceptions`). |
| `reraise` | If `True` and circuit is **open**, raise `CircuitOpenError` instead of calling the function. |
| `default_return` | When `reraise=False` and circuit is **open**, return this value (static fallback). |
| `fallback` | Optional `Callable[..., Any]` invoked when **open** and `reraise=False`; signature should accept same `*args, **kwargs` as the wrapped function (or document a narrower contract). |
| `log_closed_success` | If `True`, log successful calls on the **closed** path at DEBUG; default `False` to avoid noise. |

### Exceptions

- **`CircuitOpenError`**: Subclass of `Exception`. Carries at least `name` (str) and a **reset hint** (e.g. seconds until half-open / retry-after semantics) so callers and logs stay actionable. Implementation may wrap or map from `pybreaker.CircuitBreakerError` after normalizing fields.

### Dependency: `pybreaker`

- Use **[pybreaker](https://pypi.org/project/pybreaker/)** as the state machine engine.
- Register **listeners** (or equivalent hooks) so **open**, **half-open** probe, and **closed** recovery transitions emit structured messages via the supplied logger.
- **Optional extra** in `pyproject.toml` (e.g. `circuit-breaker` or under a broader extra) so base installs stay lean.
- **Import policy (choose one and keep code + doc aligned)**:
  - **Fail fast**: Using `CircuitBreaker` without the extra raises a clear `ImportError` or `RuntimeError` with install instructions; or
  - **Lazy import**: Decorator factory imports `pybreaker` only when the decorator is first constructed/applied, with the same clear error if missing.

## Semantics

### States

1. **Closed** — Calls pass through to the wrapped function. Failures that match the failure policy increment the failure count; successes reset the failure count (per `pybreaker` behavior — document the exact rule once implemented).
2. **Open** — Calls short-circuit: no call to the wrapped function. Behavior depends on `reraise` / `default_return` / `fallback`.
3. **Half-open** — Probe call allowed; success closes the circuit; failure re-opens (document alignment with `pybreaker`).

### Failure policy

- Only exceptions that are instances of types in `exceptions` (and optionally pass `failure_predicate`) count as failures.
- Exceptions outside that set propagate without affecting the breaker (same mental model as excluding “business errors” from retries).

### Open-circuit behavior

| `reraise` | Behavior when open |
|-----------|----------------------|
| `True` | Raise `CircuitOpenError` with `name` and reset hint. |
| `False` | Return `default_return`, or invoke `fallback(*args, **kwargs)` if provided; document precedence if both are set (recommend: `fallback` wins over `default_return`, or disallow both and validate in `__init__`). |

### Logging

- **Warning** (or **ERROR** per product preference) when entering **open** (trip).
- **Info** when entering **half-open** (probe) and when **closing** after a successful probe (recovery).
- Avoid logging every successful **closed** call unless `log_closed_success=True` (DEBUG-level detail).

## Composition with `@Retry`

Order matters. Recommended default for HTTP and similar flaky I/O:

- **`@Retry` outside `@CircuitBreaker`** — Applied bottom-up in Python, that means: `@Retry` is the **outer** decorator, `@CircuitBreaker` is **inner** (closer to the function). Each retry attempt hits the breaker; if the circuit is open, the breaker short-circuits before the inner call. This is the usual pattern for “retry transient errors while respecting upstream health.”

```mermaid
flowchart LR
  call[Caller]
  retry[Retry]
  cb[CircuitBreaker]
  fn[Underlying fn]
  call --> retry --> cb --> fn
```

- **`@CircuitBreaker` outside `@Retry`** — One logical outer call: the breaker sees a single outcome while `Retry` may loop internally only if composed the other way. Use when intentional (e.g. breaker wraps a batch where retries are handled inside the function).

Document the stacking idiom explicitly in examples:

```python
@Retry(logger, max_attempts=3, delay=1.0, exceptions=(ConnectionError,))
@CircuitBreaker(logger, fail_max=5, reset_timeout_seconds=30, name="payments-api")
def fetch_payments():
    ...
```

## Async stance (v1)

- **v1 is sync-only.** The decorator applies to synchronous callables only.
- **Async** (`async def`) support is explicitly **deferred**: either a separate `AsyncCircuitBreaker` factory or an extension section in this doc once a design is chosen (tasks, event loop, and `pybreaker` thread-safety must be reviewed).

## Future extensions (non-goals for v1)

- **Distributed breaker** (e.g. Redis-backed shared state) for multi-process / multi-host coordination.
- **Async** variant as above.

## Test matrix

Implementation should be covered by `pytest` with at least the following cases (names illustrative):

| # | Case | Expectation |
|---|------|-------------|
| 1 | Trip after `fail_max` | After `fail_max` matching failures, circuit is **open**; next call does not invoke wrapped function (or raises per `reraise`). |
| 2 | Reset after timeout | After **open**, wait (or mock time) past `reset_timeout_seconds`, probe in **half-open** runs wrapped function once. |
| 3 | Half-open success | Successful probe transitions to **closed**; subsequent calls run normally. |
| 4 | Half-open failure | Failed probe returns to **open** (or equivalent per `pybreaker`). |
| 5 | Excluded / non-counted exceptions | Exception types not in `exceptions` do not increment failures; circuit stays **closed** unless other failures tripped it. |
| 6 | `failure_predicate` | When provided, exceptions matching `exceptions` but failing the predicate do not count (or inverse — document precisely in API). |
| 7 | `reraise=True` when open | Raises `CircuitOpenError` with expected `name` / reset metadata. |
| 8 | `reraise=False`, `default_return` | Returns default without calling wrapped function when open. |
| 9 | `fallback` when open | Invokes fallback with appropriate args when open. |
|10 | Composition with `Retry` | With `Retry` outer and `CircuitBreaker` inner, retries occur only when breaker allows through; open circuit prevents inner calls. |
|11 | Logging | State transitions produce expected log levels / messages (mock logger). |
|12 | Missing optional dependency | If extra not installed, clear error when decorator is used (per chosen import policy). |
|13 | `@wraps` / metadata | Wrapped function preserves `__name__`, `__doc__`, etc. |

## Implementation checklist (reference)

1. Mirror `Retry` / `CatchAndLog` signature style, typing, and test layout under the AxiomPy repo.
2. `pyproject.toml` — optional dependency group for `pybreaker` with a pinned minimum version.
3. Implementation module — build `pybreaker.CircuitBreaker` per decorated function or accept a shared instance (document: one breaker per downstream dependency is typical); `@functools.wraps`; open-state behavior per API above.
4. `CircuitOpenError` — map from `pybreaker`’s open error if needed.
5. `axiompy.decorators` exports — `CircuitBreaker`, `CircuitOpenError`.
6. Tests — rows in the matrix above.
7. This doc — keep in sync with shipped API.
8. Main decorators README — short “Circuit breaker” section: extra name, install line, minimal example.

---

*Source plan: AxiomPy `CircuitBreaker` decorator — doc + implementation (factory, `pybreaker`, composition with `Retry`, sync-only v1).*
