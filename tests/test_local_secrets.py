"""Tests for the LOCAL secrets backend (axiompy.secrets)."""

import pytest

from axiompy.secrets import (
    LocalSettings,
    SecretsClientFactory,
    SecretsClientType,
)


class TestLocalSettings:
    """Tests for LocalSettings dataclass."""

    def test_defaults(self):
        """Test default values are applied."""
        settings = LocalSettings()
        assert settings.env_file == ".env"
        assert settings.vault_path == ""
        assert settings.case_insensitive is True

    def test_custom_values(self):
        """Test custom values override defaults."""
        settings = LocalSettings(
            env_file="/tmp/.env.test",
            vault_path="app/secrets",
            case_insensitive=False,
        )
        assert settings.env_file == "/tmp/.env.test"
        assert settings.vault_path == "app/secrets"
        assert settings.case_insensitive is False


class TestLocalSecretClientFactory:
    """Tests for creating LocalSecretClient via factory."""

    def test_create_with_valid_file(self, tmp_path):
        """Test factory creates client from a valid .env file."""
        env = tmp_path / ".env"
        env.write_text("KEY=value\n")
        settings = LocalSettings(env_file=str(env))
        result = SecretsClientFactory.create(SecretsClientType.LOCAL, settings)
        assert result.is_ok()

    def test_create_with_missing_file(self):
        """Test factory succeeds even when file is missing (empty secrets)."""
        settings = LocalSettings(env_file="/nonexistent/.env")
        result = SecretsClientFactory.create(SecretsClientType.LOCAL, settings)
        assert result.is_ok()


class TestLocalSecretClientGetSecret:
    """Tests for get_secret()."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a client with a sample .env file."""
        env = tmp_path / ".env"
        env.write_text(
            "AD_BIND_PASSWORD=secret123\n"
            "AUTHZ_API_TOKEN=tok-456\n"
            "snowflake_account=acme.us-east-1\n"
        )
        settings = LocalSettings(env_file=str(env))
        return SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()

    def test_exact_key(self, client):
        """Test retrieving secret by exact key."""
        assert client.get_secret("AD_BIND_PASSWORD").unwrap() == "secret123"

    def test_case_insensitive_lowercase(self, client):
        """Test lowercase key resolves with case_insensitive=True."""
        assert client.get_secret("ad_bind_password").unwrap() == "secret123"

    def test_case_insensitive_uppercase(self, client):
        """Test uppercase key resolves for a lowercase-defined key."""
        assert client.get_secret("SNOWFLAKE_ACCOUNT").unwrap() == "acme.us-east-1"

    def test_missing_key_returns_err(self, client):
        """Test missing key returns Err."""
        result = client.get_secret("nonexistent_key")
        assert result.is_err()

    def test_missing_file_get_secret_returns_err(self):
        """Test get_secret returns Err when file was not found."""
        settings = LocalSettings(env_file="/nonexistent/.env")
        client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
        result = client.get_secret("anything")
        assert result.is_err()


class TestLocalSecretClientGetSecrets:
    """Tests for get_secrets()."""

    def test_returns_all_secrets(self, tmp_path):
        """Test get_secrets returns all parsed key-value pairs."""
        env = tmp_path / ".env"
        env.write_text("KEY1=val1\nKEY2=val2\n")
        settings = LocalSettings(env_file=str(env))
        client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
        secrets = client.get_secrets("any/path").unwrap()
        assert "key1" in secrets
        assert secrets["key1"] == "val1"
        assert "key2" in secrets
        assert secrets["key2"] == "val2"

    def test_path_is_ignored(self, tmp_path):
        """Test secret_path argument is ignored for local backend."""
        env = tmp_path / ".env"
        env.write_text("A=1\n")
        settings = LocalSettings(env_file=str(env))
        client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
        result1 = client.get_secrets("path/one").unwrap()
        result2 = client.get_secrets("path/two").unwrap()
        assert result1 == result2


class TestLocalSecretClientGetSecretByKey:
    """Tests for get_secret_by_key()."""

    def test_delegates_to_get_secret(self, tmp_path):
        """Test get_secret_by_key delegates to get_secret using key param."""
        env = tmp_path / ".env"
        env.write_text("MY_KEY=my_value\n")
        settings = LocalSettings(env_file=str(env))
        client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
        assert client.get_secret_by_key("ignored/path", "my_key").unwrap() == "my_value"


