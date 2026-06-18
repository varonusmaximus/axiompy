# @!secrets

"""
AWS KMS (Key Management Service) secret client implementation.

AWS KMS is primarily for encryption/decryption operations.
Secrets are typically stored elsewhere and encrypted with KMS.
Requires boto3: pip install boto3
"""

import base64
from typing import Any, Dict, List, Optional

from axiompy.loggers import LoggerFactory
from axiompy.result import Err, Ok, Result

from ..client import SecretsClient
from ..types import AWSKMSSettings

logger = LoggerFactory.create_logger(__name__)


class AWSKMSSecretClient(SecretsClient):
    """
    AWS KMS secret client implementation.

    Primarily used for encryption/decryption operations.
    For storing secrets, use AWSSecretsManagerClient instead.

    Example:
        >>> from axiompy.secrets import AWSKMSSettings
        >>> settings = AWSKMSSettings(key_id="arn:aws:kms:...", region="us-west-2")
        >>> client = AWSKMSSecretClient(settings)
        >>> plaintext = "my-secret-value"
        >>> encrypted = client.encrypt(plaintext).unwrap()
        >>> decrypted = client.decrypt(encrypted).unwrap()
    """

    def __init__(self, settings: AWSKMSSettings):
        """
        Initialize AWS KMS client.

        Args:
            settings: AWSKMSSettings with AWS configuration

        Raises:
            ImportError: If boto3 is not installed
            RuntimeError: If client initialization fails
        """
        super().__init__()
        self.settings = settings
        logger.info(f"Initializing AWS KMS client for key: {settings.key_id}")

        # Initialize client immediately - fail fast on misconfiguration
        try:
            import boto3

            kwargs = {
                "region_name": self.settings.region,
            }

            if self.settings.access_key_id:
                kwargs["aws_access_key_id"] = self.settings.access_key_id
                kwargs["aws_secret_access_key"] = self.settings.secret_access_key

            if self.settings.endpoint_url:
                kwargs["endpoint_url"] = self.settings.endpoint_url

            self._client = boto3.client("kms", **kwargs)
            logger.info("AWS KMS client initialized successfully")

        except ImportError as e:
            raise ImportError(
                "boto3 is required for AWSKMSSecretClient. Install it with: pip install boto3"
            ) from e
        except Exception as e:
            logger.error(f"Failed to initialize AWS KMS client: {e}")
            raise RuntimeError(f"AWS KMS client initialization failed: {e}") from e

    def encrypt(self, plaintext: str) -> Result[str, str]:
        """
        Encrypt plaintext using KMS.

        Args:
            plaintext: Text to encrypt

        Returns:
            Result[str, str]: Ok(base64_encoded_ciphertext) or Err(error_message)
        """
        try:
            from botocore.exceptions import ClientError

            response = self._client.encrypt(
                KeyId=self.settings.key_id,
                Plaintext=plaintext.encode("utf-8"),
            )

            ciphertext_blob = response["CiphertextBlob"]
            ciphertext_b64 = base64.b64encode(ciphertext_blob).decode("utf-8")

            logger.debug("Encrypted plaintext using KMS")
            return Ok(ciphertext_b64)

        except ClientError as e:
            error_msg = f"Failed to encrypt with KMS: {e.response['Error']['Message']}"
            logger.error(error_msg, exc_info=True)
            return Err(error_msg)
        except Exception as e:
            error_msg = f"Failed to encrypt: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err(error_msg)

    def decrypt(self, ciphertext_b64: str) -> Result[str, str]:
        """
        Decrypt KMS-encrypted ciphertext.

        Args:
            ciphertext_b64: Base64-encoded ciphertext from encrypt()

        Returns:
            Result[str, str]: Ok(plaintext) or Err(error_message)
        """
        try:
            from botocore.exceptions import ClientError

            ciphertext_blob = base64.b64decode(ciphertext_b64)

            response = self._client.decrypt(CiphertextBlob=ciphertext_blob)

            plaintext = response["Plaintext"].decode("utf-8")

            logger.debug("Decrypted ciphertext using KMS")
            return Ok(plaintext)

        except ClientError as e:
            error_msg = f"Failed to decrypt with KMS: {e.response['Error']['Message']}"
            logger.error(error_msg, exc_info=True)
            return Err(error_msg)
        except Exception as e:
            error_msg = f"Failed to decrypt: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err(error_msg)

    # SecretClient abstract methods (not typically used for KMS)

    def get_secret(self, secret_path: str) -> Result[str, str]:
        """AWS KMS is for encryption, not secret storage."""
        return Err(
            "AWS KMS is for encryption/decryption only. "
            "Use AWSSecretsManagerClient for secret storage."
        )

    def get_secrets(self, secret_path: str) -> Result[Dict[str, str], str]:
        """AWS KMS is for encryption, not secret storage."""
        return Err(
            "AWS KMS is for encryption/decryption only. "
            "Use AWSSecretsManagerClient for secret storage."
        )

    def get_secret_by_key(self, secret_path: str, key: str) -> Result[str, str]:
        """AWS KMS is for encryption, not secret storage."""
        return Err(
            "AWS KMS is for encryption/decryption only. "
            "Use AWSSecretsManagerClient for secret storage."
        )

    def put_secret(
        self, secret_path: str, secret_value: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Result[bool, str]:
        """AWS KMS is for encryption, not secret storage."""
        return Err(
            "AWS KMS is for encryption/decryption only. "
            "Use AWSSecretsManagerClient for secret storage."
        )

    def put_secrets(
        self, secret_path: str, secrets: Dict[str, str], metadata: Optional[Dict[str, Any]] = None
    ) -> Result[bool, str]:
        """AWS KMS is for encryption, not secret storage."""
        return Err(
            "AWS KMS is for encryption/decryption only. "
            "Use AWSSecretsManagerClient for secret storage."
        )

    def delete_secret(self, secret_path: str) -> Result[bool, str]:
        """AWS KMS is for encryption, not secret storage."""
        return Err(
            "AWS KMS is for encryption/decryption only. "
            "Use AWSSecretsManagerClient for secret storage."
        )

    def delete_secrets(self, secret_path: str) -> Result[bool, str]:
        """AWS KMS is for encryption, not secret storage."""
        return Err(
            "AWS KMS is for encryption/decryption only. "
            "Use AWSSecretsManagerClient for secret storage."
        )

    def secret_exists(self, secret_path: str) -> Result[bool, str]:
        """AWS KMS is for encryption, not secret storage."""
        return Err(
            "AWS KMS is for encryption/decryption only. "
            "Use AWSSecretsManagerClient for secret storage."
        )

    def list_secrets(self, secret_path: str) -> Result[List[str], str]:
        """AWS KMS is for encryption, not secret storage."""
        return Err(
            "AWS KMS is for encryption/decryption only. "
            "Use AWSSecretsManagerClient for secret storage."
        )


__all__ = [
    "AWSKMSSecretClient",
]
