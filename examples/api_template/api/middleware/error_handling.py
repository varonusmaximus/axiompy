"""Framework-agnostic error handling utilities.

Error handling is implemented at the handler level using:
1. @CatchAndLog decorators for exception management
2. ErrorHandler utility for consistent error formatting
3. (dict, status_code) tuples returned from handlers

This approach works with any Server implementation (FastAPI, Flask, etc.)
and keeps the template framework-independent.
"""

from typing import Any, Dict, Optional

from axiompy.loggers import LoggerFactory

logger = LoggerFactory.create_logger(__name__)


class ErrorHandler:
    """
    Framework-agnostic error handler utility.

    Provides common error handling patterns that work regardless of the
    underlying framework (FastAPI, Flask, etc.).

    All error handling uses @CatchAndLog decorators at the handler level
    and returns (error_dict, status_code) tuples.
    """

    @staticmethod
    def format_error(
        error: str,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
        recovery_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Format error response consistently across all handlers.

        Args:
            error: Error message
            error_code: Machine-readable error code
            details: Additional error details
            recovery_hint: Suggestion for recovery

        Returns:
            Formatted error response dict
        """
        response = {
            "error": error,
            "error_code": error_code,
        }

        if recovery_hint:
            response["recovery_hint"] = recovery_hint

        if details:
            response["details"] = details

        return response

    @staticmethod
    def handle_validation_error(field: str, message: str) -> Dict[str, Any]:
        """
        Handle validation errors.

        Args:
            field: Field that failed validation
            message: Error message

        Returns:
            Formatted validation error response
        """
        return ErrorHandler.format_error(
            error="Validation failed",
            error_code="VALIDATION_ERROR",
            details={"field": field, "message": message},
            recovery_hint="Check the field value and try again",
        )

    @staticmethod
    def handle_not_found(resource_type: str, resource_id: Any) -> Dict[str, Any]:
        """
        Handle resource not found errors.

        Args:
            resource_type: Type of resource (e.g., 'Resource', 'User')
            resource_id: ID of the resource

        Returns:
            Formatted not found error response
        """
        return ErrorHandler.format_error(
            error=f"{resource_type} {resource_id} not found",
            error_code="RESOURCE_NOT_FOUND",
            recovery_hint=f"Check that the {resource_type.lower()} ID is valid and exists",
        )

    @staticmethod
    def handle_internal_error(message: str = "Internal server error") -> Dict[str, Any]:
        """
        Handle unexpected internal errors.

        Args:
            message: Error message

        Returns:
            Formatted internal error response
        """
        return ErrorHandler.format_error(
            error=message,
            error_code="INTERNAL_SERVER_ERROR",
            recovery_hint="Contact support if the problem persists",
        )
