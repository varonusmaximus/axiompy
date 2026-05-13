"""
Examples demonstrating the object storage abstraction layer.

This file shows how to use the ObjectStorage interface with different cloud providers
(AWS S3, Google Cloud Storage, Azure Blob Storage).

The examples demonstrate:
1. Basic operations (upload, download, delete)
2. Listing and metadata operations
3. Advanced features (copy, presigned URLs)
4. Dependency injection for testing
5. Error handling patterns
"""

import logging
from typing import Optional

from axiompy.io.object import (
    ObjectNotFoundError,
    ObjectStorage,
    ObjectStorageError,
    ObjectStorageFactory,
    StorageConnectionError,
    StorageSettings,
    StorageType,
)

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# Example 1: Basic S3 Usage
# =============================================================================


def example_s3_basic():
    """Basic S3 operations - upload, download, delete."""
    print("\n" + "=" * 70)
    print("Example 1: Basic S3 Operations")
    print("=" * 70)

    # Configure S3 storage
    settings = StorageSettings(
        bucket="my-app-bucket",
        region="us-east-1",
        access_key_id="YOUR_ACCESS_KEY",  # Or use IAM roles
        secret_access_key="YOUR_SECRET_KEY",
    )

    try:
        # Create S3 storage instance
        storage = ObjectStorageFactory.create(StorageType.S3, settings)

        # Upload a file
        content = b"Hello from S3!"
        storage.put_object("documents/hello.txt", content, content_type="text/plain")
        print("✓ Uploaded file to S3")

        # Download the file
        downloaded = storage.get_object("documents/hello.txt")
        print(f"✓ Downloaded file: {downloaded.decode()}")

        # Check if file exists
        exists = storage.object_exists("documents/hello.txt")
        print(f"✓ File exists: {exists}")

        # Delete the file
        storage.delete_object("documents/hello.txt")
        print("✓ Deleted file from S3")

    except StorageConnectionError as e:
        print(f"✗ Failed to connect to S3: {e}")
    except ObjectStorageError as e:
        print(f"✗ Storage operation failed: {e}")


# =============================================================================
# Example 2: Google Cloud Storage Usage
# =============================================================================


def example_gcs_with_credentials():
    """GCS operations using service account credentials."""
    print("\n" + "=" * 70)
    print("Example 2: Google Cloud Storage with Service Account")
    print("=" * 70)

    # Configure GCS storage
    settings = StorageSettings(
        bucket="my-gcs-bucket",
        project_id="my-project-id",
        credentials_path="/path/to/service-account.json",
    )

    try:
        # Create GCS storage instance
        storage = ObjectStorageFactory.create(StorageType.GCS, settings)

        # Upload with metadata
        content = b"Data for GCS"
        metadata = {
            "author": "user123",
            "version": "1.0",
        }
        storage.put_object(
            "data/report.txt",
            content,
            content_type="text/plain",
            metadata=metadata,
        )
        print("✓ Uploaded file to GCS with metadata")

        # Get metadata without downloading
        obj_metadata = storage.get_object_metadata("data/report.txt")
        print(f"✓ File size: {obj_metadata.size} bytes")
        print(f"✓ Last modified: {obj_metadata.last_modified}")
        print(f"✓ Custom metadata: {obj_metadata.metadata}")

    except StorageConnectionError as e:
        print(f"✗ Failed to connect to GCS: {e}")
    except ObjectStorageError as e:
        print(f"✗ Storage operation failed: {e}")


# =============================================================================
# Example 3: Azure Blob Storage Usage
# =============================================================================


