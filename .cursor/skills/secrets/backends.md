# Secrets backends (secrets domain)

## Factory dispatch

```python
from axiompy.secrets import SecretsClientFactory, SecretsClientType, LocalSettings

settings = LocalSettings(env_file=".env")
client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
```

## AWS

- KMS and Secrets Manager adapters live under `implementations/` — keep IAM assumptions documented in module docstrings.
- Use `moto` in tests when mocking AWS; never commit real ARNs or keys.

## Local / dev

- `.env` backend for development only — document production alternatives in README.

## Caching

- Credential cache TTL and invalidation must be explicit; test expiration paths.
