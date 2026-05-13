"""
Object storage abstraction layer with support for multiple cloud providers.

Provides a consistent interface for interacting with different object storage systems through
an abstract base class and concrete implementations. Supports AWS S3, Google Cloud Storage (GCS),
and Azure Blob Storage with automatic connection management and unified error handling.

Key Benefits:
    - Consistent API across all storage providers
    - Easy mocking for unit testing without real cloud connections
    - Dependency injection-friendly design
    - Automatic resource cleanup
    - Support for common operations: upload, download, delete, list, copy

Quick Example:
    >>> from axiompy.io.object import ObjectStorageFactory, StorageType, StorageSettings
    >>>
    >>> settings = StorageSettings(bucket="my-bucket", region="us-east-1")
    >>> storage = ObjectStorageFactory.create(StorageType.S3, settings)
    >>>
    >>> # Upload a file
    >>> storage.put_object("path/to/file.txt", b"Hello, World!")
    >>>
    >>> # Download a file
    >>> content = storage.get_object("path/to/file.txt")
    >>>
    >>> # List objects
    >>> objects = storage.list_objects(prefix="path/to/")
    >>>
    >>> # Generate presigned URL for temporary access
    >>> url = storage.generate_presigned_url("path/to/file.txt", expiration=3600)

For comprehensive examples and documentation, see axiompy/io/README.md
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Union

from axiompy.decorators import LogExecutionTime, Retry
from axiompy.loggers import LoggerFactory
from axiompy.validators import ensure_not_empty, ensure_not_none

logger = LoggerFactory.create_logger(__name__)


class StorageType(Enum):
    """Supported object storage types."""

    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"


@dataclass
class StorageSettings:
    """
    Object storage connection configuration.

    Attributes:
        bucket: Bucket/container name
        region: Cloud region (AWS/GCS)

        # AWS S3 settings
        access_key_id: AWS access key ID
        secret_access_key: AWS secret access key
        endpoint_url: Custom S3 endpoint (for S3-compatible services like MinIO)

        # GCS settings
        project_id: GCP project ID
        credentials_path: Path to GCP service account JSON file

        # Azure settings
        account_name: Azure storage account name
        account_key: Azure storage account key
        connection_string: Azure connection string (alternative to account_name/key)

        # Common settings
        timeout: Operation timeout in seconds
        max_retries: Maximum number of retry attempts
        extra_params: Additional provider-specific parameters
    """

    bucket: str
    region: Optional[str] = None

    # AWS S3
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    endpoint_url: Optional[str] = None

    # GCS
    project_id: Optional[str] = None
    credentials_path: Optional[str] = None

    # Azure
    account_name: Optional[str] = None
    account_key: Optional[str] = None
    connection_string: Optional[str] = None

    # Common
    timeout: int = 300
    max_retries: int = 3
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ObjectMetadata:
    """
    Metadata for a stored object.

    Attributes:
        key: Object key/path
        size: Size in bytes
        last_modified: Last modification timestamp
        etag: Entity tag (hash/version identifier)
        content_type: MIME type
        metadata: Additional custom metadata
    """

    key: str
    size: int
    last_modified: datetime
    etag: Optional[str] = None
    content_type: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)


class ObjectStorageError(Exception):
    """Base exception for object storage errors."""

    pass


class StorageConnectionError(ObjectStorageError):
    """Storage connection/initialization failure."""

    pass


class ObjectNotFoundError(ObjectStorageError):
    """Requested object does not exist."""

    pass


class ObjectOperationError(ObjectStorageError):
    """Object operation (upload, download, delete, etc.) failure."""

    pass


class ObjectStorage(ABC):
    """
    Abstract base class for object storage systems.

    All storage implementations provide a consistent interface for common operations:
    upload, download, delete, list, copy, and presigned URL generation.

    Connections/clients are established automatically on instantiation and cleaned up
    via __del__.

    Design Advantages:
        - Dependency Injection: Services depend on interface, not implementations
        - Easy Testing: Create simple mocks without real cloud connections
        - Swappable: Switch storage providers without changing business logic
        - Consistent: Same error types across all implementations

    Example Usage:
        >>> class DocumentService:
        ...     def __init__(self, storage: ObjectStorage):
        ...         self.storage = storage
        ...
        ...     def save_document(self, doc_id: str, content: bytes):
        ...         key = f"documents/{doc_id}.pdf"
        ...         self.storage.put_object(key, content)
        ...
        ...     def get_document(self, doc_id: str) -> bytes:
        ...         key = f"documents/{doc_id}.pdf"
        ...         return self.storage.get_object(key)

        # Works with any ObjectStorage implementation (S3, GCS, Azure, mock, etc.)
    """

    def __init__(self, settings: StorageSettings):
        """
        Initialize storage instance.

        Subclasses should establish connection in __init__ and raise
        StorageConnectionError if connection fails.

        Args:
            settings: Storage configuration

        Raises:
            StorageConnectionError: If connection fails
        """
        self.settings = settings
        self._client = None

    def __del__(self):
        """Ensure resources are cleaned up when instance is destroyed."""
        self._cleanup()

    def _cleanup(self) -> None:
        """
        Clean up storage resources.

        Subclasses should override to close connections and free resources.
        Should not raise exceptions.
        """
        pass

    @abstractmethod
    def put_object(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:  # pragma: no cover
        """
        Upload an object to storage.

        Args:
            key: Object key/path in the bucket
            data: Object data as bytes or file-like object
            content_type: MIME type of the object
            metadata: Additional metadata key-value pairs

        Raises:
            ObjectOperationError: If upload fails
        """
        pass

    @abstractmethod
    def get_object(self, key: str) -> bytes:  # pragma: no cover
        """
        Download an object from storage.

        Args:
            key: Object key/path in the bucket

        Returns:
            Object data as bytes

        Raises:
            ObjectNotFoundError: If object doesn't exist
            ObjectOperationError: If download fails
        """
        pass

    @abstractmethod
    def delete_object(self, key: str) -> None:  # pragma: no cover
        """
        Delete an object from storage.

        Args:
            key: Object key/path in the bucket

        Raises:
            ObjectOperationError: If deletion fails
        """
        pass

    @abstractmethod
    def object_exists(self, key: str) -> bool:  # pragma: no cover
        """
        Check if an object exists in storage.

        Args:
            key: Object key/path in the bucket

        Returns:
            True if object exists, False otherwise

        Raises:
            ObjectOperationError: If check fails (not for non-existence)
        """
        pass

    @abstractmethod
    def list_objects(
        self,
        prefix: str = "",
        max_results: Optional[int] = None,
    ) -> List[ObjectMetadata]:  # pragma: no cover
        """
        List objects in storage.

        Args:
            prefix: Only return objects with keys starting with this prefix
            max_results: Maximum number of results to return

        Returns:
            List of object metadata

        Raises:
            ObjectOperationError: If listing fails
        """
        pass

    @abstractmethod
    def get_object_metadata(self, key: str) -> ObjectMetadata:  # pragma: no cover
        """
        Get metadata for an object without downloading it.

        Args:
            key: Object key/path in the bucket

        Returns:
            Object metadata

        Raises:
            ObjectNotFoundError: If object doesn't exist
            ObjectOperationError: If metadata retrieval fails
        """
        pass

    @abstractmethod
    def copy_object(
        self,
        source_key: str,
        destination_key: str,
        source_bucket: Optional[str] = None,
    ) -> None:  # pragma: no cover
        """
        Copy an object within or between buckets.

        Args:
            source_key: Source object key
            destination_key: Destination object key
            source_bucket: Source bucket (if different from current bucket)

        Raises:
            ObjectNotFoundError: If source object doesn't exist
            ObjectOperationError: If copy fails
        """
        pass

    @abstractmethod
    def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        http_method: str = "GET",
    ) -> str:  # pragma: no cover
        """
        Generate a presigned URL for temporary access to an object.

        Args:
            key: Object key/path in the bucket
            expiration: URL expiration time in seconds
            http_method: HTTP method the URL will be used for (GET, PUT, etc.)

        Returns:
            Presigned URL string

        Raises:
            ObjectOperationError: If URL generation fails
        """
        pass

    def put_file(
        self,
        key: str,
        file_path: Union[str, Path],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:  # pragma: no cover
        """
        Upload a file from disk to storage.

        Convenience method that reads a file and uploads it.

        Args:
            key: Object key/path in the bucket
            file_path: Path to the file to upload
            content_type: MIME type of the object
            metadata: Additional metadata key-value pairs

        Raises:
            FileNotFoundError: If file doesn't exist
            ObjectOperationError: If upload fails
        """
        file_path = Path(file_path)
        with open(file_path, "rb") as f:
            self.put_object(key, f, content_type=content_type, metadata=metadata)
        logger.debug(f"Uploaded file {file_path} to {key}")

    def get_file(self, key: str, file_path: Union[str, Path]) -> None:
        """
        Download an object from storage to a file on disk.

        Convenience method that downloads and writes to a file.

        Args:
            key: Object key/path in the bucket
            file_path: Path where the file will be saved

        Raises:
            ObjectNotFoundError: If object doesn't exist
            ObjectOperationError: If download fails
            IOError: If file write fails
        """
        file_path = Path(file_path)
        data = self.get_object(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(data)
        logger.debug(f"Downloaded {key} to file {file_path}")

    def delete_objects(self, keys: List[str]) -> Dict[str, bool]:
        """
        Delete multiple objects from storage.

        Default implementation deletes objects one by one. Subclasses can override
        for batch deletion if the provider supports it.

        Args:
            keys: List of object keys to delete

        Returns:
            Dictionary mapping keys to success status (True/False)
        """
        results = {}
        for key in keys:
            try:
                self.delete_object(key)
                results[key] = True
                logger.debug(f"Deleted object: {key}")
            except Exception as e:
                logger.warning(f"Failed to delete {key}: {e}")
                results[key] = False
        return results


class S3ObjectStorage(ObjectStorage):
    """AWS S3 object storage implementation using boto3."""

    def __init__(self, settings: StorageSettings):
        super().__init__(settings)

        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError

            self._boto3 = boto3
            self._ClientError = ClientError
            self._BotoCoreError = BotoCoreError
        except ImportError:
            raise StorageConnectionError("AWS SDK not installed. Install with: pip install boto3")

        try:
            client_config = {
                "region_name": self.settings.region or "us-east-1",
            }

            if self.settings.access_key_id and self.settings.secret_access_key:
                client_config["aws_access_key_id"] = self.settings.access_key_id
                client_config["aws_secret_access_key"] = self.settings.secret_access_key

            if self.settings.endpoint_url:
                client_config["endpoint_url"] = self.settings.endpoint_url

            self._client = self._boto3.client("s3", **client_config)

            # Verify bucket access
            self._client.head_bucket(Bucket=self.settings.bucket)
            logger.info(f"Connected to S3 bucket: {self.settings.bucket}")

        except Exception as e:
            raise StorageConnectionError(f"Failed to connect to S3: {str(e)}")

    def _cleanup(self) -> None:
        self._client = None
        logger.debug("S3 client closed")

    @LogExecutionTime(logger, message_template="S3 put_object completed in {elapsed:.4f}s")
    @Retry(max_attempts=3, delay=1.0, backoff=2.0)
    def put_object(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        ensure_not_empty(key, "Object key cannot be empty")
        ensure_not_none(data, "Object data cannot be None")

        try:
            put_kwargs = {
                "Bucket": self.settings.bucket,
                "Key": key,
                "Body": data,
            }

            if content_type:
                put_kwargs["ContentType"] = content_type

            if metadata:
                put_kwargs["Metadata"] = metadata

            self._client.put_object(**put_kwargs)
            logger.debug(f"Uploaded object to S3: {key}")

        except Exception as e:
            raise ObjectOperationError(f"Failed to upload object to S3: {str(e)}")

    @LogExecutionTime(logger, message_template="S3 get_object completed in {elapsed:.4f}s")
    @Retry(max_attempts=3, delay=1.0, backoff=2.0)
    def get_object(self, key: str) -> bytes:
        ensure_not_empty(key, "Object key cannot be empty")

        try:
            response = self._client.get_object(
                Bucket=self.settings.bucket,
                Key=key,
            )
            data = response["Body"].read()
            logger.debug(f"Downloaded object from S3: {key}")
            return data

        except self._ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise ObjectNotFoundError(f"Object not found in S3: {key}")
            raise ObjectOperationError(f"Failed to download object from S3: {str(e)}")
        except Exception as e:
            raise ObjectOperationError(f"Failed to download object from S3: {str(e)}")

    @LogExecutionTime(logger, message_template="S3 delete_object completed in {elapsed:.4f}s")
    @Retry(max_attempts=3, delay=1.0, backoff=2.0)
    def delete_object(self, key: str) -> None:
        ensure_not_empty(key, "Object key cannot be empty")

        try:
            self._client.delete_object(
                Bucket=self.settings.bucket,
                Key=key,
            )
            logger.debug(f"Deleted object from S3: {key}")

        except Exception as e:
            raise ObjectOperationError(f"Failed to delete object from S3: {str(e)}")

    def object_exists(self, key: str) -> bool:
        try:
            self._client.head_object(
                Bucket=self.settings.bucket,
                Key=key,
            )
            return True
        except self._ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise ObjectOperationError(f"Failed to check object existence in S3: {str(e)}")
        except Exception as e:
            raise ObjectOperationError(f"Failed to check object existence in S3: {str(e)}")

    @LogExecutionTime(logger, message_template="S3 list_objects completed in {elapsed:.4f}s")
    @Retry(max_attempts=3, delay=1.0, backoff=2.0)
    def list_objects(
        self,
        prefix: str = "",
        max_results: Optional[int] = None,
    ) -> List[ObjectMetadata]:
        try:
            list_kwargs = {
                "Bucket": self.settings.bucket,
                "Prefix": prefix,
            }

            if max_results:
                list_kwargs["MaxKeys"] = max_results

            response = self._client.list_objects_v2(**list_kwargs)

            objects = []
            for obj in response.get("Contents", []):
                metadata = ObjectMetadata(
                    key=obj["Key"],
                    size=obj["Size"],
                    last_modified=obj["LastModified"],
                    etag=obj.get("ETag", "").strip('"'),
                )
                objects.append(metadata)

            logger.debug(f"Listed {len(objects)} objects from S3 with prefix: {prefix}")
            return objects

        except Exception as e:
            raise ObjectOperationError(f"Failed to list objects in S3: {str(e)}")

    def get_object_metadata(self, key: str) -> ObjectMetadata:
        try:
            response = self._client.head_object(
                Bucket=self.settings.bucket,
                Key=key,
            )

            metadata = ObjectMetadata(
                key=key,
                size=response["ContentLength"],
                last_modified=response["LastModified"],
                etag=response.get("ETag", "").strip('"'),
                content_type=response.get("ContentType"),
                metadata=response.get("Metadata", {}),
            )

            logger.debug(f"Retrieved metadata for S3 object: {key}")
            return metadata

        except self._ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise ObjectNotFoundError(f"Object not found in S3: {key}")
            raise ObjectOperationError(f"Failed to get metadata from S3: {str(e)}")
        except Exception as e:
            raise ObjectOperationError(f"Failed to get metadata from S3: {str(e)}")

    def copy_object(
        self,
        source_key: str,
        destination_key: str,
        source_bucket: Optional[str] = None,
    ) -> None:
        try:
            source_bucket = source_bucket or self.settings.bucket
            copy_source = {
                "Bucket": source_bucket,
                "Key": source_key,
            }

            self._client.copy_object(
                CopySource=copy_source,
                Bucket=self.settings.bucket,
                Key=destination_key,
            )

            logger.debug(f"Copied S3 object from {source_key} to {destination_key}")

        except self._ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise ObjectNotFoundError(f"Source object not found in S3: {source_key}")
            raise ObjectOperationError(f"Failed to copy object in S3: {str(e)}")
        except Exception as e:
            raise ObjectOperationError(f"Failed to copy object in S3: {str(e)}")

    def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        http_method: str = "GET",
    ) -> str:
        try:
            method_map = {
                "GET": "get_object",
                "PUT": "put_object",
                "DELETE": "delete_object",
            }

            client_method = method_map.get(http_method.upper(), "get_object")

            url = self._client.generate_presigned_url(
                client_method,
                Params={
                    "Bucket": self.settings.bucket,
                    "Key": key,
                },
                ExpiresIn=expiration,
            )

            logger.debug(f"Generated presigned URL for S3 object: {key}")
            return url

        except Exception as e:
            raise ObjectOperationError(f"Failed to generate presigned URL for S3: {str(e)}")

    def delete_objects(self, keys: List[str]) -> Dict[str, bool]:
        """Batch delete objects using S3's native batch API."""
        if not keys:
            return {}

        try:
            # S3 batch delete supports up to 1000 objects at a time
            results = {}
            batch_size = 1000

            for i in range(0, len(keys), batch_size):
                batch = keys[i : i + batch_size]
                delete_objects = [{"Key": key} for key in batch]

                response = self._client.delete_objects(
                    Bucket=self.settings.bucket,
                    Delete={"Objects": delete_objects},
                )

                # Mark deleted objects as successful
                for deleted in response.get("Deleted", []):
                    results[deleted["Key"]] = True

                # Mark failed objects
                for error in response.get("Errors", []):
                    results[error["Key"]] = False
                    logger.warning(
                        f"Failed to delete {error['Key']}: {error['Code']} - {error['Message']}"
                    )

                # Mark remaining batch items as successful if not in response
                for key in batch:
                    if key not in results:
                        results[key] = True

            logger.debug(f"Batch deleted {len(keys)} objects from S3")
            return results

        except Exception as e:
            logger.error(f"Batch delete failed in S3: {e}")
            # Fall back to individual deletes
            return super().delete_objects(keys)


