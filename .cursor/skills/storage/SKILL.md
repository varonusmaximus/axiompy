---
name: storage
description: Durable data stores — SQL and DynamoDB adapters, database factories. Use when editing axiompy.io.database or storage-related examples.
---

# Storage domain (axiompy)

Shared **code-style** and **design-patterns** load separately. This skill is **database/persistence-only** guidance.

## Scope

`axiompy/io/database.py` and database-focused examples/tests.

## APIs

- `DatabaseFactory` — enum-based backend dispatch.
- Public methods use intent names (`execute_sql`, `query`) — not engine-specific names.

## Sidecars (auto-included)

`sql.md` — SQL safety, migrations, adapter testing.

## Pointers

- `axiompy/io/README.md` — Database Abstraction Layer.
- Install: `pip install "axiompy[databases]"` or `"axiompy[io]"`.
