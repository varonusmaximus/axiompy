# SQL & database adapters (storage domain)

## Factory pattern

- One `DatabaseFactory` (or equivalent) with `create(type, settings)` — no `create_for_postgres()` proliferation.
- Backend selection via **enum** + `match` / `case`.

## Migrations & schema

- One logical change per migration when adding migration support in examples.
- Document rollback or provide down migrations when feasible.

## Testing

- Use `create_mock()` in unit tests; integration tests opt in to real drivers via markers/extras.

## Errors

- Map driver exceptions to small hierarchy (`DatabaseError`, connection vs query failures).
