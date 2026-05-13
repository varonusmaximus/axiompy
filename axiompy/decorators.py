"""
Decorator utilities for logging, error handling, and tracing
"""

import functools
import logging
import time
import traceback
import warnings
from typing import Any, Callable, Optional, Tuple, Type

# Default logger
_default_logger = logging.getLogger(__name__)


class CatchAndLog:
    """
    Decorator to catch exceptions and log them

    Usage:
        @CatchAndLog(logger)
        def my_function():
            ...

        @CatchAndLog(logger, reraise=False, default_return=None)
        def safe_function():
            ...
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        reraise: bool = True,
        default_return: Any = None,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        log_level: int = logging.ERROR,
    ):
        """
        Args:
            logger: Logger instance to use (uses default if None)
            reraise: Whether to reraise the exception after logging
            default_return: Value to return if exception caught and not reraised
            exceptions: Tuple of exception types to catch
            log_level: Logging level for caught exceptions
        """
        self.logger = logger or _default_logger
        self.reraise = reraise
        self.default_return = default_return
        self.exceptions = exceptions
        self.log_level = log_level

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except self.exceptions as e:
                self.logger.log(
                    self.log_level,
                    f"Exception in {func.__name__}: {str(e)}\n{traceback.format_exc()}",
                )
                if self.reraise:
                    raise
                return self.default_return

        return wrapper


class LogAndRethrow:
    """
    Decorator to log exceptions and always rethrow them.

    Simpler alternative to CatchAndLog for the common use case where you want
    to log exceptions for debugging/monitoring but let them propagate normally.

    Usage:
        @LogAndRethrow(logger)
        def my_function():
            raise ValueError("Something went wrong")
            # Logs the full exception with traceback, then re-raises it

        @LogAndRethrow(logger, log_level=logging.WARNING)
        def another_function():
            ...
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        log_level: int = logging.ERROR,
        include_traceback: bool = True,
    ):
        """
        Args:
            logger: Logger instance to use (uses default if None)
            log_level: Logging level for caught exceptions (default: ERROR)
            include_traceback: Whether to include full traceback in log (default: True)
        """
        self.logger = logger or _default_logger
        self.log_level = log_level
        self.include_traceback = include_traceback

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Build log message
                msg = f"Exception in {func.__name__}: {type(e).__name__}: {str(e)}"

                if self.include_traceback:
                    msg += f"\n{traceback.format_exc()}"

                # Log the exception
                self.logger.log(self.log_level, msg)

                # Always rethrow
                raise

        return wrapper


