# Local `.env` secrets backend

The `LOCAL` backend reads secrets from a `.env` file using the same `SecretsClient` interface as
AWS Secrets Manager and other remote vaults, so applications can use one code path in every
environment.

## Motivation

Without `LOCAL`, teams often split logic:

- **Production**: factory + remote backend (for example AWS Secrets Manager)
- **Local dev**: `os.environ.get("KEY")` or ad-hoc `.env` loading

That encourages key-name drift (for example `api_token` vs `API_TOKEN`). `LOCAL` keeps the factory
and `get_secret()` calls identical while swapping the backing store to a file.

## Usage

```python
from axiompy.secrets import LocalSettings, SecretsClientFactory, SecretsClientType

client = SecretsClientFactory.create(
    SecretsClientType.LOCAL,
    LocalSettings(env_file=".env", case_insensitive=True),
).unwrap()

value = client.get_secret("authz_api_token").unwrap()
```

See `axiompy/secrets/README.md` and `tests/test_local_secrets.py` for more detail.
