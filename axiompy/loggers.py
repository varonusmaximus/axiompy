# @!core

"""
Logger Factory Module

This module provides a flexible and extensible factory pattern for creating and configuring
Python loggers with multiple handlers (console, file, Splunk, etc.).

The factory pattern allows for easy addition of new handler types and consistent logger
configuration across your application.

Example:
    Basic console logger:
        >>> logger = LoggerFactory.create_logger("my_app")
        >>> logger.info("Application started")

    Logger with file output:
        >>> settings = {"file_path": "/var/log/app.log"}
        >>> logger = LoggerFactory.create_logger("my_app", settings=settings)

    Logger with extra context fields:
        >>> settings = {"extra": {"service": "api", "env": "production"}}
        >>> logger = LoggerFactory.create_logger("my_app", settings=settings)
        >>> logger.info("Request processed")
"""

import logging
import sys
from abc import ABC, abstractmethod
from logging import DEBUG
from pathlib import Path
from typing import Dict, Optional

try:
    from tqdm import tqdm

    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


class BaseLogHandler(ABC):
    """
    Abstract base class for creating custom logging handlers.

    This class defines the interface for log handler creators and provides common
    functionality for setting handler properties and formatting log messages.

    To create a custom handler, subclass this class and implement the create_handler() method.

    Example:
        >>> class CustomLogHandler(BaseLogHandler):
        ...     def create_handler(self):
        ...         # Return your custom handler instance
        ...         return MyCustomHandler()
    """

    @abstractmethod
    def create_handler(self) -> None:
        """
        Create and return a logging handler instance.

        This method must be implemented by subclasses to create their specific
        handler type (e.g., StreamHandler, FileHandler, custom handlers).

        Returns:
            logging.Handler: A configured logging handler instance, or None if
                           the handler cannot be created.

        Raises:
            NotImplementedError: If the subclass doesn't implement this method.
        """
        raise NotImplementedError

    def set_handler_properties(self, handler, logger, extra: Optional[Dict]) -> None:
        """
        Configure and attach a handler to a logger with formatting and extra fields.

        This method:
        1. Creates a formatted log message pattern including any extra context fields
        2. Applies the formatter to the handler
        3. Attaches the handler to the logger (avoiding duplicates)

        The default log format is:
            "timestamp - logger_name - level - [extra_fields] - message"

        Args:
            handler (logging.Handler): The logging handler to configure
            logger (logging.Logger): The logger to attach the handler to
            extra (Optional[Dict]): Dictionary of extra contextual fields to include
                                   in log messages (e.g., {"service": "api", "env": "prod"})

        Note:
            Handlers of the same type are not added multiple times to prevent
            duplicate log entries.
        """
        extra_format = self._get_extra_format(extra)
        formatter = logging.Formatter(
            f"%(asctime)s - %(name)s - %(levelname)s{extra_format} - %(message)s"
        )
        handler.setFormatter(formatter)

        # Only add handler if this type doesn't already exist (prevent duplicates)
        if not any(isinstance(h, type(handler)) for h in logger.handlers):
            logger.addHandler(handler)

    def _get_extra_format(self, extra: Optional[Dict]) -> str:
        """
        Generate format string for extra contextual fields in log messages.

        Converts a dictionary of extra fields into a format string that can be
        used by logging.Formatter to include those fields in log output.

        Args:
            extra (Optional[Dict]): Dictionary of extra field names and values.
                                   Keys become field names in the log output.

        Returns:
            str: A formatted string for inclusion in the log format pattern.
                Empty string if no extra fields are provided.
                Format: " - key1: %(key1)s - key2: %(key2)s"

        Example:
            >>> extra = {"service": "api", "request_id": "12345"}
            >>> self._get_extra_format(extra)
            ' - service: %(service)s - request_id: %(request_id)s'
        """
        return "" if not extra else f" - {' - '.join(f'{key}: %({key})s' for key in extra)}"


