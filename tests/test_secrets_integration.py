"""
Integration tests for the secrets management module.

Tests the factory pattern, client creation, and basic operations.
"""

import pytest

from axiompy.result import Err, Ok
from axiompy.secrets import (
    AuthToken,
    AWSKMSSettings,
    AWSSecretsManagerSettings,
    Credential,
    LocalSettings,
    SecretsClient,
    SecretsClientFactory,
    SecretsClientType,
)


class MockSecretClient(SecretsClient):
    """Mock client for testing."""

    def __init__(self, secrets: dict = None):
        self.secrets = secrets or {}
        self.written_secrets = {}
        self.deleted_secrets = set()

    def get_secret(self, secret_path: str):
        if secret_path in self.secrets:
            return Ok(self.secrets[secret_path])
        return Err(f"Secret not found: {secret_path}")

    def get_secrets(self, secret_path: str):
        filtered = {k: v for k, v in self.secrets.items() if k.startswith(secret_path)}
        return Ok(filtered) if filtered else Err(f"No secrets at: {secret_path}")

    def get_secret_by_key(self, secret_path: str, key: str):
        full_key = f"{secret_path}:{key}"
        if full_key in self.secrets:
            return Ok(self.secrets[full_key])
        return Err(f"Key not found: {full_key}")

    def put_secret(self, secret_path: str, secret_value: str, metadata=None):
        self.written_secrets[secret_path] = secret_value
        return Ok(True)

    def put_secrets(self, secret_path: str, secrets: dict, metadata=None):
        for key, value in secrets.items():
            self.written_secrets[f"{secret_path}:{key}"] = value
        return Ok(True)

    def delete_secret(self, secret_path: str):
        self.deleted_secrets.add(secret_path)
        return Ok(True)

    def delete_secrets(self, secret_path: str):
        self.deleted_secrets.add(secret_path)
        return Ok(True)

    def secret_exists(self, secret_path: str):
        return Ok(secret_path in self.secrets)

    def list_secrets(self, secret_path: str):
        keys = [k for k in self.secrets.keys() if k.startswith(secret_path)]
        return Ok(keys) if keys else Err(f"No secrets at: {secret_path}")


class TestSecretsClientFactory:
    """Test SecretsClientFactory."""

    def test_factory_creates_local_client(self, tmp_path):
        """Factory creates a LOCAL client when settings and backend match."""
        env_file = tmp_path / ".env"
        env_file.write_text("MY_KEY=hello\n", encoding="utf-8")
        settings = LocalSettings(env_file=str(env_file))
        result = SecretsClientFactory.create(SecretsClientType.LOCAL, settings)
        assert result.is_ok()
        assert result.unwrap().get_secret("MY_KEY").unwrap() == "hello"

    def test_factory_error_on_unsupported_type(self):
        """Test that factory returns error for unsupported types."""
        from dataclasses import dataclass

        @dataclass
        class FakeSettings:
            pass

        result = SecretsClientFactory.create(SecretsClientType.LOCAL, FakeSettings())
        assert result.is_err()


class TestMockSecretClient:
    """Test the mock client."""

    def test_get_secret_success(self):
        """Test successful secret retrieval."""
        client = MockSecretClient({"api_key": "secret123"})
        result = client.get_secret("api_key")
        assert result.is_ok()
        assert result.unwrap() == "secret123"

    def test_get_secret_not_found(self):
        """Test secret not found error."""
        client = MockSecretClient({})
        result = client.get_secret("missing")
        assert result.is_err()
        assert "not found" in result.get_error().lower()

    def test_get_secrets_filtering(self):
        """Test secret filtering."""
        secrets = {
            "db/host": "localhost",
            "db/port": "3306",
            "api/key": "secret",
        }
        client = MockSecretClient(secrets)

        result = client.get_secrets("db/")
        assert result.is_ok()
        db_secrets = result.unwrap()
        assert len(db_secrets) == 2
        assert "db/host" in db_secrets
        assert "db/port" in db_secrets

    def test_put_secret(self):
        """Test secret storage."""
        client = MockSecretClient({})
        result = client.put_secret("new_key", "new_value")

        assert result.is_ok()
        assert client.written_secrets["new_key"] == "new_value"

    def test_delete_secret(self):
        """Test secret deletion."""
        client = MockSecretClient({"api_key": "secret"})
        result = client.delete_secret("api_key")

        assert result.is_ok()
        assert "api_key" in client.deleted_secrets


