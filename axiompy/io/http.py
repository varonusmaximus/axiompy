# @!io

"""
HTTP client utilities with retry logic, auth support, and flexible serialization.

This module provides a comprehensive HTTP client with built-in retry mechanisms,
exponential backoff, and support for authentication, custom headers, and pluggable
serializers/deserializers for flexible payload handling.

Features:
    - **Basic HTTP Methods**: GET, POST, PUT, DELETE, PATCH
    - **Flexible Serialization**: Pass custom serializers for requests, deserializers for responses
    - **Retry Logic**: Configurable exponential backoff
    - **Authentication**: Support for Basic Auth, Bearer tokens, and custom auth
    - **Injectable Headers**: Set default headers and request-specific headers
    - **Type-Safe**: Generic response handling with optional deserialization
    - **Factory Pattern**: Consistent factory for client creation
    - **Comprehensive Logging**: Built-in request/response logging

Quick Examples:
    >>> from axiompy.io import HTTPClientFactory, RetryConfig, DeserializerFactory
    >>>
    >>> # Basic usage (get raw response)
    >>> client = HTTPClientFactory.create(timeout_secs=30)
    >>> response = client.get("https://api.example.com/data")
    >>>
    >>> # With deserializer for JSON parsing
    >>> deserializer = DeserializerFactory.create_json()
    >>> data = client.get("https://api.example.com/data", deserializer=deserializer)
    >>>
    >>> # With auth and headers (fluent chaining)
    >>> client = (
    ...     HTTPClientFactory.create(timeout_secs=30)
    ...     .bearer_token("my_token")
    ...     .add_header("X-API-Key", "secret")
    ...     .add_header("X-API-Version", "v2")
    ... )
    >>> response = client.get("https://api.example.com/data")
    >>>
    >>> # With retry and custom deserializer
    >>> retry_config = RetryConfig().with_max_attempts(5)
    >>> deserializer = DeserializerFactory.create_json()
    >>> data = client.get_with_retry(
    ...     "https://api.example.com/data",
    ...     retry_config=retry_config,
    ...     deserializer=deserializer
    ... )
"""

import contextlib
import time
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, TypeVar, Union

import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from axiompy.decorators import LogExecutionTime
from axiompy.loggers import LoggerFactory

# Import SerializationError for error handling
try:
    from axiompy.io.serialization import SerializationError
except ImportError:
    SerializationError = Exception

logger = LoggerFactory.create_logger(__name__)

if TYPE_CHECKING:
    from axiompy.io.http_async import AsyncHTTPClient

T = TypeVar("T")
Serializer = Callable[[Any], Any]
Deserializer = Callable[[requests.Response], T]


class AuthType(Enum):
    """Supported authentication types."""

    BASIC = "basic"
    DIGEST = "digest"
    BEARER = "bearer"
    CUSTOM = "custom"


class HTTPTransport(StrEnum):
    """Transport selection for :class:`HTTPClientFactory`."""

    SYNC = "sync"
    ASYNC = "async"