class ConsoleLogHandler(BaseLogHandler):
    """
    Handler creator for console/stdout logging.

    Creates a StreamHandler that writes log messages to standard output (stdout).
    This is useful for applications running in containers, cloud environments,
    or when you want logs visible in the terminal.

    Example:
        >>> handler_creator = ConsoleLogHandler()
        >>> handler = handler_creator.create_handler()
    """

    def create_handler(self) -> logging.StreamHandler:
        """
        Create a StreamHandler that outputs to stdout.

        Returns:
            logging.StreamHandler: A handler configured to write to standard output.

        Note:
            Uses sys.stdout instead of sys.stderr to separate application logs
            from error streams.
        """
        return logging.StreamHandler(sys.stdout)


class TqdmLoggingHandler(logging.Handler):
    """
    Custom logging handler that writes through tqdm to avoid breaking progress bars.

    This handler ensures that log messages don't interfere with tqdm progress bars
    by using tqdm.write() instead of directly writing to stdout/stderr.

    When tqdm is not available, falls back to standard stream writing.
    """

    def emit(self, record):
        """
        Emit a log record using tqdm.write() to avoid interfering with progress bars.

        Args:
            record: The LogRecord to be emitted.
        """
        try:
            msg = self.format(record)
            if TQDM_AVAILABLE:
                tqdm.write(msg, file=sys.stdout)
            else:
                # Fallback to regular print if tqdm not available
                print(msg, file=sys.stdout)
        except Exception:
            self.handleError(record)


class TqdmLogHandler(BaseLogHandler):
    """
    Handler creator for tqdm-compatible console logging.

    Creates a logging handler that outputs to stdout via tqdm.write(), ensuring
    that log messages don't interfere with tqdm progress bars. This is essential
    when using tqdm progress bars alongside logging in the same terminal.

    Example:
        >>> handler_creator = TqdmLogHandler()
        >>> handler = handler_creator.create_handler()

        >>> # Use with tqdm progress bars
        >>> from tqdm import tqdm
        >>> logger = LoggerFactory.create_logger("my_app", use_tqdm=True)
        >>> for i in tqdm(range(100)):
        ...     logger.info(f"Processing item {i}")  # Won't break the progress bar!

    Note:
        Requires tqdm to be installed. If tqdm is not available, falls back to
        regular console output.
    """

    def create_handler(self) -> logging.Handler:
        """
        Create a TqdmLoggingHandler for tqdm-compatible output.

        Returns:
            TqdmLoggingHandler: A handler that uses tqdm.write() for output.
        """
        return TqdmLoggingHandler()


class SplunkLogHandler(BaseLogHandler):
    """
    Handler creator for Splunk logging integration.

    Placeholder for future Splunk integration. When implemented, this will create
    a handler that sends logs to a Splunk HTTP Event Collector (HEC) or other
    Splunk ingestion endpoint.

    TODO: Implement Splunk handler creation
          - Add Splunk HEC endpoint configuration
          - Add authentication token support
          - Add batch/async logging support

    Note:
        Currently returns None, which causes the factory to skip this handler.
    """

    def create_handler(self) -> None:
        """
        Create a Splunk logging handler.

        Returns:
            None: Not yet implemented. Returns None to indicate handler unavailable.

        TODO: Implement Splunk handler (e.g., using splunk-handler library or custom HTTP handler)
        """
        # Placeholder - return None so factory skips this handler
        return None


class FileLogHandler(BaseLogHandler):
    """
    Handler creator for file-based logging.

    Creates a FileHandler that writes log messages to a specified file path.
    Useful for persistent log storage, debugging, and audit trails.

    Args:
        file_path (str): Path to the log file. Parent directories must exist.

    Example:
        >>> handler_creator = FileLogHandler("/var/log/myapp.log")
        >>> handler = handler_creator.create_handler()

    Note:
        The file will be created if it doesn't exist, and logs will be appended
        to existing content (mode='a' by default).
    """

    def __init__(self, file_path: str) -> None:
        """
        Initialize the file handler creator with a target file path.

        Args:
            file_path (str): Absolute or relative path to the log file.
        """
        self.file_path = file_path

    def create_handler(self) -> logging.FileHandler:
        """
        Create a FileHandler that writes to the configured file path.

        Returns:
            logging.FileHandler: A handler configured to write to the specified file.

        Raises:
            IOError: If the file cannot be created or written to.
            PermissionError: If there are insufficient permissions to write to the file.
        """
        return logging.FileHandler(self.file_path)