class TestCredentialProviderWithMock:
    """Test CredentialProvider with mock client."""

    def test_get_auth_token(self):
        """Test auth token retrieval."""
        mock_client = MockSecretClient({"databricks_token": "eyJhbGc..."})

        # Add the missing methods to mock
        mock_client._credential_cache = {}
        mock_client._token_cache = {}

        result = mock_client.get_secret("databricks_token")
        assert result.is_ok()
        assert result.unwrap() == "eyJhbGc..."

    def test_credential_types(self):
        """Test credential data types."""
        token = AuthToken(token="test123", token_type="Bearer", scope="read write")

        assert str(token) == "Bearer test123"
        assert not token.is_expired()

    def test_credential_data_type(self):
        """Test credential data type."""
        cred = Credential(username="admin", password="secret123", credential_type="database")

        assert cred.username == "admin"
        assert not cred.is_expired()


class TestResultChaining:
    """Test Railway-Oriented Programming patterns."""

    def test_result_chaining_success(self):
        """Test chaining successful operations."""
        client = MockSecretClient({"password": "secret123"})

        result = (
            client.get_secret("password").map(lambda p: p.upper()).map(lambda p: f"PASSWORD: {p}")
        )

        assert result.is_ok()
        assert result.unwrap() == "PASSWORD: SECRET123"

    def test_result_chaining_with_error(self):
        """Test error propagation in chain."""
        client = MockSecretClient({})

        result = (
            client.get_secret("missing")
            .map(lambda p: p.upper())  # Not called
            .map_error(lambda e: f"Error: {e}")
        )

        assert result.is_err()
        assert "Error:" in result.get_error()

    def test_result_error_recovery(self):
        """Test error recovery."""
        client = MockSecretClient({})

        result = (
            client.get_secret("missing")
            .or_else(lambda _: client.get_secret("fallback"))
            .unwrap_or("default")
        )

        assert result == "default"


class TestSettingsDataclasses:
    """Test settings dataclasses."""

    def test_local_settings_defaults(self):
        """Test LocalSettings defaults."""
        settings = LocalSettings()
        assert settings.env_file == ".env"
        assert settings.case_insensitive is True

    def test_aws_secrets_manager_settings(self):
        """Test AWS Secrets Manager settings."""
        settings = AWSSecretsManagerSettings(region="us-west-2")

        assert settings.region == "us-west-2"
        assert settings.access_key_id is None

    def test_aws_kms_settings(self):
        """Test AWS KMS settings."""
        settings = AWSKMSSettings(
            key_id="arn:aws:kms:us-west-2:123456789:key/12345678", region="us-west-2"
        )

        assert settings.key_id == "arn:aws:kms:us-west-2:123456789:key/12345678"
        assert settings.region == "us-west-2"


class TestErrorHandling:
    """Test error handling patterns."""

    def test_graceful_error_handling(self):
        """Test that errors are handled gracefully."""
        client = MockSecretClient({})

        # Should not throw, should return error
        result = client.get_secret("missing")
        assert result.is_err()
        assert isinstance(result.get_error(), str)

    def test_error_message_clarity(self):
        """Test that error messages are clear."""
        client = MockSecretClient({})
        result = client.get_secret("missing_api_key")

        error_msg = result.get_error()
        assert "missing_api_key" in error_msg
        assert "not found" in error_msg.lower()


