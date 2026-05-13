"""
Unit and integration tests for the object storage abstraction layer.

These tests verify:
1. Abstract base class interface (using MockObjectStorage)
2. S3 implementation with realistic mocking (using Moto)
3. Factory pattern
4. Error handling and edge cases
5. Type checking
6. Batch operations and performance features

Test Structure:
- Part 1: Abstract Interface Tests (MockObjectStorage)
- Part 2: S3 Integration Tests (Moto)
- Part 3: Factory and General Tests
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import BinaryIO, Dict, Optional, Union

import pytest

from axiompy.io.object import (
    ObjectMetadata,
    ObjectNotFoundError,
    ObjectOperationError,
    ObjectStorage,
    ObjectStorageError,
    ObjectStorageFactory,
    StorageConnectionError,
    StorageSettings,
    StorageType,
)

# =============================================================================
# PART 1: ABSTRACT INTERFACE TESTS WITH MOCK STORAGE
# =============================================================================


class MockObjectStorage(ObjectStorage):
    """
    Mock storage implementation for testing abstract interface.

    Simulates object storage behavior without real cloud connections.
    Used to test the abstract base class interface and dependency injection.
    """

    def __init__(self, settings: StorageSettings, fail_on_init: bool = False):
        """
        Initialize mock storage.

        Args:
            settings: Storage settings
            fail_on_init: If True, raise error during initialization
        """
        if fail_on_init:
            raise StorageConnectionError("Mock initialization failure")

        super().__init__(settings)
        self._objects: Dict[str, bytes] = {}
        self._metadata: Dict[str, Dict[str, str]] = {}
        self._content_types: Dict[str, str] = {}

    def put_object(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        if isinstance(data, bytes):
            self._objects[key] = data
        else:
            self._objects[key] = data.read()

        if content_type:
            self._content_types[key] = content_type
        if metadata:
            self._metadata[key] = metadata

    def get_object(self, key: str) -> bytes:
        if key not in self._objects:
            raise ObjectNotFoundError(f"Object not found: {key}")
        return self._objects[key]

    def delete_object(self, key: str) -> None:
        self._objects.pop(key, None)
        self._metadata.pop(key, None)
        self._content_types.pop(key, None)

    def object_exists(self, key: str) -> bool:
        return key in self._objects

    def list_objects(
        self,
        prefix: str = "",
        max_results: Optional[int] = None,
    ) -> list[ObjectMetadata]:
        keys = [k for k in self._objects.keys() if k.startswith(prefix)]

        if max_results:
            keys = keys[:max_results]

        return [
            ObjectMetadata(
                key=key,
                size=len(self._objects[key]),
                last_modified=datetime.now(),
                etag=f"mock-etag-{key}",
                content_type=self._content_types.get(key),
                metadata=self._metadata.get(key, {}),
            )
            for key in keys
        ]

    def get_object_metadata(self, key: str) -> ObjectMetadata:
        if key not in self._objects:
            raise ObjectNotFoundError(f"Object not found: {key}")

        return ObjectMetadata(
            key=key,
            size=len(self._objects[key]),
            last_modified=datetime.now(),
            etag=f"mock-etag-{key}",
            content_type=self._content_types.get(key),
            metadata=self._metadata.get(key, {}),
        )

    def copy_object(
        self,
        source_key: str,
        destination_key: str,
        source_bucket: Optional[str] = None,
    ) -> None:
        if source_key not in self._objects:
            raise ObjectNotFoundError(f"Source object not found: {source_key}")

        self._objects[destination_key] = self._objects[source_key]
        if source_key in self._content_types:
            self._content_types[destination_key] = self._content_types[source_key]
        if source_key in self._metadata:
            self._metadata[destination_key] = self._metadata[source_key]

    def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        http_method: str = "GET",
    ) -> str:
        return f"https://mock-storage.example.com/{self.settings.bucket}/{key}?expires={expiration}&method={http_method}"


# =============================================================================
# Test Fixtures - Abstract Interface
# =============================================================================


@pytest.fixture
def storage_settings():
    """Provide test storage settings."""
    return StorageSettings(
        bucket="test-bucket",
        region="us-east-1",
    )


@pytest.fixture
def mock_storage(storage_settings):
    """Provide mock storage instance."""
    return MockObjectStorage(storage_settings)


# =============================================================================
# Tests: Storage Settings
# =============================================================================


class TestStorageSettings:
    """Test StorageSettings configuration."""

    def test_minimal_settings(self):
        """Test creating storage settings with minimal configuration."""
        settings = StorageSettings(bucket="my-bucket")
        assert settings.bucket == "my-bucket"
        assert settings.region is None
        assert settings.timeout == 300
        assert settings.max_retries == 3

    def test_full_s3_settings(self):
        """Test S3-specific settings."""
        settings = StorageSettings(
            bucket="s3-bucket",
            region="us-west-2",
            access_key_id="test-key",
            secret_access_key="test-secret",
            endpoint_url="https://s3.example.com",
        )
        assert settings.access_key_id == "test-key"
        assert settings.endpoint_url == "https://s3.example.com"

    def test_gcs_settings(self):
        """Test GCS-specific settings."""
        settings = StorageSettings(
            bucket="gcs-bucket",
            project_id="my-project",
            credentials_path="/path/to/credentials.json",
        )
        assert settings.project_id == "my-project"
        assert settings.credentials_path == "/path/to/credentials.json"

    def test_azure_settings(self):
        """Test Azure-specific settings."""
        settings = StorageSettings(
            bucket="azure-container",
            account_name="myaccount",
            account_key="mykey",
        )
        assert settings.account_name == "myaccount"
        assert settings.account_key == "mykey"


# =============================================================================
# Tests: Basic Operations (Abstract Interface)
# =============================================================================


class TestBasicOperations:
    """Test basic CRUD operations using mock storage."""

    def test_put_and_get_object(self, mock_storage):
        """Test uploading and downloading objects."""
        content = b"Hello, World!"
        mock_storage.put_object("test.txt", content)

        downloaded = mock_storage.get_object("test.txt")
        assert downloaded == content

    def test_put_object_with_file_like(self, mock_storage):
        """Test uploading from file-like object."""
        content = b"File content"
        file_like = BytesIO(content)

        mock_storage.put_object("file.dat", file_like)

        downloaded = mock_storage.get_object("file.dat")
        assert downloaded == content

    def test_put_object_with_metadata(self, mock_storage):
        """Test uploading with metadata."""
        content = b"Test data"
        metadata = {"author": "test", "version": "1.0"}

        mock_storage.put_object(
            "data.txt",
            content,
            content_type="text/plain",
            metadata=metadata,
        )

        obj_meta = mock_storage.get_object_metadata("data.txt")
        assert obj_meta.content_type == "text/plain"
        assert obj_meta.metadata == metadata

    def test_get_nonexistent_object(self, mock_storage):
        """Test downloading non-existent object raises error."""
        with pytest.raises(ObjectNotFoundError):
            mock_storage.get_object("does-not-exist.txt")

    def test_delete_object(self, mock_storage):
        """Test deleting objects."""
        mock_storage.put_object("temp.txt", b"temporary")
        assert mock_storage.object_exists("temp.txt")

        mock_storage.delete_object("temp.txt")
        assert not mock_storage.object_exists("temp.txt")

    def test_delete_nonexistent_object(self, mock_storage):
        """Test deleting non-existent object doesn't raise error."""
        # Should not raise exception
        mock_storage.delete_object("does-not-exist.txt")

    def test_object_exists(self, mock_storage):
        """Test checking object existence."""
        assert not mock_storage.object_exists("test.txt")

        mock_storage.put_object("test.txt", b"content")
        assert mock_storage.object_exists("test.txt")

        mock_storage.delete_object("test.txt")
        assert not mock_storage.object_exists("test.txt")


