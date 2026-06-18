# @!io

"""
File I/O utilities for simplified reading from disk

This module provides a comprehensive set of utilities for reading various file types
with built-in error handling, logging, and sensible defaults.
"""

import csv
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Union

from axiompy.loggers import LoggerFactory
from axiompy.result import Err, Ok, Result
from axiompy.validators import ensure_not_empty

# Optional dependencies
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# Default logger
_default_logger = LoggerFactory.create_logger(__name__)


def set_default_logger(logger: Union[logging.Logger, logging.LoggerAdapter]):
    """
    Set the default logger for all file I/O operations.

    Args:
        logger: Logger instance to use as default

    Example:
        >>> import logging
        >>> from axiompy.io import set_default_logger
        >>> my_logger = logging.getLogger('myapp')
        >>> set_default_logger(my_logger)
    """
    global _default_logger
    _default_logger = logger


def read_text(
    filepath: Union[str, Path],
    encoding: str = "utf-8",
    errors: str = "strict",
    default: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> Optional[str]:
    """
    Read a text file with encoding support and error handling.

    Args:
        filepath: Path to the file to read
        encoding: Text encoding (default: 'utf-8')
        errors: How to handle encoding errors ('strict', 'ignore', 'replace')
        default: Value to return on error (if None, raises exception)
        logger: Logger instance for error messages

    Returns:
        File contents as string, or default value on error

    Raises:
        FileNotFoundError: If file doesn't exist and default is None
        IOError: If file can't be read and default is None

    Example:
        >>> content = read_text('config.txt')
        >>> content = read_text('optional.txt', default='')  # Returns '' on error
    """
    log = logger or _default_logger
    filepath = Path(filepath)

    try:
        with filepath.open("r", encoding=encoding, errors=errors) as f:
            return f.read()
    except FileNotFoundError:
        if default is not None:
            log.warning(f"File not found: {filepath}. Returning default value.")
            return default
        log.error(f"File not found: {filepath}")
        raise
    except Exception as e:
        if default is not None:
            log.warning(f"Error reading {filepath}: {e}. Returning default value.")
            return default
        log.error(f"Error reading {filepath}: {e}")
        raise


def read_json(
    filepath: Union[str, Path],
    encoding: str = "utf-8",
    default: Optional[Union[Dict, List]] = None,
    raise_on_error: bool = True,
    logger: Optional[logging.Logger] = None,
) -> Optional[Union[Dict, List, Any]]:
    """
    Read and parse a JSON file.

    Args:
        filepath: Path to the JSON file
        encoding: Text encoding (default: 'utf-8')
        default: Value to return on error (if None and raise_on_error=False, returns None)
        raise_on_error: Whether to raise exceptions or return default
        logger: Logger instance for error messages

    Returns:
        Parsed JSON data (dict, list, or other JSON type)

    Raises:
        FileNotFoundError: If file doesn't exist and raise_on_error=True
        json.JSONDecodeError: If JSON is invalid and raise_on_error=True

    Example:
        >>> data = read_json('config.json')
        >>> data = read_json('optional.json', default={}, raise_on_error=False)
    """
    log = logger or _default_logger
    filepath = Path(filepath)

    try:
        with filepath.open("r", encoding=encoding) as f:
            return json.load(f)
    except FileNotFoundError:
        log.error(f"JSON file not found: {filepath}")
        if raise_on_error:
            raise
        return default
    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON in {filepath}: {e}")
        if raise_on_error:
            raise
        return default
    except Exception as e:
        log.error(f"Error reading JSON from {filepath}: {e}")
        if raise_on_error:
            raise
        return default


def read_lines(
    filepath: Union[str, Path],
    encoding: str = "utf-8",
    strip: bool = True,
    skip_empty: bool = False,
    logger: Optional[logging.Logger] = None,
) -> Generator[str, None, None]:
    """
    Read file line by line (memory efficient generator).

    Args:
        filepath: Path to the file to read
        encoding: Text encoding (default: 'utf-8')
        strip: Whether to strip whitespace from each line
        skip_empty: Whether to skip empty lines
        logger: Logger instance for error messages

    Yields:
        Lines from the file

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file can't be read

    Example:
        >>> for line in read_lines('large_log.txt'):
        ...     process(line)
        >>> lines = list(read_lines('config.txt', skip_empty=True))
    """
    log = logger or _default_logger
    filepath = Path(filepath)

    try:
        with filepath.open("r", encoding=encoding) as f:
            for line in f:
                if strip:
                    line = line.strip()
                if skip_empty and not line:
                    continue
                yield line
    except Exception as e:
        log.error(f"Error reading lines from {filepath}: {e}")
        raise


def read_csv(
    filepath: Union[str, Path],
    delimiter: str = ",",
    has_header: bool = True,
    encoding: str = "utf-8",
    logger: Optional[logging.Logger] = None,
) -> List[Dict[str, Any]]:
    """
    Read a CSV file into a list of dictionaries.

    Args:
        filepath: Path to the CSV file
        delimiter: Field delimiter (default: ',')
        has_header: Whether the first row contains headers
        encoding: Text encoding (default: 'utf-8')
        logger: Logger instance for error messages

    Returns:
        List of dictionaries (one per row)
        If no header, uses keys: 'column_0', 'column_1', etc.

    Raises:
        FileNotFoundError: If file doesn't exist
        csv.Error: If CSV is malformed

    Example:
        >>> data = read_csv('data.csv')
        >>> for row in data:
        ...     print(row['name'], row['age'])
    """
    log = logger or _default_logger
    filepath = Path(filepath)

    try:
        with filepath.open("r", encoding=encoding, newline="") as f:
            if has_header:
                reader = csv.DictReader(f, delimiter=delimiter)
                return list(reader)
            else:
                reader = csv.reader(f, delimiter=delimiter)
                rows = list(reader)
                if not rows:
                    return []
                # Create column names
                num_cols = len(rows[0]) if rows else 0
                headers = [f"column_{i}" for i in range(num_cols)]
                return [dict(zip(headers, row, strict=False)) for row in rows]
    except Exception as e:
        log.error(f"Error reading CSV from {filepath}: {e}")
        raise


def read_yaml(
    filepath: Union[str, Path],
    encoding: str = "utf-8",
    default: Optional[Dict] = None,
    raise_on_error: bool = True,
    logger: Optional[logging.Logger] = None,
) -> Optional[Dict]:
    """
    Read and parse a YAML file.

    Requires PyYAML to be installed. Uses safe_load for security.

    Args:
        filepath: Path to the YAML file
        encoding: Text encoding (default: 'utf-8')
        default: Value to return on error
        raise_on_error: Whether to raise exceptions or return default
        logger: Logger instance for error messages

    Returns:
        Parsed YAML data as dictionary

    Raises:
        ImportError: If PyYAML is not installed
        FileNotFoundError: If file doesn't exist and raise_on_error=True
        yaml.YAMLError: If YAML is invalid and raise_on_error=True

    Example:
        >>> config = read_yaml('config.yaml')
        >>> config = read_yaml('optional.yaml', default={}, raise_on_error=False)
    """
    if not HAS_YAML:
        raise ImportError("PyYAML is required for read_yaml. Install it with: pip install pyyaml")

    log = logger or _default_logger
    filepath = Path(filepath)

    try:
        with filepath.open("r", encoding=encoding) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        log.error(f"YAML file not found: {filepath}")
        if raise_on_error:
            raise
        return default
    except yaml.YAMLError as e:
        log.error(f"Invalid YAML in {filepath}: {e}")
        if raise_on_error:
            raise
        return default
    except Exception as e:
        log.error(f"Error reading YAML from {filepath}: {e}")
        if raise_on_error:
            raise
        return default


def read_binary(
    filepath: Union[str, Path],
    chunk_size: Optional[int] = None,
    logger: Optional[logging.Logger] = None,
) -> Union[bytes, Generator[bytes, None, None]]:
    """
    Read a binary file.

    Args:
        filepath: Path to the binary file
        chunk_size: If specified, returns a generator yielding chunks of this size
        logger: Logger instance for error messages

    Returns:
        Complete file contents as bytes, or generator yielding byte chunks

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file can't be read

    Example:
        >>> data = read_binary('image.png')
        >>> for chunk in read_binary('large_file.bin', chunk_size=8192):
        ...     process(chunk)
    """
    log = logger or _default_logger
    filepath = Path(filepath)

    try:
        if chunk_size is None:
            with filepath.open("rb") as f:
                return f.read()
        else:

            def chunk_generator():
                with filepath.open("rb") as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk

            return chunk_generator()
    except Exception as e:
        log.error(f"Error reading binary file {filepath}: {e}")
        raise


def safe_read(
    filepath: Union[str, Path],
    default: Any = None,
    parser: Optional[Callable[[str], Any]] = None,
    encoding: str = "utf-8",
    logger: Optional[logging.Logger] = None,
) -> Any:
    """
    Safely read a file, never raising exceptions.

    This is a defensive read operation that always succeeds, returning
    the default value on any error.

    Args:
        filepath: Path to the file to read
        default: Value to return on any error (default: None)
        parser: Optional function to parse the file contents
        encoding: Text encoding (default: 'utf-8')
        logger: Logger instance for error messages

    Returns:
        Parsed file contents, or default value on error

    Example:
        >>> content = safe_read('config.txt', default='# default config')
        >>> data = safe_read('data.json', parser=json.loads, default={})
        >>> number = safe_read('count.txt', parser=int, default=0)
    """
    log = logger or _default_logger
    filepath = Path(filepath)

    try:
        with filepath.open("r", encoding=encoding) as f:
            content = f.read()
            if parser:
                return parser(content)
            return content
    except Exception as e:
        log.debug(f"safe_read: Error reading {filepath}: {e}. Returning default.")
        return default


def read_multiple(
    filepaths: List[Union[str, Path]],
    reader_func: Callable = read_text,
    fail_fast: bool = False,
    logger: Optional[logging.Logger] = None,
    **reader_kwargs,
) -> Dict[str, Any]:
    """
    Read multiple files in batch.

    Args:
        filepaths: List of file paths to read
        reader_func: Function to use for reading (default: read_text)
        fail_fast: If True, stop on first error; if False, continue and log errors
        logger: Logger instance for error messages
        **reader_kwargs: Additional arguments to pass to reader_func

    Returns:
        Dictionary mapping filepath (as string) to file contents
        Failed reads are excluded from results (unless fail_fast=True)

    Raises:
        Exception: Any exception from reader_func if fail_fast=True

    Example:
        >>> files = read_multiple(['a.txt', 'b.txt', 'c.txt'])
        >>> json_files = read_multiple(['1.json', '2.json'], reader_func=read_json)
        >>> files = read_multiple(['a.txt', 'b.txt'], encoding='latin-1')
    """
    log = logger or _default_logger
    results = {}

    for filepath in filepaths:
        filepath_str = str(filepath)
        try:
            results[filepath_str] = reader_func(filepath, logger=log, **reader_kwargs)
        except Exception as e:
            if fail_fast:
                log.error(f"Error reading {filepath}: {e}")
                raise
            log.warning(f"Skipping {filepath} due to error: {e}")

    return results


def read_with_path_expansion(
    filepath: str,
    allow_env_vars: bool = True,
    allow_home: bool = True,
    encoding: str = "utf-8",
    logger: Optional[logging.Logger] = None,
) -> str:
    """
    Read a file with path expansion (environment variables and ~).

    Args:
        filepath: Path string that may contain ~ or environment variables
        allow_env_vars: Whether to expand environment variables ($VAR or ${VAR})
        allow_home: Whether to expand ~ to home directory
        encoding: Text encoding (default: 'utf-8')
        logger: Logger instance for error messages

    Returns:
        File contents as string

    Raises:
        FileNotFoundError: If expanded path doesn't exist
        IOError: If file can't be read

    Example:
        >>> content = read_with_path_expansion('~/config.txt')
        >>> content = read_with_path_expansion('$HOME/data.txt')
        >>> content = read_with_path_expansion('${CONFIG_DIR}/app.conf')
    """
    log = logger or _default_logger

    # Expand environment variables
    if allow_env_vars:
        filepath = os.path.expandvars(filepath)

    # Expand home directory
    if allow_home:
        filepath = os.path.expanduser(filepath)

    log.debug(f"Expanded path: {filepath}")
    return read_text(filepath, encoding=encoding, logger=log)


class CachedReader:
    """
    File reader with in-memory caching.

    Caches file contents in memory to avoid repeated disk reads.
    Useful for frequently accessed configuration files.

    Attributes:
        ttl: Default time-to-live for cache entries (seconds), None for no expiry
        logger: Logger instance for debug messages

    Example:
        >>> reader = CachedReader(ttl=300)  # 5 minute cache
        >>> config = reader.read('config.json', parser=json.loads)
        >>> # Second call uses cache
        >>> config = reader.read('config.json', parser=json.loads)
        >>> reader.clear_cache('config.json')  # Clear specific file
        >>> reader.clear_cache()  # Clear all
    """

    def __init__(
        self,
        ttl: Optional[int] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the cached reader.

        Args:
            ttl: Time-to-live for cache entries in seconds (None = no expiry)
            logger: Logger instance for debug messages
        """
        self.ttl = ttl
        self.logger = logger or _default_logger
        self._cache: Dict[str, Dict[str, Any]] = {}

    def read(
        self,
        filepath: Union[str, Path],
        parser: Optional[Callable[[str], Any]] = None,
        encoding: str = "utf-8",
        ttl: Optional[int] = None,
    ) -> Any:
        """
        Read a file with caching.

        Args:
            filepath: Path to the file to read
            parser: Optional function to parse the file contents
            encoding: Text encoding (default: 'utf-8')
            ttl: Time-to-live override for this specific read (None uses instance ttl)

        Returns:
            File contents (parsed if parser provided)

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file can't be read
        """
        filepath = Path(filepath)
        cache_key = str(filepath.absolute())
        ttl_to_use = ttl if ttl is not None else self.ttl

        # Check if cached and not expired
        if cache_key in self._cache:
            cache_entry = self._cache[cache_key]
            cached_time = cache_entry["time"]

            if ttl_to_use is None or (time.time() - cached_time) < ttl_to_use:
                self.logger.debug(f"Cache hit: {filepath}")
                return cache_entry["data"]
            else:
                self.logger.debug(f"Cache expired: {filepath}")

        # Read from disk
        self.logger.debug(f"Cache miss: {filepath}")
        content = read_text(filepath, encoding=encoding, logger=self.logger)

        # Parse if needed
        data = parser(content) if parser else content

        # Store in cache
        self._cache[cache_key] = {
            "data": data,
            "time": time.time(),
        }

        return data

    def clear_cache(self, filepath: Optional[Union[str, Path]] = None):
        """
        Clear the cache.

        Args:
            filepath: Specific file to clear, or None to clear all

        Example:
            >>> reader.clear_cache('config.json')  # Clear one file
            >>> reader.clear_cache()  # Clear everything
        """
        if filepath is None:
            self._cache.clear()
            self.logger.debug("Cleared all cache entries")
        else:
            cache_key = str(Path(filepath).absolute())
            if cache_key in self._cache:
                del self._cache[cache_key]
                self.logger.debug(f"Cleared cache for: {filepath}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (size, entries, etc.)
        """
        return {
            "num_entries": len(self._cache),
            "files": list(self._cache.keys()),
        }


# ============================================================================
# Result-Based File Operations (Railway-Oriented Programming)
# ============================================================================


def try_read_text(
    filepath: Union[str, Path],
    encoding: str = "utf-8",
    errors: str = "strict",
    logger: Optional[logging.Logger] = None,
) -> Result[str, str]:
    """
    Read a text file with Result-based error handling.

    Returns Ok with file contents or Err with error message.
    Never raises exceptions - all errors are returned in Err.

    Args:
        filepath: Path to the file to read
        encoding: Text encoding (default: 'utf-8')
        errors: How to handle encoding errors ('strict', 'ignore', 'replace')
        logger: Logger instance for messages

    Returns:
        Result[str, str]: Ok(contents) on success, Err(message) on failure

    Example:
        >>> result = try_read_text('config.txt')
        >>> if result.is_ok():
        ...     config = result.unwrap()
        ... else:
        ...     print(f"Error: {result.get_error()}")
    """
    log = logger or _default_logger
    filepath = Path(filepath)

    ensure_not_empty(str(filepath), "filepath cannot be empty")

    try:
        with filepath.open("r", encoding=encoding, errors=errors) as f:
            content = f.read()
            log.debug(f"Successfully read {len(content)} bytes from {filepath}")
            return Ok(content)
    except FileNotFoundError:
        msg = f"File not found: {filepath}"
        log.warning(msg)
        return Err(msg)
    except PermissionError:
        msg = f"Permission denied reading: {filepath}"
        log.warning(msg)
        return Err(msg)
    except UnicodeDecodeError as e:
        msg = f"Encoding error in {filepath}: {str(e)}"
        log.warning(msg)
        return Err(msg)
    except OSError as e:
        msg = f"IO error reading {filepath}: {str(e)}"
        log.error(msg)
        return Err(msg)
    except Exception as e:
        msg = f"Failed to read {filepath}: {str(e)}"
        log.error(msg)
        return Err(msg)


def try_read_json(
    filepath: Union[str, Path],
    encoding: str = "utf-8",
    logger: Optional[logging.Logger] = None,
) -> Result[Dict, str]:
    """
    Read a JSON file with Result-based error handling.

    Returns Ok with parsed JSON or Err with error message.

    Args:
        filepath: Path to the JSON file
        encoding: Text encoding (default: 'utf-8')
        logger: Logger instance for messages

    Returns:
        Result[Dict, str]: Ok(data) on success, Err(message) on failure

    Example:
        >>> result = try_read_json('data.json')
        >>> data = result.unwrap_or({})  # Empty dict if error
    """
    log = logger or _default_logger
    filepath = Path(filepath)

    return try_read_text(filepath, encoding=encoding, logger=log).then(
        lambda content: try_parse_json(content, filepath, log)
    )


def try_parse_json(
    content: str,
    filepath: Optional[Union[str, Path]] = None,
    logger: Optional[logging.Logger] = None,
) -> Result[Dict, str]:
    """
    Parse JSON content with Result-based error handling.

    Args:
        content: JSON string to parse
        filepath: Optional filepath for error messages
        logger: Logger instance for messages

    Returns:
        Result[Dict, str]: Ok(data) on success, Err(message) on failure
    """
    log = logger or _default_logger
    location = f" in {filepath}" if filepath else ""

    try:
        data = json.loads(content)
        log.debug(f"Successfully parsed JSON{location}")
        return Ok(data)
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON{location}: {str(e)}"
        log.warning(msg)
        return Err(msg)
    except Exception as e:
        msg = f"JSON parsing error{location}: {str(e)}"
        log.error(msg)
        return Err(msg)
