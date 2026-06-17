# @!testing

"""
Comprehensive tests for JSON-RPC Client.

Tests cover:
    - Client creation and settings validation
    - Single method calls (success and error)
    - Notifications
    - Batch requests
    - Retry logic
    - Error handling (all error types)
    - Mock client functionality
    - Factory methods
    - Fluent API configuration
    - Response parsing
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from axiompy.io.jsonrpc import (
    JSONRPCClient,
    JSONRPCClientError,
    JSONRPCClientFactory,
    JSONRPCClientSettings,
    JSONRPCConnectionError,
    JSONRPCErrorCode,
    JSONRPCMethodError,
    JSONRPCProtocolError,
    JSONRPCRequestBuilder,
    JSONRPCResponse,
    MockJSONRPCClient,
)
from axiompy.io.http import HTTPRequestError, RetryConfig


# =============================================================================
# Settings Tests
# =============================================================================


class TestJSONRPCClientSettings:
    """Tests for JSONRPCClientSettings configuration."""

    def test_valid_settings(self):
        """Test creating settings with valid parameters."""
        settings = JSONRPCClientSettings(
            url="http://localhost:8000/jsonrpc",
            timeout_secs=30,
            verify_ssl=True,
        )
        assert settings.url == "http://localhost:8000/jsonrpc"
        assert settings.timeout_secs == 30
        assert settings.verify_ssl is True
        assert settings.id_generator is None
        assert settings.extra_params == {}

    def test_settings_empty_url_raises(self):
        """Test that empty URL raises ValueError."""
        with pytest.raises(ValueError, match="Invalid"):
            JSONRPCClientSettings(url="")

    def test_settings_invalid_url_format_raises(self):
        """Test that invalid URL format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid"):
            JSONRPCClientSettings(url="not-a-valid-url")

        with pytest.raises(ValueError, match="Invalid"):
            JSONRPCClientSettings(url="just-text")

    def test_settings_invalid_timeout_raises(self):
        """Test that non-positive timeout raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be between"):
            JSONRPCClientSettings(url="http://localhost", timeout_secs=0)

        with pytest.raises(ValueError, match="Timeout must be between"):
            JSONRPCClientSettings(url="http://localhost", timeout_secs=-5)

    def test_settings_timeout_too_large_raises(self):
        """Test that timeout > 3600 raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be between"):
            JSONRPCClientSettings(url="http://localhost", timeout_secs=4000)

    def test_settings_custom_id_generator(self):
        """Test settings with custom ID generator."""
        counter = [0]

        def custom_generator():
            counter[0] += 1
            return counter[0]

        settings = JSONRPCClientSettings(
            url="http://localhost",
            id_generator=custom_generator,
        )
        assert settings.id_generator is not None
        assert settings.id_generator() == 1
        assert settings.id_generator() == 2

    def test_settings_extra_params(self):
        """Test settings with extra parameters."""
        settings = JSONRPCClientSettings(
            url="http://localhost",
            extra_params={"custom": "value", "debug": True},
        )
        assert settings.extra_params == {"custom": "value", "debug": True}


# =============================================================================
# Request Builder Tests
# =============================================================================


class TestJSONRPCRequestBuilder:
    """Tests for JSONRPCRequestBuilder."""

    def test_request_with_dict_params(self):
        """Test request builder with dictionary parameters."""
        request = JSONRPCRequestBuilder(
            method="add",
            params={"a": 1, "b": 2},
            id="req-123",
            is_notification=False,
        )
        result = request.to_dict()

        assert result == {
            "jsonrpc": "2.0",
            "method": "add",
            "params": {"a": 1, "b": 2},
            "id": "req-123",
        }

    def test_request_with_list_params(self):
        """Test request builder with list parameters."""
        request = JSONRPCRequestBuilder(
            method="add",
            params=[1, 2, 3],
            id="req-456",
            is_notification=False,
        )
        result = request.to_dict()

        assert result == {
            "jsonrpc": "2.0",
            "method": "add",
            "params": [1, 2, 3],
            "id": "req-456",
        }

    def test_request_without_params(self):
        """Test request builder without parameters."""
        request = JSONRPCRequestBuilder(
            method="ping",
            params=None,
            id="req-789",
            is_notification=False,
        )
        result = request.to_dict()

        assert result == {
            "jsonrpc": "2.0",
            "method": "ping",
            "id": "req-789",
        }
        assert "params" not in result

    def test_notification_request(self):
        """Test notification request (no ID)."""
        request = JSONRPCRequestBuilder(
            method="log",
            params={"message": "hello"},
            id=None,
            is_notification=True,
        )
        result = request.to_dict()

        assert result == {
            "jsonrpc": "2.0",
            "method": "log",
            "params": {"message": "hello"},
        }
        assert "id" not in result


