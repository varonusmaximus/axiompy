# @!code-style

"""
JSON-RPC 2.0 Client implementation with HTTP transport.

Provides a standards-compliant JSON-RPC 2.0 client that can:
    - Make single method calls
    - Send notifications (fire-and-forget)
    - Execute batch requests efficiently
    - Handle retry logic with exponential backoff

Key Benefits:
    - JSON-RPC 2.0 compliant
    - Built on top of HTTPClient for reliability
    - Automatic request ID generation
    - Structured error handling with typed exceptions
    - Fluent API for configuration
    - Factory pattern for consistent creation

Architecture:
    - JSONRPCClient: Core client handling JSON-RPC protocol
    - JSONRPCClientFactory: Factory for creating client instances
    - JSONRPCRequest: Request builder for batch operations

Quick Example:
    >>> from axiompy.io import JSONRPCClientFactory
    >>>
    >>> # Create client
    >>> client = JSONRPCClientFactory.create(
    ...     url="http://localhost:8000/jsonrpc",
    ...     timeout_secs=30
    ... )
    >>>
    >>> # Simple method call
    >>> result = client.call("add", {"a": 1, "b": 2})
    >>> print(result)  # 3
    >>>
    >>> # With authentication
    >>> client = (
    ...     JSONRPCClientFactory.create("http://localhost:8000/jsonrpc")
    ...     .bearer_token("my_token")
    ...     .add_header("X-Custom", "value")
    ... )
    >>> result = client.call("protected_method", {"data": "test"})

For comprehensive examples, see:
    - examples/jsonrpc_client_examples.py - Usage examples
    - tests/test_jsonrpc_client.py - Test patterns
"""

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from axiompy.decorators import LogExecutionTime
from axiompy.io.http import (
    HTTPClient,
    HTTPClientFactory,
    HTTPClientSettings,
    HTTPRequestError,
    RetryConfig,
)
from axiompy.loggers import LoggerFactory
from axiompy.validators import (
    ValidationError,
    ensure_in_range,
    ensure_not_empty,
    ensure_url,
)

logger = LoggerFactory.create_logger(__name__)


# =============================================================================
# JSON-RPC 2.0 Error Codes (per specification)
# =============================================================================


class JSONRPCErrorCode(Enum):
    """
    Standard JSON-RPC 2.0 error codes.

    Standard codes:
        -32700: Parse error - Invalid JSON
        -32600: Invalid Request - Not a valid Request object
        -32601: Method not found
        -32602: Invalid params
        -32603: Internal error

    Server errors (-32000 to -32099):
        -32000: Generic server error
    """

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR = -32000


# =============================================================================
# Exceptions
# =============================================================================


class JSONRPCClientError(Exception):
    """Base exception for JSON-RPC client errors."""

    pass


class JSONRPCConnectionError(JSONRPCClientError):
    """Connection failure to JSON-RPC server."""

    pass


class JSONRPCProtocolError(JSONRPCClientError):
    """JSON-RPC protocol error (invalid response format)."""

    pass


