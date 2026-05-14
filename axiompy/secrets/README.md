# Secrets Management Module

The `secrets` module provides a unified, extensible interface for managing secrets, credentials, and authentication tokens across multiple backends using the **factory pattern** and **Railway-Oriented Programming** with Result types.

## Features

- 🏭 **Factory Pattern**: Easy backend switching without code changes
- 🚂 **Railway-Oriented Programming**: Result types for elegant error handling
- 🔐 **Multiple Backends**:
  - AWS Secrets Manager
  - AWS KMS (encryption/decryption)
  - Local `.env` backend for development
- 🎯 **Specialized Credential Provider**: High-level API for auth tokens and credentials
- 💾 **Caching**: Built-in credential caching with expiration checking
- 📝 **Well-Documented**: Comprehensive docstrings and examples

## Quick Start

### Basic Usage

```python
from axiompy.secrets import LocalSettings, SecretsClientFactory, SecretsClientType

settings = LocalSettings(env_file=".env")

result = SecretsClientFactory.create(SecretsClientType.LOCAL, settings)
client = result.unwrap()  # Or handle error

secret_result = client.get_secret("database_password")
password = secret_result.unwrap()
```

### Error Handling with Result Types

```python
from axiompy.secrets import LocalSettings, SecretsClientFactory, SecretsClientType

settings = LocalSettings(env_file=".env")
result = SecretsClientFactory.create(SecretsClientType.LOCAL, settings)

# Handle error gracefully
password = (
    result
    .then(lambda client: client.get_secret("db_password"))
    .map(lambda pwd: pwd.strip())
    .unwrap_or("default_password")
)

# Or pattern match
if result.is_ok():
    client = result.unwrap()
    # use client
else:
    error = result.get_error()
    print(f"Failed: {error}")
```

## Backend Configuration

### AWS Secrets Manager

General-purpose secrets storage on AWS.

```python
from axiompy.secrets import SecretsClientFactory, SecretsClientType, AWSSecretsManagerSettings

settings = AWSSecretsManagerSettings(
    region="us-west-2",
    access_key_id="AKIAIOSFODNN7EXAMPLE",  # Optional, uses default credentials
    secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
)

result = SecretsClientFactory.create(SecretsClientType.AWS_SECRETS_MANAGER, settings)
```

**Installation**: `pip install boto3`

### AWS KMS

For encryption/decryption operations.

```python
from axiompy.secrets import SecretsClientFactory, SecretsClientType, AWSKMSSettings

settings = AWSKMSSettings(
    key_id="arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab",
    region="us-west-2"
)

result = SecretsClientFactory.create(SecretsClientType.AWS_KMS, settings)
client = result.unwrap()

# Encrypt plaintext
encrypted = client.encrypt("my-secret-value").unwrap()

# Decrypt ciphertext
decrypted = client.decrypt(encrypted).unwrap()
```

**Installation**: `pip install boto3`

### Local `.env` Backend

Use this backend for local development while keeping the same `SecretsClient`
interface and key names as production.

```python
from axiompy.secrets import LocalSettings, SecretsClientFactory, SecretsClientType

settings = LocalSettings(
    env_file=".env",
    vault_path="app/data-product-registry/secrets",  # kept for parity, ignored
    case_insensitive=True,
)

client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()

token = client.get_secret("authz_api_token").unwrap()
all_values = client.get_secrets("ignored/path").unwrap()
```

Notes:
- `get_secrets()` and `list_secrets()` return values from the loaded `.env`.
- `put_*` and `delete_*` operations are intentionally read-only and return `Err`.
- With `case_insensitive=True`, `KEY` and `key` both resolve.

## SecretsClient Interface

All clients implement the `SecretClient` interface:

### Read Operations

```python
# Get a single secret value
result: Result[str, str] = client.get_secret("password")

# Get all secrets as a dictionary
result: Result[Dict[str, str], str] = client.get_secrets("path/")

# Get a specific key from a secret
result: Result[str, str] = client.get_secret_by_key("secrets", "password")

# Check if secret exists
result: Result[bool, str] = client.secret_exists("path")

# List all secrets at a path
result: Result[List[str], str] = client.list_secrets("path/")
```

### Write Operations

```python
# Store a single secret
result: Result[bool, str] = client.put_secret("path", "secret_value")

# Store multiple secrets
secrets_dict = {"username": "admin", "password": "secret123"}
result: Result[bool, str] = client.put_secrets("path", secrets_dict)

# Delete a secret
result: Result[bool, str] = client.delete_secret("path")

# Delete multiple secrets
result: Result[bool, str] = client.delete_secrets("path/")
```