# =============================================================================
# Response Tests
# =============================================================================


class TestJSONRPCResponse:
    """Tests for JSONRPCResponse parsing."""

    def test_success_response(self):
        """Test parsing successful response."""
        data = {"jsonrpc": "2.0", "id": "123", "result": {"value": 42}}
        response = JSONRPCResponse.from_dict(data)

        assert response.id == "123"
        assert response.result == {"value": 42}
        assert response.error is None
        assert response.is_error is False

    def test_error_response(self):
        """Test parsing error response."""
        data = {
            "jsonrpc": "2.0",
            "id": "123",
            "error": {"code": -32601, "message": "Method not found"},
        }
        response = JSONRPCResponse.from_dict(data)

        assert response.id == "123"
        assert response.result is None
        assert response.error == {"code": -32601, "message": "Method not found"}
        assert response.is_error is True

    def test_response_with_null_id(self):
        """Test parsing response with null ID."""
        data = {"jsonrpc": "2.0", "id": None, "result": "ok"}
        response = JSONRPCResponse.from_dict(data)

        assert response.id is None
        assert response.result == "ok"


# =============================================================================
# Error Classes Tests
# =============================================================================


class TestJSONRPCErrors:
    """Tests for JSON-RPC error classes."""

    def test_method_error_creation(self):
        """Test creating JSONRPCMethodError."""
        error = JSONRPCMethodError(
            code=-32601,
            message="Method not found",
            data={"details": "test"},
            request_id="req-123",
        )
        assert error.code == -32601
        assert error.message == "Method not found"
        assert error.data == {"details": "test"}
        assert error.request_id == "req-123"
        assert "JSON-RPC Error -32601" in str(error)

    def test_method_error_to_dict(self):
        """Test converting error to dictionary."""
        error = JSONRPCMethodError(
            code=-32602,
            message="Invalid params",
            data={"missing": ["a", "b"]},
        )
        result = error.to_dict()

        assert result == {
            "code": -32602,
            "message": "Invalid params",
            "data": {"missing": ["a", "b"]},
        }

    def test_method_error_to_dict_without_data(self):
        """Test error to dict without optional data."""
        error = JSONRPCMethodError(
            code=-32600,
            message="Invalid Request",
        )
        result = error.to_dict()

        assert result == {"code": -32600, "message": "Invalid Request"}
        assert "data" not in result

    def test_error_code_enum_values(self):
        """Test JSON-RPC error code enum values."""
        assert JSONRPCErrorCode.PARSE_ERROR.value == -32700
        assert JSONRPCErrorCode.INVALID_REQUEST.value == -32600
        assert JSONRPCErrorCode.METHOD_NOT_FOUND.value == -32601
        assert JSONRPCErrorCode.INVALID_PARAMS.value == -32602
        assert JSONRPCErrorCode.INTERNAL_ERROR.value == -32603
        assert JSONRPCErrorCode.SERVER_ERROR.value == -32000


# =============================================================================
# Client Tests
# =============================================================================


