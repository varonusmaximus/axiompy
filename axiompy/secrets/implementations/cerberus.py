"""
Cerberus secret client implementation.

Acme's Cerberus centralized secret management backend.
Requires the cerberus-client package: pip install cerberus-client
"""

from typing import Any, Dict, List, Optional

from axiompy.loggers import LoggerFactory
from axiompy.result import Err, Ok, Result

from ..client import CredentialProvider
from ..types import CerberusSettings

logger = LoggerFactory.create_logger(__name__)


class CerberusSecretClient(CredentialProvider):
    """
    Cerberus secret client implementation.

    Integrates with Acme's Cerberus secret management system.

    Example:
        >>> from axiompy.secrets import CerberusSettings
        >>> settings = CerberusSettings(
        ...     vault_path="shared/database/mysql",
        ...     cerberus_url="https://cerberus.example.com",
        ...     cerberus_region="us-west-2"
        ... )
        >>> client = CerberusSecretClient(settings)
        >>> result = client.get_secret("password")
        >>> password = result.unwrap()
    """

    def __init__(self, settings: CerberusSettings):
        """
        Initialize Cerberus secret client.

        Args:
            settings: CerberusSettings with vault configuration

        Raises:
            ImportError: If cerberus-client is not installed
            RuntimeError: If client initialization fails
        """
        super().__init__()
        self.settings = settings
        logger.info(f"Initializing Cerberus client for vault: {settings.vault_path}")

        # Initialize client immediately - fail fast on misconfiguration
        try:
            from cerberus.client import CerberusClient

            self._cerberus_client = CerberusClient(
                self.settings.cerberus_url,
                region=self.settings.cerberus_region,
                verbose=self.settings.verbose,
            )
            logger.info("Cerberus client initialized successfully")
        except ImportError as e:
            raise ImportError(
                "cerberus-client is required for CerberusSecretClient. "
                "Install it with: pip install cerberus-client"
            ) from e
        except Exception as e:
            logger.error(f"Failed to initialize Cerberus client: {e}")
            raise RuntimeError(f"Cerberus initialization failed: {e}") from e

    def get_secret(self, secret_path: str) -> Result[str, str]:
        """
        Retrieve a single secret by path.

        Args:
            secret_path: Full path to secret in vault

        Returns:
            Result[str, str]: Ok(secret_value) or Err(error_message)
        """
        try:
            secrets_dict = self._cerberus_client.get_secrets_data(self.settings.vault_path)
            secret_value = secrets_dict.get(secret_path)

            if secret_value is None:
                return Err(f"Secret '{secret_path}' not found in vault")

            logger.debug(f"Retrieved secret: {secret_path}")
            return Ok(secret_value)

        except Exception as e:
            error_msg = f"Failed to retrieve secret '{secret_path}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err(error_msg)

    def get_secrets(self, secret_path: str) -> Result[Dict[str, str], str]:
        """
        Retrieve all secrets from vault path.

        Args:
            secret_path: Vault path (can be different from vault_path in settings)

        Returns:
            Result[Dict[str, str], str]: Ok(secrets_dict) or Err(error_message)
        """
        try:
            secrets_dict = self._cerberus_client.get_secrets_data(secret_path)
            logger.debug(f"Retrieved {len(secrets_dict)} secrets from {secret_path}")
            return Ok(secrets_dict)

        except Exception as e:
            error_msg = f"Failed to retrieve secrets from '{secret_path}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err(error_msg)

    def get_secret_by_key(self, secret_path: str, key: str) -> Result[str, str]:
        """
        Retrieve a specific secret by path and key.

        Args:
            secret_path: Vault path
            key: Key within the secrets dict

        Returns:
            Result[str, str]: Ok(value) or Err(error_message)
        """
        return self.get_secrets(secret_path).then(
            lambda secrets: (
                Ok(secrets[key])
                if key in secrets
                else Err(f"Key '{key}' not found in secrets at '{secret_path}'")
            )
        )

    def put_secret(
        self, secret_path: str, secret_value: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Result[bool, str]:
        """
        Store a secret (Cerberus typically doesn't support write operations).

        Args:
            secret_path: Path to store secret
            secret_value: Secret value
            metadata: Optional metadata

        Returns:
            Result[bool, str]: Err (Cerberus is typically read-only)
        """
        return Err(
            "Cerberus does not support write operations. "
            "Secrets must be managed through Cerberus UI or admin API."
        )

    def put_secrets(
        self, secret_path: str, secrets: Dict[str, str], metadata: Optional[Dict[str, Any]] = None
    ) -> Result[bool, str]:
        """
        Store multiple secrets (not supported in Cerberus).

        Args:
            secret_path: Path to store secrets
            secrets: Dictionary of secrets
            metadata: Optional metadata

        Returns:
            Result[bool, str]: Err (Cerberus is typically read-only)
        """
        return Err(
            "Cerberus does not support write operations. "
            "Secrets must be managed through Cerberus UI or admin API."
        )

    def delete_secret(self, secret_path: str) -> Result[bool, str]:
        """
        Delete a secret (not supported in Cerberus).

        Args:
            secret_path: Path to delete

        Returns:
            Result[bool, str]: Err (not supported)
        """
        return Err(
            "Cerberus does not support delete operations. "
            "Secrets must be managed through Cerberus UI or admin API."
        )

    def delete_secrets(self, secret_path: str) -> Result[bool, str]:
        """
        Delete multiple secrets (not supported in Cerberus).

        Args:
            secret_path: Path prefix

        Returns:
            Result[bool, str]: Err (not supported)
        """
        return Err(
            "Cerberus does not support delete operations. "
            "Secrets must be managed through Cerberus UI or admin API."
        )

    def secret_exists(self, secret_path: str) -> Result[bool, str]:
        """
        Check if a secret exists.

        Args:
            secret_path: Path to check

        Returns:
            Result[bool, str]: Ok(exists) or Err(error_message)
        """
        return self.get_secret(secret_path).map(lambda _: True).or_else(lambda _: Ok(False))

    def list_secrets(self, secret_path: str) -> Result[List[str], str]:
        """
        List all secrets at a path.

        Args:
            secret_path: Path to list

        Returns:
            Result[List[str], str]: Ok(secret_keys) or Err(error_message)
        """
        return self.get_secrets(secret_path).map(lambda secrets: list(secrets.keys()))


__all__ = [
    "CerberusSecretClient",
]