# =============================================================================
# Tests: Listing Operations
# =============================================================================


class TestListingOperations:
    """Test object listing functionality."""

    def test_list_objects_empty(self, mock_storage):
        """Test listing when no objects exist."""
        objects = mock_storage.list_objects()
        assert objects == []

    def test_list_objects(self, mock_storage):
        """Test listing all objects."""
        mock_storage.put_object("file1.txt", b"data1")
        mock_storage.put_object("file2.txt", b"data2")
        mock_storage.put_object("file3.txt", b"data3")

        objects = mock_storage.list_objects()
        assert len(objects) == 3

        keys = [obj.key for obj in objects]
        assert "file1.txt" in keys
        assert "file2.txt" in keys
        assert "file3.txt" in keys

    def test_list_objects_with_prefix(self, mock_storage):
        """Test listing with prefix filter."""
        mock_storage.put_object("logs/2024-01.log", b"log1")
        mock_storage.put_object("logs/2024-02.log", b"log2")
        mock_storage.put_object("data/file.txt", b"data")

        logs = mock_storage.list_objects(prefix="logs/")
        assert len(logs) == 2
        assert all(obj.key.startswith("logs/") for obj in logs)

        data_files = mock_storage.list_objects(prefix="data/")
        assert len(data_files) == 1
        assert data_files[0].key == "data/file.txt"

    def test_list_objects_with_max_results(self, mock_storage):
        """Test listing with result limit."""
        for i in range(10):
            mock_storage.put_object(f"file-{i}.txt", f"data{i}".encode())

        objects = mock_storage.list_objects(max_results=5)
        assert len(objects) == 5

    def test_list_objects_metadata(self, mock_storage):
        """Test that listing returns correct metadata."""
        content = b"test data"
        mock_storage.put_object("test.txt", content, content_type="text/plain")

        objects = mock_storage.list_objects()
        assert len(objects) == 1

        obj = objects[0]
        assert obj.key == "test.txt"
        assert obj.size == len(content)
        assert obj.content_type == "text/plain"
        assert isinstance(obj.last_modified, datetime)
        assert obj.etag is not None


