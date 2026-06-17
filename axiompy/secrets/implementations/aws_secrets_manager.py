# @!code-style

"""
AWS Secrets Manager secret client implementation.

AWS Secrets Manager is a more general-purpose secret management service compared to KMS.
Requires boto3: pip install boto3
"""

import json
from typing import Any, Dict, List, Optional

from axiompy.loggers import LoggerFactory
from axiompy.result import Err, Ok, Result

from ..client import CredentialProvider
from ..types import AWSSecretsManagerSettings

logger = LoggerFactory.create_logger(__name__)


class AWSSecretsManagerClient(CredentialProvider):
    """
    AWS Secrets Manager secret client implementation.

    Uses AWS Secrets Manager to store and retrieve secrets.
    Supports both string secrets and JSON secrets.

    Example:
        >>> from axiompy.secrets import AWSSecretsManagerSettings
        >>> settings = AWSSecretsManagerSettings(region="us-west-2")
        >>> client = AWSSecretsManagerClient(settings)
        >>> result = client.get_secret("prod/database/mysql-password")
        >>> password = result.unwrap()
    """

    def __init__(self, settings: AWSSecretsManagerSettings):
        """
        Initialize AWS Secrets Manager client.

        Args:
            settings: AWSSecretsManagerSettings with AWS configuration

        Raises:
            ImportError: If boto3 is not installed
            RuntimeError: If client initialization fails
        """
        super().__init__()
        self.settings = settings
        logger.info(f"Initializing AWS Secrets Manager client for region: {settings.region}")

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

            self._client = boto3.client("secretsmanager", **kwargs)
            logger.info("AWS Secrets Manager client initialized successfully")

        except ImportError as e:
            raise ImportError(
                "boto3 is required for AWSSecretsManagerClient. Install it with: pip install boto3"
            ) from e
        except Exception as e:
            logger.error(f"Failed to initialize AWS Secrets Manager client: {e}")
            raise RuntimeError(f"AWS client initialization failed: {e}") from e

    def get_secret(self, secret_path: str) -> Result[str, str]:
        """
        Retrieve a single secret by name.

        Args:
            secret_path: Secret name (path) in Secrets Manager

        Returns:
            Result[str, str]: Ok(secret_value) or Err(error_message)
        """
        try:
            from botocore.exceptions import ClientError

            response = self._client.get_secret_value(SecretId=secret_path)

            # Try to get SecretString first, then SecretBinary
            if "SecretString" in response:
                secret_value = response["SecretString"]
            else:
                secret_value = response.get("SecretBinary", "")

            logger.debug(f"Retrieved secret: {secret_path}")
            return Ok(secret_value)

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ResourceNotFoundException":
                return Err(f"Secret '{secret_path}' not found in AWS Secrets Manager")
            return Err(
                f"Failed to retrieve secret '{secret_path}': {e.response['Error']['Message']}"
            )
        except Exception as e:
            error_msg = f"Failed to retrieve secret '{secret_path}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err(error_msg)

    def get_secrets(self, secret_path: str) -> Result[Dict[str, str], str]:
        """
        Retrieve a secret and parse as JSON dictionary.

        Args:
            secret_path: Secret name containing JSON data

        Returns:
            Result[Dict[str, str], str]: Ok(parsed_dict) or Err(error_message)
        """
        return self.get_secret(secret_path).then(
            lambda secret_str: self._parse_json_secret(secret_path, secret_str)
        )

    def get_secret_by_key(self, secret_path: str, key: str) -> Result[str, str]:
        """
        Retrieve a specific key from a JSON secret.

        Args:
            secret_path: Secret name containing JSON data
            key: Key within the JSON object

        Returns:
            Result[str, str]: Ok(value) or Err(error_message)
        """
        return self.get_secrets(secret_path).then(
            lambda secrets: (
                Ok(secrets[key])
                if key in secrets
                else Err(f"Key '{key}' not found in secret '{secret_path}'")
            )
        )

    def put_secret(
        self, secret_path: str, secret_value: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Result[bool, str]:
        """
        Store a secret in AWS Secrets Manager.

        Args:
            secret_path: Secret name
            secret_value: Secret value to store
            metadata: Optional metadata (tags)

        Returns:
            Result[bool, str]: Ok(True) or Err(error_message)
        """
        try:
            from botocore.exceptions import ClientError

            kwargs = {
                "Name": secret_path,
                "SecretString": secret_value,
            }

            if metadata:
                # Convert metadata to AWS tags
                tags = [{"Key": k, "Value": str(v)} for k, v in metadata.items()]
                kwargs["Tags"] = tags

            # Try to create_secret first, if it exists update with put_secret_value
            try:
                self._client.create_secret(**kwargs)
            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceExistsException":
                    # Secret exists, update with put_secret_value instead
                    self._client.put_secret_value(SecretId=secret_path, SecretString=secret_value)
                else:
                    raise

            logger.info(f"Stored secret: {secret_path}")
            return Ok(True)

        except ClientError as e:
            error_msg = f"Failed to store secret '{secret_path}': {e.response['Error']['Message']}"
            logger.error(error_msg, exc_info=True)
            return Err(error_msg)
        except Exception as e:
            error_msg = f"Failed to store secret '{secret_path}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err(error_msg)

    def put_secrets(
        self, secret_path: str, secrets: Dict[str, str], metadata: Optional[Dict[str, Any]] = None
    ) -> Result[bool, str]:
        """
        Store multiple secrets as a JSON object.

        Args:
            secret_path: Secret name for the JSON object
            secrets: Dictionary to store as JSON
            metadata: Optional metadata (tags)

        Returns:
            Result[bool, str]: Ok(True) or Err(error_message)
        """
        try:
            json_str = json.dumps(secrets)
            return self.put_secret(secret_path, json_str, metadata)
        except Exception as e:
            return Err(f"Failed to serialize secrets as JSON: {str(e)}")

    def delete_secret(self, secret_path: str) -> Result[bool, str]:
        """
        Delete a secret from AWS Secrets Manager.

        Args:
            secret_path: Secret name to delete

        Returns:
            Result[bool, str]: Ok(True) or Err(error_message)
        """
        try:
            from botocore.exceptions import ClientError

            self._client.delete_secret(
                SecretId=secret_path,
                ForceDeleteWithoutRecovery=True,
            )

            logger.info(f"Deleted secret: {secret_path}")
            return Ok(True)

        except ClientError as e:
            error_msg = f"Failed to delete secret '{secret_path}': {e.response['Error']['Message']}"
            logger.error(error_msg, exc_info=True)
            return Err(error_msg)
        except Exception as e:
            error_msg = f"Failed to delete secret '{secret_path}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err(error_msg)

    def delete_secrets(self, secret_path: str) -> Result[bool, str]:
        """
        Delete a secret (same as delete_secret for Secrets Manager).

        Args:
            secret_path: Secret name prefix (exact match only)

        Returns:
            Result[bool, str]: Ok(True) or Err(error_message)
        """
        return self.delete_secret(secret_path)

    def secret_exists(self, secret_path: str) -> Result[bool, str]:
        """
        Check if a secret exists.

        Args:
            secret_path: Secret name to check

        Returns:
            Result[bool, str]: Ok(exists) or Err(error_message)
        """
        return self.get_secret(secret_path).map(lambda _: True).or_else(lambda _: Ok(False))

    def list_secrets(self, secret_path: str) -> Result[List[str], str]:
        """
        List secrets (filters by prefix).

        Args:
            secret_path: Prefix to filter by

        Returns:
            Result[List[str], str]: Ok(secret_names) or Err(error_message)
        """
        try:
            secrets = []
            paginator = self._client.get_paginator("list_secrets")

            for page in paginator.paginate():
                for secret in page.get("SecretList", []):
                    name = secret["Name"]
                    if name.startswith(secret_path):
                        secrets.append(name)

            logger.debug(f"Listed {len(secrets)} secrets with prefix: {secret_path}")
            return Ok(secrets)

        except Exception as e:
            error_msg = f"Failed to list secrets: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err(error_msg)

    @staticmethod
    def _parse_json_secret(secret_path: str, secret_str: str) -> Result[Dict[str, str], str]:
        """Parse JSON secret string."""
        try:
            return Ok(json.loads(secret_str))
        except json.JSONDecodeError as e:
            return Err(f"Secret '{secret_path}' is not valid JSON: {str(e)}")


__all__ = [
    "AWSSecretsManagerClient",
]
