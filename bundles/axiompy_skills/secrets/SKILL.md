---
name: secrets
description: Secrets, credentials, and KMS backends — factory-based, security-reviewed. Use when editing axiompy.secrets.
---

# Secrets domain (axiompy)

Shared **code-style**, **design-patterns**, and **code-review** load separately. This skill is **secrets/KMS-only** guidance.

## Scope

`axiompy/secrets/**`.

## APIs

- `SecretsClientFactory.create(type, settings)` — sole construction path.
- `SecretsClientType`, `LocalSettings`, and backend-specific Settings types.

## Secrets-only rules

- Never log secret values, tokens, or decrypted payloads.
- Use `axiompy.result` for client operations — document `unwrap_or` defaults in examples.

## Sidecars (auto-included)

`backends.md` — local, AWS KMS, Secrets Manager, moto testing.

## Pointers

- `axiompy/secrets/README.md`
