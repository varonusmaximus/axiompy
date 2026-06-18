# @!io

"""
Web framework utilities for HTTP layers (framework-agnostic).

Provides railway-oriented programming (ROP) helpers for:
- Input validation with Result[T, E] returns
- Error handling and conversion to HTTP responses
- Generic adapter patterns for HTTP layers
- Pagination utilities
- Framework-agnostic error formatting
"""

from typing import Any, Callable, Dict, List, Optional, TypeVar

from pydantic import BaseModel, ValidationError

from axiompy.loggers import LoggerFactory
from axiompy.result import Err, Ok, Result

T = TypeVar("T")
E = TypeVar("E")

logger = LoggerFactory.create_logger(__name__)


class HttpResponseError(Exception):
    """Framework-agnostic HTTP error with status code and JSON-serializable detail."""

    def __init__(self, status_code: int, detail: dict[str, Any]) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class ResultValidator:
    """
    Generic result-based validators that return Result[T, str] instead of raising exceptions.

    Designed to be used with .map() and .then() for composable error handling chains.
    All validators catch exceptions and convert them to Err results for automatic
    short-circuiting in Result pipelines.
    """

    @staticmethod
    def parse_model(data: Dict[str, Any], model_class: type) -> Result:
        """
        Parse and validate HTTP input using a Pydantic model.

        Args:
            data: Raw HTTP request data (dict)
            model_class: Pydantic model class to validate against

        Returns:
            Result[model_instance, str]:
            - Ok(model) if validation succeeds
            - Err(message) if validation fails
        """
        try:
            model = model_class(**data)
            return Ok(model)
        except ValidationError as e:
            return Err(f"Validation error: {e.error_count()} field(s) failed")
        except Exception as e:
            return Err(f"Invalid request: {str(e)}")

    @staticmethod
    def validate_pagination(page: int, per_page: int) -> Result[tuple, str]:
        """
        Validate pagination parameters.

        Args:
            page: Page number (must be >= 1)
            per_page: Items per page (must be between 1 and max_per_page)

        Returns:
            Result[tuple, str]:
            - Ok((page, per_page)) if valid
            - Err(message) if invalid
        """
        try:
            from axiompy.validators import ensure_in_range, ensure_positive

            ensure_positive(page, "Page must be positive")
            ensure_in_range(
                per_page,
                min_value=1,
                max_value=100,
                message="Items per page must be between 1 and 100",
            )
            return Ok((page, per_page))
        except Exception as e:
            return Err(str(e))

    @staticmethod
    def validate_id(resource_id: int, field_name: str = "ID") -> Result[int, str]:
        """
        Validate a resource ID.

        Args:
            resource_id: The ID to validate
            field_name: Name of field for error message

        Returns:
            Result[int, str]:
            - Ok(resource_id) if valid
            - Err(message) if invalid
        """
        try:
            from axiompy.validators import ensure_not_empty

            ensure_not_empty(resource_id, f"{field_name} cannot be empty")
            return Ok(resource_id)
        except Exception as e:
            return Err(str(e))

    @staticmethod
    def validate_required(value: Any, field_name: str) -> Result[Any, str]:
        """
        Validate that a value is not None or empty.

        Args:
            value: The value to validate
            field_name: Name of field for error message

        Returns:
            Result[Any, str]:
            - Ok(value) if not empty
            - Err(message) if empty/None
        """
        try:
            from axiompy.validators import ensure_not_empty

            ensure_not_empty(value, f"{field_name} cannot be empty")
            return Ok(value)
        except Exception as e:
            return Err(str(e))


class ResultConverter:
    """
    Generic converters for working with Results in HTTP layers.

    Bridges between service layer (which may return None) and Result-based
    composition for elegant error handling.
    """

    @staticmethod
    def or_not_found(
        value: Optional[T], resource_type: str = "Resource", resource_id: Any = None
    ) -> Result[T, str]:
        """
        Convert a potentially None value to Result[T, str].

        Use when service returns None to indicate "not found".
        Converts to Err track so pipeline short-circuits properly.

        Args:
            value: The value (Resource or None)
            resource_type: Type name for error message (e.g., "Resource", "User")
            resource_id: Optional ID for better error message

        Returns:
            Result[T, str]:
            - Ok(value) if not None
            - Err(message) if None
        """
        if value is None:
            if resource_id:
                return Err(f"{resource_type} {resource_id} not found")
            return Err(f"{resource_type} not found")
        return Ok(value)

    @staticmethod
    def or_empty_list(value: Optional[List[T]]) -> Result[List[T], str]:
        """
        Convert a potentially None list to Result.

        Args:
            value: The list (or None)

        Returns:
            Result[List[T], str]:
            - Ok(value) if not None
            - Ok([]) if None
        """
        if value is None:
            return Ok([])
        return Ok(value)


