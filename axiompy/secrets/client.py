# @!secrets

"""
Abstract secret client interface for unified secret management.

Defines the core interface that all secret backends must implement,
supporting various operations like retrieval, storage, and deletion.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from axiompy.result import Result

from .types import AuthToken, Credential


class SecretsClient(ABC):  # pragma: no cover
    """
    Abstract base class for secret management clients.

    Provides a unified interface for interacting with different secret backends.
    All methods return Result types for Railway-Oriented Programming error handling.

    Methods should be implemented with appropriate error handling and logging.
    """

    @abstractmethod  # pragma: no cover
    def get_secret(self, secret_path: str) -> Result[str, str]:  # pragma: no cover
        """
        Retrieve a single secret by path.

        Args:
            secret_path: Path to the secret (format depends on backend)

        Returns:
            Result[str, str]: Ok(secret_value) or Err(error_message)

        Examples:
            - AWS Secrets Manager: "prod/database/mysql-password"
            - Vault-style path: "secret/data/database/mysql"
        """
        pass

    @abstractmethod  # pragma: no cover
    def get_secrets(self, secret_path: str) -> Result[Dict[str, str], str]:
        """
        Retrieve all secrets at a path (returns dict).

        Args:
            secret_path: Path prefix to retrieve secrets from

        Returns:
            Result[Dict[str, str], str]: Ok(secrets_dict) or Err(error_message)
        """

    @abstractmethod  # pragma: no cover
    def get_secret_by_key(self, secret_path: str, key: str) -> Result[str, str]:
        """
        Retrieve a specific secret by path and key.

        Args:
            secret_path: Path to the secret
            key: Specific key within the secret

        Returns:
            Result[str, str]: Ok(value) or Err(error_message)
        """

    @abstractmethod  # pragma: no cover
    def put_secret(
        self, secret_path: str, secret_value: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Result[bool, str]:
        """
        Store a secret.

        Args:
            secret_path: Path where the secret should be stored
            secret_value: The secret value to store
            metadata: Optional metadata about the secret

        Returns:
            Result[bool, str]: Ok(True) on success or Err(error_message)
        """

    @abstractmethod  # pragma: no cover
    def put_secrets(
        self, secret_path: str, secrets: Dict[str, str], metadata: Optional[Dict[str, Any]] = None
    ) -> Result[bool, str]:
        """
        Store multiple secrets.

        Args:
            secret_path: Path where secrets should be stored
            secrets: Dictionary of secrets to store
            metadata: Optional metadata about the secrets

        Returns:
            Result[bool, str]: Ok(True) on success or Err(error_message)
        """

    @abstractmethod  # pragma: no cover
    def delete_secret(self, secret_path: str) -> Result[bool, str]:
        """
        Delete a secret.

        Args:
            secret_path: Path to the secret to delete

        Returns:
            Result[bool, str]: Ok(True) on success or Err(error_message)
        """

    @abstractmethod  # pragma: no cover
    def delete_secrets(self, secret_path: str) -> Result[bool, str]:
        """
        Delete multiple secrets at a path.

        Args:
            secret_path: Path prefix for secrets to delete

        Returns:
            Result[bool, str]: Ok(True) on success or Err(error_message)
        """

    @abstractmethod  # pragma: no cover
    def secret_exists(self, secret_path: str) -> Result[bool, str]:
        """
        Check if a secret exists.

        Args:
            secret_path: Path to check

        Returns:
            Result[bool, str]: Ok(exists) or Err(error_message)
        """

    @abstractmethod  # pragma: no cover
    def list_secrets(self, secret_path: str) -> Result[List[str], str]:
        """
        List all secrets at a path.

        Args:
            secret_path: Path to list secrets from

        Returns:
            Result[List[str], str]: Ok(secret_paths) or Err(error_message)
        """


class CredentialProvider(SecretsClient):  # pragma: no cover
    """
    Extended SecretClient specialized for credential and authentication token management.

    Builds on SecretClient to provide high-level methods for:
    - Retrieving authentication tokens
    - Managing username/password credentials
    - Database connection credentials
    - API keys and service principal credentials

    Includes caching and expiration checking for credentials.
    """

    def __init__(self):
        """Initialize credential provider with empty cache."""
        self._credential_cache: Dict[str, Credential] = {}
        self._token_cache: Dict[str, AuthToken] = {}

    def get_auth_token(self, token_path: str) -> Result[AuthToken, str]:
        """
        Retrieve an authentication token.

        Args:
            token_path: Path to the token secret

        Returns:
            Result[AuthToken, str]: Ok(token) or Err(error_message)
        """
        return self.get_secret(token_path).then(
            lambda token_str: self._parse_auth_token(token_path, token_str)
        )

    def get_credential(self, cred_path: str) -> Result[Credential, str]:
        """
        Retrieve a credential (username/password pair).

        Args:
            cred_path: Path to the credential

        Returns:
            Result[Credential, str]: Ok(credential) or Err(error_message)
        """
        # Check cache first
        if cred_path in self._credential_cache:
            cached = self._credential_cache[cred_path]
            if not cached.is_expired():
                return self.Ok(cached)

        return self.get_secrets(cred_path).then(
            lambda cred_dict: self._parse_credential(cred_path, cred_dict)
        )

    def get_database_credentials(self, db_cred_path: str) -> Result[Credential, str]:
        """
        Retrieve database credentials.

        Args:
            db_cred_path: Path to database credentials

        Returns:
            Result[Credential, str]: Ok(credential) or Err(error_message)
        """
        return self.get_credential(db_cred_path).map(
            lambda cred: Credential(
                username=cred.username,
                password=cred.password,
                credential_type="database",
                metadata=cred.metadata,
            )
        )

    def get_api_key(self, key_path: str) -> Result[str, str]:
        """
        Retrieve an API key.

        Args:
            key_path: Path to the API key

        Returns:
            Result[str, str]: Ok(api_key) or Err(error_message)
        """
        return self.get_secret(key_path)

    def refresh_credential_cache(self) -> None:
        """Clear credential cache to force fresh retrieval."""
        self._credential_cache.clear()

    def refresh_token_cache(self) -> None:
        """Clear token cache to force fresh retrieval."""
        self._token_cache.clear()

    def refresh_all_caches(self) -> None:
        """Clear all caches to force fresh retrieval."""
        self.refresh_credential_cache()
        self.refresh_token_cache()

    def _parse_auth_token(self, path: str, token_str: str) -> Result[AuthToken, str]:
        """Parse token string into AuthToken object."""
        try:
            token = AuthToken(token=token_str, token_type="Bearer")
            self._token_cache[path] = token
            return self._ok(token)
        except Exception as e:
            return self._err(f"Failed to parse auth token: {str(e)}")

    def _parse_credential(self, path: str, cred_dict: Dict[str, str]) -> Result[Credential, str]:
        """Parse credential dictionary into Credential object."""
        try:
            username = cred_dict.get("username") or cred_dict.get("user")
            password = cred_dict.get("password") or cred_dict.get("pass")

            if not username or not password:
                return self._err(f"Credential missing username or password at {path}")

            credential = Credential(
                username=username,
                password=password,
                credential_type="generic",
                metadata=cred_dict,
            )
            self._credential_cache[path] = credential
            return self._ok(credential)
        except Exception as e:
            return self._err(f"Failed to parse credential: {str(e)}")

    @staticmethod
    def _ok(value):
        """Helper to create Ok result."""
        from axiompy.result import Ok

        return Ok(value)

    @staticmethod
    def _err(error):
        """Helper to create Err result."""
        from axiompy.result import Err

        return Err(error)


__all__ = [
    "SecretsClient",
    "CredentialProvider",
]