class GCSObjectStorage(ObjectStorage):  # pragma: no cover
    """Google Cloud Storage implementation using google-cloud-storage."""

    def __init__(self, settings: StorageSettings):
        super().__init__(settings)

        try:
            from google.cloud import storage
            from google.cloud.exceptions import GoogleCloudError, NotFound

            self._storage = storage
            self._NotFound = NotFound
            self._GoogleCloudError = GoogleCloudError
        except ImportError:
            raise StorageConnectionError(
                "GCS SDK not installed. Install with: pip install google-cloud-storage"
            )

        try:
            client_kwargs = {}

            if self.settings.project_id:
                client_kwargs["project"] = self.settings.project_id

            if self.settings.credentials_path:
                from google.oauth2 import service_account

                credentials = service_account.Credentials.from_service_account_file(
                    self.settings.credentials_path
                )
                client_kwargs["credentials"] = credentials

            self._client = self._storage.Client(**client_kwargs)
            self._bucket = self._client.bucket(self.settings.bucket)

            # Verify bucket access
            if not self._bucket.exists():
                raise StorageConnectionError(f"GCS bucket does not exist: {self.settings.bucket}")

            logger.info(f"Connected to GCS bucket: {self.settings.bucket}")

        except Exception as e:
            raise StorageConnectionError(f"Failed to connect to GCS: {str(e)}")

    def _cleanup(self) -> None:
        self._client = None
        self._bucket = None
        logger.debug("GCS client closed")

    def put_object(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        try:
            blob = self._bucket.blob(key)

            if content_type:
                blob.content_type = content_type

            if metadata:
                blob.metadata = metadata

            if isinstance(data, bytes):
                blob.upload_from_string(data)
            else:
                blob.upload_from_file(data)

            logger.debug(f"Uploaded object to GCS: {key}")

        except Exception as e:
            raise ObjectOperationError(f"Failed to upload object to GCS: {str(e)}")

    def get_object(self, key: str) -> bytes:
        try:
            blob = self._bucket.blob(key)

            if not blob.exists():
                raise ObjectNotFoundError(f"Object not found in GCS: {key}")

            data = blob.download_as_bytes()
            logger.debug(f"Downloaded object from GCS: {key}")
            return data

        except ObjectNotFoundError:
            raise
        except Exception as e:
            raise ObjectOperationError(f"Failed to download object from GCS: {str(e)}")

    def delete_object(self, key: str) -> None:
        try:
            blob = self._bucket.blob(key)
            blob.delete()
            logger.debug(f"Deleted object from GCS: {key}")

        except self._NotFound:
            # GCS delete is idempotent - don't raise if object doesn't exist
            logger.debug(f"Object already deleted or doesn't exist in GCS: {key}")
        except Exception as e:
            raise ObjectOperationError(f"Failed to delete object from GCS: {str(e)}")

    def object_exists(self, key: str) -> bool:
        try:
            blob = self._bucket.blob(key)
            return blob.exists()
        except Exception as e:
            raise ObjectOperationError(f"Failed to check object existence in GCS: {str(e)}")

    def list_objects(
        self,
        prefix: str = "",
        max_results: Optional[int] = None,
    ) -> List[ObjectMetadata]:
        try:
            blobs = self._client.list_blobs(
                self._bucket,
                prefix=prefix,
                max_results=max_results,
            )

            objects = []
            for blob in blobs:
                metadata = ObjectMetadata(
                    key=blob.name,
                    size=blob.size,
                    last_modified=blob.updated,
                    etag=blob.etag,
                    content_type=blob.content_type,
                    metadata=blob.metadata or {},
                )
                objects.append(metadata)

            logger.debug(f"Listed {len(objects)} objects from GCS with prefix: {prefix}")
            return objects

        except Exception as e:
            raise ObjectOperationError(f"Failed to list objects in GCS: {str(e)}")

    def get_object_metadata(self, key: str) -> ObjectMetadata:
        try:
            blob = self._bucket.blob(key)

            if not blob.exists():
                raise ObjectNotFoundError(f"Object not found in GCS: {key}")

            blob.reload()

            metadata = ObjectMetadata(
                key=key,
                size=blob.size,
                last_modified=blob.updated,
                etag=blob.etag,
                content_type=blob.content_type,
                metadata=blob.metadata or {},
            )

            logger.debug(f"Retrieved metadata for GCS object: {key}")
            return metadata

        except ObjectNotFoundError:
            raise
        except Exception as e:
            raise ObjectOperationError(f"Failed to get metadata from GCS: {str(e)}")

    def copy_object(
        self,
        source_key: str,
        destination_key: str,
        source_bucket: Optional[str] = None,
    ) -> None:
        try:
            if source_bucket:
                source_bucket_obj = self._client.bucket(source_bucket)
            else:
                source_bucket_obj = self._bucket

            source_blob = source_bucket_obj.blob(source_key)

            if not source_blob.exists():
                raise ObjectNotFoundError(f"Source object not found in GCS: {source_key}")

            self._bucket.blob(destination_key)
            self._bucket.copy_blob(source_blob, self._bucket, destination_key)

            logger.debug(f"Copied GCS object from {source_key} to {destination_key}")

        except ObjectNotFoundError:
            raise
        except Exception as e:
            raise ObjectOperationError(f"Failed to copy object in GCS: {str(e)}")

    def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        http_method: str = "GET",
    ) -> str:
        try:
            blob = self._bucket.blob(key)

            from datetime import timedelta

            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expiration),
                method=http_method.upper(),
            )

            logger.debug(f"Generated presigned URL for GCS object: {key}")
            return url

        except Exception as e:
            raise ObjectOperationError(f"Failed to generate presigned URL for GCS: {str(e)}")