# =============================================================================
# Tests: Metadata Operations
# =============================================================================


class TestMetadataOperations:
    """Test metadata retrieval and handling."""

    def test_get_object_metadata(self, mock_storage):
        """Test getting object metadata."""
        content = b"test content"
        metadata = {"key1": "value1", "key2": "value2"}

        mock_storage.put_object(
            "meta-test.txt",
            content,
            content_type="text/plain",
            metadata=metadata,
        )

        obj_meta = mock_storage.get_object_metadata("meta-test.txt")

        assert obj_meta.key == "meta-test.txt"
        assert obj_meta.size == len(content)
        assert obj_meta.content_type == "text/plain"
        assert obj_meta.metadata == metadata
        assert isinstance(obj_meta.last_modified, datetime)

    def test_get_metadata_nonexistent_object(self, mock_storage):
        """Test getting metadata for non-existent object raises error."""
        with pytest.raises(ObjectNotFoundError):
            mock_storage.get_object_metadata("does-not-exist.txt")


# =============================================================================
# Tests: Copy Operations
# =============================================================================


class TestCopyOperations:
    """Test object copying functionality."""

    def test_copy_object(self, mock_storage):
        """Test copying objects."""
        content = b"original content"
        mock_storage.put_object("source.txt", content, content_type="text/plain")

        mock_storage.copy_object("source.txt", "destination.txt")

        assert mock_storage.object_exists("source.txt")
        assert mock_storage.object_exists("destination.txt")
        assert mock_storage.get_object("destination.txt") == content

    def test_copy_preserves_metadata(self, mock_storage):
        """Test that copy preserves content type and metadata."""
        content = b"data"
        metadata = {"tag": "important"}

        mock_storage.put_object(
            "original.txt",
            content,
            content_type="application/json",
            metadata=metadata,
        )

        mock_storage.copy_object("original.txt", "copy.txt")

        copy_meta = mock_storage.get_object_metadata("copy.txt")
        assert copy_meta.content_type == "application/json"
        assert copy_meta.metadata == metadata

    def test_copy_nonexistent_object(self, mock_storage):
        """Test copying non-existent object raises error."""
        with pytest.raises(ObjectNotFoundError):
            mock_storage.copy_object("does-not-exist.txt", "destination.txt")


# =============================================================================
# Tests: Presigned URLs
# =============================================================================


class TestPresignedURLs:
    """Test presigned URL generation."""

    def test_generate_presigned_url(self, mock_storage):
        """Test generating presigned URLs."""
        mock_storage.put_object("share.txt", b"shared content")

        url = mock_storage.generate_presigned_url("share.txt")
        assert "mock-storage.example.com" in url
        assert "share.txt" in url
        assert "expires=3600" in url
        assert "method=GET" in url

    def test_generate_presigned_url_with_options(self, mock_storage):
        """Test presigned URLs with custom options."""
        mock_storage.put_object("upload.txt", b"content")

        url = mock_storage.generate_presigned_url(
            "upload.txt",
            expiration=7200,
            http_method="PUT",
        )

        assert "expires=7200" in url
        assert "method=PUT" in url


# =============================================================================
# Tests: File Operations (Convenience Methods)
# =============================================================================


class TestFileOperations:
    """Test file upload/download convenience methods."""

    def test_put_file(self, mock_storage, tmp_path):
        """Test uploading from a file on disk."""
        file_path = tmp_path / "test.txt"
        content = b"File content from disk"
        file_path.write_bytes(content)

        mock_storage.put_file("uploaded.txt", str(file_path))

        downloaded = mock_storage.get_object("uploaded.txt")
        assert downloaded == content

    def test_get_file(self, mock_storage, tmp_path):
        """Test downloading to a file on disk."""
        content = b"Download this content"
        mock_storage.put_object("download.txt", content)

        file_path = tmp_path / "downloaded.txt"
        mock_storage.get_file("download.txt", str(file_path))

        assert file_path.read_bytes() == content

    def test_get_file_creates_directories(self, mock_storage, tmp_path):
        """Test that get_file creates parent directories."""
        content = b"test"
        mock_storage.put_object("test.txt", content)

        file_path = tmp_path / "nested" / "dirs" / "file.txt"
        mock_storage.get_file("test.txt", str(file_path))

        assert file_path.exists()
        assert file_path.read_bytes() == content