class TestJSONRPCClient:
    """Tests for JSONRPCClient."""

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        with patch("axiompy.io.jsonrpc.HTTPClientFactory.create") as mock_factory:
            mock_client = Mock()
            mock_factory.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def client(self, mock_http_client):
        """Create JSON-RPC client with mocked HTTP client."""
        settings = JSONRPCClientSettings(url="http://localhost:8000/jsonrpc")
        return JSONRPCClient(settings)

    def test_client_initialization(self, mock_http_client):
        """Test client initialization."""
        settings = JSONRPCClientSettings(
            url="http://localhost:8000/jsonrpc",
            timeout_secs=60,
            verify_ssl=False,
        )
        client = JSONRPCClient(settings)
        assert client.settings == settings

    def test_call_success(self, client, mock_http_client):
        """Test successful method call."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": 42,
        }
        mock_http_client.post.return_value = mock_response

        # Patch the ID generator
        with patch.object(client, "_generate_id", return_value="test-id"):
            result = client.call("add", {"a": 1, "b": 2})

        assert result == 42
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert call_args[0][0] == "http://localhost:8000/jsonrpc"

    def test_call_with_error_response(self, client, mock_http_client):
        """Test method call that returns error."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "error": {"code": -32601, "message": "Method not found"},
        }
        mock_http_client.post.return_value = mock_response

        with patch.object(client, "_generate_id", return_value="test-id"):
            with pytest.raises(JSONRPCMethodError) as exc_info:
                client.call("unknown_method", {})

        assert exc_info.value.code == -32601
        assert "Method not found" in exc_info.value.message

    def test_call_connection_error(self, client, mock_http_client):
        """Test method call with connection failure."""
        mock_http_client.post.side_effect = HTTPRequestError("Connection refused")

        with pytest.raises(JSONRPCConnectionError):
            client.call("add", {"a": 1, "b": 2})

    def test_call_invalid_response_format(self, client, mock_http_client):
        """Test handling invalid response format."""
        mock_response = Mock()
        mock_response.json.return_value = "not an object"
        mock_http_client.post.return_value = mock_response

        with patch.object(client, "_generate_id", return_value="test-id"):
            with pytest.raises(JSONRPCProtocolError, match="must be an object"):
                client.call("add", {"a": 1, "b": 2})

    def test_call_invalid_jsonrpc_version(self, client, mock_http_client):
        """Test handling invalid JSON-RPC version."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "1.0",
            "id": "test-id",
            "result": 42,
        }
        mock_http_client.post.return_value = mock_response

        with patch.object(client, "_generate_id", return_value="test-id"):
            with pytest.raises(JSONRPCProtocolError, match="Invalid JSON-RPC version"):
                client.call("add", {"a": 1, "b": 2})

    def test_notify(self, client, mock_http_client):
        """Test notification (fire-and-forget)."""
        mock_http_client.post.return_value = Mock()

        client.notify("log", {"message": "hello"})

        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        body = call_args[1]["json"]
        assert "id" not in body
        assert body["method"] == "log"

    def test_notify_connection_error(self, client, mock_http_client):
        """Test notification with connection failure."""
        mock_http_client.post.side_effect = HTTPRequestError("Connection refused")

        with pytest.raises(JSONRPCConnectionError):
            client.notify("log", {"message": "hello"})

    def test_batch_requests(self, client, mock_http_client):
        """Test batch request execution."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "non-empty"
        mock_response.json.return_value = [
            {"jsonrpc": "2.0", "id": "1", "result": 3},
            {"jsonrpc": "2.0", "id": "2", "result": 12},
        ]
        mock_http_client.post.return_value = mock_response

        requests = [
            JSONRPCRequestBuilder("add", {"a": 1, "b": 2}, "1", False),
            JSONRPCRequestBuilder("multiply", {"x": 3, "y": 4}, "2", False),
        ]
        results = client.batch(requests)

        assert len(results) == 2
        assert results[0] == ("1", 3, None)
        assert results[1] == ("2", 12, None)

    def test_batch_empty_requests(self, client, mock_http_client):
        """Test batch with empty request list."""
        results = client.batch([])
        assert results == []

    def test_batch_with_errors(self, client, mock_http_client):
        """Test batch with some errors."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "non-empty"
        mock_response.json.return_value = [
            {"jsonrpc": "2.0", "id": "1", "result": 3},
            {
                "jsonrpc": "2.0",
                "id": "2",
                "error": {"code": -32601, "message": "Not found"},
            },
        ]
        mock_http_client.post.return_value = mock_response

        requests = [
            JSONRPCRequestBuilder("add", {"a": 1, "b": 2}, "1", False),
            JSONRPCRequestBuilder("unknown", {}, "2", False),
        ]
        results = client.batch(requests)

        assert len(results) == 2
        assert results[0] == ("1", 3, None)
        assert results[1][0] == "2"
        assert results[1][1] is None
        assert results[1][2]["code"] == -32601

    def test_batch_all_notifications(self, client, mock_http_client):
        """Test batch with all notifications (empty response)."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_http_client.post.return_value = mock_response

        requests = [
            JSONRPCRequestBuilder("log", {"msg": "a"}, None, True),
            JSONRPCRequestBuilder("log", {"msg": "b"}, None, True),
        ]
        results = client.batch(requests)

        assert results == []

    def test_batch_connection_error(self, client, mock_http_client):
        """Test batch with connection failure."""
        mock_http_client.post.side_effect = HTTPRequestError("Connection refused")

        requests = [JSONRPCRequestBuilder("add", {"a": 1}, "1", False)]
        with pytest.raises(JSONRPCConnectionError):
            client.batch(requests)

    def test_batch_invalid_response(self, client, mock_http_client):
        """Test batch with invalid response format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "non-empty"
        mock_response.json.return_value = "invalid"
        mock_http_client.post.return_value = mock_response

        requests = [JSONRPCRequestBuilder("add", {"a": 1}, "1", False)]
        with pytest.raises(JSONRPCProtocolError, match="must be an array"):
            client.batch(requests)


# =============================================================================
# Retry Tests
# =============================================================================


class TestJSONRPCClientRetry:
    """Tests for retry functionality."""

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        with patch("axiompy.io.jsonrpc.HTTPClientFactory.create") as mock_factory:
            mock_client = Mock()
            mock_factory.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def client(self, mock_http_client):
        """Create JSON-RPC client with mocked HTTP client."""
        settings = JSONRPCClientSettings(url="http://localhost:8000/jsonrpc")
        return JSONRPCClient(settings)

    def test_call_with_retry_success(self, client, mock_http_client):
        """Test call with retry - success."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": "success",
        }
        mock_http_client.post_with_retry.return_value = mock_response

        with patch.object(client, "_generate_id", return_value="test-id"):
            result = client.call_with_retry("method", {"param": "value"})

        assert result == "success"
        mock_http_client.post_with_retry.assert_called_once()

    def test_call_with_retry_custom_config(self, client, mock_http_client):
        """Test call with retry - custom config."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": "success",
        }
        mock_http_client.post_with_retry.return_value = mock_response

        retry_config = RetryConfig().with_max_attempts(5)

        with patch.object(client, "_generate_id", return_value="test-id"):
            result = client.call_with_retry("method", {}, retry_config=retry_config)

        assert result == "success"
        call_args = mock_http_client.post_with_retry.call_args
        assert call_args[1]["retry_config"] == retry_config

    def test_call_with_retry_connection_error(self, client, mock_http_client):
        """Test call with retry - connection failure."""
        mock_http_client.post_with_retry.side_effect = HTTPRequestError("Failed")

        with pytest.raises(JSONRPCConnectionError, match="after retries"):
            client.call_with_retry("method", {})

    def test_batch_with_retry_success(self, client, mock_http_client):
        """Test batch with retry - success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "non-empty"
        mock_response.json.return_value = [
            {"jsonrpc": "2.0", "id": "1", "result": "ok"},
        ]
        mock_http_client.post_with_retry.return_value = mock_response

        requests = [JSONRPCRequestBuilder("method", {}, "1", False)]
        results = client.batch_with_retry(requests)

        assert len(results) == 1
        assert results[0] == ("1", "ok", None)

    def test_batch_with_retry_empty(self, client, mock_http_client):
        """Test batch with retry - empty request list."""
        results = client.batch_with_retry([])
        assert results == []

    def test_batch_with_retry_connection_error(self, client, mock_http_client):
        """Test batch with retry - connection failure."""
        mock_http_client.post_with_retry.side_effect = HTTPRequestError("Failed")

        requests = [JSONRPCRequestBuilder("method", {}, "1", False)]
        with pytest.raises(JSONRPCConnectionError, match="after retries"):
            client.batch_with_retry(requests)


