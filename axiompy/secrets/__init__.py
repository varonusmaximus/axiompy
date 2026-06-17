# @!code-style

"""
Secrets and credential management module for axiompy.

Provides a unified interface for managing secrets, credentials, and authentication tokens
across multiple backends (AWS KMS, AWS Secrets Manager, local `.env`, and other vault-style systems).

Features:
    - Multiple secret backend support with factory pattern
    - Railway-oriented programming with Result types for error handling
    - Caching and lazy initialization
    - Unified API for authentication, secrets, and credentials
    - Support for both simple key-value secrets and complex credential objects

Quick Example:
    >>> from axiompy.secrets import LocalSettings, SecretsClientFactory, SecretsClientType
    >>> settings = LocalSettings(env_file=".env")
    >>> client = SecretsClientFactory.create(SecretsClientType.LOCAL, settings).unwrap()
    >>> secret = client.get_secret("database_password").unwrap()
    >>> all_secrets = client.get_secrets("").unwrap()

Supported Backends:
    - AWS_SECRETS_MANAGER: AWS Secrets Manager
    - AWS_KMS: AWS Key Management Service (encryption)
    - LOCAL: Local .env file backend for development

For comprehensive documentation, see:
    - axiompy/secrets/README.md - Complete guide
    - axiompy/secrets/client.py - Abstract client interface
    - axiompy/secrets/implementations/ - Backend implementations
"""

from .client import CredentialProvider, SecretsClient
from .factory import SecretsClientFactory
from .types import (
    AuthToken,
    AWSKMSSettings,
    AWSSecretsManagerSettings,
    Credential,
    LocalSettings,
    SecretsClientType,
    SecretsSettings,
)

__all__ = [
    # Clients
    "SecretsClient",
    "CredentialProvider",
    # Factory
    "SecretsClientFactory",
    # Types and Enums
    "SecretsClientType",
    "SecretsSettings",
    "AWSSecretsManagerSettings",
    "AWSKMSSettings",
    "LocalSettings",
    "Credential",
    "AuthToken",
]
