"""
Factory for creating secret clients.

Implements the factory pattern to instantiate appropriate secret clients
based on the configured backend type.
"""

from __future__ import annotations

from typing import Type

from axiompy.loggers import LoggerFactory
from axiompy.result import Err, Ok, Result

from .client import SecretsClient
from .types import SecretsClientType, SecretsSettings

logger = LoggerFactory.create_logger(__name__)


class SecretsClientFactory:
    """
    Factory for creating secret clients using the factory pattern.

    Supports multiple backends and provides a unified way to instantiate clients
    with appropriate error handling.

    Example:
        >>> from axiompy.secrets import LocalSettings, SecretsClientFactory, SecretsClientType
        >>> settings = LocalSettings(env_file=".env")
        >>> result = SecretsClientFactory.create(SecretsClientType.LOCAL, settings)
        >>> client = result.unwrap()  # Or handle error with result.map_error()
    """

    # Registry of available client implementations
    _IMPLEMENTATIONS: dict[SecretsClientType, Type[SecretsClient]] = {}

    @classmethod
    def create(
        cls, client_type: SecretsClientType, settings: SecretsSettings
    ) -> Result[SecretsClient, str]:
        """
        Create a secret client of the specified type.

        Args:
            client_type: Type of secret client to create
            settings: Configuration settings for the client

        Returns:
            Result[SecretClient, str]: Ok(client) or Err(error_message)

        Example:
            >>> from axiompy.secrets import LocalSettings, SecretsClientFactory, SecretsClientType
            >>> settings = LocalSettings(env_file=".env")
            >>> client_result = SecretsClientFactory.create(SecretsClientType.LOCAL, settings)
            >>> client = client_result.unwrap()
        """
        try:
            if client_type not in cls._IMPLEMENTATIONS:
                return Err(
                    f"Unsupported secret client type: {client_type.value}. "
                    f"Available types: {[t.value for t in cls._IMPLEMENTATIONS]}"
                )

            implementation = cls._IMPLEMENTATIONS[client_type]
            client = implementation(settings)

            logger.info(
                f"Created {client_type.value} secret client with settings: "
                f"{settings.__class__.__name__}"
            )
            return Ok(client)

        except Exception as e:
            error_msg = f"Failed to create {client_type.value} secret client: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err(error_msg)


# Auto-register implementations
def _register_implementations():
    """Auto-register all available implementations."""
    try:
        from .implementations.aws_secrets_manager import AWSSecretsManagerClient

        SecretsClientFactory._IMPLEMENTATIONS[SecretsClientType.AWS_SECRETS_MANAGER] = (
            AWSSecretsManagerClient
        )
        logger.debug("Registered AWSSecretsManagerClient")
    except ImportError:
        logger.debug("AWSSecretsManagerClient not available (boto3 not installed)")

    try:
        from .implementations.aws_kms import AWSKMSSecretClient

        SecretsClientFactory._IMPLEMENTATIONS[SecretsClientType.AWS_KMS] = AWSKMSSecretClient
        logger.debug("Registered AWSKMSSecretClient")
    except ImportError:
        logger.debug("AWSKMSSecretClient not available (boto3 not installed)")

    try:
        from .implementations.local import LocalSecretClient

        SecretsClientFactory._IMPLEMENTATIONS[SecretsClientType.LOCAL] = LocalSecretClient
        logger.debug("Registered LocalSecretClient")
    except ImportError:
        logger.debug("LocalSecretClient not available")


# Register implementations when module is imported
_register_implementations()


__all__ = [
    "SecretsClientFactory",
]