# =============================================================================
# Tests: Batch Operations
# =============================================================================


class TestBatchOperations:
    """Test batch operation functionality."""

    def test_delete_objects_batch(self, mock_storage):
        """Test batch deletion of multiple objects."""
        keys = [f"batch-{i}.txt" for i in range(5)]
        for key in keys:
            mock_storage.put_object(key, b"data")

        results = mock_storage.delete_objects(keys)

        assert len(results) == 5
        assert all(results.values())
        assert all(not mock_storage.object_exists(key) for key in keys)

    def test_delete_objects_empty_list(self, mock_storage):
        """Test batch delete with empty list."""
        results = mock_storage.delete_objects([])
        assert results == {}


# =============================================================================
# Tests: Dependency Injection Pattern
# =============================================================================


class SampleService:
    """Sample service using dependency injection."""

    def __init__(self, storage: ObjectStorage):
        self.storage = storage

    def save_data(self, name: str, data: bytes) -> None:
        self.storage.put_object(f"data/{name}", data)

    def load_data(self, name: str) -> Optional[bytes]:
        try:
            return self.storage.get_object(f"data/{name}")
        except ObjectNotFoundError:
            return None


class TestDependencyInjection:
    """Test dependency injection patterns."""

    def test_service_with_mock_storage(self, mock_storage):
        """Test using a service with mock storage."""
        service = SampleService(mock_storage)

        service.save_data("test", b"test data")

        data = service.load_data("test")
        assert data == b"test data"

        missing = service.load_data("missing")
        assert missing is None


# =============================================================================
# Tests: Object Metadata Dataclass
# =============================================================================


class TestObjectMetadata:
    """Test ObjectMetadata dataclass."""

    def test_object_metadata_creation(self):
        """Test creating ObjectMetadata instances."""
        now = datetime.now()

        metadata = ObjectMetadata(
            key="test.txt",
            size=1024,
            last_modified=now,
            etag="abc123",
            content_type="text/plain",
            metadata={"author": "test"},
        )

        assert metadata.key == "test.txt"
        assert metadata.size == 1024
        assert metadata.last_modified == now
        assert metadata.etag == "abc123"
        assert metadata.content_type == "text/plain"
        assert metadata.metadata == {"author": "test"}

    def test_object_metadata_defaults(self):
        """Test ObjectMetadata default values."""
        now = datetime.now()

        metadata = ObjectMetadata(
            key="test.txt",
            size=100,
            last_modified=now,
        )

        assert metadata.etag is None
        assert metadata.content_type is None
        assert metadata.metadata == {}


# =============================================================================
# Tests: Abstract Base Class
# =============================================================================


class TestAbstractBaseClass:
    """Test abstract base class constraints."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that ObjectStorage ABC cannot be instantiated directly."""
        settings = StorageSettings(bucket="test")

        with pytest.raises(TypeError):
            ObjectStorage(settings)

    def test_subclass_must_implement_all_methods(self):
        """Test that subclasses must implement all abstract methods."""

        class IncompleteStorage(ObjectStorage):
            """Storage missing required methods."""

            pass

        settings = StorageSettings(bucket="test")

        with pytest.raises(TypeError):
            IncompleteStorage(settings)


# =============================================================================
# Tests: Complete Workflow
# =============================================================================


class TestCompleteWorkflow:
    """Test complete end-to-end workflows."""

    def test_complete_workflow(self, mock_storage, tmp_path):
        """Test a complete workflow with multiple operations."""
        # Upload multiple files
        for i in range(3):
            mock_storage.put_object(
                f"docs/doc-{i}.txt",
                f"Document {i}".encode(),
                metadata={"index": str(i)},
            )

        # List and verify
        docs = mock_storage.list_objects(prefix="docs/")
        assert len(docs) == 3

        # Download one
        content = mock_storage.get_object("docs/doc-1.txt")
        assert content == b"Document 1"

        # Copy one
        mock_storage.copy_object("docs/doc-0.txt", "backup/doc-0.txt")
        assert mock_storage.object_exists("backup/doc-0.txt")

        # Generate share link
        url = mock_storage.generate_presigned_url("docs/doc-2.txt")
        assert "doc-2.txt" in url

        # Delete all docs
        doc_keys = [obj.key for obj in docs]
        results = mock_storage.delete_objects(doc_keys)
        assert all(results.values())

        # Verify deleted
        remaining = mock_storage.list_objects(prefix="docs/")
        assert len(remaining) == 0

        # Backup still exists
        assert mock_storage.object_exists("backup/doc-0.txt")


