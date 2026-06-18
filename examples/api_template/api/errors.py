# @!documentation

"""
Custom error hierarchy for the API.

Extends axiompy error patterns with API-specific error types.
"""

from typing import Any, Dict, Optional

from axiompy.data.error import DataProcessingError


class AxiomPyAPIError(DataProcessingError):
    """Base error for AxiomPy API."""

    def __init__(
        self,
        message: str,
        error_code: str,
        recovery_hint: Optional[str] = None,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, recovery_hint)
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON response."""
        return {
            "error": str(self),
            "error_code": self.error_code,
            "recovery_hint": self.recovery_hint,
            "details": self.details,
        }


class ValidationError(AxiomPyAPIError):
    """Request validation error."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        recovery_hint: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            recovery_hint=recovery_hint or "Check request parameters and try again",
            status_code=400,
            details={"field": field} if field else {},
        )


class ResourceNotFound(AxiomPyAPIError):
    """Resource not found error."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        recovery_hint: Optional[str] = None,
    ):
        super().__init__(
            message=f"{resource_type} '{resource_id}' not found",
            error_code="RESOURCE_NOT_FOUND",
            recovery_hint=recovery_hint or f"Verify the {resource_type.lower()} ID and try again",
            status_code=404,
            details={"resource_type": resource_type, "resource_id": resource_id},
        )


class ResourceConflict(AxiomPyAPIError):
    """Resource conflict error (e.g., duplicate)."""

    def __init__(
        self,
        resource_type: str,
        conflict_field: str,
        value: str,
        recovery_hint: Optional[str] = None,
    ):
        super().__init__(
            message=f"{resource_type} with {conflict_field}='{value}' already exists",
            error_code="RESOURCE_CONFLICT",
            recovery_hint=recovery_hint or f"Use a unique {conflict_field} value",
            status_code=409,
            details={
                "resource_type": resource_type,
                "conflict_field": conflict_field,
                "value": value,
            },
        )


class ServiceError(AxiomPyAPIError):
    """Service-level error."""

    def __init__(
        self,
        service_name: str,
        operation: str,
        message: str,
        recovery_hint: Optional[str] = None,
    ):
        super().__init__(
            message=f"{service_name}.{operation} failed: {message}",
            error_code="SERVICE_ERROR",
            recovery_hint=recovery_hint or "Contact support if the problem persists",
            status_code=500,
            details={"service": service_name, "operation": operation},
        )


class ExternalServiceError(AxiomPyAPIError):
    """External service dependency error."""

    def __init__(
        self,
        service_name: str,
        message: str,
        recovery_hint: Optional[str] = None,
    ):
        super().__init__(
            message=f"External service '{service_name}' error: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            recovery_hint=recovery_hint
            or "External service is temporarily unavailable, please try again later",
            status_code=503,
            details={"service": service_name},
        )


class RateLimitError(AxiomPyAPIError):
    """Rate limit exceeded."""

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        recovery_hint: Optional[str] = None,
    ):
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window_seconds}s",
            error_code="RATE_LIMIT_EXCEEDED",
            recovery_hint=recovery_hint or f"Wait {window_seconds} seconds before retrying",
            status_code=429,
            details={"limit": limit, "window_seconds": window_seconds},
        )
