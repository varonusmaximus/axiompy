# LOCAL_SECRETS — Implementation Plan

> Add a `LOCAL` backend to `axiompy.secrets` that reads secrets from a `.env` file using the same
> `SecretsClient` interface. This eliminates the split between Cerberus-in-production and
> env-vars-in-dev — local development uses the same key names, same code path, different backend.

## Motivation

Currently, applications that use `axiompy.secrets` have two code paths:

- **Production**: `SecretsClientFactory.create(SecretsClientType.CERBERUS, settings)` reads from Cerberus SDB
- **Local dev**: `os.environ.get("AD_BIND_PASSWORD")` reads from env vars or `.env` files

This means secret key names can drift between environments (e.g. `ad_bind_password` in Cerberus
vs `AD_BIND_PASSWORD` in env). The `LOCAL` backend unifies them: same factory, same key names,
same `SecretsClient` interface — backed by a `.env` file instead of a vault.

```python
# Production
client = SecretsClientFactory.create(SecretsClientType.CERBERUS, CerberusSettings(
    vault_path="app/data-product-registry/secrets",
    cerberus_url="https://cerberus.example.com",
    cerberus_region="us-west-2",
)).unwrap()

# Local — same interface, same key names, reads from .env file
client = SecretsClientFactory.create(SecretsClientType.LOCAL, LocalSettings(
    env_file=".env",
    vault_path="app/data-product-registry/secrets",  # ignored but kept for parity
)).unwrap()

# Both return the same thing:
token = client.get_secret("authz_api_token").unwrap()
all_secrets = client.get_secrets("app/data-product-registry/secrets").unwrap()
```

## Files to Create/Modify

### 1. `axiompy/secrets/types.py` — Add `LOCAL` to enum and `LocalSettings`

```python
class SecretsClientType(Enum):
    CERBERUS = "cerberus"
    AWS_SECRETS_MANAGER = "aws_secrets_manager"
    AWS_KMS = "aws_kms"
    LOCAL = "local"                           # <-- new

@dataclass
class LocalSettings(SecretsSettings):
    """Local .env file backend for development."""
    env_file: str = ".env"
    vault_path: str = ""                      # kept for interface parity, not used
    case_insensitive: bool = True             # map KEY=val to both "KEY" and "key"
```

### 2. `axiompy/secrets/implementations/local.py` — New file

Implement `LocalSecretClient(CredentialProvider)` that:

- On `__init__`, reads the `.env` file into a `dict[str, str]`
- Parsing: strips comments (`#`), skips blank lines, handles `KEY=value` and `KEY="value"`
- When `case_insensitive=True`, stores both `KEY` and `key` variants so lookups match
  Cerberus key names (lowercase) and env var names (uppercase)
- Implements all `SecretsClient` methods:

| Method | Behavior |
|--------|----------|
| `get_secret(key)` | Lookup `key` in the parsed dict → `Ok(value)` or `Err("not found")` |
| `get_secrets(path)` | Return entire dict (path is ignored for local) → `Ok(dict)` |
| `get_secret_by_key(path, key)` | Same as `get_secret(key)` |
| `put_secret(...)` | `Err("Local backend is read-only")` |
| `put_secrets(...)` | `Err("Local backend is read-only")` |
| `delete_secret(...)` | `Err("Local backend is read-only")` |
| `delete_secrets(...)` | `Err("Local backend is read-only")` |
| `secret_exists(key)` | `Ok(key in dict)` |
| `list_secrets(path)` | `Ok(list(dict.keys()))` |

```python
class LocalSecretClient(CredentialProvider):
    """Read secrets from a local .env file.

    Provides the same SecretsClient interface as Cerberus, AWS Secrets Manager, etc.
    Used for local development so the same key names and code paths work in all
    environments.
    """

    def __init__(self, settings: LocalSettings):
        super().__init__()
        self.settings = settings
        self._secrets: dict[str, str] = {}
        self._load(settings.env_file, settings.case_insensitive)

    def _load(self, env_file: str, case_insensitive: bool) -> None:
        """Parse .env file into key-value dict."""
        try:
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    self._secrets[key] = value
                    if case_insensitive:
                        self._secrets[key.lower()] = value
                        self._secrets[key.upper()] = value
        except FileNotFoundError:
            pass  # empty secrets — get_secret will return Err

    def get_secret(self, secret_path: str) -> Result[str, str]:
        value = self._secrets.get(secret_path)
        if value is None:
            return Err(f"Secret '{secret_path}' not found in {self.settings.env_file}")
        return Ok(value)

    def get_secrets(self, secret_path: str) -> Result[dict[str, str], str]:
        return Ok(dict(self._secrets))

    def get_secret_by_key(self, secret_path: str, key: str) -> Result[str, str]:
        return self.get_secret(key)

    # Write operations are not supported for local files
    def put_secret(self, *args, **kwargs):
        return Err("Local backend is read-only. Edit the .env file directly.")

    def put_secrets(self, *args, **kwargs):
        return Err("Local backend is read-only. Edit the .env file directly.")

    def delete_secret(self, *args, **kwargs):
        return Err("Local backend is read-only. Edit the .env file directly.")

    def delete_secrets(self, *args, **kwargs):
        return Err("Local backend is read-only. Edit the .env file directly.")

    def secret_exists(self, secret_path: str) -> Result[bool, str]:
        return Ok(secret_path in self._secrets)

    def list_secrets(self, secret_path: str) -> Result[list[str], str]:
        return Ok(list(self._secrets.keys()))
```