class TestLocalSecretClientParsing:
    """Tests for .env file parsing edge cases."""

    def test_skips_comments(self, tmp_path):
        """Test lines starting with # are skipped."""
        env = tmp_path / ".env"
        env.write_text("# comment\nKEY=value\n# another comment\n")
        settings = LocalSettings(env_file=str(env))
        client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
        assert client.get_secret("key").unwrap() == "value"

    def test_skips_blank_lines(self, tmp_path):
        """Test blank lines are skipped."""
        env = tmp_path / ".env"
        env.write_text("\n\nKEY=value\n\n")
        settings = LocalSettings(env_file=str(env))
        client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
        assert client.get_secret("key").unwrap() == "value"

    def test_skips_lines_without_equals(self, tmp_path):
        """Test lines without = are skipped."""
        env = tmp_path / ".env"
        env.write_text("not_a_pair\nKEY=value\n")
        settings = LocalSettings(env_file=str(env))
        client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
        assert client.get_secret("key").unwrap() == "value"

    def test_handles_double_quoted_values(self, tmp_path):
        """Test double-quoted values are stripped."""
        env = tmp_path / ".env"
        env.write_text('KEY="quoted value"\n')
        settings = LocalSettings(env_file=str(env))
        client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
        assert client.get_secret("key").unwrap() == "quoted value"

    def test_handles_single_quoted_values(self, tmp_path):
        """Test single-quoted values are stripped."""
        env = tmp_path / ".env"
        env.write_text("KEY='single quoted'\n")
        settings = LocalSettings(env_file=str(env))
        client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
        assert client.get_secret("key").unwrap() == "single quoted"

    def test_handles_equals_in_value(self, tmp_path):
        """Test values containing = are parsed correctly."""
        env = tmp_path / ".env"
        env.write_text("URL=https://example.com?key=val&other=1\n")
        settings = LocalSettings(env_file=str(env))
        client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
        assert (
            client.get_secret("url").unwrap()
            == "https://example.com?key=val&other=1"
        )

    def test_whitespace_around_key_and_value(self, tmp_path):
        """Test whitespace around key and value is stripped."""
        env = tmp_path / ".env"
        env.write_text("  KEY  =  value  \n")
        settings = LocalSettings(env_file=str(env))
        client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
        assert client.get_secret("key").unwrap() == "value"


class TestLocalSecretClientCaseSensitive:
    """Tests for case_insensitive=False mode."""

    def test_exact_match_only(self, tmp_path):
        """Test only exact key matches when case_insensitive=False."""
        env = tmp_path / ".env"
        env.write_text("MyKey=value\n")
        settings = LocalSettings(env_file=str(env), case_insensitive=False)
        client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
        assert client.get_secret("MyKey").unwrap() == "value"
        assert client.get_secret("mykey").is_err()
        assert client.get_secret("MYKEY").is_err()


class TestLocalSecretClientReadOnly:
    """Tests for read-only write operations."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a client with a minimal .env file."""
        env = tmp_path / ".env"
        env.write_text("K=V\n")
        settings = LocalSettings(env_file=str(env))
        return SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()

    def test_put_secret_returns_err(self, client):
        """Test put_secret returns read-only error."""
        assert client.put_secret("key", "val").is_err()

    def test_put_secrets_returns_err(self, client):
        """Test put_secrets returns read-only error."""
        assert client.put_secrets("path", {"k": "v"}).is_err()

    def test_delete_secret_returns_err(self, client):
        """Test delete_secret returns read-only error."""
        assert client.delete_secret("key").is_err()

    def test_delete_secrets_returns_err(self, client):
        """Test delete_secrets returns read-only error."""
        assert client.delete_secrets("path").is_err()


class TestLocalSecretClientSecretExists:
    """Tests for secret_exists()."""

    def test_existing_key(self, tmp_path):
        """Test secret_exists returns True for existing key."""
        env = tmp_path / ".env"
        env.write_text("MY_SECRET=val\n")
        settings = LocalSettings(env_file=str(env))
        client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
        assert client.secret_exists("my_secret").unwrap() is True

    def test_missing_key(self, tmp_path):
        """Test secret_exists returns False for missing key."""
        env = tmp_path / ".env"
        env.write_text("MY_SECRET=val\n")
        settings = LocalSettings(env_file=str(env))
        client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
        assert client.secret_exists("other_key").unwrap() is False


class TestLocalSecretClientListSecrets:
    """Tests for list_secrets()."""

    def test_lists_all_keys(self, tmp_path):
        """Test list_secrets returns all key names."""
        env = tmp_path / ".env"
        env.write_text("A=1\nB=2\n")
        settings = LocalSettings(env_file=str(env))
        client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
        keys = client.list_secrets("any/path").unwrap()
        assert "A" in keys
        assert "B" in keys
        assert "a" in keys
        assert "b" in keys