def example_azure_basic():
    """Azure Blob Storage operations."""
    print("\n" + "=" * 70)
    print("Example 3: Azure Blob Storage Operations")
    print("=" * 70)

    # Option 1: Using connection string
    settings = StorageSettings(
        bucket="my-container",  # Container name in Azure
        connection_string="DefaultEndpointsProtocol=https;AccountName=...",
    )

    # Option 2: Using account name and key
    # settings = StorageSettings(
    #     bucket="my-container",
    #     account_name="mystorageaccount",
    #     account_key="YOUR_ACCOUNT_KEY",
    # )

    try:
        # Create Azure storage instance
        storage = ObjectStorageFactory.create(StorageType.AZURE, settings)

        # Upload from file
        # storage.put_file("images/photo.jpg", "/local/path/photo.jpg")
        # print("✓ Uploaded file from disk to Azure")

        # Download to file
        # storage.get_file("images/photo.jpg", "/local/path/downloaded.jpg")
        # print("✓ Downloaded file from Azure to disk")

        print("✓ Azure storage initialized successfully")

    except StorageConnectionError as e:
        print(f"✗ Failed to connect to Azure: {e}")
    except ObjectStorageError as e:
        print(f"✗ Storage operation failed: {e}")


# =============================================================================
# Example 4: Listing and Searching Objects
# =============================================================================


def example_listing_objects(storage: ObjectStorage):
    """List and search for objects in storage."""
    print("\n" + "=" * 70)
    print("Example 4: Listing Objects")
    print("=" * 70)

    try:
        # Upload some test files
        for i in range(5):
            storage.put_object(f"logs/2024-01-{i:02d}.log", f"Log data {i}".encode())

        # List all objects in logs/ directory
        objects = storage.list_objects(prefix="logs/")
        print(f"\n✓ Found {len(objects)} log files:")
        for obj in objects:
            print(f"  - {obj.key} ({obj.size} bytes, modified {obj.last_modified})")

        # List with limit
        recent_logs = storage.list_objects(prefix="logs/", max_results=3)
        print(f"\n✓ Most recent 3 logs: {[obj.key for obj in recent_logs]}")

    except ObjectStorageError as e:
        print(f"✗ Failed to list objects: {e}")


# =============================================================================
# Example 5: Copy and Move Operations
# =============================================================================


def example_copy_operations(storage: ObjectStorage):
    """Copy objects within or between buckets."""
    print("\n" + "=" * 70)
    print("Example 5: Copy Operations")
    print("=" * 70)

    try:
        # Upload original file
        storage.put_object("original/data.json", b'{"status": "active"}')
        print("✓ Uploaded original file")

        # Copy within same bucket
        storage.copy_object("original/data.json", "backup/data.json")
        print("✓ Copied file to backup location")

        # Verify copy exists
        if storage.object_exists("backup/data.json"):
            print("✓ Backup copy verified")

        # To move: copy then delete
        storage.copy_object("original/data.json", "archive/data.json")
        storage.delete_object("original/data.json")
        print("✓ Moved file to archive")

    except ObjectStorageError as e:
        print(f"✗ Copy operation failed: {e}")


# =============================================================================
# Example 6: Presigned URLs for Temporary Access
# =============================================================================


def example_presigned_urls(storage: ObjectStorage):
    """Generate temporary URLs for sharing files."""
    print("\n" + "=" * 70)
    print("Example 6: Presigned URLs")
    print("=" * 70)

    try:
        # Upload a file to share
        storage.put_object("shared/document.pdf", b"PDF content here")

        # Generate URL for downloading (valid for 1 hour)
        download_url = storage.generate_presigned_url(
            "shared/document.pdf",
            expiration=3600,
            http_method="GET",
        )
        print(f"✓ Download URL (valid 1 hour):\n  {download_url[:100]}...")

        # Generate URL for uploading (valid for 15 minutes)
        upload_url = storage.generate_presigned_url(
            "uploads/new-file.txt",
            expiration=900,
            http_method="PUT",
        )
        print(f"✓ Upload URL (valid 15 min):\n  {upload_url[:100]}...")

    except ObjectStorageError as e:
        print(f"✗ Failed to generate presigned URL: {e}")


# =============================================================================
# Example 7: Batch Delete Operations
# =============================================================================


