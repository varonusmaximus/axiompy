# @!documentation

"""
HTTP Request and Response models (Pydantic adapters).

This module contains HTTP-layer models that serve as adapters between HTTP requests/responses
and domain entities. These models are Pydantic-based for FastAPI integration and automatic
validation.

Models include:
- Domain adapters (ResourceModel): Convert to/from domain entities via from_domain()/to_domain()
- Response wrappers: Error responses, list responses
- Pagination parameters
"""

from typing import TYPE_CHECKING, Any, List, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from services.domain import Resource


class ErrorDetail(BaseModel):
    """Error response detail."""

    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Machine-readable error code")
    recovery_hint: Optional[str] = Field(None, description="Suggestion for recovery")
    details: Optional[dict] = Field(None, description="Additional error details")


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Check timestamp")
    message: str = Field(..., description="Health message")
    uptime_seconds: Optional[float] = Field(None, description="Seconds since API startup")


class ResourceModel(BaseModel):
    """
    HTTP adapter for Resource domain entity.

    This is the HTTP representation sent to/from clients.
    Includes adapter methods (from_domain/to_domain) to convert between
    HTTP representation and domain entity.

    Note: No business validation here (just type hints).
    Business validation happens in the service layer.
    """

    id: Optional[int] = Field(None, description="Unique resource ID (auto-generated)")
    name: str = Field(..., description="Resource name")
    description: Optional[str] = Field(None, description="Resource description")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    @classmethod
    def from_domain(cls, resource: "Resource") -> "ResourceModel":
        """
        Convert domain entity to HTTP representation.

        Args:
            resource: Resource domain entity

        Returns:
            ResourceModel (HTTP representation)
        """
        return cls(
            id=resource.id,
            name=resource.name,
            description=resource.description,
            created_at=resource.created_at,
            updated_at=resource.updated_at,
        )

    def to_domain(self) -> "Resource":
        """
        Convert HTTP representation to domain entity.

        Args:
            self: HTTP model instance

        Returns:
            Resource domain entity
        """
        from services.domain import Resource

        return Resource(
            id=self.id,
            name=self.name,
            description=self.description,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class ResourceListResponse(BaseModel):
    """List of resources with pagination."""

    items: List[ResourceModel] = Field(..., description="List of resources")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total pages")


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    page: int = Field(1, ge=1, description="Page number (1-based)")
    per_page: int = Field(10, ge=1, le=100, description="Items per page")


class OperationResponse(BaseModel):
    """Generic operation response."""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation message")
    data: Optional[Any] = Field(None, description="Operation result data")