## CredentialProvider Interface

The `CredentialProvider` extends `SecretClient` with high-level credential management:

```python
from axiompy.secrets import AuthToken, Credential

# Get authentication token
token_result: Result[AuthToken, str] = client.get_auth_token("service/api-token")
token = token_result.unwrap()
print(f"Token: {token}")  # Prints "Bearer <token_value>"

# Get database credentials
cred_result: Result[Credential, str] = client.get_database_credentials("db/mysql")
cred = cred_result.unwrap()
print(f"{cred.username}:{cred.password}")

# Get API key
key_result: Result[str, str] = client.get_api_key("api/stripe-key")
key = key_result.unwrap()
```

### Credential Caching

```python
# Credentials are automatically cached after first retrieval
cred = client.get_database_credentials("db/mysql").unwrap()

# Clear credential cache to force refresh
client.refresh_credential_cache()

# Clear all caches (tokens + credentials)
client.refresh_all_caches()
```

## Usage Patterns

### Pattern 1: Simple Secret Retrieval

```python
from axiompy.secrets import LocalSettings, SecretsClientFactory, SecretsClientType


def get_database_password() -> str:
    settings = LocalSettings(env_file=".env")
    client = SecretsClientFactory.create(
        SecretsClientType.LOCAL, settings
    ).unwrap()

    return client.get_secret("db_password").unwrap()
```

### Pattern 2: Error Recovery

```python
result = client.get_secret("missing_secret").or_else(
    lambda error: Ok("default_value")
)
value = result.unwrap()
```

### Pattern 3: Transform and Chain

```python
token_result = (
    client.get_auth_token("api/token")
    .map(lambda token: str(token))  # Convert to string
    .map(lambda token_str: token_str.strip())  # Clean whitespace
)
```

### Pattern 4: Multi-Secret Retrieval

```python
db_creds = client.get_secrets("database/").unwrap()
for key, value in db_creds.items():
    print(f"Setting {key}...")
```

### Pattern 5: Environment-Specific Configuration

```python
import os
from axiompy.secrets import SecretsClientFactory, SecretsClientType

backend = os.getenv("SECRET_BACKEND", "local").lower()
client_type = SecretsClientType[backend.upper()]

# Backend-specific settings using match/case (Python 3.10+)
match client_type:
    case SecretsClientType.LOCAL:
        from axiompy.secrets import LocalSettings

        settings = LocalSettings(env_file=os.getenv("ENV_FILE", ".env"))
    case SecretsClientType.AWS_SECRETS_MANAGER:
        from axiompy.secrets import AWSSecretsManagerSettings

        settings = AWSSecretsManagerSettings(...)
    case SecretsClientType.AWS_KMS:
        from axiompy.secrets import AWSKMSSettings

        settings = AWSKMSSettings(...)
    case _:
        raise ValueError(f"Unknown backend: {client_type}")

client = SecretsClientFactory.create(client_type, settings).unwrap()
```

## Authentication & Authorization Integration

### Using Secrets for Authentication

```python
# Get auth token for API calls
token_result = client.get_auth_token("databricks/service-token")
token = token_result.unwrap()

# Use in headers
headers = {"Authorization": str(token)}
response = requests.get("https://api.databricks.com/...", headers=headers)
```

### Using Credentials for Basic Auth

```python
from axiompy.secrets import Credential

cred_result = client.get_credential("api/basic-auth")
cred = cred_result.unwrap()

# Encode for Basic Auth
import base64
auth_string = base64.b64encode(
    f"{cred.username}:{cred.password}".encode()
).decode()

headers = {"Authorization": f"Basic {auth_string}"}
response = requests.get("https://api.example.com/...", headers=headers)
```

### Service Principal Credentials

```python
cred_result = client.get_credential("azure/service-principal")
cred = cred_result.unwrap()

# Use for Azure SDK authentication
from azure.identity import ClientSecretCredential

credential = ClientSecretCredential(
    tenant_id=cred.metadata.get("tenant_id"),
    client_id=cred.username,
    client_secret=cred.password
)
```

## Type Safety

### Authentication Types