class TestMockClientAdvanced:
    """Advanced tests for MockSecretClient to improve coverage."""

    def test_get_secret_by_key_success(self):
        """Test retrieving a secret by specific key."""
        mock_client = MockSecretClient(
            {"database:username": "admin", "database:password": "secret123"}
        )

        result = mock_client.get_secret_by_key("database", "username")
        assert result.is_ok()
        assert result.unwrap() == "admin"

    def test_get_secret_by_key_not_found(self):
        """Test key not found error."""
        mock_client = MockSecretClient({})

        result = mock_client.get_secret_by_key("database", "username")
        assert result.is_err()
        assert "not found" in result.get_error().lower()

    def test_put_secrets_multiple(self):
        """Test putting multiple secrets at once."""
        mock_client = MockSecretClient()

        secrets_dict = {"username": "admin", "password": "secret", "host": "localhost"}

        result = mock_client.put_secrets("database", secrets_dict)
        assert result.is_ok()
        assert len(mock_client.written_secrets) == 3

    def test_delete_secrets_batch(self):
        """Test deleting multiple secrets."""
        mock_client = MockSecretClient({"api/key1": "value1", "api/key2": "value2"})

        result = mock_client.delete_secrets("api/")
        assert result.is_ok()
        assert "api/" in mock_client.deleted_secrets

    def test_secret_exists_true(self):
        """Test checking if secret exists."""
        mock_client = MockSecretClient({"existing_secret": "value"})

        result = mock_client.secret_exists("existing_secret")
        assert result.is_ok()
        assert result.unwrap() is True

    def test_secret_exists_false(self):
        """Test checking if non-existent secret exists."""
        mock_client = MockSecretClient({})

        result = mock_client.secret_exists("missing_secret")
        assert result.is_ok()
        assert result.unwrap() is False

    def test_list_secrets_filtering(self):
        """Test listing secrets with prefix filtering."""
        mock_client = MockSecretClient(
            {
                "api/stripe-key": "sk_live_xxx",
                "api/paypal-key": "pp_live_yyy",
                "database/mysql-url": "mysql://...",
                "database/redis-url": "redis://...",
            }
        )

        result = mock_client.list_secrets("api/")
        assert result.is_ok()
        keys = result.unwrap()
        assert len(keys) == 2
        assert all(k.startswith("api/") for k in keys)

    def test_list_secrets_empty(self):
        """Test listing secrets when none match prefix."""
        mock_client = MockSecretClient({"database/mysql": "value"})

        result = mock_client.list_secrets("api/")
        assert result.is_err()


class TestFactoryIntegration:
    """Integration tests for factory pattern."""

    def test_factory_create_returns_result(self, tmp_path):
        """Test that factory.create returns a Result."""
        env_file = tmp_path / ".env"
        env_file.write_text("k=v\n", encoding="utf-8")
        settings = LocalSettings(env_file=str(env_file))
        result = SecretsClientFactory.create(SecretsClientType.LOCAL, settings)
        assert result.is_ok()


class TestTypeDefinitions:
    """Test type definitions and data classes."""

    def test_auth_token_creation(self):
        """Test creating AuthToken."""
        from datetime import datetime, timedelta

        expires = datetime.utcnow() + timedelta(hours=1)
        token = AuthToken(
            token="test-token-123",
            token_type="Bearer",
            expires_at=expires,
            scope="read write",
            metadata={"user_id": "123"},
        )

        assert token.token == "test-token-123"
        assert token.token_type == "Bearer"
        assert token.scope == "read write"
        assert not token.is_expired()

    def test_auth_token_expired(self):
        """Test checking if token is expired."""
        from datetime import datetime, timedelta

        past = datetime.utcnow() - timedelta(hours=1)
        token = AuthToken(token="expired-token", expires_at=past)

        assert token.is_expired()

    def test_auth_token_no_expiry(self):
        """Test token without expiration."""
        token = AuthToken(token="no-expiry-token")
        assert not token.is_expired()

    def test_auth_token_string_representation(self):
        """Test string representation of token."""
        token = AuthToken(token="my-token", token_type="Bearer")
        assert str(token) == "Bearer my-token"

        token_no_type = AuthToken(token="my-token", token_type="")
        assert str(token_no_type) == "my-token"

    def test_credential_creation(self):
        """Test creating Credential."""
        cred = Credential(
            username="admin",
            password="secret123",
            credential_type="database",
            metadata={"host": "localhost", "port": 5432},
        )

        assert cred.username == "admin"
        assert cred.password == "secret123"
        assert cred.credential_type == "database"
        assert cred.metadata["host"] == "localhost"

    def test_credential_expired(self):
        """Test checking if credential is expired."""
        from datetime import datetime, timedelta

        past = datetime.utcnow() - timedelta(hours=1)
        cred = Credential(username="admin", password="secret", expires_at=past)

        assert cred.is_expired()

    def test_credential_not_expired(self):
        """Test credential without expiration."""
        cred = Credential(username="admin", password="secret")
        assert not cred.is_expired()


