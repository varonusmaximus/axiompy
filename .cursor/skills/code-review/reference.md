# Code review — compact examples

Use with **`code-review` SKILL**. For the full rule set, see **`AGENTS.md`**.

## Rule of three

Wait for multiple real use cases before introducing an ABC; prefer **`Protocol`** once the abstraction is justified.

## Single responsibility

Split services that mix email, reporting, and core domain logic.

## Layered HTTP

Routes validate and delegate; services own rules; repositories own persistence. No `db.session` in route functions.

## Dependency inversion

Inject `Database` / `Emailer` ports; construct with factories at the composition root.

## Smells (examples)

- Replace magic `429` / `60` with named constants for backoff.
- Replace duplicated validation blocks with a shared helper.
- Replace bare `except:` with specific exceptions and logging.

## Security

Never commit credentials; use env vars or `SecretsClientFactory` patterns from **`axiompy.secrets`**.