# =============================================================================
# Fluent API Tests
# =============================================================================


class TestJSONRPCClientFluentAPI:
    """Tests for fluent API configuration."""

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        with patch("axiompy.io.jsonrpc.HTTPClientFactory.create") as mock_factory:
            mock_client = Mock()
            mock_factory.return_value = mock_client
            yield mock_client

    def test_add_header(self, mock_http_client):
        """Test adding headers with fluent API."""
        settings = JSONRPCClientSettings(url="http://localhost:8000/jsonrpc")
        client = JSONRPCClient(settings)

        result = client.add_header("X-Custom", "value")

        assert result is client  # Returns self
        mock_http_client.add_header.assert_called_once_with("X-Custom", "value")

    def test_bearer_token(self, mock_http_client):
        """Test setting bearer token."""
        settings = JSONRPCClientSettings(url="http://localhost:8000/jsonrpc")
        client = JSONRPCClient(settings)

        result = client.bearer_token("my_token")

        assert result is client
        mock_http_client.bearer_token.assert_called_once_with("my_token")

    def test_basic_auth(self, mock_http_client):
        """Test setting basic auth."""
        settings = JSONRPCClientSettings(url="http://localhost:8000/jsonrpc")
        client = JSONRPCClient(settings)

        result = client.basic_auth("user", "pass")

        assert result is client
        mock_http_client.basic_auth.assert_called_once_with("user", "pass")

    def test_custom_auth(self, mock_http_client):
        """Test setting custom auth."""
        settings = JSONRPCClientSettings(url="http://localhost:8000/jsonrpc")
        client = JSONRPCClient(settings)

        result = client.custom_auth("X-API-Key", "secret")

        assert result is client
        mock_http_client.custom_auth.assert_called_once_with("X-API-Key", "secret")

    def test_fluent_chaining(self, mock_http_client):
        """Test chaining multiple fluent calls."""
        settings = JSONRPCClientSettings(url="http://localhost:8000/jsonrpc")
        client = (
            JSONRPCClient(settings)
            .add_header("X-Custom", "value")
            .bearer_token("token")
            .add_header("X-Another", "header")
        )

        assert client is not None
        assert mock_http_client.add_header.call_count == 2
        mock_http_client.bearer_token.assert_called_once()