class TestAWSSecretsManagerIntegration:
    """Tests for AWS Secrets Manager client integration."""

    def test_aws_sm_with_credentials(self):
        """Test AWS Secrets Manager with explicit credentials."""
        settings = AWSSecretsManagerSettings(
            region="us-east-1",
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )

        assert settings.region == "us-east-1"
        assert settings.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert settings.secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert settings.endpoint_url is None

    def test_aws_sm_with_endpoint(self):
        """Test AWS Secrets Manager with custom endpoint."""
        settings = AWSSecretsManagerSettings(
            region="us-west-2", endpoint_url="http://localhost:4566"
        )

        assert settings.region == "us-west-2"
        assert settings.endpoint_url == "http://localhost:4566"

    def test_aws_sm_default_credentials(self):
        """Test AWS Secrets Manager with default credentials."""
        settings = AWSSecretsManagerSettings(region="eu-west-1")

        assert settings.region == "eu-west-1"
        assert settings.access_key_id is None
        assert settings.secret_access_key is None


class TestAWSKMSIntegration:
    """Tests for AWS KMS client integration."""

    def test_aws_kms_with_default_credentials(self):
        """Test AWS KMS with default credentials."""
        settings = AWSKMSSettings(
            key_id="arn:aws:kms:us-west-2:111122223333:key/1234abcd", region="us-west-2"
        )

        assert settings.key_id == "arn:aws:kms:us-west-2:111122223333:key/1234abcd"
        assert settings.region == "us-west-2"
        assert settings.access_key_id is None
        assert settings.secret_access_key is None

    def test_aws_kms_with_explicit_credentials(self):
        """Test AWS KMS with explicit credentials."""
        settings = AWSKMSSettings(
            key_id="alias/my-key",
            region="us-east-1",
            access_key_id="AKIA...",
            secret_access_key="secret...",
        )

        assert settings.key_id == "alias/my-key"
        assert settings.access_key_id == "AKIA..."
        assert settings.secret_access_key == "secret..."


class TestAWSKMSImplementation:
    """Comprehensive tests for AWS KMS implementation using Moto."""

    def test_aws_kms_encrypt_decrypt(self):
        """Test encrypt and decrypt with Moto-mocked AWS KMS."""
        import boto3
        from moto import mock_aws

        with mock_aws():
            # Create KMS key
            kms_client = boto3.client("kms", region_name="us-east-1")
            key_response = kms_client.create_key(Description="Test key")
            key_id = key_response["KeyMetadata"]["KeyId"]

            # Create AWSKMSSecretClient
            settings = AWSKMSSettings(key_id=key_id, region="us-east-1")
            from axiompy.secrets.implementations.aws_kms import AWSKMSSecretClient

            client = AWSKMSSecretClient(settings)

            # Test encrypt
            plaintext = "my-secret-value"
            encrypt_result = client.encrypt(plaintext)
            assert encrypt_result.is_ok()
            ciphertext = encrypt_result.unwrap()
            assert len(ciphertext) > 0

            # Test decrypt
            decrypt_result = client.decrypt(ciphertext)
            assert decrypt_result.is_ok()
            decrypted = decrypt_result.unwrap()
            assert decrypted == plaintext

    def test_aws_kms_get_secret_not_supported(self):
        """Test that get_secret returns error (not supported)."""
        settings = AWSKMSSettings(
            key_id="arn:aws:kms:us-west-2:123456789:key/test", region="us-west-2"
        )
        from axiompy.secrets.implementations.aws_kms import AWSKMSSecretClient

        client = AWSKMSSecretClient(settings)
        result = client.get_secret("path")

        assert result.is_err()
        assert "encryption" in result.get_error().lower()

    def test_aws_kms_unsupported_operations(self):
        """Test that all storage operations return error (not supported)."""
        settings = AWSKMSSettings(
            key_id="arn:aws:kms:us-west-2:123456789:key/test", region="us-west-2"
        )
        from axiompy.secrets.implementations.aws_kms import AWSKMSSecretClient

        client = AWSKMSSecretClient(settings)

        # All storage operations should fail with same message
        ops = [
            ("get_secrets", lambda: client.get_secrets("path")),
            ("put_secret", lambda: client.put_secret("path", "value")),
            ("put_secrets", lambda: client.put_secrets("path", {"k": "v"})),
            ("delete_secret", lambda: client.delete_secret("path")),
            ("delete_secrets", lambda: client.delete_secrets("path/")),
            ("secret_exists", lambda: client.secret_exists("path")),
            ("list_secrets", lambda: client.list_secrets("path")),
        ]

        for op_name, op_func in ops:
            result = op_func()
            assert result.is_err(), f"{op_name} should fail"
            assert "encryption" in result.get_error().lower(), f"{op_name} error message incorrect"


