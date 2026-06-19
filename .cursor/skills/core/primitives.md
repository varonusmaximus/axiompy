# Core primitives checklist

## Validators & decorators

- Validate inputs in `__post_init__` on Settings dataclasses and at public function entry.
- Use `LogExecutionTime`, `Retry`, `CatchAndLog` from `axiompy.decorators` where they clarify cross-cutting behavior.

## Result types

- Railway-oriented flows in library code use `axiompy.result` — avoid bare `try/except` that swallows typed errors.
- Pattern-match on `Result` variants; document `unwrap_or` defaults when used.

## Config & errors

- Small exception hierarchies (base + specific types) per area.
- Settings objects are explicit — no hidden `os.environ` reads in core modules.