class ResultErrorHandler:
    """
    Generic error handling for Results in HTTP layers.

    Converts Result errors to HTTP response errors with appropriate status codes
    and error formatting.
    """

    @staticmethod
    def handle_error(result: Result, default_status: int = 400) -> None:
        """
        Handle error result by raising HttpResponseError.

        Determines status code and error formatting based on error message.
        Call this when result.is_err() to raise the appropriate HTTP error.

        Args:
            result: The Result in error state
            default_status: Default status code for non-specific errors

        Raises:
            HttpResponseError: With appropriate status code and formatted error detail
        """
        error = result.get_error()
        logger.warning(f"HTTP error: {error}")

        # Determine status code based on error type
        if "not found" in error.lower():
            status_code = 404
            error_code = "NOT_FOUND"
        elif "validation" in error.lower():
            status_code = 400
            error_code = "VALIDATION_ERROR"
        elif "conflict" in error.lower() or "already exists" in error.lower():
            status_code = 409
            error_code = "CONFLICT"
        else:
            status_code = default_status
            error_code = "ERROR"

        error_detail = {"error": error, "error_code": error_code}
        raise HttpResponseError(status_code=status_code, detail=error_detail)


class PaginationHelper:
    """
    Generic pagination utilities for HTTP responses.
    """

    @staticmethod
    def paginate(items: List[T], page: int, per_page: int) -> Dict[str, Any]:
        """
        Paginate a list of items.

        Args:
            items: The full list of items
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            dict: {
                "items": [paginated items],
                "pagination": {
                    "page": int,
                    "per_page": int,
                    "total": int,
                    "total_pages": int
                }
            }
        """
        total = len(items)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_items = items[start_idx:end_idx]

        total_pages = (total + per_page - 1) // per_page

        return {
            "items": paginated_items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
            },
        }

    @staticmethod
    def paginate_models(items: List[BaseModel], page: int, per_page: int) -> Dict[str, Any]:
        """
        Paginate a list of Pydantic models and serialize to dict.

        Args:
            items: The full list of Pydantic models
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            dict: {
                "items": [serialized items],
                "pagination": {...}
            }
        """
        total = len(items)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_items = items[start_idx:end_idx]

        total_pages = (total + per_page - 1) // per_page

        return {
            "items": [item.model_dump(mode="json") for item in paginated_items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
            },
        }


class AdapterPattern:
    """
    Helper for implementing the 5-step adapter pattern in HTTP routes.

    The pattern:
    1. Parse HTTP input → Pydantic model (validate)
    2. Convert model → Domain entity
    3. Call service layer (business logic)
    4. Convert domain entity → HTTP model
    5. Return HTTP response dict

    This class provides utilities for composing these steps with Result.
    """

    @staticmethod
    def adapt_create(
        data: dict,
        model_class: type,
        to_domain_fn: Callable,
        service_create_fn: Callable,
        from_domain_fn: Callable,
    ) -> Result:
        """
        Execute full 5-step adapter pattern for CREATE operations.

        Args:
            data: Raw HTTP request data
            model_class: Pydantic model class for validation
            to_domain_fn: Function to convert model → domain entity
            service_create_fn: Service method to call (receives domain entity)
            from_domain_fn: Function to convert domain entity → HTTP model

        Returns:
            Result[dict, str]: Success contains response dict, error contains error message
        """
        return (
            ResultValidator.parse_model(data, model_class)
            .map(to_domain_fn)
            .then(lambda entity: Ok(service_create_fn(entity)))
            .map(from_domain_fn)
            .map(lambda model: {"data": model.model_dump(mode="json"), "message": "Created"})
        )

    @staticmethod
    def adapt_get(resource_id: int, service_get_fn: Callable, from_domain_fn: Callable) -> Result:
        """
        Execute adapter pattern for GET operations.

        Args:
            resource_id: ID to fetch
            service_get_fn: Service method to call
            from_domain_fn: Function to convert domain entity → HTTP model

        Returns:
            Result[dict, str]: Success contains response dict, error contains error message
        """
        return (
            ResultValidator.validate_id(resource_id)
            .then(lambda rid: ResultConverter.or_not_found(service_get_fn(rid), "Resource", rid))
            .map(from_domain_fn)
            .map(lambda model: {"data": model.model_dump(mode="json")})
        )