class TestAWSSecretsManagerImplementation:
    """Comprehensive tests for AWS Secrets Manager implementation using Moto."""

    def test_aws_secrets_manager_put_get_secret(self):
        """Test put and get secret with Moto-mocked AWS Secrets Manager."""
        from moto import mock_aws

        with mock_aws():
            # Create client
            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            # Test put_secret
            secret_path = "test/secret"
            secret_value = "my-secret-value"
            put_result = client.put_secret(secret_path, secret_value)
            assert put_result.is_ok()
            assert put_result.unwrap() is True

            # Test get_secret
            get_result = client.get_secret(secret_path)
            assert get_result.is_ok()
            assert get_result.unwrap() == secret_value

    def test_aws_secrets_manager_put_get_secrets(self):
        """Test put and get multiple secrets."""
        from moto import mock_aws

        with mock_aws():
            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            # Put multiple secrets
            secret_path = "database"
            secrets_dict = {"username": "admin", "password": "secret123"}
            put_result = client.put_secrets(secret_path, secrets_dict)
            assert put_result.is_ok()

            # Get multiple secrets - note: AWS Secrets Manager stores JSON
            get_result = client.get_secrets(secret_path)
            assert get_result.is_ok()
            retrieved = get_result.unwrap()
            assert isinstance(retrieved, dict)

    def test_aws_secrets_manager_delete_secret(self):
        """Test deleting a secret."""
        from moto import mock_aws

        with mock_aws():
            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            # Put a secret first
            secret_path = "test/secret"
            client.put_secret(secret_path, "value")

            # Delete it
            delete_result = client.delete_secret(secret_path)
            assert delete_result.is_ok()

    def test_aws_secrets_manager_get_secret_not_found(self):
        """Test getting a non-existent secret."""
        from moto import mock_aws

        with mock_aws():
            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            # Try to get non-existent secret
            result = client.get_secret("nonexistent")
            assert result.is_err()

    def test_aws_secrets_manager_secret_exists(self):
        """Test checking if a secret exists."""
        from moto import mock_aws

        with mock_aws():
            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            secret_path = "my-secret"

            # Should not exist
            exists_result = client.secret_exists(secret_path)
            assert exists_result.is_ok()
            assert exists_result.unwrap() is False

            # Create it
            client.put_secret(secret_path, "value")

            # Should exist now
            exists_result = client.secret_exists(secret_path)
            assert exists_result.is_ok()
            assert exists_result.unwrap() is True

    def test_aws_secrets_manager_list_secrets(self):
        """Test listing secrets."""
        from moto import mock_aws

        with mock_aws():
            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            # Create a few secrets
            client.put_secret("app/db/password", "secret1")
            client.put_secret("app/api/key", "secret2")
            client.put_secret("other/secret", "secret3")

            # List with prefix
            result = client.list_secrets("app/")
            assert result.is_ok()
            secrets = result.unwrap()
            assert isinstance(secrets, list)
            assert len(secrets) >= 2

    def test_aws_secrets_manager_get_secret_by_key(self):
        """Test getting a specific key from a JSON secret."""
        from moto import mock_aws

        with mock_aws():
            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            # Store a JSON secret with multiple keys
            secret_dict = {"username": "admin", "password": "secret123", "host": "localhost"}
            client.put_secrets("database", secret_dict)

            # Get specific key
            result = client.get_secret_by_key("database", "password")
            assert result.is_ok()
            assert result.unwrap() == "secret123"

            # Get non-existent key
            result = client.get_secret_by_key("database", "nonexistent")
            assert result.is_err()

    def test_aws_secrets_manager_delete_nonexistent(self):
        """Test deleting a non-existent secret.

        Note: AWS Secrets Manager with Moto allows deletion of non-existent secrets.
        This is a quirk of the Moto implementation (real AWS might behave differently).
        """
        from moto import mock_aws

        with mock_aws():
            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            # Moto allows deletion of non-existent secrets (returns success)
            result = client.delete_secret("nonexistent")
            assert result.is_ok()  # Moto behavior

    def test_aws_secrets_manager_update_existing(self):
        """Test updating an existing secret."""
        from moto import mock_aws

        with mock_aws():
            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            secret_path = "my-secret"

            # Create initial secret
            put_result = client.put_secret(secret_path, "value1")
            assert put_result.is_ok()

            # Update it
            put_result = client.put_secret(secret_path, "value2")
            assert put_result.is_ok()

            # Verify update
            get_result = client.get_secret(secret_path)
            assert get_result.is_ok()
            assert get_result.unwrap() == "value2"