@dataclass
class RetryConfig:
    """Retry configuration for HTTP requests."""

    max_attempts: int = 3
    initial_backoff_ms: int = 100
    max_backoff_ms: int = 30000
    backoff_multiplier: float = 2.0
    retry_on_client_error: bool = False

    def calculate_backoff(self, attempt: int) -> float:
        """
        Calculate backoff duration for a given attempt.

        Args:
            attempt: Zero-indexed attempt number

        Returns:
            Backoff duration in seconds
        """
        backoff_ms = self.initial_backoff_ms * (self.backoff_multiplier**attempt)
        backoff_ms = min(backoff_ms, self.max_backoff_ms)
        return backoff_ms / 1000.0

    def should_retry(self, status_code: int) -> bool:
        """
        Check if status code should trigger retry.

        Args:
            status_code: HTTP status code

        Returns:
            True if should retry, False otherwise
        """
        # Always retry on server errors (5xx)
        if 500 <= status_code < 600:
            return True

        # Always retry on rate limiting and timeout
        if status_code in (429, 408):
            return True

        # Retry on client errors if enabled
        return bool(self.retry_on_client_error and 400 <= status_code < 500)

    def with_max_attempts(self, max_attempts: int) -> "RetryConfig":
        """Set maximum number of attempts."""
        self.max_attempts = max_attempts
        return self

    def with_initial_backoff_ms(self, backoff_ms: int) -> "RetryConfig":
        """Set initial backoff duration in milliseconds."""
        self.initial_backoff_ms = backoff_ms
        return self

    def with_max_backoff_ms(self, backoff_ms: int) -> "RetryConfig":
        """Set maximum backoff duration in milliseconds."""
        self.max_backoff_ms = backoff_ms
        return self

    def with_backoff_multiplier(self, multiplier: float) -> "RetryConfig":
        """Set backoff multiplier for exponential backoff."""
        self.backoff_multiplier = multiplier
        return self

    def with_retry_on_client_error(self, retry: bool) -> "RetryConfig":
        """Set whether to retry on client errors."""
        self.retry_on_client_error = retry
        return self


class HTTPClientError(Exception):
    """Base exception for HTTP client errors."""

    pass


class HTTPConnectionError(HTTPClientError):
    """HTTP connection failure."""

    pass


class HTTPRequestError(HTTPClientError):
    """HTTP request execution failure."""

    pass


class HTTPAuthError(HTTPClientError):
    """HTTP authentication failure."""

    pass


@dataclass
class HTTPClientSettings:
    """HTTP client configuration settings."""

    timeout_secs: int = 30
    verify_ssl: bool = True
    allow_redirects: bool = True
    extra_params: Dict[str, Any] = field(default_factory=dict)