# =============================================================================
# Request Builder Methods Tests
# =============================================================================


class TestJSONRPCClientRequestMethods:
    """Tests for request builder methods."""

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        with patch("axiompy.io.jsonrpc.HTTPClientFactory.create") as mock_factory:
            mock_client = Mock()
            mock_factory.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def client(self, mock_http_client):
        """Create JSON-RPC client with mocked HTTP client."""
        settings = JSONRPCClientSettings(url="http://localhost:8000/jsonrpc")
        return JSONRPCClient(settings)

    def test_request_method(self, client):
        """Test request() builder method."""
        request = client.request("add", {"a": 1, "b": 2})

        assert isinstance(request, JSONRPCRequestBuilder)
        assert request.method == "add"
        assert request.params == {"a": 1, "b": 2}
        assert request.is_notification is False
        assert request.id is not None  # Auto-generated

    def test_notification_request_method(self, client):
        """Test notification_request() builder method."""
        request = client.notification_request("log", {"msg": "hello"})

        assert isinstance(request, JSONRPCRequestBuilder)
        assert request.method == "log"
        assert request.params == {"msg": "hello"}
        assert request.is_notification is True
        assert request.id is None


# =============================================================================
# Mock Client Tests
# =============================================================================


class TestMockJSONRPCClient:
    """Tests for MockJSONRPCClient."""

    def test_mock_creation(self):
        """Test creating mock client."""
        mock = MockJSONRPCClient()
        assert mock.calls == []
        assert mock.notifications == []

    def test_mock_set_response(self):
        """Test setting mock response."""
        mock = MockJSONRPCClient()
        result = mock.set_response("add", 42)

        assert result is mock  # Fluent
        assert mock.call("add", {"a": 1, "b": 2}) == 42

    def test_mock_set_error(self):
        """Test setting mock error."""
        mock = MockJSONRPCClient()
        mock.set_error("fail", -32000, "Server error", {"detail": "test"})

        with pytest.raises(JSONRPCMethodError) as exc_info:
            mock.call("fail", {})

        assert exc_info.value.code == -32000
        assert exc_info.value.message == "Server error"
        assert exc_info.value.data == {"detail": "test"}

    def test_mock_unknown_method(self):
        """Test calling unknown method on mock."""
        mock = MockJSONRPCClient()

        with pytest.raises(JSONRPCMethodError) as exc_info:
            mock.call("unknown", {})

        assert exc_info.value.code == JSONRPCErrorCode.METHOD_NOT_FOUND.value

    def test_mock_tracks_calls(self):
        """Test that mock tracks all calls."""
        mock = MockJSONRPCClient()
        mock.set_response("add", 3)
        mock.set_response("multiply", 12)

        mock.call("add", {"a": 1, "b": 2})
        mock.call("multiply", {"x": 3, "y": 4})

        assert len(mock.calls) == 2
        assert mock.calls[0] == ("add", {"a": 1, "b": 2})
        assert mock.calls[1] == ("multiply", {"x": 3, "y": 4})

    def test_mock_notify(self):
        """Test mock notification."""
        mock = MockJSONRPCClient()

        mock.notify("log", {"message": "hello"})

        assert len(mock.notifications) == 1
        assert mock.notifications[0] == ("log", {"message": "hello"})

    def test_mock_batch(self):
        """Test mock batch request."""
        mock = MockJSONRPCClient()
        mock.set_response("add", 3)
        mock.set_response("multiply", 12)

        requests = [
            JSONRPCRequestBuilder("add", {"a": 1}, "1", False),
            JSONRPCRequestBuilder("multiply", {"x": 3}, "2", False),
            JSONRPCRequestBuilder("log", {"msg": "test"}, None, True),  # Notification
        ]
        results = mock.batch(requests)

        assert len(results) == 2  # Notifications not in results
        assert results[0] == ("1", 3, None)
        assert results[1] == ("2", 12, None)
        assert len(mock.notifications) == 1

    def test_mock_batch_with_unknown_method(self):
        """Test mock batch with unknown method."""
        mock = MockJSONRPCClient()
        mock.set_response("add", 3)

        requests = [
            JSONRPCRequestBuilder("add", {}, "1", False),
            JSONRPCRequestBuilder("unknown", {}, "2", False),
        ]
        results = mock.batch(requests)

        assert len(results) == 2
        assert results[0][2] is None  # No error
        assert results[1][2]["code"] == JSONRPCErrorCode.METHOD_NOT_FOUND.value

    def test_mock_batch_with_error(self):
        """Test mock batch with error response."""
        mock = MockJSONRPCClient()
        mock.set_response("add", 3)
        mock.set_error("fail", -32000, "Error")

        requests = [
            JSONRPCRequestBuilder("add", {}, "1", False),
            JSONRPCRequestBuilder("fail", {}, "2", False),
        ]
        results = mock.batch(requests)

        assert results[0][2] is None
        assert results[1][2]["code"] == -32000

    def test_mock_call_with_retry(self):
        """Test mock call with retry."""
        mock = MockJSONRPCClient()
        mock.set_response("method", "result")

        result = mock.call_with_retry("method", {})

        assert result == "result"

    def test_mock_batch_with_retry(self):
        """Test mock batch with retry."""
        mock = MockJSONRPCClient()
        mock.set_response("method", "result")

        requests = [JSONRPCRequestBuilder("method", {}, "1", False)]
        results = mock.batch_with_retry(requests)

        assert len(results) == 1
        assert results[0][1] == "result"

    def test_mock_reset(self):
        """Test resetting mock state."""
        mock = MockJSONRPCClient()
        mock.set_response("add", 3)

        mock.call("add", {})
        mock.notify("log", {})

        assert len(mock.calls) == 1
        assert len(mock.notifications) == 1

        mock.reset()

        assert mock.calls == []
        assert mock.notifications == []

    def test_mock_custom_settings(self):
        """Test mock with custom settings."""
        settings = JSONRPCClientSettings(url="http://custom", timeout_secs=60)
        mock = MockJSONRPCClient(settings)

        assert mock.settings.url == "http://custom"
        assert mock.settings.timeout_secs == 60