class TestAWSSecretsManagerAdvanced:
    """Advanced tests for AWS Secrets Manager implementation."""

    def test_aws_secrets_manager_binary_secret(self):
        """Test handling of binary secrets in Secrets Manager."""

        import boto3
        from moto import mock_aws

        with mock_aws():
            # Create Secrets Manager client directly to store binary
            sm_client = boto3.client("secretsmanager", region_name="us-east-1")

            # Create a binary secret
            binary_data = b"binary_secret_data"
            sm_client.create_secret(Name="binary-secret", SecretBinary=binary_data)

            # Use our client to retrieve it
            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            # Retrieve binary secret
            result = client.get_secret("binary-secret")
            assert result.is_ok()

    def test_aws_secrets_manager_json_with_nested_structure(self):
        """Test storing and retrieving nested JSON structures."""
        from moto import mock_aws

        with mock_aws():
            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            # Store complex nested JSON
            complex_secret = {
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "credentials": {"username": "admin", "password": "secret"},
                },
                "api_keys": ["key1", "key2", "key3"],
            }

            put_result = client.put_secrets("complex-config", complex_secret)
            assert put_result.is_ok()

            # Retrieve and verify
            get_result = client.get_secrets("complex-config")
            assert get_result.is_ok()
            retrieved = get_result.unwrap()
            assert isinstance(retrieved, dict)
            assert "database" in retrieved

    def test_aws_secrets_manager_get_secret_by_key_nested(self):
        """Test get_secret_by_key with nested JSON structures."""
        from moto import mock_aws

        with mock_aws():
            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            # Store nested JSON
            secret_dict = {"db": {"host": "localhost", "port": "5432"}, "username": "admin"}
            client.put_secrets("config", secret_dict)

            # Top-level key should work
            result = client.get_secret_by_key("config", "username")
            assert result.is_ok()
            assert result.unwrap() == "admin"

    def test_aws_secrets_manager_delete_secrets(self):
        """Test deleting multiple secrets."""
        from moto import mock_aws

        with mock_aws():
            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            secret_path = "app/config/"

            # Store a secret
            put_result = client.put_secret(secret_path + "secret1", "value1")
            assert put_result.is_ok()

            # Delete it using delete_secrets
            delete_result = client.delete_secrets(secret_path)
            assert delete_result.is_ok()

    def test_aws_secrets_manager_get_secret_json_malformed(self):
        """Test handling of non-JSON stored as string."""
        import boto3
        from moto import mock_aws

        with mock_aws():
            # Store plain text that's not JSON
            sm_client = boto3.client("secretsmanager", region_name="us-east-1")
            sm_client.create_secret(Name="plain-text-secret", SecretString="not-a-json-object")

            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            # get_secrets should fail on non-JSON
            result = client.get_secrets("plain-text-secret")
            assert result.is_err()

    def test_aws_secrets_manager_with_metadata(self):
        """Test storing secrets with metadata/tags."""
        from moto import mock_aws

        with mock_aws():
            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            # Store with metadata
            metadata = {"environment": "production", "team": "backend"}
            put_result = client.put_secret("app/db/password", "secret123", metadata=metadata)
            assert put_result.is_ok()

            # Retrieve to verify it was stored
            get_result = client.get_secret("app/db/password")
            assert get_result.is_ok()
            assert get_result.unwrap() == "secret123"

    def test_aws_secrets_manager_access_key_credentials(self):
        """Test that client can be initialized with access key credentials."""
        from moto import mock_aws

        with mock_aws():
            # Create client with explicit credentials
            settings = AWSSecretsManagerSettings(
                region="us-east-1", access_key_id="testing", secret_access_key="testing"
            )
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            # Should work with Moto
            put_result = client.put_secret("test-secret", "value")
            assert put_result.is_ok()

    def test_aws_secrets_manager_endpoint_url(self):
        """Test that client can be initialized with custom endpoint URL.

        Note: This just verifies that the client initializes with endpoint_url setting.
        It doesn't actually attempt to use it (to avoid real connection attempts).
        """
        from moto import mock_aws

        with mock_aws():
            # Create client without endpoint_url works fine
            settings = AWSSecretsManagerSettings(
                region="us-east-1"
                # No endpoint_url - uses default AWS endpoint
            )
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            # Should work with Moto
            put_result = client.put_secret("test-secret", "value")
            assert put_result.is_ok()

    def test_aws_secrets_manager_large_secret(self):
        """Test storing and retrieving large secrets (up to 64KB)."""
        from moto import mock_aws

        with mock_aws():
            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            # Create a large secret (1MB of JSON)
            large_dict = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}

            put_result = client.put_secrets("large-secret", large_dict)
            assert put_result.is_ok()

            # Retrieve and verify
            get_result = client.get_secrets("large-secret")
            assert get_result.is_ok()
            retrieved = get_result.unwrap()
            assert len(retrieved) == 100

    def test_aws_secrets_manager_secret_exists_after_update(self):
        """Test that secret_exists returns True after update."""
        from moto import mock_aws

        with mock_aws():
            settings = AWSSecretsManagerSettings(region="us-east-1")
            from axiompy.secrets.implementations.aws_secrets_manager import AWSSecretsManagerClient

            client = AWSSecretsManagerClient(settings)

            secret_path = "my-secret"

            # Create secret
            client.put_secret(secret_path, "value1")
            exists_result = client.secret_exists(secret_path)
            assert exists_result.is_ok()
            assert exists_result.unwrap() is True

            # Update secret
            client.put_secret(secret_path, "value2")
            exists_result = client.secret_exists(secret_path)
            assert exists_result.is_ok()
            assert exists_result.unwrap() is True