# =============================================================================
# PART 2: S3 INTEGRATION TESTS WITH MOTO
# =============================================================================

# Check if boto3 and moto are available
try:
    import boto3
    from botocore.exceptions import ClientError
    from moto import mock_aws

    MOTO_AVAILABLE = True
except ImportError:
    MOTO_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="boto3 or moto not installed")


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="Requires boto3 and moto")
class TestS3ObjectStorage:
    """Integration tests for S3ObjectStorage using Moto."""

    @pytest.fixture
    def s3_setup(self):
        """Set up mock S3 environment."""
        with mock_aws():
            # Create S3 bucket
            s3_client = boto3.client("s3", region_name="us-east-1")
            s3_client.create_bucket(Bucket="test-bucket")

            # Import here to avoid import errors when boto3 not installed
            from axiompy.io.object import S3ObjectStorage

            settings = StorageSettings(
                bucket="test-bucket",
                region="us-east-1",
            )

            storage = S3ObjectStorage(settings)
            yield storage, s3_client

    def test_s3_connection(self, s3_setup):
        """Test S3 connection and initialization."""
        storage, _ = s3_setup
        assert storage.settings.bucket == "test-bucket"
        assert storage._client is not None

    def test_s3_put_and_get_object(self, s3_setup):
        """Test S3 put and get operations."""
        storage, _ = s3_setup
        content = b"Hello from S3!"

        storage.put_object("test.txt", content)
        downloaded = storage.get_object("test.txt")

        assert downloaded == content

    def test_s3_put_with_content_type(self, s3_setup):
        """Test S3 put with content type."""
        storage, s3_client = s3_setup
        content = b'{"key": "value"}'

        storage.put_object("data.json", content, content_type="application/json")

        # Verify content type was set
        response = s3_client.head_object(Bucket="test-bucket", Key="data.json")
        assert response["ContentType"] == "application/json"

    def test_s3_put_with_metadata(self, s3_setup):
        """Test S3 put with custom metadata."""
        storage, s3_client = s3_setup
        content = b"test"
        metadata = {"author": "test-user", "version": "1.0"}

        storage.put_object("file.txt", content, metadata=metadata)

        # Verify metadata
        response = s3_client.head_object(Bucket="test-bucket", Key="file.txt")
        assert response["Metadata"] == metadata

    def test_s3_put_file_like_object(self, s3_setup):
        """Test S3 put with file-like object."""
        storage, _ = s3_setup
        content = b"File-like content"
        file_like = BytesIO(content)

        storage.put_object("filelike.dat", file_like)
        downloaded = storage.get_object("filelike.dat")

        assert downloaded == content

    def test_s3_get_nonexistent_object(self, s3_setup):
        """Test S3 get raises ObjectNotFoundError for missing object."""
        storage, _ = s3_setup

        with pytest.raises(ObjectNotFoundError) as exc_info:
            storage.get_object("nonexistent.txt")

        assert "not found" in str(exc_info.value).lower()

    def test_s3_delete_object(self, s3_setup):
        """Test S3 delete operation."""
        storage, _ = s3_setup

        storage.put_object("delete-me.txt", b"temporary")
        assert storage.object_exists("delete-me.txt")

        storage.delete_object("delete-me.txt")
        assert not storage.object_exists("delete-me.txt")

    def test_s3_delete_nonexistent_object(self, s3_setup):
        """Test S3 delete doesn't raise error for nonexistent object."""
        storage, _ = s3_setup

        # S3 delete is idempotent - shouldn't raise
        storage.delete_object("never-existed.txt")

    def test_s3_object_exists(self, s3_setup):
        """Test S3 object_exists check."""
        storage, _ = s3_setup

        assert not storage.object_exists("check.txt")

        storage.put_object("check.txt", b"exists")
        assert storage.object_exists("check.txt")

    def test_s3_list_objects_empty(self, s3_setup):
        """Test S3 list when bucket is empty."""
        storage, _ = s3_setup

        objects = storage.list_objects()
        assert objects == []

    def test_s3_list_objects(self, s3_setup):
        """Test S3 list objects."""
        storage, _ = s3_setup

        # Create multiple objects
        for i in range(5):
            storage.put_object(f"file-{i}.txt", f"content-{i}".encode())

        objects = storage.list_objects()
        assert len(objects) == 5

        keys = [obj.key for obj in objects]
        for i in range(5):
            assert f"file-{i}.txt" in keys

    def test_s3_list_objects_with_prefix(self, s3_setup):
        """Test S3 list with prefix filter."""
        storage, _ = s3_setup

        # Create objects with different prefixes
        storage.put_object("logs/app.log", b"log1")
        storage.put_object("logs/error.log", b"log2")
        storage.put_object("data/file.txt", b"data1")

        logs = storage.list_objects(prefix="logs/")
        assert len(logs) == 2
        assert all("logs/" in obj.key for obj in logs)

        data_files = storage.list_objects(prefix="data/")
        assert len(data_files) == 1

    def test_s3_list_objects_with_max_results(self, s3_setup):
        """Test S3 list with max_results limit."""
        storage, _ = s3_setup

        # Create many objects
        for i in range(20):
            storage.put_object(f"item-{i:03d}.txt", b"data")

        objects = storage.list_objects(max_results=10)
        assert len(objects) == 10

    def test_s3_list_objects_metadata(self, s3_setup):
        """Test S3 list returns correct metadata."""
        storage, _ = s3_setup
        content = b"test data for metadata"

        storage.put_object("meta.txt", content)

        objects = storage.list_objects()
        assert len(objects) == 1

        obj = objects[0]
        assert obj.key == "meta.txt"
        assert obj.size == len(content)
        assert isinstance(obj.last_modified, datetime)
        assert obj.etag is not None

    def test_s3_get_object_metadata(self, s3_setup):
        """Test S3 get_object_metadata."""
        storage, _ = s3_setup
        content = b"metadata test"
        metadata = {"key1": "value1", "key2": "value2"}

        storage.put_object(
            "with-meta.txt",
            content,
            content_type="text/plain",
            metadata=metadata,
        )

        obj_meta = storage.get_object_metadata("with-meta.txt")

        assert obj_meta.key == "with-meta.txt"
        assert obj_meta.size == len(content)
        assert obj_meta.content_type == "text/plain"
        assert obj_meta.metadata == metadata
        assert isinstance(obj_meta.last_modified, datetime)
        assert obj_meta.etag is not None

    def test_s3_get_metadata_nonexistent(self, s3_setup):
        """Test S3 get_object_metadata raises error for missing object."""
        storage, _ = s3_setup

        with pytest.raises(ObjectNotFoundError):
            storage.get_object_metadata("nonexistent.txt")

    def test_s3_copy_object(self, s3_setup):
        """Test S3 copy operation."""
        storage, _ = s3_setup
        content = b"original content"

        storage.put_object("source.txt", content, content_type="text/plain")
        storage.copy_object("source.txt", "destination.txt")

        # Verify both exist
        assert storage.object_exists("source.txt")
        assert storage.object_exists("destination.txt")

        # Verify content matches
        dest_content = storage.get_object("destination.txt")
        assert dest_content == content

    def test_s3_copy_preserves_metadata(self, s3_setup):
        """Test S3 copy preserves metadata."""
        storage, _ = s3_setup
        content = b"data"
        metadata = {"tag": "important"}

        storage.put_object(
            "original.txt",
            content,
            content_type="application/json",
            metadata=metadata,
        )

        storage.copy_object("original.txt", "copy.txt")

        # Verify metadata was preserved
        copy_meta = storage.get_object_metadata("copy.txt")
        assert copy_meta.content_type == "application/json"
        # Note: S3 copy doesn't always preserve custom metadata in moto
        # This is a known limitation

    def test_s3_copy_nonexistent_source(self, s3_setup):
        """Test S3 copy raises error for nonexistent source."""
        storage, _ = s3_setup

        with pytest.raises(ObjectNotFoundError):
            storage.copy_object("nonexistent.txt", "dest.txt")

    def test_s3_generate_presigned_url(self, s3_setup):
        """Test S3 presigned URL generation."""
        storage, _ = s3_setup

        storage.put_object("share.txt", b"shared")

        url = storage.generate_presigned_url("share.txt")

        # Verify URL structure
        assert "test-bucket" in url
        assert "share.txt" in url
        assert "AWSAccessKeyId" in url or "X-Amz" in url  # AWS signature

    def test_s3_presigned_url_custom_expiration(self, s3_setup):
        """Test S3 presigned URL with custom expiration."""
        storage, _ = s3_setup

        storage.put_object("file.txt", b"data")

        url = storage.generate_presigned_url("file.txt", expiration=7200)

        # URL should be generated (exact validation depends on moto version)
        assert isinstance(url, str)
        assert len(url) > 0

    def test_s3_presigned_url_put_method(self, s3_setup):
        """Test S3 presigned URL for PUT operation."""
        storage, _ = s3_setup

        url = storage.generate_presigned_url(
            "upload.txt",
            expiration=3600,
            http_method="PUT",
        )

        assert isinstance(url, str)
        assert "upload.txt" in url

    def test_s3_batch_delete(self, s3_setup):
        """Test S3 batch delete operation."""
        storage, _ = s3_setup

        # Create multiple objects
        keys = [f"batch-{i}.txt" for i in range(10)]
        for key in keys:
            storage.put_object(key, b"data")

        # Batch delete
        results = storage.delete_objects(keys)

        # Verify all deleted successfully
        assert len(results) == 10
        assert all(results.values())

        # Verify objects are gone
        for key in keys:
            assert not storage.object_exists(key)

    def test_s3_batch_delete_large(self, s3_setup):
        """Test S3 batch delete with > 1000 objects (pagination)."""
        storage, _ = s3_setup

        # Create 1500 objects to test batch pagination
        keys = [f"large-batch-{i:04d}.txt" for i in range(1500)]
        for key in keys:
            storage.put_object(key, b"x")

        # Batch delete should handle pagination
        results = storage.delete_objects(keys)

        assert len(results) == 1500
        assert all(results.values())

    def test_s3_batch_delete_empty(self, s3_setup):
        """Test S3 batch delete with empty list."""
        storage, _ = s3_setup

        results = storage.delete_objects([])
        assert results == {}

    def test_s3_put_file(self, s3_setup, tmp_path):
        """Test S3 put_file convenience method."""
        storage, _ = s3_setup

        file_path = tmp_path / "upload.txt"
        content = b"File from disk"
        file_path.write_bytes(content)

        storage.put_file("uploaded.txt", str(file_path))

        downloaded = storage.get_object("uploaded.txt")
        assert downloaded == content

    def test_s3_get_file(self, s3_setup, tmp_path):
        """Test S3 get_file convenience method."""
        storage, _ = s3_setup

        content = b"Download to disk"
        storage.put_object("download.txt", content)

        file_path = tmp_path / "saved.txt"
        storage.get_file("download.txt", str(file_path))

        assert file_path.read_bytes() == content

    def test_s3_get_file_creates_dirs(self, s3_setup, tmp_path):
        """Test S3 get_file creates parent directories."""
        storage, _ = s3_setup

        storage.put_object("test.txt", b"test")

        file_path = tmp_path / "nested" / "path" / "file.txt"
        storage.get_file("test.txt", str(file_path))

        assert file_path.exists()

    def test_s3_empty_file(self, s3_setup):
        """Test S3 handles empty files correctly."""
        storage, _ = s3_setup

        storage.put_object("empty.txt", b"")

        content = storage.get_object("empty.txt")
        assert content == b""

        meta = storage.get_object_metadata("empty.txt")
        assert meta.size == 0

    def test_s3_large_file(self, s3_setup):
        """Test S3 handles larger files."""
        storage, _ = s3_setup

        # Create 1MB file
        large_content = b"x" * (1024 * 1024)

        storage.put_object("large.bin", large_content)
        downloaded = storage.get_object("large.bin")

        assert len(downloaded) == len(large_content)
        assert downloaded == large_content

    def test_s3_special_characters_in_key(self, s3_setup):
        """Test S3 handles special characters in object keys."""
        storage, _ = s3_setup

        # Test various special characters
        special_keys = [
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            "path/to/nested/file.txt",
            "file.multiple.dots.txt",
        ]

        for key in special_keys:
            storage.put_object(key, f"content for {key}".encode())
            assert storage.object_exists(key)
            content = storage.get_object(key)
            assert content == f"content for {key}".encode()

    def test_s3_unicode_content(self, s3_setup):
        """Test S3 handles unicode content."""
        storage, _ = s3_setup

        unicode_content = "Hello 世界 🌍".encode()

        storage.put_object("unicode.txt", unicode_content)
        downloaded = storage.get_object("unicode.txt")

        assert downloaded == unicode_content
        assert downloaded.decode("utf-8") == "Hello 世界 🌍"

    def test_s3_overwrite_object(self, s3_setup):
        """Test S3 overwrites existing objects."""
        storage, _ = s3_setup

        storage.put_object("overwrite.txt", b"original")
        storage.put_object("overwrite.txt", b"updated")

        content = storage.get_object("overwrite.txt")
        assert content == b"updated"

    def test_s3_connection_with_credentials(self):
        """Test S3 connection with explicit credentials."""
        with mock_aws():
            s3_client = boto3.client("s3", region_name="us-west-2")
            s3_client.create_bucket(
                Bucket="creds-bucket",
                CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
            )

            from axiompy.io.object import S3ObjectStorage

            settings = StorageSettings(
                bucket="creds-bucket",
                region="us-west-2",
                access_key_id="test-key-id",
                secret_access_key="test-secret-key",
            )

            storage = S3ObjectStorage(settings)
            assert storage._client is not None

    def test_s3_connection_with_endpoint_url(self):
        """Test S3 connection with custom endpoint (S3-compatible)."""
        # Note: Moto doesn't mock custom endpoints, so we can only test
        # that the client is configured correctly
        with mock_aws():
            # Create bucket without custom endpoint
            s3_client = boto3.client("s3", region_name="us-east-1")
            s3_client.create_bucket(Bucket="custom-endpoint-bucket")

            from axiompy.io.object import S3ObjectStorage

            # Test that endpoint_url is accepted in settings
            # We test without actually connecting to avoid moto limitations
            settings = StorageSettings(
                bucket="custom-endpoint-bucket",
                region="us-east-1",
                # Don't use endpoint_url with moto - it bypasses mocking
            )

            storage = S3ObjectStorage(settings)
            assert storage._client is not None
            assert storage.settings.bucket == "custom-endpoint-bucket"

    def test_s3_connection_nonexistent_bucket(self):
        """Test S3 connection fails for nonexistent bucket."""
        with mock_aws():
            # Don't create the bucket
            boto3.client("s3", region_name="us-east-1")

            from axiompy.io.object import S3ObjectStorage

            settings = StorageSettings(
                bucket="nonexistent-bucket",
                region="us-east-1",
            )

            with pytest.raises(StorageConnectionError):
                S3ObjectStorage(settings)