class JSONRPCMethodError(JSONRPCClientError):
    """
    JSON-RPC method execution error.

    Raised when the server returns an error response.

    Attributes:
        code: JSON-RPC error code
        message: Error message from server
        data: Optional additional error data
    """

    def __init__(
        self,
        code: int,
        message: str,
        data: Optional[Any] = None,
        request_id: Optional[Union[str, int]] = None,
    ):
        self.code = code
        self.message = message
        self.data = data
        self.request_id = request_id
        super().__init__(f"JSON-RPC Error {code}: {message}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary representation."""
        error: Dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            error["data"] = self.data
        return error


# =============================================================================
# Settings and Configuration
# =============================================================================


@dataclass
class JSONRPCClientSettings:
    """
    JSON-RPC client configuration.

    Attributes:
        url: JSON-RPC endpoint URL
        timeout_secs: Request timeout in seconds (default: 30)
        verify_ssl: Whether to verify SSL certificates (default: True)
        id_generator: Function to generate request IDs (default: UUID)
        extra_params: Additional parameters for customization
    """

    url: str
    timeout_secs: int = 30
    verify_ssl: bool = True
    id_generator: Optional[Callable[[], Union[str, int]]] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate settings after initialization."""
        try:
            ensure_url(self.url, "Invalid JSON-RPC endpoint URL format")
        except ValidationError as e:
            raise ValueError(str(e))
        try:
            ensure_in_range(
                self.timeout_secs,
                min_value=1,
                max_value=3600,
                message="Timeout must be between 1 and 3600 seconds",
            )
        except ValidationError as e:
            raise ValueError(str(e))
        logger.debug(f"JSONRPCClientSettings validated: url={self.url}")


# =============================================================================
# Request Builder
# =============================================================================


@dataclass
class JSONRPCRequestBuilder:
    """
    Builder for JSON-RPC requests (used in batch operations).

    Attributes:
        method: Method name to call
        params: Optional parameters
        id: Request ID (None for notifications)
        is_notification: Whether this is a notification
    """

    method: str
    params: Optional[Union[Dict[str, Any], List[Any]]] = None
    id: Optional[Union[str, int]] = None
    is_notification: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert request to JSON-RPC format."""
        request: Dict[str, Any] = {"jsonrpc": "2.0", "method": self.method}
        if self.params is not None:
            request["params"] = self.params
        if not self.is_notification and self.id is not None:
            request["id"] = self.id
        return request


# =============================================================================
# Response Parser
# =============================================================================


@dataclass
class JSONRPCResponse:
    """
    Parsed JSON-RPC response.

    Attributes:
        id: Request identifier
        result: Success result (if no error)
        error: Error object (if error occurred)
        is_error: Whether response is an error
    """

    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    @property
    def is_error(self) -> bool:
        """Check if response contains an error."""
        return self.error is not None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JSONRPCResponse":
        """Parse response from dictionary."""
        return cls(
            id=data.get("id"),
            result=data.get("result"),
            error=data.get("error"),
        )


# =============================================================================
# JSON-RPC Client
# =============================================================================


class JSONRPCClient:
    """
    JSON-RPC 2.0 client over HTTP.

    Provides a clean interface for making JSON-RPC calls with support for:
        - Single method calls
        - Notifications (no response expected)
        - Batch requests
        - Retry logic with exponential backoff
        - Authentication via underlying HTTPClient

    Examples:
        >>> client = JSONRPCClient(JSONRPCClientSettings(url="http://localhost:8000/jsonrpc"))
        >>> result = client.call("add", {"a": 1, "b": 2})
        >>> print(result)  # 3
    """

    def __init__(self, settings: JSONRPCClientSettings):
        """
        Initialize JSON-RPC client.

        Args:
            settings: Client configuration
        """
        self.settings = settings
        self._http_client = HTTPClientFactory.create(
            timeout_secs=settings.timeout_secs,
            verify_ssl=settings.verify_ssl,
        )
        self._id_generator = settings.id_generator or self._default_id_generator
        logger.info(f"JSONRPCClient initialized for {settings.url}")

    @staticmethod
    def _default_id_generator() -> str:
        """Generate unique request ID using UUID."""
        return str(uuid.uuid4())

    def _generate_id(self) -> Union[str, int]:
        """Generate a unique request ID."""
        return self._id_generator()

    # =========================================================================
    # Fluent Configuration (delegates to HTTPClient)
    # =========================================================================

    def add_header(self, key: str, value: str) -> "JSONRPCClient":
        """
        Add a default header for all requests.

        Args:
            key: Header name
            value: Header value

        Returns:
            Self for method chaining
        """
        self._http_client.add_header(key, value)
        return self

    def basic_auth(self, username: str, password: str) -> "JSONRPCClient":
        """
        Set HTTP Basic Authentication.

        Args:
            username: Username
            password: Password

        Returns:
            Self for method chaining
        """
        self._http_client.basic_auth(username, password)
        return self

    def bearer_token(self, token: str) -> "JSONRPCClient":
        """
        Set Bearer Token Authentication.

        Args:
            token: Bearer token

        Returns:
            Self for method chaining
        """
        self._http_client.bearer_token(token)
        return self

    def custom_auth(self, auth_header: str, auth_value: str) -> "JSONRPCClient":
        """
        Set custom authentication header.

        Args:
            auth_header: Header name (e.g., "X-API-Key")
            auth_value: Header value

        Returns:
            Self for method chaining
        """
        self._http_client.custom_auth(auth_header, auth_value)
        return self

    # =========================================================================
    # Request Building
    # =========================================================================

    def request(
        self,
        method: str,
        params: Optional[Union[Dict[str, Any], List[Any]]] = None,
    ) -> JSONRPCRequestBuilder:
        """
        Create a request builder for batch operations.

        Args:
            method: Method name to call
            params: Optional parameters (dict for named, list for positional)

        Returns:
            JSONRPCRequestBuilder instance

        Example:
            >>> requests = [
            ...     client.request("add", {"a": 1, "b": 2}),
            ...     client.request("multiply", {"x": 3, "y": 4}),
            ... ]
            >>> results = client.batch(requests)
        """
        return JSONRPCRequestBuilder(
            method=method,
            params=params,
            id=self._generate_id(),
            is_notification=False,
        )

    def notification_request(
        self,
        method: str,
        params: Optional[Union[Dict[str, Any], List[Any]]] = None,
    ) -> JSONRPCRequestBuilder:
        """
        Create a notification request builder (no response expected).

        Args:
            method: Method name to call
            params: Optional parameters

        Returns:
            JSONRPCRequestBuilder instance for notification
        """
        return JSONRPCRequestBuilder(
            method=method,
            params=params,
            id=None,
            is_notification=True,
        )

    # =========================================================================
    # Core Methods
    # =========================================================================

    @LogExecutionTime(logger, message_template="JSON-RPC '{func_name}' completed in {elapsed:.4f}s")
    def call(
        self,
        method: str,
        params: Optional[Union[Dict[str, Any], List[Any]]] = None,
    ) -> Any:
        """
        Make a JSON-RPC method call.

        Args:
            method: Method name to invoke
            params: Optional parameters (dict for named, list for positional)

        Returns:
            Result from the method call

        Raises:
            JSONRPCMethodError: If the server returns an error response
            JSONRPCConnectionError: If connection to server fails
            JSONRPCProtocolError: If response format is invalid
            ValueError: If method name is empty

        Example:
            >>> result = client.call("add", {"a": 1, "b": 2})
            >>> print(result)  # 3
        """
        try:
            ensure_not_empty(method.strip() if method else method, "Method name cannot be empty")
        except ValidationError as e:
            raise ValueError(str(e))

        request_id = self._generate_id()
        request_body = {
            "jsonrpc": "2.0",
            "method": method.strip(),
            "id": request_id,
        }
        if params is not None:
            request_body["params"] = params

        logger.debug(f"JSON-RPC call: method={method.strip()}, id={request_id}")

        try:
            response = self._http_client.post(
                self.settings.url,
                json=request_body,
                headers={"Content-Type": "application/json"},
            )
            return self._parse_response(response.json(), request_id)
        except HTTPRequestError as e:
            raise JSONRPCConnectionError(f"Connection failed: {e}")

    def notify(
        self,
        method: str,
        params: Optional[Union[Dict[str, Any], List[Any]]] = None,
    ) -> None:
        """
        Send a JSON-RPC notification (fire-and-forget).

        Notifications don't expect a response from the server.

        Args:
            method: Method name to invoke
            params: Optional parameters

        Raises:
            JSONRPCConnectionError: If connection to server fails
            ValueError: If method name is empty

        Example:
            >>> client.notify("log", {"message": "User logged in", "level": "info"})
        """
        try:
            ensure_not_empty(method.strip() if method else method, "Method name cannot be empty")
        except ValidationError as e:
            raise ValueError(str(e))

        request_body: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method.strip(),
        }
        if params is not None:
            request_body["params"] = params

        logger.debug(f"JSON-RPC notification: method={method.strip()}")

        try:
            self._http_client.post(
                self.settings.url,
                json=request_body,
                headers={"Content-Type": "application/json"},
            )
        except HTTPRequestError as e:
            raise JSONRPCConnectionError(f"Connection failed: {e}")

    @LogExecutionTime(logger, message_template="JSON-RPC '{func_name}' completed in {elapsed:.4f}s")
    def batch(
        self,
        requests: List[JSONRPCRequestBuilder],
    ) -> List[Tuple[Optional[Union[str, int]], Any, Optional[Dict[str, Any]]]]:
        """
        Execute multiple requests in a single batch call.

        Args:
            requests: List of JSONRPCRequestBuilder instances

        Returns:
            List of tuples: (request_id, result, error)
            - For successful requests: (id, result, None)
            - For failed requests: (id, None, error_dict)
            - Notifications are not included in results

        Raises:
            JSONRPCConnectionError: If connection to server fails
            JSONRPCProtocolError: If batch response format is invalid

        Example:
            >>> requests = [
            ...     client.request("add", {"a": 1, "b": 2}),
            ...     client.request("multiply", {"x": 3, "y": 4}),
            ... ]
            >>> results = client.batch(requests)
            >>> for req_id, result, error in results:
            ...     if error:
            ...         print(f"Error: {error['message']}")
            ...     else:
            ...         print(f"Result: {result}")
        """
        if not requests:
            return []

        batch_body = [req.to_dict() for req in requests]

        # Track which requests expect responses
        non_notification_ids = {req.id for req in requests if not req.is_notification}

        logger.debug(f"JSON-RPC batch: {len(requests)} requests")

        try:
            response = self._http_client.post(
                self.settings.url,
                json=batch_body,
                headers={"Content-Type": "application/json"},
            )

            # Handle empty response (all notifications)
            if response.status_code == 204 or not response.text:
                return []

            response_data = response.json()
            return self._parse_batch_response(response_data, non_notification_ids)
        except HTTPRequestError as e:
            raise JSONRPCConnectionError(f"Connection failed: {e}")

    # =========================================================================
    # Retry Methods
    # =========================================================================

    @LogExecutionTime(logger, message_template="JSON-RPC '{func_name}' completed in {elapsed:.4f}s")
    def call_with_retry(
        self,
        method: str,
        params: Optional[Union[Dict[str, Any], List[Any]]] = None,
        retry_config: Optional[RetryConfig] = None,
    ) -> Any:
        """
        Make a JSON-RPC call with retry logic.

        Args:
            method: Method name to invoke
            params: Optional parameters
            retry_config: Retry configuration (default: 3 attempts)

        Returns:
            Result from the method call

        Raises:
            JSONRPCMethodError: If the server returns an error response
            JSONRPCConnectionError: If all retry attempts fail
            ValueError: If method name is empty

        Example:
            >>> from axiompy.io import RetryConfig
            >>> retry = RetryConfig().with_max_attempts(5)
            >>> result = client.call_with_retry("unreliable_method", {}, retry)
        """
        try:
            ensure_not_empty(method.strip() if method else method, "Method name cannot be empty")
        except ValidationError as e:
            raise ValueError(str(e))

        retry_config = retry_config or RetryConfig()
        request_id = self._generate_id()
        request_body = {
            "jsonrpc": "2.0",
            "method": method.strip(),
            "id": request_id,
        }
        if params is not None:
            request_body["params"] = params

        logger.debug(f"JSON-RPC call with retry: method={method.strip()}, id={request_id}")

        try:
            response = self._http_client.post_with_retry(
                self.settings.url,
                json=request_body,
                headers={"Content-Type": "application/json"},
                retry_config=retry_config,
            )
            return self._parse_response(response.json(), request_id)
        except HTTPRequestError as e:
            raise JSONRPCConnectionError(f"Connection failed after retries: {e}")

    @LogExecutionTime(logger, message_template="JSON-RPC '{func_name}' completed in {elapsed:.4f}s")
    def batch_with_retry(
        self,
        requests: List[JSONRPCRequestBuilder],
        retry_config: Optional[RetryConfig] = None,
    ) -> List[Tuple[Optional[Union[str, int]], Any, Optional[Dict[str, Any]]]]:
        """
        Execute batch requests with retry logic.

        Args:
            requests: List of JSONRPCRequestBuilder instances
            retry_config: Retry configuration (default: 3 attempts)

        Returns:
            List of tuples: (request_id, result, error)

        Raises:
            JSONRPCConnectionError: If all retry attempts fail
        """
        if not requests:
            return []

        retry_config = retry_config or RetryConfig()
        batch_body = [req.to_dict() for req in requests]
        non_notification_ids = {req.id for req in requests if not req.is_notification}

        logger.debug(f"JSON-RPC batch with retry: {len(requests)} requests")

        try:
            response = self._http_client.post_with_retry(
                self.settings.url,
                json=batch_body,
                headers={"Content-Type": "application/json"},
                retry_config=retry_config,
            )

            if response.status_code == 204 or not response.text:
                return []

            response_data = response.json()
            return self._parse_batch_response(response_data, non_notification_ids)
        except HTTPRequestError as e:
            raise JSONRPCConnectionError(f"Connection failed after retries: {e}")

    # =========================================================================
    # Response Parsing
    # =========================================================================

    def _parse_response(
        self,
        data: Dict[str, Any],
        expected_id: Union[str, int],
    ) -> Any:
        """
        Parse a single JSON-RPC response.

        Args:
            data: Response data dictionary
            expected_id: Expected request ID

        Returns:
            Result value from response

        Raises:
            JSONRPCProtocolError: If response format is invalid
            JSONRPCMethodError: If response contains an error
        """
        # Validate response format
        if not isinstance(data, dict):
            raise JSONRPCProtocolError("Response must be an object")

        if data.get("jsonrpc") != "2.0":
            raise JSONRPCProtocolError("Invalid JSON-RPC version in response")

        # Check for error
        if "error" in data:
            error = data["error"]
            raise JSONRPCMethodError(
                code=error.get("code", JSONRPCErrorCode.INTERNAL_ERROR.value),
                message=error.get("message", "Unknown error"),
                data=error.get("data"),
                request_id=data.get("id"),
            )

        # Validate ID matches
        if data.get("id") != expected_id:
            logger.warning(f"Response ID mismatch: expected={expected_id}, got={data.get('id')}")

        return data.get("result")

    def _parse_batch_response(
        self,
        data: Union[List[Dict[str, Any]], Dict[str, Any]],
        expected_ids: set,
    ) -> List[Tuple[Optional[Union[str, int]], Any, Optional[Dict[str, Any]]]]:
        """
        Parse batch response.

        Args:
            data: Response data (list or single response)
            expected_ids: Set of expected request IDs

        Returns:
            List of (id, result, error) tuples
        """
        # Handle single response wrapped in batch call
        if isinstance(data, dict):
            data = [data]

        if not isinstance(data, list):
            raise JSONRPCProtocolError("Batch response must be an array")

        results = []
        for response in data:
            if not isinstance(response, dict):
                continue

            response_id = response.get("id")
            error = response.get("error")
            result = response.get("result")

            if error:
                results.append((response_id, None, error))
            else:
                results.append((response_id, result, None))

        return results