def example_batch_delete(storage: ObjectStorage):
    """Delete multiple objects efficiently."""
    print("\n" + "=" * 70)
    print("Example 7: Batch Delete")
    print("=" * 70)

    try:
        # Upload multiple files
        test_keys = [f"temp/file-{i}.txt" for i in range(10)]
        for key in test_keys:
            storage.put_object(key, b"temporary data")
        print(f"✓ Created {len(test_keys)} temporary files")

        # Delete all at once
        results = storage.delete_objects(test_keys)

        successful = sum(1 for success in results.values() if success)
        print(f"✓ Deleted {successful}/{len(test_keys)} files")

        # Show any failures
        failures = [key for key, success in results.items() if not success]
        if failures:
            print(f"✗ Failed to delete: {failures}")

    except ObjectStorageError as e:
        print(f"✗ Batch delete failed: {e}")


# =============================================================================
# Example 8: Error Handling Patterns
# =============================================================================


def example_error_handling(storage: ObjectStorage):
    """Demonstrate proper error handling."""
    print("\n" + "=" * 70)
    print("Example 8: Error Handling")
    print("=" * 70)

    # Try to download non-existent file
    try:
        storage.get_object("does-not-exist.txt")
    except ObjectNotFoundError:
        print("✓ Correctly handled missing file")
    except ObjectStorageError as e:
        print(f"✗ Unexpected storage error: {e}")

    # Safe check before operations
    key = "maybe-exists.txt"
    if storage.object_exists(key):
        data = storage.get_object(key)
        print(f"✓ File exists, downloaded {len(data)} bytes")
    else:
        print("✓ File doesn't exist, skipping download")

    # Graceful fallback
    try:
        data = storage.get_object("config.json")
    except ObjectNotFoundError:
        # Use default configuration
        data = b'{"default": true}'
        print("✓ Using default config (file not found)")


# =============================================================================
# Example 9: Dependency Injection for Testing
# =============================================================================


class DocumentService:
    """Service that uses object storage via dependency injection."""

    def __init__(self, storage: ObjectStorage):
        """
        Initialize service with storage backend.

        This design allows easy testing with mock storage implementations.
        """
        self.storage = storage

    def save_document(self, doc_id: str, content: bytes) -> None:
        """Save a document to storage."""
        key = f"documents/{doc_id}.pdf"
        self.storage.put_object(
            key,
            content,
            content_type="application/pdf",
            metadata={"doc_id": doc_id},
        )
        logger.info(f"Saved document: {doc_id}")

    def get_document(self, doc_id: str) -> Optional[bytes]:
        """Retrieve a document from storage."""
        key = f"documents/{doc_id}.pdf"
        try:
            return self.storage.get_object(key)
        except ObjectNotFoundError:
            logger.warning(f"Document not found: {doc_id}")
            return None

    def list_documents(self) -> list[str]:
        """List all available documents."""
        objects = self.storage.list_objects(prefix="documents/")
        return [obj.key for obj in objects]

    def generate_share_link(self, doc_id: str, hours: int = 24) -> str:
        """Generate a temporary download link."""
        key = f"documents/{doc_id}.pdf"
        return self.storage.generate_presigned_url(
            key,
            expiration=hours * 3600,
            http_method="GET",
        )


def example_dependency_injection():
    """Use the service with real storage."""
    print("\n" + "=" * 70)
    print("Example 9: Dependency Injection Pattern")
    print("=" * 70)

    # Production: Use real storage
    settings = StorageSettings(
        bucket="my-documents",
        region="us-east-1",
    )

    try:
        storage = ObjectStorageFactory.create(StorageType.S3, settings)
        service = DocumentService(storage)

        # Use the service
        # service.save_document("report-2024", b"PDF content here")
        # doc = service.get_document("report-2024")
        # link = service.generate_share_link("report-2024", hours=48)

        print("✓ Service initialized with S3 storage")
        print("  This same service can be tested with a mock storage implementation")

    except StorageConnectionError as e:
        print(f"✗ Failed to initialize service: {e}")


# =============================================================================
# Example 10: Mock Storage for Testing
# =============================================================================