class HTTPClient:
    """
    HTTP client wrapper with retry and authentication support.

    Provides a simple interface for making HTTP requests with built-in
    retry logic, exponential backoff, and authentication.
    """

    def __init__(self, settings: HTTPClientSettings):
        """
        Initialize HTTP client.

        Args:
            settings: Client configuration settings
        """
        self.settings = settings
        self.session = requests.Session()
        self.session.timeout = settings.timeout_secs
        self.session.verify = settings.verify_ssl
        self.session.allow_redirects = settings.allow_redirects
        self._default_headers: Dict[str, str] = {}
        self._auth = None
        logger.debug(f"HTTPClient initialized with timeout={settings.timeout_secs}s")

    def __del__(self):
        """Clean up session on object destruction."""
        with contextlib.suppress(Exception):
            self.session.close()

    def add_header(self, key: str, value: str) -> "HTTPClient":
        """
        Add a default header for all requests.

        Supports fluent chaining to add multiple headers in sequence.

        Args:
            key: Header name
            value: Header value

        Returns:
            Self for method chaining

        Examples:
            >>> client = (
            ...     HTTPClientFactory.create()
            ...     .add_header("Authorization", "Bearer token123")
            ...     .add_header("Content-Type", "application/json")
            ...     .add_header("X-Custom-Header", "value")
            ... )
        """
        self._default_headers[key] = value
        self.session.headers.update({key: value})
        logger.debug(f"Added header: {key}")
        return self

    def basic_auth(self, username: str, password: str) -> "HTTPClient":
        """
        Set HTTP Basic Authentication.

        Args:
            username: Username
            password: Password

        Returns:
            Self for method chaining
        """
        self._auth = HTTPBasicAuth(username, password)
        logger.debug(f"Set Basic Auth for user: {username}")
        return self

    def digest_auth(self, username: str, password: str) -> "HTTPClient":
        """
        Set HTTP Digest Authentication.

        Args:
            username: Username
            password: Password

        Returns:
            Self for method chaining
        """
        self._auth = HTTPDigestAuth(username, password)
        logger.debug(f"Set Digest Auth for user: {username}")
        return self

    def bearer_token(self, token: str) -> "HTTPClient":
        """
        Set Bearer Token Authentication.

        Args:
            token: Bearer token

        Returns:
            Self for method chaining
        """
        self.add_header("Authorization", f"Bearer {token}")
        logger.debug("Set Bearer Auth")
        return self

    def custom_auth(self, auth_header: str, auth_value: str) -> "HTTPClient":
        """
        Set custom authentication header.

        Args:
            auth_header: Header name (e.g., "X-API-Key")
            auth_value: Header value

        Returns:
            Self for method chaining
        """
        self.add_header(auth_header, auth_value)
        logger.debug(f"Set Custom Auth with header: {auth_header}")
        return self

    @LogExecutionTime(logger, message_template="GET request to '{url}' completed in {elapsed:.4f}s")
    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        deserializer: Optional[Deserializer] = None,
    ) -> Union[requests.Response, T]:
        """
        Perform a GET request.

        Args:
            url: Target URL
            headers: Request-specific headers (merged with defaults)
            params: Query parameters
            deserializer: Optional function to deserialize response (e.g., response.json)

        Returns:
            Response object, or deserialized response if deserializer provided

        Raises:
            HTTPRequestError: If request fails
        """
        try:
            logger.debug(f"GET request to: {url}")
            response = self.session.get(
                url,
                headers=headers,
                params=params,
                auth=self._auth,
            )
            self._check_response(response)
            return self._deserialize_response(response, deserializer)
        except requests.RequestException as e:
            raise HTTPRequestError(f"GET request failed: {str(e)}")

    @LogExecutionTime(
        logger, message_template="POST request to '{url}' completed in {elapsed:.4f}s"
    )
    def post(
        self,
        url: str,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        serializer: Optional[Serializer] = None,
        deserializer: Optional[Deserializer] = None,
        **kwargs,
    ) -> Union[requests.Response, T]:
        """
        Perform a POST request.

        Args:
            url: Target URL
            data: Request body (form data)
            json: Request body (JSON)
            headers: Request-specific headers
            serializer: Optional function to serialize the json payload before sending
            deserializer: Optional function to deserialize response
            **kwargs: Additional arguments to pass to session.post()

        Returns:
            Response object, or deserialized response if deserializer provided

        Raises:
            HTTPRequestError: If request fails
        """
        try:
            logger.debug(f"POST request to: {url}")
            # Apply serializer if provided and json is present
            if serializer and json is not None:
                json = serializer(json)
            response = self.session.post(
                url,
                data=data,
                json=json,
                headers=headers,
                auth=self._auth,
                **kwargs,
            )
            self._check_response(response)
            return self._deserialize_response(response, deserializer)
        except requests.RequestException as e:
            raise HTTPRequestError(f"POST request failed: {str(e)}")

    @LogExecutionTime(logger, message_template="PUT request to '{url}' completed in {elapsed:.4f}s")
    def put(
        self,
        url: str,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        serializer: Optional[Serializer] = None,
        deserializer: Optional[Deserializer] = None,
        **kwargs,
    ) -> Union[requests.Response, T]:
        """
        Perform a PUT request.

        Args:
            url: Target URL
            data: Request body (form data)
            json: Request body (JSON)
            headers: Request-specific headers
            serializer: Optional function to serialize the json payload before sending
            deserializer: Optional function to deserialize response
            **kwargs: Additional arguments

        Returns:
            Response object, or deserialized response if deserializer provided

        Raises:
            HTTPRequestError: If request fails
        """
        try:
            logger.debug(f"PUT request to: {url}")
            # Apply serializer if provided and json is present
            if serializer and json is not None:
                json = serializer(json)
            response = self.session.put(
                url,
                data=data,
                json=json,
                headers=headers,
                auth=self._auth,
                **kwargs,
            )
            self._check_response(response)
            return self._deserialize_response(response, deserializer)
        except requests.RequestException as e:
            raise HTTPRequestError(f"PUT request failed: {str(e)}")

    @LogExecutionTime(
        logger, message_template="PATCH request to '{url}' completed in {elapsed:.4f}s"
    )
    def patch(
        self,
        url: str,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        serializer: Optional[Serializer] = None,
        deserializer: Optional[Deserializer] = None,
        **kwargs,
    ) -> Union[requests.Response, T]:
        """
        Perform a PATCH request.

        Args:
            url: Target URL
            data: Request body (form data)
            json: Request body (JSON)
            headers: Request-specific headers
            serializer: Optional function to serialize the json payload before sending
            deserializer: Optional function to deserialize response
            **kwargs: Additional arguments

        Returns:
            Response object, or deserialized response if deserializer provided

        Raises:
            HTTPRequestError: If request fails
        """
        try:
            logger.debug(f"PATCH request to: {url}")
            # Apply serializer if provided and json is present
            if serializer and json is not None:
                json = serializer(json)
            response = self.session.patch(
                url,
                data=data,
                json=json,
                headers=headers,
                auth=self._auth,
                **kwargs,
            )
            self._check_response(response)
            return self._deserialize_response(response, deserializer)
        except requests.RequestException as e:
            raise HTTPRequestError(f"PATCH request failed: {str(e)}")

    @LogExecutionTime(
        logger, message_template="DELETE request to '{url}' completed in {elapsed:.4f}s"
    )
    def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        deserializer: Optional[Deserializer] = None,
        **kwargs,
    ) -> Union[requests.Response, T]:
        """
        Perform a DELETE request.

        Args:
            url: Target URL
            headers: Request-specific headers
            deserializer: Optional function to deserialize response
            **kwargs: Additional arguments

        Returns:
            Response object, or deserialized response if deserializer provided

        Raises:
            HTTPRequestError: If request fails
        """
        try:
            logger.debug(f"DELETE request to: {url}")
            response = self.session.delete(
                url,
                headers=headers,
                auth=self._auth,
                **kwargs,
            )
            self._check_response(response)
            return self._deserialize_response(response, deserializer)
        except requests.RequestException as e:
            raise HTTPRequestError(f"DELETE request failed: {str(e)}")

    def get_with_retry(
        self,
        url: str,
        retry_config: Optional[RetryConfig] = None,
        deserializer: Optional[Deserializer] = None,
        **kwargs,
    ) -> Union[requests.Response, T]:
        """
        Perform a GET request with retry logic.

        Args:
            url: Target URL
            retry_config: Retry configuration
            deserializer: Optional function to deserialize response
            **kwargs: Additional arguments to pass to get()

        Returns:
            Response object, or deserialized response if deserializer provided

        Raises:
            HTTPRequestError: If all retry attempts fail
        """
        retry_config = retry_config or RetryConfig()
        return self._retry(lambda: self.get(url, deserializer=deserializer, **kwargs), retry_config)

    def post_with_retry(
        self,
        url: str,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json: Optional[Dict[str, Any]] = None,
        retry_config: Optional[RetryConfig] = None,
        serializer: Optional[Serializer] = None,
        deserializer: Optional[Deserializer] = None,
        **kwargs,
    ) -> Union[requests.Response, T]:
        """
        Perform a POST request with retry logic.

        Args:
            url: Target URL
            data: Request body (form data)
            json: Request body (JSON)
            retry_config: Retry configuration
            serializer: Optional function to serialize the json payload before sending
            deserializer: Optional function to deserialize response
            **kwargs: Additional arguments

        Returns:
            Response object, or deserialized response if deserializer provided

        Raises:
            HTTPRequestError: If all retry attempts fail
        """
        retry_config = retry_config or RetryConfig()
        return self._retry(
            lambda: self.post(
                url,
                data=data,
                json=json,
                serializer=serializer,
                deserializer=deserializer,
                **kwargs,
            ),
            retry_config,
        )

    def put_with_retry(
        self,
        url: str,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json: Optional[Dict[str, Any]] = None,
        retry_config: Optional[RetryConfig] = None,
        serializer: Optional[Serializer] = None,
        deserializer: Optional[Deserializer] = None,
        **kwargs,
    ) -> Union[requests.Response, T]:
        """
        Perform a PUT request with retry logic.

        Args:
            url: Target URL
            data: Request body (form data)
            json: Request body (JSON)
            retry_config: Retry configuration
            serializer: Optional function to serialize the json payload before sending
            deserializer: Optional function to deserialize response
            **kwargs: Additional arguments

        Returns:
            Response object, or deserialized response if deserializer provided

        Raises:
            HTTPRequestError: If all retry attempts fail
        """
        retry_config = retry_config or RetryConfig()
        return self._retry(
            lambda: self.put(
                url,
                data=data,
                json=json,
                serializer=serializer,
                deserializer=deserializer,
                **kwargs,
            ),
            retry_config,
        )

    def patch_with_retry(
        self,
        url: str,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json: Optional[Dict[str, Any]] = None,
        retry_config: Optional[RetryConfig] = None,
        serializer: Optional[Serializer] = None,
        deserializer: Optional[Deserializer] = None,
        **kwargs,
    ) -> Union[requests.Response, T]:
        """
        Perform a PATCH request with retry logic.

        Args:
            url: Target URL
            data: Request body (form data)
            json: Request body (JSON)
            retry_config: Retry configuration
            serializer: Optional function to serialize the json payload before sending
            deserializer: Optional function to deserialize response
            **kwargs: Additional arguments

        Returns:
            Response object, or deserialized response if deserializer provided

        Raises:
            HTTPRequestError: If all retry attempts fail
        """
        retry_config = retry_config or RetryConfig()
        return self._retry(
            lambda: self.patch(
                url,
                data=data,
                json=json,
                serializer=serializer,
                deserializer=deserializer,
                **kwargs,
            ),
            retry_config,
        )

    def delete_with_retry(
        self,
        url: str,
        retry_config: Optional[RetryConfig] = None,
        deserializer: Optional[Deserializer] = None,
        **kwargs,
    ) -> Union[requests.Response, T]:
        """
        Perform a DELETE request with retry logic.

        Args:
            url: Target URL
            retry_config: Retry configuration
            deserializer: Optional function to deserialize response
            **kwargs: Additional arguments

        Returns:
            Response object, or deserialized response if deserializer provided

        Raises:
            HTTPRequestError: If all retry attempts fail
        """
        retry_config = retry_config or RetryConfig()
        return self._retry(
            lambda: self.delete(url, deserializer=deserializer, **kwargs), retry_config
        )

    def _retry(self, func, retry_config: RetryConfig) -> T:
        """
        Retry a function with exponential backoff.

        Args:
            func: Function to retry
            retry_config: Retry configuration

        Returns:
            Result of function call

        Raises:
            HTTPRequestError: If all retry attempts fail
        """

        for attempt in range(retry_config.max_attempts):
            try:
                result = func()
                if attempt > 0:
                    logger.debug(f"Request succeeded on attempt {attempt + 1}")
                return result
            except HTTPRequestError as e:
                should_retry = self._should_retry_error(e, retry_config)

                if not should_retry or attempt >= retry_config.max_attempts - 1:
                    logger.warning(f"Request failed after {attempt + 1} attempts: {str(e)}")
                    raise

                backoff = retry_config.calculate_backoff(attempt)
                logger.warning(
                    f"Request failed (attempt {attempt + 1}), retrying in {backoff:.2f}s: {str(e)}"
                )
                time.sleep(backoff)

        raise HTTPRequestError(f"Request failed after {retry_config.max_attempts} attempts")

    def _should_retry_error(self, error: HTTPRequestError, retry_config: RetryConfig) -> bool:
        """
        Determine if an error should trigger a retry.

        Args:
            error: The error that occurred
            retry_config: Retry configuration

        Returns:
            True if should retry, False otherwise
        """
        error_msg = str(error)
        # Try to extract status code from error message
        for code in [429, 408, 500, 502, 503, 504]:
            if str(code) in error_msg:
                return retry_config.should_retry(code)
        return True

    def _deserialize_response(
        self, response: requests.Response, deserializer: Optional[Deserializer]
    ) -> Any:
        """
        Deserialize response using deserializer if provided.

        Args:
            response: Response object
            deserializer: Optional Deserializer object or callable

        Returns:
            Deserialized response or original response if no deserializer

        Raises:
            HTTPRequestError: If deserialization fails
        """
        if not deserializer:
            return response

        try:
            # Handle both Deserializer objects (with deserialize method) and callable functions
            if hasattr(deserializer, "deserialize"):
                return deserializer.deserialize(response)
            return deserializer(response)
        except SerializationError as e:
            raise HTTPRequestError(f"Failed to deserialize response: {str(e)}")

    def _check_response(self, response: requests.Response) -> None:
        """
        Check response status and raise error if not successful.

        Args:
            response: Response object

        Raises:
            HTTPRequestError: If response status is not 2xx
        """
        if not response.ok:
            try:
                error_text = response.text[:200]
            except Exception:
                error_text = "Unable to read response"

            raise HTTPRequestError(f"HTTP {response.status_code}: {error_text}")


