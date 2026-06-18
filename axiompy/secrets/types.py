# @!secrets

"""
Type definitions for secrets management.

Includes enums for supported backends, dataclasses for configuration,
and models for authentication credentials.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class SecretsClientType(Enum):
    """Supported secret management backends."""

    AWS_SECRETS_MANAGER = "aws_secrets_manager"
    AWS_KMS = "aws_kms"
    LOCAL = "local"


@dataclass
class SecretsSettings:
    """
    Base settings for secret clients.

    All backend-specific settings should inherit from this class.
    """

    pass


@dataclass
class AWSSecretsManagerSettings(SecretsSettings):
    """AWS Secrets Manager configuration."""

    region: str
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    endpoint_url: Optional[str] = None


@dataclass
class AWSKMSSettings(SecretsSettings):
    """AWS KMS (Key Management Service) configuration."""

    key_id: str
    region: str
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    endpoint_url: Optional[str] = None


@dataclass
class LocalSettings(SecretsSettings):
    """
    Local .env file backend for development.

    Reads secrets from a local .env file, providing the same SecretsClient
    interface as production backends. Eliminates the split between vault-based
    secrets in production and os.environ in development.

    Attributes:
        env_file: Path to the .env file (default: ".env")
        vault_path: Kept for interface parity with other backends, not used
        case_insensitive: Store both upper and lower key variants for lookup
    """

    env_file: str = ".env"
    vault_path: str = ""
    case_insensitive: bool = True


@dataclass
class AuthToken:
    """
    Represents an authentication token.

    Attributes:
        token: The actual token value
        token_type: Type of token (e.g., "Bearer", "Basic")
        expires_at: When the token expires (optional)
        scope: Token scope/permissions (optional)
        metadata: Additional metadata about the token
    """

    token: str
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at

    def __str__(self) -> str:
        """Return formatted token string."""
        return f"{self.token_type} {self.token}" if self.token_type else self.token


@dataclass
class Credential:
    """
    Represents a credential pair (username/password or similar).

    Attributes:
        username: Username or identifier
        password: Password or secret value
        credential_type: Type of credential (e.g., "database", "api", "service_principal")
        expires_at: When the credential expires (optional)
        metadata: Additional metadata about the credential
    """

    username: str
    password: str
    credential_type: str = "generic"
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if credential is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at


__all__ = [
    "SecretsClientType",
    "SecretsSettings",
    "AWSSecretsManagerSettings",
    "AWSKMSSettings",
    "LocalSettings",
    "AuthToken",
    "Credential",
]