class MockObjectStorage(ObjectStorage):
    """
    Mock storage implementation for unit testing.

    This allows testing business logic without real cloud connections.
    """

    def __init__(self, settings: StorageSettings):
        super().__init__(settings)
        self._objects = {}  # In-memory storage

    def put_object(self, key: str, data, content_type=None, metadata=None) -> None:
        if isinstance(data, bytes):
            self._objects[key] = data
        else:
            self._objects[key] = data.read()

    def get_object(self, key: str) -> bytes:
        if key not in self._objects:
            raise ObjectNotFoundError(f"Mock object not found: {key}")
        return self._objects[key]

    def delete_object(self, key: str) -> None:
        self._objects.pop(key, None)

    def object_exists(self, key: str) -> bool:
        return key in self._objects

    def list_objects(self, prefix: str = "", max_results: Optional[int] = None):
        from datetime import datetime

        from axiompy.io.object import ObjectMetadata

        keys = [k for k in self._objects.keys() if k.startswith(prefix)]
        if max_results:
            keys = keys[:max_results]

        return [
            ObjectMetadata(
                key=key,
                size=len(self._objects[key]),
                last_modified=datetime.now(),
            )
            for key in keys
        ]

    def get_object_metadata(self, key: str):
        from datetime import datetime

        from axiompy.io.object import ObjectMetadata

        if key not in self._objects:
            raise ObjectNotFoundError(f"Mock object not found: {key}")

        return ObjectMetadata(
            key=key,
            size=len(self._objects[key]),
            last_modified=datetime.now(),
        )

    def copy_object(self, source_key: str, destination_key: str, source_bucket=None) -> None:
        if source_key not in self._objects:
            raise ObjectNotFoundError(f"Mock source not found: {source_key}")
        self._objects[destination_key] = self._objects[source_key]

    def generate_presigned_url(
        self, key: str, expiration: int = 3600, http_method: str = "GET"
    ) -> str:
        return f"https://mock-storage.example.com/{self.settings.bucket}/{key}?expires={expiration}"


def example_testing_with_mock():
    """Test the DocumentService with mock storage."""
    print("\n" + "=" * 70)
    print("Example 10: Testing with Mock Storage")
    print("=" * 70)

    # Create mock storage (no real cloud connection)
    mock_storage = MockObjectStorage(StorageSettings(bucket="test-bucket"))

    # Use the same service with mock storage
    service = DocumentService(mock_storage)

    # Test save operation
    service.save_document("test-doc", b"Test PDF content")
    print("✓ Saved document to mock storage")

    # Test retrieve operation
    content = service.get_document("test-doc")
    assert content == b"Test PDF content"
    print("✓ Retrieved document from mock storage")

    # Test list operation
    docs = service.list_documents()
    assert "documents/test-doc.pdf" in docs
    print(f"✓ Listed documents: {docs}")

    # Test share link generation
    link = service.generate_share_link("test-doc")
    print(f"✓ Generated mock share link: {link}")

    # Test non-existent document
    missing = service.get_document("does-not-exist")
    assert missing is None
    print("✓ Correctly handled missing document")

    print("\n✓ All tests passed! No real cloud storage needed.")


# =============================================================================
# Main Runner
# =============================================================================


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("OBJECT STORAGE EXAMPLES")
    print("=" * 70)
    print("\nThese examples demonstrate the ObjectStorage abstraction layer.")
    print("Most examples are commented out to avoid requiring real credentials.")
    print("Uncomment and configure with your credentials to try them.\n")

    # Basic examples (commented out - require real credentials)
    # example_s3_basic()
    # example_gcs_with_credentials()
    # example_azure_basic()

    # Examples that work with any storage instance
    # (Uncomment after setting up storage above)
    # settings = StorageSettings(bucket="my-bucket", region="us-east-1")
    # storage = ObjectStorageFactory.create(StorageType.S3, settings)
    # example_listing_objects(storage)
    # example_copy_operations(storage)
    # example_presigned_urls(storage)
    # example_batch_delete(storage)
    # example_error_handling(storage)

    # Dependency injection pattern
    example_dependency_injection()

    # Testing with mocks (always works - no credentials needed!)
    example_testing_with_mock()

    print("\n" + "=" * 70)
    print("Examples complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
