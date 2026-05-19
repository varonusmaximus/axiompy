# AxiomPy testing standards (normative summary)

Companion to **`testing` / SKILL.md**.

## Default bias: **unit-heavy**

- Prefer **fast unit tests** that exercise **pure logic** and **factories/settings** with fakes or `create_mock()`.
- Add **integration tests at port boundaries** (real HTTP shape with moto, secrets backends, filesystem temp dirs) where the **risk** is wiring, not arithmetic—**not** integration-first for everything.

## Layout

- `tests/test_<module>.py`
- **pytest** + fixtures; group tests in classes when it helps readability
- **80%+** coverage on touched modules (`pyproject.toml` `fail_under`)

## Patterns

- **Settings:** valid succeeds; invalid raises; defaults apply
- **Factories:** `create()` per enum; **`create_mock()`** usable; unknown types → `ValueError`
- **Services / I/O boundaries:** happy path, boundaries, errors; **`unittest.mock.patch`** for externals

### Mock client pattern

Use **`Factory.create_mock()`** and assert on recorded calls when the API supports it.

## Integration examples (boundary)

For **moto**-style AWS integration patterns, see **`tests/test_secrets_integration.py`** and **`axiompy/secrets/README.md`** — treat as **examples of port-level tests**, not the default style for every module.