```python
from axiompy.secrets import AuthToken, Credential
from datetime import datetime, timedelta

# Create auth token
token = AuthToken(
    token="eyJhbGc...",
    token_type="Bearer",
    expires_at=datetime.utcnow() + timedelta(hours=1),
    scope="read write",
    metadata={"user_id": "12345"}
)

# Check expiration
if token.is_expired():
    print("Token expired, refresh needed")

# Create credential
cred = Credential(
    username="admin",
    password="secret123",
    credential_type="database",
    metadata={"host": "localhost", "port": 3306}
)

if cred.is_expired():
    print("Credential expired")
```

## Testing

### Mock Client for Tests

```python
from axiompy.secrets import SecretClient
from axiompy.result import Ok, Err, Result
from typing import Dict, List, Optional, Any

class MockSecretClient(SecretClient):
    def __init__(self, secrets: Dict[str, str]):
        self.secrets = secrets

    def get_secret(self, secret_path: str) -> Result[str, str]:
        if secret_path in self.secrets:
            return Ok(self.secrets[secret_path])
        return Err(f"Secret not found: {secret_path}")

    # ... implement other methods ...

# Use in tests
mock_client = MockSecretClient({
    "db_password": "test123",
    "api_key": "key123"
})

result = mock_client.get_secret("db_password")
assert result.is_ok()
assert result.unwrap() == "test123"
```

## Backend Comparison

| Feature | AWS Secrets Manager | AWS KMS | Local `.env` |
|---------|----------------------|---------|---------------|
| **Read Secrets** | ✅ | ❌ | ✅ |
| **Write Secrets** | ✅ | ❌ | ❌ |
| **Delete Secrets** | ✅ | ❌ | ❌ |
| **Encryption** | ✅ | ✅ | ❌ |
| **Rotation** | ✅ | ❌ | ❌ |
| **Audit Logging** | ✅ | ✅ | ❌ |
| **Cost** | Low-Med | Low | Very Low |

## Error Handling

All operations return `Result[T, E]` types for safe error handling:

```python
from axiompy.result import Ok, Err

# Always returns Result
result = client.get_secret("password")

# Safe unwrapping
if result.is_ok():
    password = result.unwrap()
else:
    error = result.get_error()
    print(f"Error: {error}")

# With default
password = result.unwrap_or("default_password")

# With error transformation
password = result.map_error(
    lambda err: f"Failed to get password: {err}"
).unwrap_or("default")

# Chain operations
result = (
    client.get_secret("token")
    .then(lambda token: validate_token(token))
    .map(lambda token: token.strip())
)
```

## Best Practices

1. **Use Factory Pattern**: Always use `SecretsClientFactory` for client creation
2. **Handle Results**: Don't unwrap without error handling in production code
3. **Cache Credentials**: Use built-in caching for frequently accessed credentials
4. **Refresh Strategically**: Call `refresh_*_cache()` before sensitive operations
5. **Log Appropriately**: Use the built-in logging (sensitive data is not logged)
6. **Validate Secrets**: Check expiration times for time-sensitive credentials
7. **Environment-Specific**: Use environment variables to switch backends
8. **Test with Mocks**: Use mock clients in unit tests

## Contributing

To add a new backend:

1. Create `implementations/my_backend.py`
2. Implement the `SecretClient` or `CredentialProvider` interface
3. Register in `factory.py` with `_register_implementations()`
4. Add documentation and examples to this README

## See Also

- `axiompy/result.py` - Result type documentation
- `axiompy/io/database.py` - Similar factory pattern for databases
- Examples in `/examples/` directory

---

## Integration Guide

### Migrating from Direct Backend Usage

This guide explains how to integrate the `axiompy.secrets` module into projects that currently use direct backend clients.

#### Before (Direct boto3)

```python
import boto3

client = boto3.client("secretsmanager", region_name="us-west-2")
response = client.get_secret_value(SecretId="prod/db/password")
password = response["SecretString"]  # Can throw botocore exceptions
```

#### After (Using axiompy.secrets)

```python
from axiompy.secrets import AWSSecretsManagerSettings, SecretsClientFactory, SecretsClientType

settings = AWSSecretsManagerSettings(
    region="us-west-2",
)

client = SecretsClientFactory.create(
    SecretsClientType.AWS_SECRETS_MANAGER, settings
).unwrap()
```

### Server Integration with ServerFactory

Use AxiomPy's ServerFactory pattern to integrate secrets management with your server:

```python
from axiompy.servers import ServerFactory, ServerType
from axiompy.secrets import CredentialProvider, SecretsClientFactory, SecretsClientType

class MyAPIServer:
    def __init__(self):
        self.secrets_client = None

    def startup(self):
        """Initialize secrets client on server startup."""
        settings = LocalSettings(env_file=".env")
        self.secrets_client = SecretsClientFactory.create(
            SecretsClientType.LOCAL, settings
        ).unwrap()

    def get_secret_client(self) -> CredentialProvider:
        """Access secrets client during request handling."""
        return self.secrets_client

# Create and run server
api = MyAPIServer()
factory = ServerFactory()
server = factory.create(
    ServerType.FASTAPI,
    port=8000,
    startup_hook=api.startup
)
server.run()
```

### Environment-Specific Configuration

Create a centralized configuration that adapts to the backend:

```python
import os
from axiompy.secrets import SecretsClientFactory, SecretsClientType
from axiompy.result import Result

class SecretsConfig:
    @staticmethod
    def get_client() -> Result:
        """Get configured secret client based on environment."""

        backend = os.getenv("SECRET_BACKEND", "LOCAL").upper()
        client_type = SecretsClientType[backend]

        # Backend-specific settings using match/case (Python 3.10+)
        match client_type:
            case SecretsClientType.LOCAL:
                from axiompy.secrets import LocalSettings

                settings = LocalSettings(env_file=os.getenv("ENV_FILE", ".env"))
            case SecretsClientType.AWS_SECRETS_MANAGER:
                from axiompy.secrets import AWSSecretsManagerSettings

                settings = AWSSecretsManagerSettings(
                    region=os.getenv("AWS_REGION", "us-west-2"),
                    access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                    secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                )
            case SecretsClientType.AWS_KMS:
                from axiompy.secrets import AWSKMSSettings

                settings = AWSKMSSettings(
                    key_id=os.getenv("AWS_KMS_KEY_ID"),
                    region=os.getenv("AWS_REGION", "us-west-2"),
                )
            case _:
                raise ValueError(f"Unknown backend: {client_type}")

        return SecretsClientFactory.create(client_type, settings)

# Use as singleton
_client_instance = None

def get_secret_client():
    global _client_instance
    if _client_instance is None:
        _client_instance = SecretsConfig.get_client().unwrap()
    return _client_instance
```

### Authentication Patterns

#### Service-to-Service Authentication in Routes
```python
from axiompy.servers import ServerFactory, ServerType
from axiompy.secrets import CredentialProvider

class APIRoutes:
    def __init__(self, secrets_client: CredentialProvider):
        self.secrets = secrets_client

    async def call_external_api(self):
        token = (
            self.secrets.get_auth_token("service/token")
            .unwrap_or_else(lambda err: raise_error(err))
        )

        headers = {"Authorization": str(token)}
        response = await client.get("https://api.example.com/", headers=headers)
        return response
```

#### Database Authentication in Services
```python
from axiompy.secrets import CredentialProvider

class DatabaseService:
    def __init__(self, secrets_client: CredentialProvider):
        self.secrets = secrets_client

    def connect_to_database(self):
        cred = self.secrets.get_database_credentials("db/mysql").unwrap()

        db = Database(
            host="localhost",
            user=cred.username,
            password=cred.password
        )
        return db
```

#### Service Principal Authentication
```python
from axiompy.secrets import CredentialProvider

class AzureAuthenticator:
    def __init__(self, secrets_client: CredentialProvider):
        self.secrets = secrets_client

    def authenticate(self):
        cred = self.secrets.get_credential("azure/service-principal").unwrap()

        from azure.identity import ClientSecretCredential

        auth = ClientSecretCredential(
            tenant_id=cred.metadata.get("tenant_id"),
            client_id=cred.username,
            client_secret=cred.password
        )
        return auth
```

### Error Handling Comparison

#### Before (Exception-based)
```python
try:
    cred_mgr = CredentialManager.get_instance()
    token = cred_mgr.get_databricks_token()
except KeyError as e:
    logger.error(f"Missing token: {e}")
    raise
except RuntimeError as e:
    logger.error(f"Failed to get token: {e}")
    raise
```

#### After (Result-based)
```python
token_result = (
    get_secret_client()
    .get_auth_token("databricks/token")
    .map_error(lambda err: logger.error(f"Failed: {err}") or err)
)

if token_result.is_err():
    return error_response(token_result.get_error(), 401)

token = token_result.unwrap()
```

### Testing with Mock Client