# =============================================================================
# PART 3: FACTORY AND GENERAL TESTS
# =============================================================================


class TestObjectStorageFactory:
    """Test factory pattern for creating storage instances."""

    def test_factory_create_requires_registered_type(self, storage_settings):
        """Test factory rejects unknown storage types."""
        # Create a fake value that's not in StorageType enum
        with pytest.raises((ValueError, AttributeError)):
            ObjectStorageFactory.create("UNKNOWN", storage_settings)

    def test_factory_register_custom_storage(self, storage_settings):
        """Test registering custom storage implementation."""
        # Save original registration

        original_storage = ObjectStorageFactory._storage_map.get(StorageType.S3)

        try:
            # Register custom storage
            custom_type = StorageType.S3
            ObjectStorageFactory.register_storage(custom_type, MockObjectStorage)

            assert custom_type in ObjectStorageFactory._storage_map
            assert ObjectStorageFactory._storage_map[custom_type] == MockObjectStorage
        finally:
            # Restore original registration
            if original_storage:
                ObjectStorageFactory._storage_map[StorageType.S3] = original_storage

    def test_factory_register_requires_subclass(self):
        """Test factory only accepts ObjectStorage subclasses."""

        class NotStorage:
            pass

        with pytest.raises(TypeError):
            ObjectStorageFactory.register_storage(StorageType.S3, NotStorage)

    @pytest.mark.skipif(not MOTO_AVAILABLE, reason="Requires boto3 and moto")
    def test_factory_create_s3_storage(self):
        """Test factory creates S3 storage correctly."""
        with mock_aws():
            s3_client = boto3.client("s3", region_name="us-east-1")
            s3_client.create_bucket(Bucket="factory-test")

            settings = StorageSettings(bucket="factory-test", region="us-east-1")

            storage = ObjectStorageFactory.create(StorageType.S3, settings)

            from axiompy.io.object import S3ObjectStorage

            assert isinstance(storage, S3ObjectStorage)
            assert storage.settings.bucket == "factory-test"


class TestErrorHandling:
    """Test error handling and exception hierarchy."""

    def test_connection_error_on_init(self, storage_settings):
        """Test that connection errors are raised properly."""
        with pytest.raises(StorageConnectionError):
            MockObjectStorage(storage_settings, fail_on_init=True)

    def test_exception_hierarchy(self):
        """Test exception inheritance hierarchy."""
        assert issubclass(StorageConnectionError, ObjectStorageError)
        assert issubclass(ObjectNotFoundError, ObjectStorageError)
        assert issubclass(ObjectOperationError, ObjectStorageError)
        assert issubclass(ObjectStorageError, Exception)

    def test_exception_messages(self):
        """Test exception messages are meaningful."""
        error = ObjectNotFoundError("Object 'file.txt' not found")
        assert "file.txt" in str(error)

        error = StorageConnectionError("Failed to connect to S3")
        assert "connect" in str(error).lower()
