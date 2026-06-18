# @!documentation

"""
Service layer - Business logic for resources.

This module contains the ResourceService which orchestrates business logic,
validates business rules, and coordinates with the repository layer.

Responsibilities:
- Define and enforce business rules
- Validate domain entities
- Orchestrate repository operations
- Return domain entities (not dicts)

Pattern: Service is standalone (not inheriting from a base class).
Each domain gets its own service with custom business logic.
"""

from typing import List, Optional

from axiompy.decorators import LogAndRethrow
from axiompy.loggers import LoggerFactory
from axiompy.validators import ensure_length, ensure_not_empty, ensure_positive
from services.domain import Resource
from services.repository import ResourceRepository

logger = LoggerFactory.create_logger(__name__)


class ResourceService:
    """
    Business logic for resources.

    Orchestrates resource operations with business validation.
    Works with domain entities (Resource) and coordinates with repository (data access).

    This layer is responsible for:
    - Business rule validation
    - Domain entity manipulation
    - Repository coordination
    - Returning domain entities
    """

    def __init__(self, repository: ResourceRepository):
        """
        Initialize service with repository.

        Args:
            repository: ResourceRepository instance for data access
        """
        self.repository = repository
        logger.info("ResourceService initialized")

    @LogAndRethrow(logger)
    def create_resource(self, resource: Resource) -> Resource:
        """
        Create a new resource with business validation.

        Business Rules:
        - Name must not be empty
        - Name must be 1-255 characters
        - Description (if provided) must be <= 500 characters

        Args:
            resource: Resource domain entity to create

        Returns:
            Created Resource with generated ID and timestamps

        Raises:
            ValueError: If business validation fails (logged automatically by @LogAndRethrow)
        """
        logger.debug(f"Creating resource: {resource.name}")

        # Validate business rules
        ensure_not_empty(resource.name, "Resource name cannot be empty")
        ensure_length(
            resource.name,
            min_length=1,
            max_length=255,
            message="Resource name must be 1-255 characters",
        )

        if resource.description:
            ensure_length(
                resource.description,
                max_length=500,
                message="Resource description must not exceed 500 characters",
            )

        # Persist (convert domain to dict)
        resource_dict = resource.to_dict()
        resource_id = self.repository.create(resource_dict)

        # Retrieve and convert back to domain
        created_dict = self.repository.get_by_id(resource_id)
        if not created_dict:
            raise ValueError(f"Failed to retrieve created resource: {resource_id}")

        created_resource = Resource.from_dict(created_dict)
        logger.info(f"Created resource: {created_resource.id}")
        return created_resource

    def get_resource(self, resource_id: int) -> Optional[Resource]:
        """
        Get resource by ID.

        Args:
            resource_id: Resource unique identifier

        Returns:
            Resource if found, None otherwise

        Raises:
            ValueError: If resource_id is invalid
        """
        ensure_not_empty(resource_id, "Resource ID cannot be empty")
        ensure_positive(resource_id, "Resource ID must be positive")

        logger.debug(f"Getting resource: {resource_id}")

        resource_dict = self.repository.get_by_id(resource_id)
        if not resource_dict:
            logger.debug(f"Resource not found: {resource_id}")
            return None

        return Resource.from_dict(resource_dict)

    def list_resources(self) -> List[Resource]:
        """
        List all resources.

        Returns:
            List of Resource entities
        """
        logger.debug("Listing all resources")

        resource_dicts = self.repository.get_all()
        resources = [Resource.from_dict(d) for d in resource_dicts]

        logger.info(f"Listed {len(resources)} resources")
        return resources

    @LogAndRethrow(logger)
    def update_resource(self, resource_id: int, resource: Resource) -> Optional[Resource]:
        """
        Update an existing resource.

        Business Rules:
        - Resource must exist
        - Name must not be empty
        - Name must be 1-255 characters

        Args:
            resource_id: Resource unique identifier
            resource: Updated Resource entity

        Returns:
            Updated Resource if successful, None if not found

        Raises:
            ValueError: If business validation fails (logged automatically by @LogAndRethrow)
        """
        ensure_not_empty(resource_id, "Resource ID cannot be empty")
        ensure_positive(resource_id, "Resource ID must be positive")

        logger.debug(f"Updating resource: {resource_id}")

        # Check if resource exists
        if not self.repository.exists(resource_id):
            logger.warning(f"Resource not found for update: {resource_id}")
            return None

        # Validate business rules
        if resource.name:
            ensure_not_empty(resource.name, "Resource name cannot be empty")
            ensure_length(
                resource.name,
                min_length=1,
                max_length=255,
                message="Resource name must be 1-255 characters",
            )

        if resource.description:
            ensure_length(
                resource.description,
                max_length=500,
                message="Resource description must not exceed 500 characters",
            )

        # Update (convert domain to dict, excluding id and created_at)
        update_data = {"name": resource.name, "description": resource.description}
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}

        self.repository.update(resource_id, update_data)

        # Retrieve and convert back to domain
        updated_dict = self.repository.get_by_id(resource_id)
        if not updated_dict:
            raise ValueError(f"Failed to retrieve updated resource: {resource_id}")

        updated_resource = Resource.from_dict(updated_dict)
        logger.info(f"Updated resource: {resource_id}")
        return updated_resource

    def delete_resource(self, resource_id: int) -> bool:
        """
        Delete a resource.

        Args:
            resource_id: Resource unique identifier

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If resource_id is invalid
        """
        ensure_not_empty(resource_id, "Resource ID cannot be empty")
        ensure_positive(resource_id, "Resource ID must be positive")

        logger.debug(f"Deleting resource: {resource_id}")

        affected = self.repository.delete(resource_id)
        success = affected > 0

        if success:
            logger.info(f"Deleted resource: {resource_id}")
        else:
            logger.warning(f"Resource not found for delete: {resource_id}")

        return success