### 3. `axiompy/secrets/factory.py` — Register LOCAL implementation

Add to `_register_implementations()`:

```python
try:
    from .implementations.local import LocalSecretClient
    SecretsClientFactory._IMPLEMENTATIONS[SecretsClientType.LOCAL] = LocalSecretClient
    logger.debug("Registered LocalSecretClient")
except ImportError:
    logger.debug("LocalSecretClient not available")
```

### 4. `axiompy/secrets/__init__.py` — Export new types

Add `LocalSettings` to imports and `__all__`:

```python
from .types import (
    ...,
    LocalSettings,
)

__all__ = [
    ...,
    "LocalSettings",
]
```

### 5. Tests — `tests/test_local_secrets.py`

```python
def test_local_client_reads_env_file(tmp_path):
    env = tmp_path / ".env"
    env.write_text("AD_BIND_PASSWORD=secret123\nAUTHZ_API_TOKEN=tok-456\n")
    settings = LocalSettings(env_file=str(env))
    client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()

    assert client.get_secret("ad_bind_password").unwrap() == "secret123"  # case insensitive
    assert client.get_secret("AUTHZ_API_TOKEN").unwrap() == "tok-456"

def test_local_client_get_secrets_returns_all(tmp_path):
    env = tmp_path / ".env"
    env.write_text("KEY1=val1\nKEY2=val2\n")
    settings = LocalSettings(env_file=str(env))
    client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
    secrets = client.get_secrets("any/path").unwrap()
    assert "key1" in secrets
    assert secrets["key1"] == "val1"

def test_local_client_missing_file_returns_empty():
    settings = LocalSettings(env_file="/nonexistent/.env")
    client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
    result = client.get_secret("anything")
    assert result.is_err()

def test_local_client_skips_comments(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comment\nKEY=value\n\n# another\n")
    settings = LocalSettings(env_file=str(env))
    client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
    assert client.get_secret("key").unwrap() == "value"

def test_local_client_write_returns_error(tmp_path):
    env = tmp_path / ".env"
    env.write_text("K=V\n")
    settings = LocalSettings(env_file=str(env))
    client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
    assert client.put_secret("k", "v").is_err()
```

## .env File Convention

The `.env` file uses the **same key names as Cerberus** (lowercase) so the application code
works identically in both environments:

```bash
# Secrets (same keys as Cerberus SDB at app/data-product-registry/secrets)
authz_api_token=63be72af-fc2e-4a32-87b4-b28d2058804f
ad_bind_password=my-ldap-password
snowflake_account=acme.us-east-1
snowflake_user=svc-registry
snowflake_password=secret
databricks_host=https://adb-1234.azuredatabricks.net
databricks_token=dapi-xyz
databricks_http_path=/sql/1.0/warehouses/abc

# Config (non-secret, also readable via get_secret but not sensitive)
AUTHZ_MODE=inprocess
DATABASE_PATH=registry.db
QUERY_EXECUTOR_TYPE=duckdb
```

The `case_insensitive=True` default means `get_secret("authz_api_token")` and
`get_secret("AUTHZ_API_TOKEN")` both resolve, so existing env var conventions and Cerberus
lowercase conventions both work.

## Consumer Usage (Data Product Registry)

After this is implemented, `settings_builder.py` simplifies to:

```python
from axiompy.secrets import SecretsClientFactory, SecretsClientType, CerberusSettings, LocalSettings

CERBERUS_URL = "https://cerberus.example.com"
CERBERUS_REGION = "us-west-2"
CERBERUS_VAULT_PATH = "app/data-product-registry/secrets"

def _create_secrets_client():
    """Create secrets client — Cerberus in production, .env locally."""
    if os.environ.get("CERBERUS_ENABLED", "false").lower() == "true":
        settings = CerberusSettings(
            vault_path=CERBERUS_VAULT_PATH,
            cerberus_url=CERBERUS_URL,
            cerberus_region=CERBERUS_REGION,
        )
        return SecretsClientFactory.create(SecretsClientType.CERBERUS, settings).unwrap()

    return SecretsClientFactory.create(
        SecretsClientType.LOCAL,
        LocalSettings(env_file=".env"),
    ).unwrap()
```

Same factory. Same `get_secret()` calls. Same key names. Different backend.