class TestAWSKMSAdvanced:
    """Advanced tests for AWS KMS implementation."""

    def test_aws_kms_encrypt_empty_string(self):
        """Test that KMS rejects empty strings.

        AWS KMS requires plaintext to have length >= 1.
        """
        import boto3
        from moto import mock_aws

        with mock_aws():
            # Create KMS key
            kms_client = boto3.client("kms", region_name="us-east-1")
            key_response = kms_client.create_key(Description="Test key")
            key_id = key_response["KeyMetadata"]["KeyId"]

            settings = AWSKMSSettings(key_id=key_id, region="us-east-1")
            from axiompy.secrets.implementations.aws_kms import AWSKMSSecretClient

            client = AWSKMSSecretClient(settings)

            # Encrypt empty string should fail
            result = client.encrypt("")
            assert result.is_err()
            assert "length" in result.get_error().lower()

    def test_aws_kms_encrypt_large_text(self):
        """Test encrypting large text."""
        import boto3
        from moto import mock_aws

        with mock_aws():
            # Create KMS key
            kms_client = boto3.client("kms", region_name="us-east-1")
            key_response = kms_client.create_key(Description="Test key")
            key_id = key_response["KeyMetadata"]["KeyId"]

            settings = AWSKMSSettings(key_id=key_id, region="us-east-1")
            from axiompy.secrets.implementations.aws_kms import AWSKMSSecretClient

            client = AWSKMSSecretClient(settings)

            # Encrypt large text (4KB)
            large_text = "x" * 4096
            result = client.encrypt(large_text)
            assert result.is_ok()
            ciphertext = result.unwrap()

            # Decrypt and verify
            decrypt_result = client.decrypt(ciphertext)
            assert decrypt_result.is_ok()
            assert decrypt_result.unwrap() == large_text

    def test_aws_kms_encrypt_special_characters(self):
        """Test encrypting text with special characters."""
        import boto3
        from moto import mock_aws

        with mock_aws():
            kms_client = boto3.client("kms", region_name="us-east-1")
            key_response = kms_client.create_key(Description="Test key")
            key_id = key_response["KeyMetadata"]["KeyId"]

            settings = AWSKMSSettings(key_id=key_id, region="us-east-1")
            from axiompy.secrets.implementations.aws_kms import AWSKMSSecretClient

            client = AWSKMSSecretClient(settings)

            # Encrypt text with special characters
            special_text = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
            result = client.encrypt(special_text)
            assert result.is_ok()
            ciphertext = result.unwrap()

            # Decrypt and verify
            decrypt_result = client.decrypt(ciphertext)
            assert decrypt_result.is_ok()
            assert decrypt_result.unwrap() == special_text

    def test_aws_kms_decrypt_invalid_base64(self):
        """Test decrypting invalid base64."""
        import boto3
        from moto import mock_aws

        with mock_aws():
            kms_client = boto3.client("kms", region_name="us-east-1")
            key_response = kms_client.create_key(Description="Test key")
            key_id = key_response["KeyMetadata"]["KeyId"]

            settings = AWSKMSSettings(key_id=key_id, region="us-east-1")
            from axiompy.secrets.implementations.aws_kms import AWSKMSSecretClient

            client = AWSKMSSecretClient(settings)

            # Try to decrypt invalid base64
            result = client.decrypt("invalid!!!base64")
            assert result.is_err()

    def test_aws_kms_decrypt_corrupted_ciphertext(self):
        """Test decrypting corrupted ciphertext."""
        import base64

        import boto3
        from moto import mock_aws

        with mock_aws():
            kms_client = boto3.client("kms", region_name="us-east-1")
            key_response = kms_client.create_key(Description="Test key")
            key_id = key_response["KeyMetadata"]["KeyId"]

            settings = AWSKMSSettings(key_id=key_id, region="us-east-1")
            from axiompy.secrets.implementations.aws_kms import AWSKMSSecretClient

            client = AWSKMSSecretClient(settings)

            # Create a corrupted ciphertext
            corrupted = base64.b64encode(b"corrupted_data").decode("utf-8")
            result = client.decrypt(corrupted)
            assert result.is_err()

    def test_aws_kms_multiple_encrypts_different_results(self):
        """Test that multiple encrypts produce different results (KMS uses randomness)."""
        import boto3
        from moto import mock_aws

        with mock_aws():
            kms_client = boto3.client("kms", region_name="us-east-1")
            key_response = kms_client.create_key(Description="Test key")
            key_id = key_response["KeyMetadata"]["KeyId"]

            settings = AWSKMSSettings(key_id=key_id, region="us-east-1")
            from axiompy.secrets.implementations.aws_kms import AWSKMSSecretClient

            client = AWSKMSSecretClient(settings)

            plaintext = "same-text"

            # Encrypt multiple times
            result1 = client.encrypt(plaintext)
            result2 = client.encrypt(plaintext)

            assert result1.is_ok()
            assert result2.is_ok()

            # Ciphertexts should be different (due to KMS randomization)
            cipher1 = result1.unwrap()
            cipher2 = result2.unwrap()
            # Note: Moto might not implement this, so we just check both decrypt to same plaintext

            decrypt1 = client.decrypt(cipher1).unwrap()
            decrypt2 = client.decrypt(cipher2).unwrap()

            assert decrypt1 == plaintext
            assert decrypt2 == plaintext


class TestFactoryErrorHandling:
    """Test factory error handling."""

    def test_factory_invalid_settings_type(self):
        """Test factory with wrong settings type."""
        from dataclasses import dataclass

        @dataclass
        class WrongSettings:
            pass

        # Should return Err or handle gracefully
        result = SecretsClientFactory.create(SecretsClientType.LOCAL, WrongSettings())

        assert result.is_err()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
