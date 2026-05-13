"""
Railway-Oriented Programming Result Type for axiompy.

Provides a functional approach to error handling using Result types.
Instead of throwing exceptions, operations return Result[T, E] which can be
either Success(T) or Failure(E), allowing elegant error chaining.

Example:
    >>> from axiompy.result import Result, Ok, Err
    >>>
    >>> def parse_age(value: str) -> Result[int, str]:
    ...     try:
    ...         age = int(value)
    ...         return Ok(age) if age >= 0 else Err("Age must be positive")
    ...     except ValueError:
    ...         return Err("Invalid integer")
    >>>
    >>> def validate_adult(age: int) -> Result[int, str]:
    ...     return Ok(age) if age >= 18 else Err("Must be 18+")
    >>>
    >>> result = (parse_age("25")
    ...     .then(validate_adult)
    ...     .map(lambda age: f"Valid age: {age}")
    ...     .map_error(lambda err: f"Error: {err}")
    ...     .unwrap_or("Unknown age"))
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    cast,
)

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")
F = TypeVar("F")


class Result(ABC, Generic[T, E]):
    """
    Abstract base class for Result type.

    A Result is either Ok(value) or Err(error), representing the outcome
    of an operation that can fail.

    Type Parameters:
        T: Type of the success value
        E: Type of the error value

    Methods:
        is_ok() -> bool: Check if Result is Ok
        is_err() -> bool: Check if Result is Err
        then(func) -> Result[U, E]: Chain another operation (success only)
        or_else(func) -> Result[T, F]: Recover from error
        map(func) -> Result[U, E]: Transform success value
        map_error(func) -> Result[T, F]: Transform error value
        unwrap() -> T: Get value or raise
        unwrap_or(default) -> T: Get value or return default
        unwrap_or_else(func) -> T: Get value or compute from error
        expect(msg) -> T: Get value or raise with message
        and_then(func) -> Result[U, E]: Alias for then()
    """

    @abstractmethod
    def is_ok(self) -> bool:
        """Check if this Result is Ok."""

    @abstractmethod
    def is_err(self) -> bool:
        """Check if this Result is Err."""

    @abstractmethod
    def then(self, func: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        """
        Chain to the next operation (success only).

        If this Result is Ok, apply func to the value and return the result.
        If this Result is Err, skip func and return self as the new error.

        This is the core of Railway-Oriented Programming - errors propagate
        automatically without explicit handling.

        Args:
            func: Function that takes success value and returns Result[U, E]

        Returns:
            Result[U, E]: Either success with new value or error
        """

    @abstractmethod
    def or_else(self, func: Callable[[E], "Result[T, F]"]) -> "Result[T, F]":
        """
        Recover from an error (error only).

        If this Result is Err, apply func to the error and return result.
        If this Result is Ok, return self as-is.

        Args:
            func: Function that takes error and returns Result[T, F]

        Returns:
            Result[T, F]: Either recovered success or new error
        """

    @abstractmethod
    def map(self, func: Callable[[T], U]) -> "Result[U, E]":
        """
        Transform the success value (success only).

        If this Result is Ok, apply func to the value and wrap result in Ok.
        If this Result is Err, return self unchanged.

        Args:
            func: Function that transforms T to U

        Returns:
            Result[U, E]: Ok with transformed value or unchanged error
        """

    @abstractmethod
    def map_error(self, func: Callable[[E], F]) -> "Result[T, F]":
        """
        Transform the error value (error only).

        If this Result is Err, apply func to the error and wrap result in Err.
        If this Result is Ok, return self unchanged.

        Args:
            func: Function that transforms E to F

        Returns:
            Result[T, F]: Ok unchanged or Err with transformed error
        """

    @abstractmethod
    def unwrap(self) -> T:
        """
        Extract the success value or raise exception.

        If this Result is Ok, return the value.
        If this Result is Err, raise RuntimeError with the error.

        Returns:
            T: The success value

        Raises:
            RuntimeError: If Result is Err
        """

    @abstractmethod
    def unwrap_or(self, default: T) -> T:
        """
        Extract the success value or return default.

        If this Result is Ok, return the value.
        If this Result is Err, return default.

        Args:
            default: Value to return if Result is Err

        Returns:
            T: Either success value or default
        """

    @abstractmethod
    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        """
        Extract the success value or compute from error.

        If this Result is Ok, return the value.
        If this Result is Err, apply func to error and return result.

        Args:
            func: Function that computes value from error

        Returns:
            T: Either success value or computed value
        """

    @abstractmethod
    def expect(self, msg: str) -> T:
        """
        Extract the success value or raise exception with message.

        If this Result is Ok, return the value.
        If this Result is Err, raise RuntimeError with custom message.

        Args:
            msg: Custom error message

        Returns:
            T: The success value

        Raises:
            RuntimeError: If Result is Err with custom message
        """

    @abstractmethod
    def get_error(self) -> Optional[E]:
        """
        Get the error value if this Result is Err.

        Returns:
            Optional[E]: The error value if Err, None if Ok
        """

    @abstractmethod
    def get_value(self) -> Optional[T]:
        """
        Get the success value if this Result is Ok.

        Returns:
            Optional[T]: The success value if Ok, None if Err
        """

    # Aliases for compatibility
    def and_then(self, func: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        """Alias for then() - chain operations."""
        return self.then(func)

    def map_or(self, default: U, func: Callable[[T], U]) -> U:
        """
        Transform success value or return default.

        Args:
            default: Value to return if Result is Err
            func: Function to transform success value

        Returns:
            U: Either transformed value or default
        """
        if self.is_ok():
            return func(cast(T, self.get_value()))
        return default

    def map_or_else(self, default_func: Callable[[E], U], func: Callable[[T], U]) -> U:
        """
        Transform success value or compute from error.

        Args:
            default_func: Function to compute value from error
            func: Function to transform success value

        Returns:
            U: Either transformed value or computed value
        """
        if self.is_ok():
            return func(cast(T, self.get_value()))
        return default_func(cast(E, self.get_error()))

    def __repr__(self) -> str:
        """String representation."""
        if self.is_ok():
            return f"Ok({self.get_value()})"
        return f"Err({self.get_error()})"

    def __bool__(self) -> bool:
        """Result is truthy if Ok."""
        return self.is_ok()

    def __eq__(self, other: object) -> bool:
        """Compare Results."""
        if not isinstance(other, Result):
            return False
        if self.is_ok() and other.is_ok():
            return self.get_value() == other.get_value()
        if self.is_err() and other.is_err():
            return self.get_error() == other.get_error()
        return False


@dataclass
class Ok(Result[T, E]):
    """Success variant of Result - contains a success value."""

    value: T

    def is_ok(self) -> bool:
        """Always True for Ok."""
        return True

    def is_err(self) -> bool:
        """Always False for Ok."""
        return False

    def then(self, func: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Apply function to value."""
        return func(self.value)

    def or_else(self, func: Callable[[E], Result[T, F]]) -> Result[T, F]:
        """Return self as Ok."""
        return cast(Result[T, F], self)

    def map(self, func: Callable[[T], U]) -> Result[U, E]:
        """Transform value and wrap in Ok."""
        return Ok(func(self.value))

    def map_error(self, func: Callable[[E], F]) -> Result[T, F]:
        """Return self as Ok (error function not called)."""
        return cast(Result[T, F], self)

    def unwrap(self) -> T:
        """Return the value."""
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Return the value."""
        return self.value

    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        """Return the value (func not called)."""
        return self.value

    def expect(self, msg: str) -> T:
        """Return the value (message not used)."""
        return self.value

    def get_error(self) -> Optional[E]:
        """Return None (no error)."""
        return None

    def get_value(self) -> Optional[T]:
        """Return the success value."""
        return self.value


@dataclass
class Err(Result[T, E]):
    """Error variant of Result - contains an error value."""

    error: E

    def is_ok(self) -> bool:
        """Always False for Err."""
        return False

    def is_err(self) -> bool:
        """Always True for Err."""
        return True

    def then(self, func: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Return self as error (func not called)."""
        return cast(Result[U, E], self)

    def or_else(self, func: Callable[[E], Result[T, F]]) -> Result[T, F]:
        """Apply function to error."""
        return func(self.error)

    def map(self, func: Callable[[T], U]) -> Result[U, E]:
        """Return self as error (func not called)."""
        return cast(Result[U, E], self)

    def map_error(self, func: Callable[[E], F]) -> Result[T, F]:
        """Transform error and wrap in Err."""
        return Err(func(self.error))

    def unwrap(self) -> T:
        """Raise exception with error."""
        raise RuntimeError(f"Called unwrap() on Err: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """Return the default value."""
        return default

    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        """Compute value from error."""
        return func(self.error)

    def expect(self, msg: str) -> T:
        """Raise exception with custom message."""
        raise RuntimeError(f"{msg}: {self.error}")

    def get_error(self) -> Optional[E]:
        """Return the error value."""
        return self.error

    def get_value(self) -> Optional[T]:
        """Return None (no success value)."""
        return None


# Utility functions for working with Results


def collect_results(results: List[Result[T, E]]) -> Result[List[T], E]:
    """
    Collect multiple Results into one Result of a list.

    If all Results are Ok, returns Ok with list of all values.
    If any Result is Err, returns the first Err encountered.

    Args:
        results: List of Results to collect

    Returns:
        Result[List[T], E]: Either list of values or first error
    """
    values: List[T] = []
    for result in results:
        if result.is_err():
            return cast(Result[List[T], E], result)
        values.append(cast(T, result.get_value()))
    return Ok(values)


def partition_results(results: List[Result[T, E]]) -> Tuple[List[T], List[E]]:
    """
    Partition Results into successes and errors.

    Args:
        results: List of Results to partition

    Returns:
        Tuple[List[T], List[E]]: Tuple of (successes, errors)
    """
    successes: List[T] = []
    errors: List[E] = []
    for result in results:
        if result.is_ok():
            successes.append(cast(T, result.get_value()))
        else:
            errors.append(cast(E, result.get_error()))
    return successes, errors


def try_catch(func: Callable[..., T], *args: Any, **kwargs: Any) -> Result[T, str]:
    """
    Convert a function that raises exceptions into a Result.

    Executes the function and catches any exception, wrapping it as Err.

    Args:
        func: Callable to execute
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result[T, str]: Ok with return value or Err with exception message
    """
    try:
        return Ok(func(*args, **kwargs))
    except Exception as e:
        return Err(str(e))


# CoreResult alias for compatibility and branding
CoreResult = Result

__all__ = [
    "Result",
    "Ok",
    "Err",
    "CoreResult",
    "collect_results",
    "partition_results",
    "try_catch",
]