```python
from axiompy.secrets import SecretsClient
from axiompy.result import Ok, Err

class MockSecretClient(SecretsClient):
    def __init__(self, secrets: dict):
        self.secrets = secrets

    def get_secret(self, path: str):
        if path in self.secrets:
            return Ok(self.secrets[path])
        return Err(f"Not found: {path}")

# Use in tests
mock_client = MockSecretClient({
    "databricks/token": "test-token",
    "db/mysql": '{"username": "admin", "password": "test123"}'
})

result = mock_client.get_secret("databricks/token")
assert result.unwrap() == "test-token"
```

### Common Troubleshooting

#### Issue: Backend Import Not Available
**Solution**: Install the appropriate backend dependency:
```bash
pip install boto3              # For AWS Secrets Manager & KMS
```

#### Issue: Authentication Fails
**Solution**: Verify credentials and permissions:
```bash
# For AWS
aws sts get-caller-identity
```

#### Issue: Caching Causes Stale Credentials
**Solution**: Refresh cache when credentials change:
```python
client.refresh_credential_cache()
client.refresh_token_cache()
```

## Testing with Moto

The secrets module uses **Moto** for comprehensive AWS testing without requiring real AWS credentials.

### Test Coverage

- **Overall**: 81.02% (81 tests)
- **AWS KMS**: 84.15% (9 tests)
- **AWS Secrets Manager**: 70.40% (19 tests)
- **Local `.env`**: integration tests in `tests/test_local_secrets.py`
- **Types**: 100% (perfect coverage)
- **Client**: 100% (perfect coverage)

### Running Tests

```bash
# Run all secrets tests
python -m pytest tests/test_secrets_integration.py -v

# With coverage report
python -m pytest tests/test_secrets_integration.py --cov=axiompy.secrets --cov-report=term-missing

# Run specific test class
python -m pytest tests/test_secrets_integration.py::TestAWSSecretsManagerImplementation -v

# Run specific test
python -m pytest tests/test_secrets_integration.py::TestAWSKMSImplementation::test_aws_kms_encrypt_decrypt -xvs
```

### Test Structure

The test suite (`tests/test_secrets_integration.py`) includes:

#### Factory Tests
- Client creation and registration
- Invalid settings handling
- Settings validation

#### Type Tests
- Credential expiration checking
- AuthToken serialization
- Dataclass validation

#### Local `.env` tests

See `tests/test_local_secrets.py` for read-only `.env` parsing and lookups.

#### AWS KMS Tests (9 tests)
- Encrypt/decrypt operations
- Large data (4KB) handling
- Special character (UTF-8) encryption
- Empty string rejection (KMS constraint)
- Invalid base64 error handling
- Corrupted ciphertext detection
- Unsupported storage operations

#### AWS Secrets Manager Tests (19 tests)
- Put/get single secrets
- Put/get multiple secrets (JSON)
- Secret existence checking
- Delete operations
- List secrets with prefix
- Key extraction from JSON
- Binary secret handling
- Nested JSON structures
- Metadata/tag storage
- Large secrets (1MB)
- AWS credential configuration
- Error handling (non-existent secrets, malformed JSON)

### Writing New Backend Tests

When adding a new backend, follow this pattern:

```python
from moto import mock_aws  # or appropriate mock
from axiompy.secrets import SecretsClientFactory, SecretsClientType, YourSettings

class TestYourBackend:
    """Test your new backend implementation."""

    def test_basic_operation(self):
        """Test basic get/put operations."""
        with mock_aws():  # or mock_your_service()
            # Create settings
            settings = YourSettings(region="us-east-1")

            # Create client
            result = SecretsClientFactory.create(SecretsClientType.YOUR_BACKEND, settings)
            client = result.unwrap()

            # Test operation
            result = client.put_secret("test", "value")
            assert result.is_ok()

            # Verify retrieval
            result = client.get_secret("test")
            assert result.is_ok()
            assert result.unwrap() == "value"
```

### Moto Benefits

- **No Real AWS Credentials**: Tests run safely in CI/CD
- **Fast Execution**: No network calls, sub-second test execution
- **Realistic Behavior**: Moto accurately simulates AWS service behavior
- **Easy to Mock**: Simple context manager for test isolation
- **Comprehensive**: Covers both success and error paths

### Performance

- **Full test suite**: ~7.4 seconds
- **Secrets tests only**: ~6.6 seconds
- **No network calls**: All tests use mocked AWS services
- **No external dependencies**: Moto already in requirements-dev.txt

## Local `.env` backend

> The `LOCAL` backend reads secrets from a `.env` file using the same `SecretsClient` interface as
> AWS and other remote vaults — local development uses the same key names, same code path, different backend.

### Motivation