class LogExecutionTime:
    """
    Decorator to log function execution time (only if logger is at DEBUG level).

    Usage:
        @LogExecutionTime(logger)
        def slow_function():
            ...

        # Only logs if logger.level <= logging.DEBUG
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        message_template: str = "Function '{func_name}' executed in {elapsed:.4f}s",
    ):
        """
        Args:
            logger: Logger instance to use
            message_template: Template for log message (receives func_name and elapsed)

        Note:
            Execution time is only logged if the logger's effective level is DEBUG or lower.
            This prevents performance overhead from excessive logging in production.
        """
        self.logger = logger or _default_logger
        self.message_template = message_template

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Only log if logger is at DEBUG level or lower
                if self.logger.isEnabledFor(logging.DEBUG):
                    elapsed = time.time() - start_time
                    # Extract URL from kwargs if present, otherwise from
                    # first positional arg after self
                    url = kwargs.get("url", "")
                    if not url and len(args) > 1:
                        url = args[1]  # args[0] is self, args[1] is url

                    try:
                        log_message = self.message_template.format(
                            func_name=func.__name__, elapsed=elapsed, url=url
                        )
                    except KeyError:
                        # If template doesn't have all placeholders, just use the ones we have
                        log_message = self.message_template.format(
                            func_name=func.__name__, elapsed=elapsed
                        )
                    self.logger.debug(log_message)

        return wrapper


class LogInputOutput:
    """
    Decorator to log function inputs and outputs

    Usage:
        @LogInputOutput(logger)
        def my_function(x, y):
            return x + y

        @LogInputOutput(logger, log_args=True, log_kwargs=True, log_result=True)
        def detailed_function(a, b, c=None):
            ...
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        log_args: bool = True,
        log_kwargs: bool = True,
        log_result: bool = True,
        log_level: int = logging.DEBUG,
        max_length: int = 200,
    ):
        """
        Args:
            logger: Logger instance to use
            log_args: Whether to log positional arguments
            log_kwargs: Whether to log keyword arguments
            log_result: Whether to log return value
            log_level: Logging level
            max_length: Max length for logged values (truncates longer strings)
        """
        self.logger = logger or _default_logger
        self.log_args = log_args
        self.log_kwargs = log_kwargs
        self.log_result = log_result
        self.log_level = log_level
        self.max_length = max_length

    def _truncate(self, value: Any) -> str:
        """Truncate long values"""
        value_str = str(value)
        if len(value_str) > self.max_length:
            return value_str[: self.max_length] + "..."
        return value_str

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Log inputs
            if self.log_args and args:
                args_str = ", ".join(self._truncate(arg) for arg in args)
                self.logger.log(self.log_level, f"{func.__name__} called with args: {args_str}")

            if self.log_kwargs and kwargs:
                kwargs_str = ", ".join(f"{k}={self._truncate(v)}" for k, v in kwargs.items())
                self.logger.log(
                    self.log_level, "%s called with kwargs: %s", func.__name__, kwargs_str
                )

            # Execute function
            result = func(*args, **kwargs)

            # Log output
            if self.log_result:
                self.logger.log(
                    self.log_level, "%s returned: %s", func.__name__, self._truncate(result)
                )

            return result

        return wrapper


class Retry:
    """
    Decorator to retry function execution on failure

    Usage:
        @Retry(logger, max_attempts=3, delay=1.0)
        def flaky_function():
            ...

        @Retry(logger, max_attempts=5, delay=2.0, backoff=2.0, exceptions=(ConnectionError,))
        def network_call():
            ...
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 1.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        """
        Args:
            logger: Logger instance to use
            max_attempts: Maximum number of attempts
            delay: Initial delay between retries (seconds)
            backoff: Multiplier for delay after each retry
            exceptions: Tuple of exception types to catch and retry
        """
        self.logger = logger or _default_logger
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = self.delay

            for attempt in range(1, self.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except self.exceptions as e:
                    if attempt == self.max_attempts:
                        self.logger.error(
                            f"{func.__name__} failed after {self.max_attempts} attempts: {str(e)}"
                        )
                        raise

                    self.logger.warning(
                        "%s failed (attempt %d/%d): %s. Retrying in %ss...",
                        func.__name__,
                        attempt,
                        self.max_attempts,
                        str(e),
                        current_delay,
                    )
                    time.sleep(current_delay)
                    current_delay *= self.backoff

        return wrapper


class Trace:
    """
    Decorator to trace function entry and exit

    Usage:
        @Trace(logger)
        def my_function():
            ...

        @Trace(logger, log_level=logging.DEBUG, show_args=True)
        def detailed_trace(x, y):
            ...
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        log_level: int = logging.DEBUG,
        show_args: bool = False,
    ):
        """
        Args:
            logger: Logger instance to use
            log_level: Logging level for trace messages
            show_args: Whether to show function arguments
        """
        self.logger = logger or _default_logger
        self.log_level = log_level
        self.show_args = show_args

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if self.show_args:
                args_repr = ", ".join(repr(a) for a in args)
                kwargs_repr = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
                all_args = ", ".join(filter(None, [args_repr, kwargs_repr]))
                self.logger.log(self.log_level, "→ Entering %s(%s)", func.__name__, all_args)
            else:
                self.logger.log(self.log_level, "→ Entering %s", func.__name__)

            try:
                result = func(*args, **kwargs)
                self.logger.log(self.log_level, "← Exiting %s", func.__name__)
                return result
            except Exception as e:
                self.logger.log(self.log_level, "✗ Exception in %s: %s", func.__name__, str(e))
                raise

        return wrapper