# =============================================================================
# Factory Tests
# =============================================================================


class TestJSONRPCClientFactory:
    """Tests for JSONRPCClientFactory."""

    def test_create_basic(self):
        """Test creating basic client."""
        with patch("axiompy.io.jsonrpc.HTTPClientFactory.create"):
            client = JSONRPCClientFactory.create(url="http://localhost:8000/jsonrpc")

        assert isinstance(client, JSONRPCClient)
        assert client.settings.url == "http://localhost:8000/jsonrpc"
        assert client.settings.timeout_secs == 30  # Default
        assert client.settings.verify_ssl is True  # Default

    def test_create_with_options(self):
        """Test creating client with options."""
        with patch("axiompy.io.jsonrpc.HTTPClientFactory.create"):
            client = JSONRPCClientFactory.create(
                url="http://localhost:8000/jsonrpc",
                timeout_secs=60,
                verify_ssl=False,
            )

        assert client.settings.timeout_secs == 60
        assert client.settings.verify_ssl is False

    def test_create_with_custom_id_generator(self):
        """Test creating client with custom ID generator."""
        counter = [0]

        def custom_generator():
            counter[0] += 1
            return counter[0]

        with patch("axiompy.io.jsonrpc.HTTPClientFactory.create"):
            client = JSONRPCClientFactory.create(
                url="http://localhost:8000/jsonrpc",
                id_generator=custom_generator,
            )

        # Generate some IDs
        id1 = client._generate_id()
        id2 = client._generate_id()

        assert id1 == 1
        assert id2 == 2

    def test_create_from_settings(self):
        """Test creating client from settings object."""
        settings = JSONRPCClientSettings(
            url="http://localhost:8000/jsonrpc",
            timeout_secs=45,
        )

        with patch("axiompy.io.jsonrpc.HTTPClientFactory.create"):
            client = JSONRPCClientFactory.create_from_settings(settings)

        assert client.settings is settings
        assert client.settings.timeout_secs == 45

    def test_create_mock(self):
        """Test creating mock client."""
        mock = JSONRPCClientFactory.create_mock()

        assert isinstance(mock, MockJSONRPCClient)
        assert mock.calls == []

    def test_create_mock_with_responses(self):
        """Test creating mock client with predefined responses."""
        mock = JSONRPCClientFactory.create_mock(responses={"add": 42, "multiply": 12})

        assert mock.call("add", {}) == 42
        assert mock.call("multiply", {}) == 12