Typical split without `LOCAL`:

- **Production**: `SecretsClientFactory.create(SecretsClientType.AWS_SECRETS_MANAGER, settings)` (or another remote backend)
- **Local dev**: `os.environ.get("AD_BIND_PASSWORD")` reads from env vars or `.env` files

This means secret key names can drift between environments (e.g. `ad_bind_password` in a vault
vs `AD_BIND_PASSWORD` in env). The `LOCAL` backend unifies them: same factory, same key names,
same `SecretsClient` interface — backed by a `.env` file instead of a remote API.

```python
# Production (example: AWS Secrets Manager)
from axiompy.secrets import AWSSecretsManagerSettings, SecretsClientFactory, SecretsClientType

client = SecretsClientFactory.create(
    SecretsClientType.AWS_SECRETS_MANAGER,
    AWSSecretsManagerSettings(region="us-west-2"),
).unwrap()

# Local — same interface, same key names, reads from .env file
client = SecretsClientFactory.create(SecretsClientType.LOCAL, LocalSettings(
    env_file=".env",
    vault_path="app/data-product-registry/secrets",  # optional parity field
)).unwrap()

token = client.get_secret("authz_api_token").unwrap()
```

### Types reference

```python
class SecretsClientType(Enum):
    AWS_SECRETS_MANAGER = "aws_secrets_manager"
    AWS_KMS = "aws_kms"
    LOCAL = "local"

@dataclass
class LocalSettings(SecretsSettings):
    env_file: str = ".env"
    vault_path: str = ""
    case_insensitive: bool = True
```

#### 2. `axiompy/secrets/implementations/local.py`

Implement `LocalSecretClient(CredentialProvider)` that:

- On `__init__`, reads the `.env` file into a `dict[str, str]`
- Parsing: strips comments (`#`), skips blank lines, handles `KEY=value` and `KEY="value"`
- When `case_insensitive=True`, stores both `KEY` and `key` variants so lookups match
  typical lowercase secret keys and uppercase environment variable names
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

    Provides the same SecretsClient interface as AWS Secrets Manager and other backends.
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

#### 3. `axiompy/secrets/factory.py` — Register LOCAL implementation

Add to `_register_implementations()`:

```python
try:
    from .implementations.local import LocalSecretClient
    SecretsClientFactory._IMPLEMENTATIONS[SecretsClientType.LOCAL] = LocalSecretClient
    logger.debug("Registered LocalSecretClient")
except ImportError:
    logger.debug("LocalSecretClient not available")
```

#### 4. `axiompy/secrets/__init__.py` — Export new types

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

#### 5. Tests — `tests/test_local_secrets.py`

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

### `.env` file convention

The `.env` file can use **lowercase key names** so application code matches common vault conventions:

```bash
# Secrets (example keys aligned with a remote vault path)
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
`get_secret("AUTHZ_API_TOKEN")` both resolve, so uppercase env var names and lowercase secret keys
both work.

### Consumer usage (Data Product Registry)

After this is implemented, `settings_builder.py` simplifies to:

```python
from axiompy.secrets import LocalSettings, SecretsClientFactory, SecretsClientType


def _create_secrets_client():
    """Create secrets client — remote vault in production, .env locally."""
    import os

    if os.environ.get("USE_LOCAL_SECRETS", "false").lower() == "true":
        return SecretsClientFactory.create(
            SecretsClientType.LOCAL,
            LocalSettings(env_file=os.getenv("ENV_FILE", ".env")),
        ).unwrap()

    from axiompy.secrets import AWSSecretsManagerSettings

    return SecretsClientFactory.create(
        SecretsClientType.AWS_SECRETS_MANAGER,
        AWSSecretsManagerSettings(region=os.getenv("AWS_REGION", "us-west-2")),
    ).unwrap()
```

Same factory. Same `get_secret()` calls. Same key names. Different backend.

## Migration Checklist

- [ ] Add `axiompy` dependency
- [ ] Ensure backend-specific dependencies are installed
- [ ] Create centralized secrets configuration
- [ ] Set up FastAPI dependency injection (if using FastAPI)
- [ ] Update routes to use new credential provider
- [ ] Add tests for new credential usage
- [ ] Remove old direct backend usage
- [ ] Update environment configuration files
- [ ] Update CI/CD for new environment variables

---

**For complete working examples, see `examples/secrets_management_examples.py`**

**For comprehensive test examples, see `tests/test_secrets_integration.py`**

---

**Last Updated:** 2026-04-08