class Deprecated:
    """
    Decorator to mark functions as deprecated

    Usage:
        @Deprecated(logger, "Use new_function() instead")
        def old_function():
            ...
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        message: str = "",
        category: Type[Warning] = DeprecationWarning,
    ):
        """
        Args:
            logger: Logger instance to use
            message: Deprecation message
            category: Warning category
        """
        self.logger = logger or _default_logger
        self.message = message
        self.category = category

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warning_msg = f"{func.__name__} is deprecated"
            if self.message:
                warning_msg += f". {self.message}"

            warnings.warn(warning_msg, category=self.category, stacklevel=2)
            self.logger.warning(warning_msg)

            return func(*args, **kwargs)

        return wrapper


class RateLimited:
    """
    Decorator to rate limit function calls

    Usage:
        @RateLimited(logger, max_calls=10, period=60)  # 10 calls per minute
        def api_call():
            ...
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        max_calls: int = 10,
        period: float = 60.0,
    ):
        """
        Args:
            logger: Logger instance to use
            max_calls: Maximum number of calls allowed
            period: Time period in seconds
        """
        self.logger = logger or _default_logger
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()

            # Remove old calls outside the period
            self.calls = [call_time for call_time in self.calls if now - call_time < self.period]

            if len(self.calls) >= self.max_calls:
                wait_time = self.period - (now - self.calls[0])
                self.logger.warning(
                    f"{func.__name__} rate limited. {len(self.calls)} calls in {self.period}s. "
                    f"Wait {wait_time:.2f}s"
                )
                raise RuntimeError(f"Rate limit exceeded. Retry after {wait_time:.2f}s")

            self.calls.append(now)
            return func(*args, **kwargs)

        return wrapper


# Convenience function decorators (use default logger)
def catch_and_log(func: Callable) -> Callable:
    """Simple error catching decorator with default settings"""
    return CatchAndLog()(func)


def log_time(func: Callable) -> Callable:
    """Simple timing decorator with default settings"""
    return LogExecutionTime()(func)


def trace(func: Callable) -> Callable:
    """Simple tracing decorator with default settings"""
    return Trace()(func)


# ============================================================================
# Decorator Stacks (Composite Decorators)
# ============================================================================


class DecoratorStack:
    """
    Utility for composing multiple decorators in a clean, readable way.

    Allows stacking decorators with specific execution order:
    1. Outer decorators run first (wrap the function)
    2. Inner decorators run last (execute during function call)

    Example:
        stack = DecoratorStack()
        stack.add_catch_and_log(logger)
        stack.add_retry(max_attempts=3, delay=1.0)
        stack.add_timing(logger)

        @stack.apply
        def my_function():
            ...
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize decorator stack with optional logger."""
        self.logger = logger or _default_logger
        self.decorators = []  # List of (decorator_class, kwargs) tuples

    def add_catch_and_log(
        self,
        reraise: bool = True,
        default_return: Any = None,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        log_level: int = logging.ERROR,
    ) -> "DecoratorStack":
        """Add CatchAndLog decorator to stack."""
        self.decorators.append(
            (
                CatchAndLog,
                {
                    "logger": self.logger,
                    "reraise": reraise,
                    "default_return": default_return,
                    "exceptions": exceptions,
                    "log_level": log_level,
                },
            )
        )
        return self

    def add_retry(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 1.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ) -> "DecoratorStack":
        """Add Retry decorator to stack."""
        self.decorators.append(
            (
                Retry,
                {
                    "logger": self.logger,
                    "max_attempts": max_attempts,
                    "delay": delay,
                    "backoff": backoff,
                    "exceptions": exceptions,
                },
            )
        )
        return self

    def add_timing(self, message_template: Optional[str] = None) -> "DecoratorStack":
        """Add LogExecutionTime decorator to stack."""
        self.decorators.append(
            (LogExecutionTime, {"logger": self.logger, "message_template": message_template})
        )
        return self

    def add_trace(self) -> "DecoratorStack":
        """Add Trace decorator to stack."""
        self.decorators.append((Trace, {"logger": self.logger}))
        return self

    def add_rate_limit(self, max_calls: int = 10, period: float = 60.0) -> "DecoratorStack":
        """Add RateLimited decorator to stack."""
        self.decorators.append(
            (RateLimited, {"logger": self.logger, "max_calls": max_calls, "period": period})
        )
        return self

    def add_custom(self, decorator_class: Type, **kwargs) -> "DecoratorStack":
        """Add custom decorator to stack."""
        self.decorators.append((decorator_class, kwargs))
        return self

    def apply(self, func: Callable) -> Callable:
        """Apply all decorators in stack to function."""
        # Apply decorators in reverse order (so first added is outermost)
        result = func
        for decorator_class, kwargs in reversed(self.decorators):
            result = decorator_class(**kwargs)(result)
        return result

    def __call__(self, func: Callable) -> Callable:
        """Allow using stack as a decorator directly."""
        return self.apply(func)