# =============================================================================
# Mock Client for Testing
# =============================================================================


class MockJSONRPCClient(JSONRPCClient):
    """
    Mock JSON-RPC client for unit testing.

    Allows setting predefined responses and tracking calls.

    Example:
        >>> mock = MockJSONRPCClient(JSONRPCClientSettings(url="http://mock"))
        >>> mock.set_response("add", 3)
        >>> result = mock.call("add", {"a": 1, "b": 2})
        >>> print(result)  # 3
        >>> print(mock.calls)  # [("add", {"a": 1, "b": 2})]
    """

    def __init__(self, settings: Optional[JSONRPCClientSettings] = None):
        """Initialize mock client without actual HTTP client."""
        if settings is None:
            settings = JSONRPCClientSettings(url="http://mock-jsonrpc")
        # Don't call super().__init__ to avoid creating real HTTP client
        self.settings = settings
        self._id_generator = settings.id_generator or self._default_id_generator
        self._responses: Dict[str, Any] = {}
        self._errors: Dict[str, JSONRPCMethodError] = {}
        self.calls: List[Tuple[str, Optional[Union[Dict, List]]]] = []
        self.notifications: List[Tuple[str, Optional[Union[Dict, List]]]] = []
        logger.info("MockJSONRPCClient initialized")

    def set_response(self, method: str, result: Any) -> "MockJSONRPCClient":
        """
        Set a predefined response for a method.

        Args:
            method: Method name
            result: Result to return

        Returns:
            Self for method chaining
        """
        self._responses[method] = result
        return self

    def set_error(
        self,
        method: str,
        code: int,
        message: str,
        data: Optional[Any] = None,
    ) -> "MockJSONRPCClient":
        """
        Set a predefined error for a method.

        Args:
            method: Method name
            code: Error code
            message: Error message
            data: Optional error data

        Returns:
            Self for method chaining
        """
        self._errors[method] = JSONRPCMethodError(code, message, data)
        return self

    def call(
        self,
        method: str,
        params: Optional[Union[Dict[str, Any], List[Any]]] = None,
    ) -> Any:
        """Make a mock method call."""
        self.calls.append((method, params))

        if method in self._errors:
            raise self._errors[method]

        if method in self._responses:
            return self._responses[method]

        raise JSONRPCMethodError(
            JSONRPCErrorCode.METHOD_NOT_FOUND.value,
            f"Method '{method}' not found",
        )

    def notify(
        self,
        method: str,
        params: Optional[Union[Dict[str, Any], List[Any]]] = None,
    ) -> None:
        """Send a mock notification."""
        self.notifications.append((method, params))

    def batch(
        self,
        requests: List[JSONRPCRequestBuilder],
    ) -> List[Tuple[Optional[Union[str, int]], Any, Optional[Dict[str, Any]]]]:
        """Execute mock batch request."""
        results = []
        for req in requests:
            if req.is_notification:
                self.notifications.append((req.method, req.params))
                continue

            self.calls.append((req.method, req.params))

            if req.method in self._errors:
                error = self._errors[req.method]
                results.append((req.id, None, error.to_dict()))
            elif req.method in self._responses:
                results.append((req.id, self._responses[req.method], None))
            else:
                results.append(
                    (
                        req.id,
                        None,
                        {
                            "code": JSONRPCErrorCode.METHOD_NOT_FOUND.value,
                            "message": f"Method '{req.method}' not found",
                        },
                    )
                )

        return results

    def call_with_retry(
        self,
        method: str,
        params: Optional[Union[Dict[str, Any], List[Any]]] = None,
        retry_config: Optional[RetryConfig] = None,
    ) -> Any:
        """Mock call with retry (same as call for mock)."""
        return self.call(method, params)

    def batch_with_retry(
        self,
        requests: List[JSONRPCRequestBuilder],
        retry_config: Optional[RetryConfig] = None,
    ) -> List[Tuple[Optional[Union[str, int]], Any, Optional[Dict[str, Any]]]]:
        """Mock batch with retry (same as batch for mock)."""
        return self.batch(requests)

    def reset(self) -> None:
        """Reset all recorded calls and notifications."""
        self.calls.clear()
        self.notifications.clear()


