"""
Secrets and credential management module for axiompy.

Provides a unified interface for managing secrets, credentials, and authentication tokens
across multiple backends (Cerberus, AWS KMS, AWS Secrets Manager, HashiCorp Vault, Azure Key Vault).

Features:
    - Multiple secret backend support with factory pattern
    - Railway-oriented programming with Result types for error handling
    - Caching and lazy initialization
    - Unified API for authentication, secrets, and credentials
    - Support for both simple key-value secrets and complex credential objects

Quick Example:
    >>> from axiompy.secrets import SecretsClientFactory, SecretsClientType, CerberusSettings
    >>> settings = CerberusSettings(
    ...     vault_path="shared/database/mysql",
    ...     cerberus_url="https://cerberus.example.com",
    ...     cerberus_region="us-west-2"
    ... )
    >>> client = SecretsClientFactory.create(SecretsClientType.CERBERUS, settings).unwrap()
    >>> secret = client.get_secret("database_password").unwrap()
    >>> all_secrets = client.get_secrets("shared/database/").unwrap()

Supported Backends:
    - CERBERUS: Acme's centralized secret management system
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
    CerberusSettings,
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
    "CerberusSettings",
    "AWSSecretsManagerSettings",
    "AWSKMSSettings",
    "LocalSettings",
    "Credential",
    "AuthToken",
]