# Convenience function for common stacks (using fluent API)
def http_request_stack(logger: Optional[logging.Logger] = None) -> DecoratorStack:
    """
    Create a decorator stack optimized for HTTP request methods.

    Stack composition (execution order):
    1. @LogExecutionTime - Outer, logs timing
    2. @Retry - Retries on failure
    3. @CatchAndLog - Inner, catches and logs errors

    Example:
        @http_request_stack(logger)
        def get_user(user_id: int):
            return requests.get(f"https://api.example.com/users/{user_id}")
    """
    return (
        DecoratorStack(logger)
        .add_timing(message_template="HTTP request completed in {elapsed:.4f}s")
        .add_retry(max_attempts=3, delay=0.5, backoff=2.0)
        .add_catch_and_log(reraise=False, default_return=None)
    )


def database_operation_stack(logger: Optional[logging.Logger] = None) -> DecoratorStack:
    """
    Create a decorator stack optimized for database operations.

    Stack composition (execution order):
    1. @LogExecutionTime - Outer, logs timing
    2. @Retry - Retries on transient failures
    3. @CatchAndLog - Inner, catches and logs errors

    Example:
        @database_operation_stack(logger)
        def query_users():
            return db.execute("SELECT * FROM users")
    """
    return (
        DecoratorStack(logger)
        .add_timing(message_template="Database query completed in {elapsed:.4f}s")
        .add_retry(max_attempts=3, delay=0.1, backoff=2.0)
        .add_catch_and_log(reraise=False, default_return=None)
    )


def api_endpoint_stack(logger: Optional[logging.Logger] = None) -> DecoratorStack:
    """
    Create a decorator stack optimized for API endpoints/route handlers.

    Stack composition (execution order):
    1. @Trace - Outer, traces function calls
    2. @LogExecutionTime - Logs timing
    3. @CatchAndLog - Inner, catches and logs errors with details

    Example:
        @api_endpoint_stack(logger)
        def get_products():
            return {"products": []}
    """
    return (
        DecoratorStack(logger)
        .add_trace()
        .add_timing(message_template="API endpoint completed in {elapsed:.4f}s")
        .add_catch_and_log(reraise=False, default_return={"error": "Internal error"})
    )


def resilient_operation_stack(logger: Optional[logging.Logger] = None) -> DecoratorStack:
    """
    Create a decorator stack for resilient operations with full error recovery.

    Stack composition (execution order):
    1. @LogExecutionTime - Outer, logs timing
    2. @Retry - Retries with exponential backoff (5 attempts)
    3. @Trace - Traces execution
    4. @CatchAndLog - Inner, catches all errors

    Useful for:
    - External API calls
    - Network operations
    - Distributed system calls

    Example:
        @resilient_operation_stack(logger)
        def call_external_service():
            return requests.post("https://external-api.example.com/data")
    """
    return (
        DecoratorStack(logger)
        .add_timing(message_template="Operation completed in {elapsed:.4f}s")
        .add_retry(max_attempts=5, delay=0.5, backoff=2.0)
        .add_trace()
        .add_catch_and_log(reraise=False, default_return=None)
    )