class HTTPClientFactory:
    """
    Factory for creating HTTP clients with fluent configuration.

    Provides a consistent factory pattern for HTTP client creation,
    matching the pattern used by DatabaseFactory, ServerFactory, etc.

    The factory returns HTTPClient instances that support fluent method chaining
    for configuring authentication, headers, and other settings.

    Examples:
        >>> # Basic client
        >>> client = HTTPClientFactory.create(timeout_secs=30)
        >>> response = client.get("https://api.example.com/data")
        >>>
        >>> # With fluent chaining
        >>> client = (
        ...     HTTPClientFactory.create(timeout_secs=30)
        ...     .bearer_token("my_token")
        ...     .default_header("X-API-Key", "secret")
        ... )
        >>> response = client.get("https://api.example.com/data")
        >>>
        >>> # With basic auth and headers
        >>> client = (
        ...     HTTPClientFactory.create(timeout_secs=60)
        ...     .basic_auth("user", "pass")
        ...     .default_header("X-API-Version", "v2")
        ... )
    """

    @staticmethod
    def create(
        timeout_secs: int = 30,
        verify_ssl: bool = True,
        allow_redirects: bool = True,
        *,
        transport: HTTPTransport = HTTPTransport.SYNC,
        settings: Optional[HTTPClientSettings] = None,
    ) -> Union[HTTPClient, "AsyncHTTPClient"]:
        """
        Create a new HTTP client with configuration.

        Supports fluent method chaining for setting authentication, headers, and other options.
        Use ``transport=HTTPTransport.ASYNC`` for :class:`~axiompy.io.http_async.AsyncHTTPClient`
        (requires ``httpx``; install ``axiompy[http-async]``).

        Args:
            timeout_secs: Request timeout in seconds (default: 30); ignored if ``settings`` is set.
            verify_ssl: Whether to verify SSL certificates (default: True)
            allow_redirects: Whether to allow HTTP redirects (default: True)
            transport: ``SYNC`` (``requests``) or ``ASYNC`` (``httpx`` batch client).
            settings: Optional explicit settings; when set, overrides timeout/verify/redirect args.

        Returns:
            :class:`HTTPClient` or :class:`~axiompy.io.http_async.AsyncHTTPClient`

        Examples:
            >>> client = HTTPClientFactory.create(timeout_secs=30)
            >>> response = client.get("https://api.example.com/data")
            >>>
            >>> # Fluent chaining
            >>> response = (
            ...     HTTPClientFactory.create()
            ...     .bearer_token("token")
            ...     .add_header("X-Custom", "value")
            ...     .get("https://api.example.com/data")
            ... )
        """
        resolved = settings or HTTPClientSettings(
            timeout_secs=timeout_secs,
            verify_ssl=verify_ssl,
            allow_redirects=allow_redirects,
        )
        match transport:
            case HTTPTransport.SYNC:
                return HTTPClient(resolved)
            case HTTPTransport.ASYNC:
                from axiompy.io.http_async import AsyncHTTPClient

                return AsyncHTTPClient(resolved)
            case _:
                raise ValueError(f"Unknown HTTP transport: {transport}")
