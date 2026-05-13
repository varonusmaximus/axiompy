"""
Repository layer - Data access abstraction.

This module provides the data access layer for resources. It abstracts database operations
and works with dictionaries (not domain entities). The repository is database-agnostic
and can work with any axiompy Database implementation.

Responsibilities:
- CRUD operations on resources
- Schema management (table creation)
- Timestamp management (created_at, updated_at)
- Input validation using axiompy validators
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from axiompy.io.database import Database, DatabaseQueryError
from axiompy.loggers import LoggerFactory
from axiompy.validators import ensure_not_none, ensure_positive, ensure_type

logger = LoggerFactory.create_logger(__name__)


class ResourceRepository:
    """
    Data access layer for resources.

    Handles all database operations using the axiompy Database abstraction.
    Works with dictionaries (pure data access layer - no domain logic).

    This layer is database-agnostic and can work with SQLite, PostgreSQL, MySQL, or DynamoDB.
    """

    def __init__(self, database: Database):
        """
        Initialize repository with database connection.

        Args:
            database: Database instance from axiompy DatabaseFactory

        Raises:
            ValueError: If database is None or invalid type
        """
        ensure_not_none(database, "Database instance cannot be None")
        ensure_type(database, Database, "Database must be a Database instance")

        self.db = database
        self._ensure_schema()
        logger.info("ResourceRepository initialized")

    def _ensure_schema(self) -> None:
        """
        Create resources table if it doesn't exist.

        Called during initialization to ensure the table is ready.
        Safe to call multiple times.
        """
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """
        try:
            self.db.execute(create_table_sql)
            logger.info("Resources table schema verified")
        except DatabaseQueryError as e:
            logger.error(f"Failed to create resources table: {str(e)}")
            raise

    def create(self, data: Dict[str, Any]) -> int:
        """
        Create a new resource.

        Args:
            data: Dictionary with resource fields (name, description, etc.)

        Returns:
            ID of the created resource

        Raises:
            ValueError: If data is invalid
            DatabaseQueryError: If database operation fails
        """
        ensure_not_none(data, "Resource data cannot be None")
        ensure_type(data, dict, "Resource data must be a dictionary")

        now = datetime.utcnow().isoformat()
        resource_data = {**data, "created_at": now, "updated_at": now}
        # Remove None id if present (should be auto-generated)
        resource_data.pop("id", None)

        try:
            resource_id = self.db.set("resources", resource_data)
            logger.info(f"Created resource: {resource_id}")
            return resource_id
        except DatabaseQueryError as e:
            logger.error(f"Failed to create resource: {str(e)}")
            raise

    def get_by_id(self, resource_id: int) -> Optional[Dict[str, Any]]:
        """
        Get resource by ID.

        Args:
            resource_id: Resource unique identifier

        Returns:
            Resource data dictionary or None if not found

        Raises:
            ValueError: If resource_id is invalid
        """
        ensure_not_none(resource_id, "Resource ID cannot be None")
        ensure_type(resource_id, int, "Resource ID must be an integer")
        ensure_positive(resource_id, f"Resource ID must be positive, got {resource_id}")

        try:
            resource = self.db.get("resources", resource_id)
            if resource:
                logger.debug(f"Retrieved resource: {resource_id}")
            return resource
        except DatabaseQueryError as e:
            logger.error(f"Failed to get resource {resource_id}: {str(e)}")
            raise

    def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all resources.

        Returns:
            List of resource data dictionaries

        Raises:
            DatabaseQueryError: If database operation fails
        """
        try:
            resources = self.db.get_all("resources")
            logger.debug(f"Retrieved {len(resources)} resources")
            return resources
        except DatabaseQueryError as e:
            logger.error(f"Failed to get all resources: {str(e)}")
            raise

    def update(self, resource_id: int, data: Dict[str, Any]) -> int:
        """
        Update an existing resource.

        Args:
            resource_id: Resource unique identifier
            data: Fields to update (name, description, etc.)

        Returns:
            Number of rows affected

        Raises:
            ValueError: If parameters are invalid
            DatabaseQueryError: If database operation fails
        """
        ensure_not_none(resource_id, "Resource ID cannot be None")
        ensure_type(resource_id, int, "Resource ID must be an integer")
        ensure_positive(resource_id, f"Resource ID must be positive, got {resource_id}")
        ensure_not_none(data, "Update data cannot be None")
        ensure_type(data, dict, "Update data must be a dictionary")

        update_data = {**data, "updated_at": datetime.utcnow().isoformat()}
        # Remove id and created_at from update data
        update_data.pop("id", None)
        update_data.pop("created_at", None)

        try:
            affected = self.db.update("resources", resource_id, update_data)
            logger.info(f"Updated resource {resource_id}: {affected} rows")
            return affected
        except DatabaseQueryError as e:
            logger.error(f"Failed to update resource {resource_id}: {str(e)}")
            raise

    def delete(self, resource_id: int) -> int:
        """
        Delete a resource by ID.

        Args:
            resource_id: Resource unique identifier

        Returns:
            Number of rows affected

        Raises:
            ValueError: If resource_id is invalid
            DatabaseQueryError: If database operation fails
        """
        ensure_not_none(resource_id, "Resource ID cannot be None")
        ensure_type(resource_id, int, "Resource ID must be an integer")
        ensure_positive(resource_id, f"Resource ID must be positive, got {resource_id}")

        try:
            affected = self.db.delete("resources", resource_id)
            logger.info(f"Deleted resource {resource_id}: {affected} rows")
            return affected
        except DatabaseQueryError as e:
            logger.error(f"Failed to delete resource {resource_id}: {str(e)}")
            raise

    def exists(self, resource_id: int) -> bool:
        """
        Check if a resource exists.

        Args:
            resource_id: Resource unique identifier

        Returns:
            True if resource exists, False otherwise
        """
        try:
            return self.get_by_id(resource_id) is not None
        except (DatabaseQueryError, ValueError):
            return False