class AzureBlobStorage(ObjectStorage):  # pragma: no cover
    """Azure Blob Storage implementation using azure-storage-blob."""

    def __init__(self, settings: StorageSettings):
        super().__init__(settings)

        try:
            from azure.core.exceptions import AzureError, ResourceNotFoundError
            from azure.storage.blob import BlobClient, BlobServiceClient, ContainerClient

            self._BlobServiceClient = BlobServiceClient
            self._ResourceNotFoundError = ResourceNotFoundError
            self._AzureError = AzureError
        except ImportError:
            raise StorageConnectionError(
                "Azure SDK not installed. Install with: pip install azure-storage-blob"
            )

        try:
            if self.settings.connection_string:
                self._service_client = self._BlobServiceClient.from_connection_string(
                    self.settings.connection_string
                )
            elif self.settings.account_name and self.settings.account_key:
                account_url = f"https://{self.settings.account_name}.blob.core.windows.net"
                self._service_client = self._BlobServiceClient(
                    account_url=account_url,
                    credential=self.settings.account_key,
                )
            else:
                raise StorageConnectionError(
                    "Azure requires either connection_string or both account_name and account_key"
                )

            self._container_client = self._service_client.get_container_client(self.settings.bucket)

            # Verify container access
            if not self._container_client.exists():
                raise StorageConnectionError(
                    f"Azure container does not exist: {self.settings.bucket}"
                )

            logger.info(f"Connected to Azure Blob Storage container: {self.settings.bucket}")

        except StorageConnectionError:
            raise
        except Exception as e:
            raise StorageConnectionError(f"Failed to connect to Azure Blob Storage: {str(e)}")

    def _cleanup(self) -> None:
        self._service_client = None
        self._container_client = None
        logger.debug("Azure Blob Storage client closed")

    def put_object(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        try:
            blob_client = self._container_client.get_blob_client(key)

            upload_kwargs = {}
            if content_type:
                upload_kwargs["content_settings"] = {
                    "content_type": content_type,
                }
            if metadata:
                upload_kwargs["metadata"] = metadata

            blob_client.upload_blob(data, overwrite=True, **upload_kwargs)
            logger.debug(f"Uploaded object to Azure: {key}")

        except Exception as e:
            raise ObjectOperationError(f"Failed to upload object to Azure: {str(e)}")

    def get_object(self, key: str) -> bytes:
        try:
            blob_client = self._container_client.get_blob_client(key)
            data = blob_client.download_blob().readall()
            logger.debug(f"Downloaded object from Azure: {key}")
            return data

        except self._ResourceNotFoundError:
            raise ObjectNotFoundError(f"Object not found in Azure: {key}")
        except Exception as e:
            raise ObjectOperationError(f"Failed to download object from Azure: {str(e)}")

    def delete_object(self, key: str) -> None:
        try:
            blob_client = self._container_client.get_blob_client(key)
            blob_client.delete_blob()
            logger.debug(f"Deleted object from Azure: {key}")

        except self._ResourceNotFoundError:
            # Azure delete is idempotent - don't raise if object doesn't exist
            logger.debug(f"Object already deleted or doesn't exist in Azure: {key}")
        except Exception as e:
            raise ObjectOperationError(f"Failed to delete object from Azure: {str(e)}")

    def object_exists(self, key: str) -> bool:
        try:
            blob_client = self._container_client.get_blob_client(key)
            return blob_client.exists()
        except Exception as e:
            raise ObjectOperationError(f"Failed to check object existence in Azure: {str(e)}")

    def list_objects(
        self,
        prefix: str = "",
        max_results: Optional[int] = None,
    ) -> List[ObjectMetadata]:
        try:
            list_kwargs = {}
            if prefix:
                list_kwargs["name_starts_with"] = prefix
            if max_results:
                list_kwargs["results_per_page"] = max_results

            blobs = self._container_client.list_blobs(**list_kwargs)

            objects = []
            for blob in blobs:
                metadata = ObjectMetadata(
                    key=blob.name,
                    size=blob.size,
                    last_modified=blob.last_modified,
                    etag=blob.etag.strip('"') if blob.etag else None,
                    content_type=(
                        blob.content_settings.content_type if blob.content_settings else None
                    ),
                    metadata=blob.metadata or {},
                )
                objects.append(metadata)

                if max_results and len(objects) >= max_results:
                    break

            logger.debug(f"Listed {len(objects)} objects from Azure with prefix: {prefix}")
            return objects

        except Exception as e:
            raise ObjectOperationError(f"Failed to list objects in Azure: {str(e)}")

    def get_object_metadata(self, key: str) -> ObjectMetadata:
        try:
            blob_client = self._container_client.get_blob_client(key)
            properties = blob_client.get_blob_properties()

            metadata = ObjectMetadata(
                key=key,
                size=properties.size,
                last_modified=properties.last_modified,
                etag=properties.etag.strip('"') if properties.etag else None,
                content_type=(
                    properties.content_settings.content_type
                    if properties.content_settings
                    else None
                ),
                metadata=properties.metadata or {},
            )

            logger.debug(f"Retrieved metadata for Azure object: {key}")
            return metadata

        except self._ResourceNotFoundError:
            raise ObjectNotFoundError(f"Object not found in Azure: {key}")
        except Exception as e:
            raise ObjectOperationError(f"Failed to get metadata from Azure: {str(e)}")

    def copy_object(
        self,
        source_key: str,
        destination_key: str,
        source_bucket: Optional[str] = None,
    ) -> None:
        try:
            if source_bucket:
                source_container = self._service_client.get_container_client(source_bucket)
                source_blob = source_container.get_blob_client(source_key)
            else:
                source_blob = self._container_client.get_blob_client(source_key)

            # Check if source exists
            if not source_blob.exists():
                raise ObjectNotFoundError(f"Source object not found in Azure: {source_key}")

            destination_blob = self._container_client.get_blob_client(destination_key)
            destination_blob.start_copy_from_url(source_blob.url)

            logger.debug(f"Copied Azure object from {source_key} to {destination_key}")

        except ObjectNotFoundError:
            raise
        except Exception as e:
            raise ObjectOperationError(f"Failed to copy object in Azure: {str(e)}")

    def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        http_method: str = "GET",
    ) -> str:
        try:
            from datetime import datetime, timedelta

            from azure.storage.blob import BlobSasPermissions, generate_blob_sas

            blob_client = self._container_client.get_blob_client(key)

            # Map HTTP method to Azure permissions
            permission_map = {
                "GET": BlobSasPermissions(read=True),
                "PUT": BlobSasPermissions(write=True, create=True),
                "DELETE": BlobSasPermissions(delete=True),
            }

            permissions = permission_map.get(http_method.upper(), BlobSasPermissions(read=True))

            sas_token = generate_blob_sas(
                account_name=self.settings.account_name,
                container_name=self.settings.bucket,
                blob_name=key,
                account_key=self.settings.account_key,
                permission=permissions,
                expiry=datetime.utcnow() + timedelta(seconds=expiration),
            )

            url = f"{blob_client.url}?{sas_token}"
            logger.debug(f"Generated presigned URL for Azure object: {key}")
            return url

        except Exception as e:
            raise ObjectOperationError(f"Failed to generate presigned URL for Azure: {str(e)}")