class LoggerFactory:
    """
    Factory class for creating and configuring application loggers.

    Provides a centralized way to create loggers with consistent formatting,
    multiple output handlers (console, file, etc.), and contextual extra fields.

    The factory automatically configures:
        - Console output (stdout)
        - Optional file output
        - Optional Splunk integration (placeholder)
        - Custom formatting with extra context fields

    Examples:
        Basic logger:
            >>> logger = LoggerFactory.create_logger("my_service")
            >>> logger.info("Service started")

        Logger with file output:
            >>> logger = LoggerFactory.create_logger(
            ...     "my_service",
            ...     level=logging.INFO,
            ...     settings={"file_path": "/var/log/service.log"}
            ... )

        Logger with extra context fields:
            >>> logger = LoggerFactory.create_logger(
            ...     "my_service",
            ...     settings={"extra": {"env": "prod", "version": "1.0"}}
            ... )
            >>> logger.info("Request processed")  # Will include env and version in output
    """

    @staticmethod
    def create_logger(
        name: str, level: int = DEBUG, settings: Optional[Dict] = None, use_tqdm: bool = False
    ) -> logging.LoggerAdapter:
        """
        Create a fully configured logger with multiple handlers and extra context.

        This method creates a logger with:
        1. Console output (always enabled) or tqdm-compatible output (if use_tqdm=True)
        2. File output (only when file_path is explicitly provided in settings)
        3. Splunk output (placeholder for future implementation)
        4. Custom extra fields that appear in all log messages

        Args:
            name (str): Name of the logger (typically module name or service name).
                       Use __name__ for automatic naming based on module.
            level (int, optional): Minimum logging level. Defaults to DEBUG.
                                  Use logging constants: DEBUG, INFO, WARNING, ERROR, CRITICAL
            settings (Optional[Dict], optional): Configuration dictionary supporting:
                - "file_path" (str): Path to log file for file-based logging
                - "extra" (Dict): Extra fields to include in every log message
                                 (e.g., {"service": "api", "env": "production"})
            use_tqdm (bool, optional): If True, uses TqdmLogHandler instead of
                                      ConsoleLogHandler to prevent log messages
                                      from interfering with tqdm progress bars.
                                      Defaults to False.

        Returns:
            logging.LoggerAdapter: A LoggerAdapter instance that wraps the configured
                                  logger with extra context fields.

        Example:
            >>> logger = LoggerFactory.create_logger(
            ...     name="payment_service",
            ...     level=logging.INFO,
            ...     settings={
            ...         "file_path": "/var/log/payments.log",
            ...         "extra": {"service": "payment", "env": "prod"}
            ...     }
            ... )
            >>> logger.info("Payment processed", extra={"amount": 100.00})

            Using with tqdm progress bars:
            >>> from tqdm import tqdm
            >>> logger = LoggerFactory.create_logger("my_app", use_tqdm=True)
            >>> for i in tqdm(range(100)):
            ...     logger.info(f"Processing item {i}")

        Note:
            - Logger propagation is disabled (propagate=False) to prevent duplicate
              log messages in hierarchical logger setups
            - Handlers are only added once (duplicates are prevented)
            - The LoggerAdapter allows extra fields to be included automatically
            - When use_tqdm=True, requires tqdm to be installed for optimal behavior
        """
        settings = settings or {}
        extra = settings.get("extra", {})
        file_path = settings.get("file_path")

        # Initialize handler creators
        # Use TqdmLogHandler if requested, otherwise use ConsoleLogHandler
        console_handler = TqdmLogHandler() if use_tqdm else ConsoleLogHandler()

        handler_creators = [
            console_handler,
            SplunkLogHandler(),
        ]

        # Only add file handler when file_path is explicitly provided
        if file_path:
            log_dir = Path(file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            handler_creators.append(FileLogHandler(file_path))

        # Get or create the base logger
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False  # Prevent duplicate logs in parent loggers

        # Create and configure all handlers
        for handler_creator in handler_creators:
            handler = handler_creator.create_handler()
            if handler:  # Only configure if handler was successfully created
                handler_creator.set_handler_properties(handler, logger, extra)

        # Return a LoggerAdapter to support extra fields in all log calls
        return logging.LoggerAdapter(logger, extra)
