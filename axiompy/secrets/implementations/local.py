# @!code-style

"""
Local .env file secrets backend for development.

Provides the same SecretsClient interface as production backends
(AWS Secrets Manager and other remote vaults) but reads secrets from a local .env file. This eliminates
the split between vault-based secrets in production and os.environ in development.

Key Features:
    - Same factory, same key names, different backend
    - Case-insensitive lookups (maps both upper and lower key variants)
    - Parses standard .env format (KEY=value, comments, quoted values)
    - Read-only — write operations return Err

Quick Example:
    >>> from axiompy.secrets import SecretsClientFactory, SecretsClientType, LocalSettings
    >>> settings = LocalSettings(env_file=".env")
    >>> client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
    >>> token = client.get_secret("authz_api_token").unwrap()
"""

from typing import Any, Dict, List, Optional

from axiompy.loggers import LoggerFactory
from axiompy.result import Err, Ok, Result

from ..client import CredentialProvider
from ..types import LocalSettings

logger = LoggerFactory.create_logger(__name__)

READ_ONLY_MSG = "Local backend is read-only. Edit the .env file directly."


class LocalSecretClient(CredentialProvider):
    """
    Read secrets from a local .env file.

    Provides the same SecretsClient interface as AWS Secrets Manager and other
    remote vault backends. Used for local development so the same key names and code paths work
    in all environments.

    Args:
        settings: LocalSettings with env_file path and options
    """

    def __init__(self, settings: LocalSettings) -> None:
        super().__init__()
        self.settings = settings
        self._secrets: Dict[str, str] = {}
        self._load(settings.env_file, settings.case_insensitive)
        logger.info(
            f"LocalSecretClient initialized from '{settings.env_file}' "
            f"({len(self._secrets)} entries)"
        )

    def _load(self, env_file: str, case_insensitive: bool) -> None:
        """
        Parse .env file into key-value dict.

        Args:
            env_file: Path to the .env file
            case_insensitive: Whether to store upper/lower key variants
        """
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
            logger.warning(f"Env file not found: {env_file} — secrets will be empty")

    def get_secret(self, secret_path: str) -> Result[str, str]:
        """
        Retrieve a single secret by key.

        Args:
            secret_path: The secret key name

        Returns:
            Ok(value) if found, Err(message) if not
        """
        value = self._secrets.get(secret_path)
        if value is None:
            return Err(f"Secret '{secret_path}' not found in {self.settings.env_file}")
        return Ok(value)

    def get_secrets(self, secret_path: str) -> Result[Dict[str, str], str]:
        """
        Return all parsed secrets.

        Args:
            secret_path: Ignored for local backend (kept for interface parity)

        Returns:
            Ok(dict) with all loaded key-value pairs
        """
        return Ok(dict(self._secrets))

    def get_secret_by_key(self, secret_path: str, key: str) -> Result[str, str]:
        """
        Retrieve a specific secret by key.

        Args:
            secret_path: Ignored for local backend
            key: The secret key name

        Returns:
            Ok(value) if found, Err(message) if not
        """
        return self.get_secret(key)

    def put_secret(
        self,
        secret_path: str,
        secret_value: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Result[bool, str]:
        """Local backend is read-only."""
        return Err(READ_ONLY_MSG)

    def put_secrets(
        self,
        secret_path: str,
        secrets: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Result[bool, str]:
        """Local backend is read-only."""
        return Err(READ_ONLY_MSG)

    def delete_secret(self, secret_path: str) -> Result[bool, str]:
        """Local backend is read-only."""
        return Err(READ_ONLY_MSG)

    def delete_secrets(self, secret_path: str) -> Result[bool, str]:
        """Local backend is read-only."""
        return Err(READ_ONLY_MSG)

    def secret_exists(self, secret_path: str) -> Result[bool, str]:
        """
        Check if a secret key exists.

        Args:
            secret_path: The secret key name

        Returns:
            Ok(True/False)
        """
        return Ok(secret_path in self._secrets)

    def list_secrets(self, secret_path: str) -> Result[List[str], str]:
        """
        List all secret keys.

        Args:
            secret_path: Ignored for local backend

        Returns:
            Ok(list of key names)
        """
        return Ok(list(self._secrets.keys()))


__all__ = [
    "LocalSecretClient",
]