class ObjectStorageFactory:
    """
    Factory for creating object storage instances.

    Main entry point for object storage connections. The factory automatically creates
    the appropriate storage implementation based on the specified type.

    Usage:
        >>> settings = StorageSettings(bucket="my-bucket", region="us-east-1")
        >>> storage = ObjectStorageFactory.create(StorageType.S3, settings)
        >>> storage.put_object("test.txt", b"Hello, World!")

    Testing:
        For unit tests, create mock implementations directly instead of using
        the factory:

        >>> class MockStorage(ObjectStorage):
        ...     def put_object(self, key, data, **kwargs): pass
        ...     def get_object(self, key): return b"mock data"
        ...     # ... implement other abstract methods ...
        >>>
        >>> mock = MockStorage(StorageSettings(bucket="test"))
        >>> service = DocumentService(mock)  # Inject mock directly
    """

    _storage_map = {
        StorageType.S3: S3ObjectStorage,
        StorageType.GCS: GCSObjectStorage,
        StorageType.AZURE: AzureBlobStorage,
    }

    @classmethod
    def create(cls, storage_type: StorageType, settings: StorageSettings) -> ObjectStorage:
        """
        Create an object storage instance.

        Args:
            storage_type: Type of storage to create
            settings: Configuration for the storage

        Returns:
            ObjectStorage instance

        Raises:
            ValueError: If storage type is not supported
            StorageConnectionError: If instance creation fails
        """
        if storage_type not in cls._storage_map:
            raise ValueError(
                f"Unsupported storage type: {storage_type}. "
                f"Supported: {list(cls._storage_map.keys())}"
            )

        storage_class = cls._storage_map[storage_type]
        try:
            return storage_class(settings)
        except (StorageConnectionError, ObjectOperationError):
            # Let storage-specific errors pass through unchanged
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise ObjectStorageError(f"Failed to create {storage_type.value} storage: {str(e)}")

    @classmethod
    def register_storage(cls, storage_type: StorageType, storage_class: type) -> None:
        """
        Register a custom storage implementation.

        Allows extending the factory with new storage types.

        Args:
            storage_type: Storage type enum value
            storage_class: Class implementing ObjectStorage interface

        Raises:
            TypeError: If storage_class doesn't inherit from ObjectStorage
        """
        if not issubclass(storage_class, ObjectStorage):
            raise TypeError("storage_class must inherit from ObjectStorage")

        cls._storage_map[storage_type] = storage_class
        logger.info(f"Registered custom storage: {storage_type.value}")