# =============================================================================
# Integration-Style Tests
# =============================================================================


class TestJSONRPCClientIntegration:
    """Integration-style tests using mock client."""

    def test_complete_workflow(self):
        """Test complete client workflow."""
        # Create mock client with responses
        client = JSONRPCClientFactory.create_mock(
            {
                "initialize": {"protocol": "2.0", "capabilities": ["tools"]},
                "tools/list": {"tools": [{"name": "add"}, {"name": "multiply"}]},
                "tools/call": {"result": 42},
            }
        )

        # Initialize
        init_result = client.call("initialize", {})
        assert init_result["protocol"] == "2.0"

        # List tools
        tools = client.call("tools/list", {})
        assert len(tools["tools"]) == 2

        # Call tool
        result = client.call("tools/call", {"name": "add", "arguments": {"a": 1, "b": 2}})
        assert result["result"] == 42

        # Send notification
        client.notify("log", {"level": "info", "message": "Operation complete"})

        # Verify call tracking
        assert len(client.calls) == 3
        assert len(client.notifications) == 1

    def test_batch_workflow(self):
        """Test batch request workflow."""
        client = JSONRPCClientFactory.create_mock(
            {
                "add": 3,
                "multiply": 12,
                "divide": 5,
            }
        )

        # Create batch requests
        requests = [
            client.request("add", {"a": 1, "b": 2}),
            client.request("multiply", {"x": 3, "y": 4}),
            client.notification_request("log", {"msg": "batch"}),
            client.request("divide", {"a": 10, "b": 2}),
        ]

        results = client.batch(requests)

        # Should have 3 results (notification excluded)
        assert len(results) == 3
        assert results[0][1] == 3  # add result
        assert results[1][1] == 12  # multiply result
        assert results[2][1] == 5  # divide result

        # Notification tracked
        assert len(client.notifications) == 1

    def test_error_handling_workflow(self):
        """Test error handling workflow."""
        client = JSONRPCClientFactory.create_mock()
        client.set_response("success", "ok")
        client.set_error("fail", -32000, "Intentional failure", {"reason": "test"})

        # Success call
        assert client.call("success", {}) == "ok"

        # Error call
        with pytest.raises(JSONRPCMethodError) as exc_info:
            client.call("fail", {})

        error = exc_info.value
        assert error.code == -32000
        assert error.data == {"reason": "test"}

        # Batch with mixed results
        requests = [
            client.request("success", {}),
            client.request("fail", {}),
        ]
        results = client.batch(requests)

        assert results[0][2] is None  # No error
        assert results[1][2] is not None  # Has error


# =============================================================================
# Edge Cases and Error Conditions
# =============================================================================


class TestJSONRPCClientValidation:
    """Tests for input validation."""

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        with patch("axiompy.io.jsonrpc.HTTPClientFactory.create") as mock_factory:
            mock_client = Mock()
            mock_factory.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def client(self, mock_http_client):
        """Create JSON-RPC client with mocked HTTP client."""
        settings = JSONRPCClientSettings(url="http://localhost:8000/jsonrpc")
        return JSONRPCClient(settings)

    def test_call_empty_method_raises(self, client):
        """Test that empty method name raises ValueError."""
        with pytest.raises(ValueError, match="Method name cannot be empty"):
            client.call("", {"a": 1})

    def test_call_whitespace_method_raises(self, client):
        """Test that whitespace-only method name raises ValueError."""
        with pytest.raises(ValueError, match="Method name cannot be empty"):
            client.call("   ", {"a": 1})

    def test_notify_empty_method_raises(self, client):
        """Test that empty method name in notify raises ValueError."""
        with pytest.raises(ValueError, match="Method name cannot be empty"):
            client.notify("", {"msg": "test"})

    def test_call_with_retry_empty_method_raises(self, client):
        """Test that empty method name in call_with_retry raises ValueError."""
        with pytest.raises(ValueError, match="Method name cannot be empty"):
            client.call_with_retry("", {})


class TestJSONRPCClientEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        with patch("axiompy.io.jsonrpc.HTTPClientFactory.create") as mock_factory:
            mock_client = Mock()
            mock_factory.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def client(self, mock_http_client):
        """Create JSON-RPC client with mocked HTTP client."""
        settings = JSONRPCClientSettings(url="http://localhost:8000/jsonrpc")
        return JSONRPCClient(settings)

    def test_call_with_list_params(self, client, mock_http_client):
        """Test call with positional (list) parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": 6,
        }
        mock_http_client.post.return_value = mock_response

        with patch.object(client, "_generate_id", return_value="test-id"):
            result = client.call("add", [1, 2, 3])

        call_args = mock_http_client.post.call_args
        body = call_args[1]["json"]
        assert body["params"] == [1, 2, 3]

    def test_call_without_params(self, client, mock_http_client):
        """Test call without parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": "pong",
        }
        mock_http_client.post.return_value = mock_response

        with patch.object(client, "_generate_id", return_value="test-id"):
            result = client.call("ping")

        call_args = mock_http_client.post.call_args
        body = call_args[1]["json"]
        assert "params" not in body

    def test_response_with_null_result(self, client, mock_http_client):
        """Test handling response with null result."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": None,
        }
        mock_http_client.post.return_value = mock_response

        with patch.object(client, "_generate_id", return_value="test-id"):
            result = client.call("method", {})

        assert result is None

    def test_response_with_error_data(self, client, mock_http_client):
        """Test error response with data field."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": {"missing": ["a", "b"]},
            },
        }
        mock_http_client.post.return_value = mock_response

        with patch.object(client, "_generate_id", return_value="test-id"):
            with pytest.raises(JSONRPCMethodError) as exc_info:
                client.call("method", {})

        assert exc_info.value.data == {"missing": ["a", "b"]}

    def test_batch_single_response_wrapped(self, client, mock_http_client):
        """Test batch that returns single response (not array)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "non-empty"
        # Server returns single response instead of array
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "1",
            "result": "ok",
        }
        mock_http_client.post.return_value = mock_response

        requests = [JSONRPCRequestBuilder("method", {}, "1", False)]
        results = client.batch(requests)

        # Should handle single response
        assert len(results) == 1
        assert results[0][1] == "ok"

    def test_id_mismatch_warning(self, client, mock_http_client):
        """Test warning logged for ID mismatch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "different-id",
            "result": 42,
        }
        mock_http_client.post.return_value = mock_response

        with patch.object(client, "_generate_id", return_value="expected-id"):
            # Should still return result but log warning
            result = client.call("method", {})

        assert result == 42

    def test_default_id_generator(self, client):
        """Test default UUID ID generator."""
        id1 = client._generate_id()
        id2 = client._generate_id()

        # Should be different UUIDs
        assert id1 != id2
        # Should be valid UUID strings
        assert len(id1) == 36
        assert len(id2) == 36


# =============================================================================
# Response Parsing Tests
# =============================================================================


class TestResponseParsing:
    """Additional tests for response parsing edge cases."""

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        with patch("axiompy.io.jsonrpc.HTTPClientFactory.create") as mock_factory:
            mock_client = Mock()
            mock_factory.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def client(self, mock_http_client):
        """Create JSON-RPC client with mocked HTTP client."""
        settings = JSONRPCClientSettings(url="http://localhost:8000/jsonrpc")
        return JSONRPCClient(settings)

    def test_batch_with_non_dict_items(self, client, mock_http_client):
        """Test batch response parsing skips non-dict items."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "non-empty"
        mock_response.json.return_value = [
            {"jsonrpc": "2.0", "id": "1", "result": "ok"},
            None,  # Invalid item
            "string",  # Invalid item
            {"jsonrpc": "2.0", "id": "2", "result": "done"},
        ]
        mock_http_client.post.return_value = mock_response

        requests = [
            JSONRPCRequestBuilder("method1", {}, "1", False),
            JSONRPCRequestBuilder("method2", {}, "2", False),
        ]
        results = client.batch(requests)

        # Should only have valid responses
        assert len(results) == 2

    def test_error_with_missing_code(self, client, mock_http_client):
        """Test error response with missing code uses default."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "error": {"message": "Unknown error"},
        }
        mock_http_client.post.return_value = mock_response

        with patch.object(client, "_generate_id", return_value="test-id"):
            with pytest.raises(JSONRPCMethodError) as exc_info:
                client.call("method", {})

        # Should use INTERNAL_ERROR as default
        assert exc_info.value.code == JSONRPCErrorCode.INTERNAL_ERROR.value

    def test_error_with_missing_message(self, client, mock_http_client):
        """Test error response with missing message uses default."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "error": {"code": -32000},
        }
        mock_http_client.post.return_value = mock_response

        with patch.object(client, "_generate_id", return_value="test-id"):
            with pytest.raises(JSONRPCMethodError) as exc_info:
                client.call("method", {})

        assert exc_info.value.message == "Unknown error"
