"""
Validation module providing flexible assertion-like validators with default and
custom error messages.

Each validator function checks a specific condition and raises a ValidationError
if the condition fails. All validators support optional custom error messages.

This module also provides a Protocol-based validation chain pattern for
composable validators.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Callable, Iterable, Optional, Protocol, Type, Union, runtime_checkable


class ValidationError(Exception):
    """Exception raised when validation fails."""


# ============================================================================
# Validation Chain Pattern (for composable validators)
# ============================================================================


class SQLErrorType(Enum):
    """
    Types of SQL validation errors.

    Used to categorize SQL validation errors for better error handling and retry logic.
    """

    EMPTY_SQL = "empty_sql"
    SYNTAX_ERROR = "syntax_error"
    COLUMN_ERROR = "column_error"
    DATABASE_ERROR = "database_error"
    GENERATION_ERROR = "generation_error"
    UNKNOWN = "unknown"


@dataclass
class ValidationContext:
    """
    Context passed through validator chain.

    This context accumulates errors and warnings as it passes through
    multiple validators in a chain.

    Example:
        context = ValidationContext(
            sql="SELECT * FROM users",
            metadata=dataset_metadata,
            db_connection=conn
        )

        # Validators add errors/warnings
        context.errors.append("Invalid syntax")
        context.warnings.append("Deprecated function used")
    """

    sql: str
    metadata: Any = None
    db_connection: Any = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@runtime_checkable
class Validator(Protocol):
    """
    Protocol for validators in a validation chain.

    Any class implementing a validate() method with this signature
    can be used as a validator, without requiring inheritance.

    This enables structural typing (duck typing with type hints).

    Example:
        class MyValidator:  # No inheritance needed!
            def validate(self, context: ValidationContext) -> ValidationContext:
                if "DROP" in context.sql:
                    context.errors.append("DROP not allowed")
                return context

        # Automatically recognized as Validator
        pipeline = ValidationPipeline([MyValidator()])
    """

    def validate(self, context: ValidationContext) -> ValidationContext:
        """
        Validate and return updated context.

        Should add errors/warnings to context.errors/context.warnings
        instead of raising exceptions (for chaining).

        Args:
            context: Validation context with sql, metadata, errors, warnings

        Returns:
            Updated context (usually the same object, modified)
        """


def ensure_not_none(value: Any, message: Optional[str] = None) -> None:
    """
    Ensure that the value is not None.

    Args:
        value: The value to check
        message: Optional custom error message

    Raises:
        ValidationError: If value is None
    """
    if value is None:
        raise ValidationError(message or "Value cannot be None")


def ensure_not_empty(
    value: Union[str, list, dict, tuple, set], message: Optional[str] = None
) -> None:
    """
    Ensure that the value is not empty (for strings, lists, dicts, tuples, sets).

    Args:
        value: The value to check
        message: Optional custom error message

    Raises:
        ValidationError: If value is empty
    """
    if not value:
        raise ValidationError(message or f"Value cannot be empty (type: {type(value).__name__})")


def ensure_type(value: Any, expected_type: Type, message: Optional[str] = None) -> None:
    """
    Ensure that the value is of the expected type.

    Args:
        value: The value to check
        expected_type: The expected type
        message: Optional custom error message

    Raises:
        ValidationError: If value is not of expected type
    """
    if not isinstance(value, expected_type):
        raise ValidationError(
            message or f"Expected type {expected_type.__name__}, got {type(value).__name__}"
        )


def ensure_instance_of(value: Any, expected_class: Type, message: Optional[str] = None) -> None:
    """
    Ensure that the value is an instance of the expected class.

    Args:
        value: The value to check
        expected_class: The expected class
        message: Optional custom error message

    Raises:
        ValidationError: If value is not an instance of expected class
    """
    if not isinstance(value, expected_class):
        raise ValidationError(
            message
            or f"Value must be an instance of {expected_class.__name__}, got {type(value).__name__}"
        )


def ensure_in_range(
    value: Union[int, float],
    min_value: Union[int, float],
    max_value: Union[int, float],
    message: Optional[str] = None,
) -> None:
    """
    Ensure that the value is within the specified range (inclusive).

    Args:
        value: The value to check
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        message: Optional custom error message

    Raises:
        ValidationError: If value is not within range
    """
    if not min_value <= value <= max_value:
        raise ValidationError(
            message or f"Value {value} is not within range [{min_value}, {max_value}]"
        )


def ensure_gt(
    value: Union[int, float], min_value: Union[int, float], message: Optional[str] = None
) -> None:
    """
    Ensure that the value is greater than the given minimum.

    Args:
        value: The value to check
        min_value: Minimum exclusive value
        message: Optional custom error message

    Raises:
        ValidationError: If value is not greater than min_value
    """
    if not value > min_value:
        raise ValidationError(message or f"Value {value} must be greater than {min_value}")


def ensure_gte(
    value: Union[int, float], min_value: Union[int, float], message: Optional[str] = None
) -> None:
    """
    Ensure that the value is greater than or equal to the given minimum.

    Args:
        value: The value to check
        min_value: Minimum inclusive value
        message: Optional custom error message

    Raises:
        ValidationError: If value is less than min_value
    """
    if value < min_value:
        raise ValidationError(message or f"Value {value} must be >= {min_value}")


def ensure_lt(
    value: Union[int, float], max_value: Union[int, float], message: Optional[str] = None
) -> None:
    """
    Ensure that the value is less than the given maximum.

    Args:
        value: The value to check
        max_value: Maximum exclusive value
        message: Optional custom error message

    Raises:
        ValidationError: If value is not less than max_value
    """
    if not value < max_value:
        raise ValidationError(message or f"Value {value} must be less than {max_value}")


def ensure_lte(
    value: Union[int, float], max_value: Union[int, float], message: Optional[str] = None
) -> None:
    """
    Ensure that the value is less than or equal to the given maximum.

    Args:
        value: The value to check
        max_value: Maximum inclusive value
        message: Optional custom error message

    Raises:
        ValidationError: If value is greater than max_value
    """
    if value > max_value:
        raise ValidationError(message or f"Value {value} must be <= {max_value}")


def ensure_between_exclusive(
    value: Union[int, float],
    min_value: Union[int, float],
    max_value: Union[int, float],
    message: Optional[str] = None,
) -> None:
    """
    Ensure that the value is within the specified range (exclusive).

    Args:
        value: The value to check
        min_value: Minimum exclusive value
        max_value: Maximum exclusive value
        message: Optional custom error message

    Raises:
        ValidationError: If value is not within range
    """
    if not min_value < value < max_value:
        raise ValidationError(
            message or f"Value {value} is not within range ({min_value}, {max_value})"
        )


def ensure_finite(value: Union[int, float], message: Optional[str] = None) -> None:
    """
    Ensure that the value is finite (not NaN or infinity).

    Args:
        value: The value to check
        message: Optional custom error message

    Raises:
        ValidationError: If value is NaN or infinite
    """
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValidationError(message or f"Value {value} must be a finite number")


def ensure_positive(
    value: Optional[Union[int, float]], message: Optional[str] = None, allow_none: bool = False
) -> None:
    """
    Ensure that the value is positive (> 0).

    By default, raises ValidationError if value is None. Set allow_none=True
    to allow None values (useful for optional parameters).

    Args:
        value: The value to check
        message: Optional custom error message
        allow_none: If True, None values are allowed (default: False)

    Raises:
        ValidationError: If value is not positive, or if None and allow_none=False

    Example:
        >>> ensure_positive(5)  # OK
        >>> ensure_positive(None)  # Raises ValidationError
        >>> ensure_positive(None, allow_none=True)  # OK (optional parameter)
        >>> ensure_positive(0)  # Raises ValidationError
        >>> ensure_positive(-1)  # Raises ValidationError
    """
    if value is None:
        if not allow_none:
            raise ValidationError(message or "Value cannot be None")
        return

    if value <= 0:
        raise ValidationError(message or f"Value must be positive, got {value}")


def ensure_non_negative(value: Union[int, float], message: Optional[str] = None) -> None:
    """
    Ensure that the value is non-negative (>= 0).

    Args:
        value: The value to check
        message: Optional custom error message

    Raises:
        ValidationError: If value is negative
    """
    if value < 0:
        raise ValidationError(message or f"Value must be non-negative, got {value}")


def ensure_negative(value: Union[int, float], message: Optional[str] = None) -> None:
    """
    Ensure that the value is negative (< 0).

    Args:
        value: The value to check
        message: Optional custom error message

    Raises:
        ValidationError: If value is not negative
    """
    if value >= 0:
        raise ValidationError(message or f"Value must be negative, got {value}")


def ensure_length(
    value: Union[str, list, tuple, set, dict],
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    message: Optional[str] = None,
) -> None:
    """
    Ensure that the value's length is within the specified constraints.

    Args:
        value: The value to check
        min_length: Minimum allowed length (optional)
        max_length: Maximum allowed length (optional)
        message: Optional custom error message

    Raises:
        ValidationError: If value's length is not within constraints
    """
    length = len(value)

    if min_length is not None and length < min_length:
        raise ValidationError(message or f"Length {length} is less than minimum {min_length}")

    if max_length is not None and length > max_length:
        raise ValidationError(message or f"Length {length} exceeds maximum {max_length}")


def ensure_min_length(
    value: Union[str, list, tuple, set, dict], min_length: int, message: Optional[str] = None
) -> None:
    """
    Ensure that the value has at least the given length.

    Args:
        value: The value to check
        min_length: Minimum allowed length
        message: Optional custom error message

    Raises:
        ValidationError: If length is less than min_length
    """
    ensure_length(value, min_length=min_length, message=message)


def ensure_max_length(
    value: Union[str, list, tuple, set, dict], max_length: int, message: Optional[str] = None
) -> None:
    """
    Ensure that the value does not exceed the given length.

    Args:
        value: The value to check
        max_length: Maximum allowed length
        message: Optional custom error message

    Raises:
        ValidationError: If length exceeds max_length
    """
    ensure_length(value, max_length=max_length, message=message)


def ensure_exact_length(
    value: Union[str, list, tuple, set, dict], length: int, message: Optional[str] = None
) -> None:
    """
    Ensure that the value has exactly the given length.

    Args:
        value: The value to check
        length: Exact required length
        message: Optional custom error message

    Raises:
        ValidationError: If length does not match
    """
    actual = len(value)
    if actual != length:
        raise ValidationError(message or f"Length {actual} does not equal {length}")


def ensure_not_blank(value: str, message: Optional[str] = None) -> None:
    """
    Ensure that a string is not blank (non-empty after stripping).

    Args:
        value: The string to check
        message: Optional custom error message

    Raises:
        ValidationError: If string is blank or not a string
    """
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(message or "String cannot be blank")


def ensure_starts_with(value: str, prefix: str, message: Optional[str] = None) -> None:
    """
    Ensure that a string starts with the given prefix.

    Args:
        value: The string to check
        prefix: Required prefix
        message: Optional custom error message

    Raises:
        ValidationError: If string does not start with prefix
    """
    if not isinstance(value, str) or not value.startswith(prefix):
        raise ValidationError(message or f"String must start with '{prefix}'")


def ensure_ends_with(value: str, suffix: str, message: Optional[str] = None) -> None:
    """
    Ensure that a string ends with the given suffix.

    Args:
        value: The string to check
        suffix: Required suffix
        message: Optional custom error message

    Raises:
        ValidationError: If string does not end with suffix
    """
    if not isinstance(value, str) or not value.endswith(suffix):
        raise ValidationError(message or f"String must end with '{suffix}'")


def ensure_contains(value: str, substring: str, message: Optional[str] = None) -> None:
    """
    Ensure that a string contains the given substring.

    Args:
        value: The string to check
        substring: Required substring
        message: Optional custom error message

    Raises:
        ValidationError: If string does not contain substring
    """
    if not isinstance(value, str) or substring not in value:
        raise ValidationError(message or f"String must contain '{substring}'")


def ensure_matches_any(value: str, patterns: Iterable[str], message: Optional[str] = None) -> None:
    """
    Ensure that a string matches at least one of the provided regex patterns.

    Args:
        value: The string to check
        patterns: Iterable of regex patterns
        message: Optional custom error message

    Raises:
        ValidationError: If string matches none of the patterns
    """
    if not isinstance(value, str):
        raise ValidationError(message or "Value must be a string")

    for pattern in patterns:
        if re.match(pattern, value):
            return

    raise ValidationError(message or "String does not match any allowed pattern")


def ensure_email(email: str, message: Optional[str] = None) -> None:
    """
    Ensure that the string is a valid email format.

    Args:
        email: The email string to check
        message: Optional custom error message

    Raises:
        ValidationError: If email format is invalid
    """
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not isinstance(email, str) or not re.match(email_pattern, email):
        raise ValidationError(message or f"String '{email}' is not a valid email format")


def ensure_url(url: str, message: Optional[str] = None) -> None:
    """
    Ensure that the string is a valid URL format.

    Args:
        url: The URL string to check
        message: Optional custom error message

    Raises:
        ValidationError: If URL format is invalid
    """
    url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    if not isinstance(url, str) or not re.match(url_pattern, url, re.IGNORECASE):
        raise ValidationError(message or f"String '{url}' is not a valid URL format")


def ensure_date(
    date_str: str, date_format: str = "%Y-%m-%d", message: Optional[str] = None
) -> None:
    """
    Ensure that the string is a valid date format.

    Args:
        date_str: The date string to check
        date_format: The expected date format (default: YYYY-MM-DD)
        message: Optional custom error message

    Raises:
        ValidationError: If date format is invalid
    """
    try:
        datetime.strptime(date_str, date_format)
    except (ValueError, TypeError) as exc:
        raise ValidationError(
            message or f"String '{date_str}' is not a valid date format (expected: {date_format})"
        ) from exc


def ensure_datetime(value: Any, message: Optional[str] = None) -> None:
    """
    Ensure that the value is a datetime instance.

    Args:
        value: The value to check
        message: Optional custom error message

    Raises:
        ValidationError: If value is not a datetime
    """
    if not isinstance(value, datetime):
        raise ValidationError(message or "Value must be a datetime instance")


def ensure_datetime_tz_aware(value: datetime, message: Optional[str] = None) -> None:
    """
    Ensure that a datetime is timezone-aware.

    Args:
        value: The datetime to check
        message: Optional custom error message

    Raises:
        ValidationError: If datetime is naive
    """
    ensure_datetime(value, message=message)
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValidationError(message or "Datetime must be timezone-aware")


def ensure_datetime_tz_naive(value: datetime, message: Optional[str] = None) -> None:
    """
    Ensure that a datetime is timezone-naive.

    Args:
        value: The datetime to check
        message: Optional custom error message

    Raises:
        ValidationError: If datetime is timezone-aware
    """
    ensure_datetime(value, message=message)
    if value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None:
        raise ValidationError(message or "Datetime must be timezone-naive")


def ensure_date_not_in_future(value: Union[date, datetime], message: Optional[str] = None) -> None:
    """
    Ensure that a date/datetime is not in the future.

    Args:
        value: The date or datetime to check
        message: Optional custom error message

    Raises:
        ValidationError: If value is in the future
    """
    if isinstance(value, datetime):
        now = datetime.now(tz=value.tzinfo) if value.tzinfo else datetime.now()
        if value > now:
            raise ValidationError(message or "Datetime cannot be in the future")
        return

    if isinstance(value, date):
        if value > date.today():
            raise ValidationError(message or "Date cannot be in the future")
        return

    raise ValidationError(message or "Value must be a date or datetime")


def ensure_date_not_in_past(value: Union[date, datetime], message: Optional[str] = None) -> None:
    """
    Ensure that a date/datetime is not in the past.

    Args:
        value: The date or datetime to check
        message: Optional custom error message

    Raises:
        ValidationError: If value is in the past
    """
    if isinstance(value, datetime):
        now = datetime.now(tz=value.tzinfo) if value.tzinfo else datetime.now()
        if value < now:
            raise ValidationError(message or "Datetime cannot be in the past")
        return

    if isinstance(value, date):
        if value < date.today():
            raise ValidationError(message or "Date cannot be in the past")
        return

    raise ValidationError(message or "Value must be a date or datetime")


def ensure_regex_match(value: str, pattern: str, message: Optional[str] = None) -> None:
    """
    Ensure that the string matches the given regex pattern.

    Args:
        value: The string to check
        pattern: The regex pattern to match
        message: Optional custom error message

    Raises:
        ValidationError: If string doesn't match pattern
    """
    if not isinstance(value, str) or not re.match(pattern, value):
        raise ValidationError(message or f"String '{value}' does not match pattern '{pattern}'")


def ensure_callable(value: Any, message: Optional[str] = None) -> None:
    """
    Ensure that the value is callable.

    Args:
        value: The value to check
        message: Optional custom error message

    Raises:
        ValidationError: If value is not callable
    """
    if not callable(value):
        raise ValidationError(message or f"Value of type {type(value).__name__} is not callable")


def ensure_dict_has_keys(
    dictionary: dict, required_keys: Iterable[str], message: Optional[str] = None
) -> None:
    """
    Ensure that the dictionary contains all required keys.

    Args:
        dictionary: The dictionary to check
        required_keys: Iterable of required key names
        message: Optional custom error message

    Raises:
        ValidationError: If dictionary is missing required keys
    """
    if not isinstance(dictionary, dict):
        raise ValidationError(f"Expected dict, got {type(dictionary).__name__}")

    missing_keys = set(required_keys) - set(dictionary.keys())
    if missing_keys:
        raise ValidationError(
            message or f"Dictionary is missing required keys: {sorted(missing_keys)}"
        )


def ensure_dict_keys_type(
    dictionary: dict, expected_type: Type, message: Optional[str] = None
) -> None:
    """
    Ensure that all dictionary keys are of the expected type.

    Args:
        dictionary: The dictionary to check
        expected_type: The expected type for keys
        message: Optional custom error message

    Raises:
        ValidationError: If any key has an unexpected type
    """
    if not isinstance(dictionary, dict):
        raise ValidationError(f"Expected dict, got {type(dictionary).__name__}")

    for key in dictionary.keys():
        if not isinstance(key, expected_type):
            raise ValidationError(
                message
                or (
                    f"Dictionary key '{key}' has type {type(key).__name__}, "
                    f"expected {expected_type.__name__}"
                )
            )


def ensure_dict_values_type(
    dictionary: dict, expected_type: Type, message: Optional[str] = None
) -> None:
    """
    Ensure that all dictionary values are of the expected type.

    Args:
        dictionary: The dictionary to check
        expected_type: The expected type for values
        message: Optional custom error message

    Raises:
        ValidationError: If any value has an unexpected type
    """
    if not isinstance(dictionary, dict):
        raise ValidationError(f"Expected dict, got {type(dictionary).__name__}")

    for key, value in dictionary.items():
        if not isinstance(value, expected_type):
            raise ValidationError(
                message
                or (
                    f"Dictionary value for key '{key}' has type {type(value).__name__}, "
                    f"expected {expected_type.__name__}"
                )
            )


def ensure_list_contains(lst: list, item: Any, message: Optional[str] = None) -> None:
    """
    Ensure that the list contains the specified item.

    Args:
        lst: The list to check
        item: The item to look for
        message: Optional custom error message

    Raises:
        ValidationError: If list doesn't contain item
    """
    if not isinstance(lst, list):
        raise ValidationError(f"Expected list, got {type(lst).__name__}")

    if item not in lst:
        raise ValidationError(message or f"List does not contain item: {item}")


def ensure_in_choices(value: Any, choices: Iterable[Any], message: Optional[str] = None) -> None:
    """
    Ensure that the value is in the given choices.

    Args:
        value: The value to check
        choices: Iterable of allowed choices
        message: Optional custom error message

    Raises:
        ValidationError: If value is not in choices
    """
    if value not in choices:
        raise ValidationError(
            message or f"Value '{value}' is not in allowed choices: {list(choices)}"
        )


def ensure_all_items_in_choices(
    iterable: Iterable[Any], choices: Iterable[Any], message: Optional[str] = None
) -> None:
    """
    Ensure that all items in the iterable are in the allowed choices.

    Args:
        iterable: The iterable to check
        choices: Iterable of allowed choices
        message: Optional custom error message

    Raises:
        ValidationError: If any item is not in choices
    """
    for index, item in enumerate(iterable):
        if item not in choices:
            raise ValidationError(
                message or f"Item at index {index} is not in allowed choices: {item}"
            )


def ensure_all_items_type(
    iterable: Iterable, expected_type: Type, message: Optional[str] = None
) -> None:
    """
    Ensure that all items in the iterable are of the expected type.

    Args:
        iterable: The iterable to check
        expected_type: The expected type for all items
        message: Optional custom error message

    Raises:
        ValidationError: If any item is not of expected type
    """
    for i, item in enumerate(iterable):
        if not isinstance(item, expected_type):
            item_type = type(item).__name__
            expected_name = expected_type.__name__
            raise ValidationError(
                message or f"Item at index {i} has type {item_type}, expected {expected_name}"
            )


def ensure_unique_items(iterable: Iterable, message: Optional[str] = None) -> None:
    """
    Ensure that all items in the iterable are unique.

    Args:
        iterable: The iterable to check
        message: Optional custom error message

    Raises:
        ValidationError: If there are duplicate items
    """
    items = list(iterable)
    unique_items = set(items)

    if len(items) != len(unique_items):
        raise ValidationError(message or "Iterable contains duplicate items")


def ensure_non_empty_iterable(iterable: Iterable, message: Optional[str] = None) -> None:
    """
    Ensure that the iterable contains at least one item.

    Args:
        iterable: The iterable to check
        message: Optional custom error message

    Raises:
        ValidationError: If iterable is empty or not iterable
    """
    try:
        iterator = iter(iterable)
    except TypeError as exc:
        raise ValidationError(message or "Value must be iterable") from exc

    try:
        next(iterator)
    except StopIteration as exc:
        raise ValidationError(message or "Iterable cannot be empty") from exc


def ensure_subclass_of(cls: Type, parent_class: Type, message: Optional[str] = None) -> None:
    """
    Ensure that the class is a subclass of the parent class.

    Args:
        cls: The class to check
        parent_class: The expected parent class
        message: Optional custom error message

    Raises:
        ValidationError: If cls is not a subclass of parent_class
    """
    if not isinstance(cls, type):
        raise ValidationError(f"Expected a class, got {type(cls).__name__}")

    if not issubclass(cls, parent_class):
        raise ValidationError(
            message or f"Class {cls.__name__} is not a subclass of {parent_class.__name__}"
        )


def ensure_equal(value: Any, expected: Any, message: Optional[str] = None) -> None:
    """
    Ensure that two values are equal.

    Args:
        value: The value to check
        expected: The expected value
        message: Optional custom error message

    Raises:
        ValidationError: If values are not equal
    """
    if value != expected:
        raise ValidationError(message or f"Value {value} does not equal {expected}")


def ensure_not_equal(value: Any, unexpected: Any, message: Optional[str] = None) -> None:
    """
    Ensure that two values are not equal.

    Args:
        value: The value to check
        unexpected: The value that must not match
        message: Optional custom error message

    Raises:
        ValidationError: If values are equal
    """
    if value == unexpected:
        raise ValidationError(message or f"Value {value} must not equal {unexpected}")


def ensure_none_or(value: Any, validator: Callable[..., None], *args: Any, **kwargs: Any) -> None:
    """
    Ensure that value is None or passes the provided validator.

    Args:
        value: The value to check
        validator: Validator function to call if value is not None
        *args: Additional args passed to validator
        **kwargs: Additional kwargs passed to validator

    Raises:
        ValidationError: If value is not None and validator fails
    """
    if value is None:
        return

    validator(value, *args, **kwargs)


# ============================================================================
# SQL Validators (for SQL validation chains)
# ============================================================================


class EmptySQLValidator:
    """
    Validates that SQL is not empty.

    This is typically the first validator in a chain as there's no point
    validating empty SQL.

    Example:
        validator = EmptySQLValidator()
        context = ValidationContext(sql="")
        context = validator.validate(context)
        assert "empty" in context.errors[0].lower()
    """

    def validate(self, context: ValidationContext) -> ValidationContext:
        """Add error if SQL is empty."""
        if not context.sql or not context.sql.strip():
            context.errors.append("SQL query is empty")
        return context


class SQLSyntaxValidator:
    """
    Validates SQL syntax using sqlparse library.

    Checks for:
    - Parseable SQL structure
    - Common syntax errors (unmatched parentheses, LIMIT without FROM, etc.)
    - Malformed queries

    Example:
        validator = SQLSyntaxValidator(use_parser=True)
        context = ValidationContext(sql="SELECT * LIMIT 10")
        context = validator.validate(context)
        assert len(context.errors) > 0  # LIMIT without FROM
    """

    def __init__(self, use_parser: bool = True):
        """
        Initialize syntax validator.

        Args:
            use_parser: Whether to use sqlparse library (default: True)
        """
        self.use_parser = use_parser

    def validate(self, context: ValidationContext) -> ValidationContext:
        """Validate SQL syntax and add errors/warnings to context."""
        from axiompy.sql_engine import SQLValidator

        result = SQLValidator.validate_syntax(context.sql, self.use_parser)
        context.errors.extend(result.errors)
        context.warnings.extend(result.warnings)
        return context


class SQLColumnValidator:
    """
    Validates that columns referenced in SQL exist in the schema.

    Extracts columns from the SQL query and checks them against
    the schema provided in context.metadata.

    Example:
        validator = SQLColumnValidator(strict=False)
        context = ValidationContext(
            sql="SELECT invalid_col FROM users",
            metadata=dataset_metadata
        )
        context = validator.validate(context)
        assert "invalid_col" in str(context.errors)
    """

    def __init__(self, strict: bool = False):
        """
        Initialize column validator.

        Args:
            strict: If True, fail on any unrecognized column (default: False)
        """
        self.strict = strict

    def validate(self, context: ValidationContext) -> ValidationContext:
        """Validate columns exist in schema."""
        if not context.metadata:
            return context

        from axiompy.sql_engine import SQLValidator

        # Extract schema columns from metadata
        schema_columns = set()
        if hasattr(context.metadata, "schema"):
            for table_schema in context.metadata.schema.values():
                if hasattr(table_schema, "columns"):
                    schema_columns.update(table_schema.columns.keys())

        if not schema_columns:
            # No schema to validate against
            return context

        result = SQLValidator.validate_columns(context.sql, schema_columns, self.strict)
        context.errors.extend(result.errors)
        context.warnings.extend(result.warnings)
        return context


class SQLDatabaseValidator:
    """
    Validates SQL using database EXPLAIN (dry-run).

    This uses the actual database engine to validate the query
    without executing it. Catches:
    - Invalid table names
    - Invalid column names
    - Syntax errors specific to the database
    - Ambiguous column references in JOINs

    Example:
        validator = SQLDatabaseValidator(dialect="sqlite")
        context = ValidationContext(
            sql="SELECT * FROM nonexistent_table",
            db_connection=connection
        )
        context = validator.validate(context)
        assert "no such table" in str(context.errors).lower()
    """

    def __init__(self, dialect: str = "sqlite"):
        """
        Initialize database validator.

        Args:
            dialect: Database dialect (sqlite, postgres, mysql)
        """
        self.dialect = dialect

    def validate(self, context: ValidationContext) -> ValidationContext:
        """Validate SQL with database EXPLAIN."""
        if not context.db_connection:
            # No connection provided, skip validation
            return context

        from axiompy.sql_engine import SQLValidator

        result = SQLValidator.validate_with_db_dryrun(
            context.sql, context.db_connection, self.dialect
        )
        context.errors.extend(result.errors)
        context.warnings.extend(result.warnings)
        return context