# =============================================================================
# Factory
# =============================================================================


class JSONRPCClientFactory:
    """
    Factory for creating JSON-RPC clients.

    Provides a unified interface for creating clients with different
    configurations while maintaining consistent patterns.

    Examples:
        >>> # Simple client
        >>> client = JSONRPCClientFactory.create(url="http://localhost:8000/jsonrpc")
        >>> result = client.call("add", {"a": 1, "b": 2})
        >>>
        >>> # Client with authentication
        >>> client = (
        ...     JSONRPCClientFactory.create(
        ...         url="http://localhost:8000/jsonrpc",
        ...         timeout_secs=60
        ...     )
        ...     .bearer_token("my_token")
        ...     .add_header("X-Custom", "value")
        ... )
        >>>
        >>> # Mock client for testing
        >>> mock = JSONRPCClientFactory.create_mock()
        >>> mock.set_response("add", 42)
    """

    @staticmethod
    def create(
        url: str,
        timeout_secs: int = 30,
        verify_ssl: bool = True,
        id_generator: Optional[Callable[[], Union[str, int]]] = None,
    ) -> JSONRPCClient:
        """
        Create a JSON-RPC client instance.

        Args:
            url: JSON-RPC endpoint URL
            timeout_secs: Request timeout in seconds (default: 30)
            verify_ssl: Whether to verify SSL certificates (default: True)
            id_generator: Custom function to generate request IDs

        Returns:
            Configured JSONRPCClient instance

        Examples:
            >>> client = JSONRPCClientFactory.create("http://localhost:8000/jsonrpc")
            >>> result = client.call("add", {"a": 1, "b": 2})
        """
        settings = JSONRPCClientSettings(
            url=url,
            timeout_secs=timeout_secs,
            verify_ssl=verify_ssl,
            id_generator=id_generator,
        )
        logger.info(f"Creating JSONRPCClient for {url}")
        return JSONRPCClient(settings)

    @staticmethod
    def create_from_settings(settings: JSONRPCClientSettings) -> JSONRPCClient:
        """
        Create a JSON-RPC client from settings object.

        Args:
            settings: JSONRPCClientSettings instance

        Returns:
            Configured JSONRPCClient instance
        """
        return JSONRPCClient(settings)

    @staticmethod
    def create_mock(
        responses: Optional[Dict[str, Any]] = None,
    ) -> MockJSONRPCClient:
        """
        Create a mock JSON-RPC client for testing.

        Args:
            responses: Optional dict of method -> result mappings

        Returns:
            MockJSONRPCClient instance

        Examples:
            >>> mock = JSONRPCClientFactory.create_mock({"add": 42, "multiply": 12})
            >>> result = mock.call("add", {"a": 1, "b": 2})  # Returns 42
            >>> print(mock.calls)  # [("add", {"a": 1, "b": 2})]
        """
        mock = MockJSONRPCClient()
        if responses:
            for method, result in responses.items():
                mock.set_response(method, result)
        return mock
