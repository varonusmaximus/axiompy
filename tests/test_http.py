# @!testing

"""
Tests for the HTTP client module.

Comprehensive test suite for HTTP client functionality including:
- Basic HTTP methods (GET, POST, PUT, PATCH, DELETE)
- Authentication (Basic, Digest, Bearer, Custom)
- Headers injection
- Retry logic with exponential backoff
- JSON serialization/deserialization
- Error handling
"""

from unittest.mock import Mock, patch

import pytest
import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from axiompy.io.http import (
    HTTPAuthError,
    HTTPClient,
    HTTPClientError,
    HTTPClientFactory,
    HTTPClientSettings,
    HTTPConnectionError,
    HTTPRequestError,
    HTTPTransport,
    RetryConfig,
)
from axiompy.io.serialization import DeserializerFactory


class TestRetryConfig:
    """Test RetryConfig class."""

    def test_default_retry_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.initial_backoff_ms == 100
        assert config.max_backoff_ms == 30000
        assert config.backoff_multiplier == 2.0
        assert config.retry_on_client_error is False

    def test_calculate_backoff(self):
        """Test backoff calculation."""
        config = RetryConfig()
        # Attempt 0: 100ms
        assert config.calculate_backoff(0) == 0.1
        # Attempt 1: 200ms
        assert config.calculate_backoff(1) == 0.2
        # Attempt 2: 400ms
        assert config.calculate_backoff(2) == 0.4

    def test_calculate_backoff_with_max_limit(self):
        """Test backoff respects maximum limit."""
        config = RetryConfig(max_backoff_ms=500)
        # Should cap at 500ms
        backoff = config.calculate_backoff(10)
        assert backoff == 0.5

    def test_should_retry_server_errors(self):
        """Test retry on server errors."""
        config = RetryConfig()
        assert config.should_retry(500) is True
        assert config.should_retry(502) is True
        assert config.should_retry(503) is True
        assert config.should_retry(504) is True

    def test_should_retry_rate_limit(self):
        """Test retry on rate limit."""
        config = RetryConfig()
        assert config.should_retry(429) is True

    def test_should_retry_timeout(self):
        """Test retry on timeout."""
        config = RetryConfig()
        assert config.should_retry(408) is True

    def test_should_not_retry_client_errors_by_default(self):
        """Test no retry on client errors by default."""
        config = RetryConfig()
        assert config.should_retry(400) is False
        assert config.should_retry(401) is False
        assert config.should_retry(404) is False

    def test_should_retry_client_errors_when_enabled(self):
        """Test retry on client errors when enabled."""
        config = RetryConfig(retry_on_client_error=True)
        assert config.should_retry(400) is True
        assert config.should_retry(401) is True
        assert config.should_retry(404) is True

    def test_retry_config_builder_chain(self):
        """Test RetryConfig builder chaining."""
        config = (
            RetryConfig()
            .with_max_attempts(5)
            .with_initial_backoff_ms(200)
            .with_max_backoff_ms(5000)
            .with_backoff_multiplier(3.0)
            .with_retry_on_client_error(True)
        )
        assert config.max_attempts == 5
        assert config.initial_backoff_ms == 200
        assert config.max_backoff_ms == 5000
        assert config.backoff_multiplier == 3.0
        assert config.retry_on_client_error is True


class TestHTTPClientSettings:
    """Test HTTPClientSettings."""

    def test_default_settings(self):
        """Test default settings."""
        settings = HTTPClientSettings()
        assert settings.timeout_secs == 30
        assert settings.verify_ssl is True
        assert settings.allow_redirects is True
        assert settings.extra_params == {}

    def test_custom_settings(self):
        """Test custom settings."""
        settings = HTTPClientSettings(
            timeout_secs=60,
            verify_ssl=False,
            allow_redirects=False,
        )
        assert settings.timeout_secs == 60
        assert settings.verify_ssl is False
        assert settings.allow_redirects is False


class TestHTTPClient:
    """Test HTTPClient class."""

    @pytest.fixture
    def client(self):
        """Create HTTP client for testing."""
        settings = HTTPClientSettings(timeout_secs=30)
        return HTTPClient(settings)

    @pytest.fixture
    def mock_response(self):
        """Create mock response."""
        response = Mock(spec=requests.Response)
        response.status_code = 200
        response.ok = True
        response.text = "Success"
        response.json.return_value = {"result": "success"}
        return response

    def test_client_initialization(self, client):
        """Test client initialization."""
        assert client.settings.timeout_secs == 30
        assert client.session is not None
        assert client._default_headers == {}
        assert client._auth is None

    def test_add_header(self, client):
        """Test adding a header."""
        result = client.add_header("X-Custom", "value")
        assert result is client  # Check method chaining
        assert client._default_headers["X-Custom"] == "value"

    def test_add_header_chaining(self, client):
        """Test adding multiple headers via chaining."""
        result = (
            client.add_header("X-Custom1", "value1")
            .add_header("X-Custom2", "value2")
            .add_header("X-Custom3", "value3")
        )
        assert result is client
        assert client._default_headers["X-Custom1"] == "value1"
        assert client._default_headers["X-Custom2"] == "value2"
        assert client._default_headers["X-Custom3"] == "value3"

    def test_add_multiple_headers_real_world_pattern(self, client):
        """Test real-world pattern of adding multiple headers in one chain."""
        client = (
            HTTPClientFactory.create()
            .add_header("Authorization", "Bearer 1234567890abcdefgh")
            .add_header("Content-Type", "application/json")
            .add_header("X-API-Version", "v2")
            .add_header("X-Request-ID", "req-12345")
            .add_header("User-Agent", "my-app/1.0")
        )

        # Verify all headers were added
        assert client._default_headers["Authorization"] == "Bearer 1234567890abcdefgh"
        assert client._default_headers["Content-Type"] == "application/json"
        assert client._default_headers["X-API-Version"] == "v2"
        assert client._default_headers["X-Request-ID"] == "req-12345"
        assert client._default_headers["User-Agent"] == "my-app/1.0"

        # Verify they're in the session headers too
        assert client.session.headers["Authorization"] == "Bearer 1234567890abcdefgh"
        assert client.session.headers["Content-Type"] == "application/json"
        assert len(client._default_headers) == 5

    def test_basic_auth(self, client):
        """Test setting basic auth."""
        result = client.basic_auth("user", "pass")
        assert result is client
        assert isinstance(client._auth, HTTPBasicAuth)

    def test_digest_auth(self, client):
        """Test setting digest auth."""
        result = client.digest_auth("user", "pass")
        assert result is client
        assert isinstance(client._auth, HTTPDigestAuth)

    def test_bearer_token(self, client):
        """Test setting bearer token."""
        result = client.bearer_token("my_token")
        assert result is client
        assert client._default_headers["Authorization"] == "Bearer my_token"

    def test_custom_auth(self, client):
        """Test setting custom auth header."""
        result = client.custom_auth("X-API-Key", "secret")
        assert result is client
        assert client._default_headers["X-API-Key"] == "secret"

    @patch("axiompy.io.http.requests.Session.get")
    def test_get_request(self, mock_get, client, mock_response):
        """Test GET request."""
        mock_get.return_value = mock_response

        response = client.get("https://api.example.com/data")

        assert response.status_code == 200
        mock_get.assert_called_once()

    @patch("axiompy.io.http.requests.Session.get")
    def test_get_request_with_headers(self, mock_get, client, mock_response):
        """Test GET request with custom headers."""
        mock_get.return_value = mock_response
        headers = {"X-Custom": "value"}

        response = client.get("https://api.example.com/data", headers=headers)

        assert response.status_code == 200

    @patch("axiompy.io.http.requests.Session.get")
    def test_get_request_with_params(self, mock_get, client, mock_response):
        """Test GET request with query parameters."""
        mock_get.return_value = mock_response
        params = {"key": "value"}

        response = client.get("https://api.example.com/data", params=params)

        assert response.status_code == 200

    @patch("axiompy.io.http.requests.Session.get")
    def test_get_json(self, mock_get, client, mock_response):
        """Test GET request and parse JSON with deserializer."""
        mock_get.return_value = mock_response
        deserializer = DeserializerFactory.create_json()

        result = client.get("https://api.example.com/data", deserializer=deserializer)

        assert result == {"result": "success"}

    @patch("axiompy.io.http.requests.Session.get")
    def test_get_json_parse_error(self, mock_get, client):
        """Test GET request JSON parse error with deserializer."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        deserializer = DeserializerFactory.create_json()

        with pytest.raises(HTTPRequestError):
            client.get("https://api.example.com/data", deserializer=deserializer)

    @patch("axiompy.io.http.requests.Session.get")
    def test_get_request_error(self, mock_get, client):
        """Test GET request error handling."""
        mock_get.side_effect = requests.RequestException("Connection error")

        with pytest.raises(HTTPRequestError):
            client.get("https://api.example.com/data")

    @patch("axiompy.io.http.requests.Session.post")
    def test_post_request(self, mock_post, client, mock_response):
        """Test POST request."""
        mock_post.return_value = mock_response

        response = client.post("https://api.example.com/data", json={"key": "value"})

        assert response.status_code == 200

    @patch("axiompy.io.http.requests.Session.post")
    def test_post_json(self, mock_post, client, mock_response):
        """Test POST with JSON."""
        mock_post.return_value = mock_response

        response = client.post("https://api.example.com/data", json={"key": "value"})

        assert response.status_code == 200

    @patch("axiompy.io.http.requests.Session.post")
    def test_post_json_for_json(self, mock_post, client, mock_response):
        """Test POST JSON for JSON response with deserializer."""
        mock_post.return_value = mock_response
        deserializer = DeserializerFactory.create_json()

        result = client.post(
            "https://api.example.com/data", json={"key": "value"}, deserializer=deserializer
        )

        assert result == {"result": "success"}

    @patch("axiompy.io.http.requests.Session.post")
    def test_post_request_error(self, mock_post, client):
        """Test POST request error."""
        mock_post.side_effect = requests.RequestException("Connection error")

        with pytest.raises(HTTPRequestError):
            client.post("https://api.example.com/data", json={"key": "value"})

    @patch("axiompy.io.http.requests.Session.put")
    def test_put_request(self, mock_put, client, mock_response):
        """Test PUT request."""
        mock_put.return_value = mock_response

        response = client.put("https://api.example.com/data", json={"key": "value"})

        assert response.status_code == 200

    @patch("axiompy.io.http.requests.Session.put")
    def test_put_json(self, mock_put, client, mock_response):
        """Test PUT with JSON."""
        mock_put.return_value = mock_response

        response = client.put("https://api.example.com/data", json={"key": "value"})

        assert response.status_code == 200

    @patch("axiompy.io.http.requests.Session.put")
    def test_put_request_error(self, mock_put, client):
        """Test PUT request error."""
        mock_put.side_effect = requests.RequestException("Connection error")

        with pytest.raises(HTTPRequestError):
            client.put("https://api.example.com/data", json={"key": "value"})

    @patch("axiompy.io.http.requests.Session.patch")
    def test_patch_request(self, mock_patch, client, mock_response):
        """Test PATCH request."""
        mock_patch.return_value = mock_response

        response = client.patch("https://api.example.com/data", json={"key": "value"})

        assert response.status_code == 200

    @patch("axiompy.io.http.requests.Session.patch")
    def test_patch_json(self, mock_patch, client, mock_response):
        """Test PATCH with JSON."""
        mock_patch.return_value = mock_response

        response = client.patch("https://api.example.com/data", json={"key": "value"})

        assert response.status_code == 200

    @patch("axiompy.io.http.requests.Session.patch")
    def test_patch_request_error(self, mock_patch, client):
        """Test PATCH request error."""
        mock_patch.side_effect = requests.RequestException("Connection error")

        with pytest.raises(HTTPRequestError):
            client.patch("https://api.example.com/data", json={"key": "value"})

    @patch("axiompy.io.http.requests.Session.delete")
    def test_delete_request(self, mock_delete, client, mock_response):
        """Test DELETE request."""
        mock_delete.return_value = mock_response

        response = client.delete("https://api.example.com/data")

        assert response.status_code == 200

    @patch("axiompy.io.http.requests.Session.delete")
    def test_delete_request_error(self, mock_delete, client):
        """Test DELETE request error."""
        mock_delete.side_effect = requests.RequestException("Connection error")

        with pytest.raises(HTTPRequestError):
            client.delete("https://api.example.com/data")

    @patch("axiompy.io.http.requests.Session.get")
    def test_get_request_error_response(self, mock_get, client):
        """Test GET request with error response."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 404
        mock_response.ok = False
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response

        with pytest.raises(HTTPRequestError):
            client.get("https://api.example.com/notfound")

    @patch("axiompy.io.http.requests.Session.get")
    @patch("time.sleep")
    def test_get_with_retry_success_on_first_attempt(
        self, mock_sleep, mock_get, client, mock_response
    ):
        """Test GET with retry succeeds on first attempt."""
        mock_get.return_value = mock_response

        response = client.get_with_retry("https://api.example.com/data")

        assert response.status_code == 200
        mock_get.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("axiompy.io.http.requests.Session.get")
    @patch("time.sleep")
    def test_get_with_retry_succeeds_after_failure(
        self, mock_sleep, mock_get, client, mock_response
    ):
        """Test GET with retry succeeds after initial failure."""
        error_response = Mock(spec=requests.Response)
        error_response.status_code = 503
        error_response.ok = False
        error_response.text = "Service Unavailable"

        mock_get.side_effect = [error_response, mock_response]

        retry_config = RetryConfig(max_attempts=2)

        # This should succeed on second attempt after failure
        response = client.get_with_retry("https://api.example.com/data", retry_config=retry_config)

        # Verify it succeeded
        assert response.status_code == 200
        # Verify we made 2 attempts
        assert mock_get.call_count == 2
        # Verify we slept between attempts (at least once)
        assert mock_sleep.call_count >= 1

    @patch("axiompy.io.http.requests.Session.get")
    @patch("time.sleep")
    def test_get_json_with_retry(self, mock_sleep, mock_get, client, mock_response):
        """Test GET JSON with retry and deserializer."""
        mock_get.return_value = mock_response
        deserializer = DeserializerFactory.create_json()

        result = client.get_with_retry("https://api.example.com/data", deserializer=deserializer)

        assert result == {"result": "success"}

    @patch("axiompy.io.http.requests.Session.post")
    @patch("time.sleep")
    def test_post_json_with_retry(self, mock_sleep, mock_post, client, mock_response):
        """Test POST JSON with retry."""
        mock_post.return_value = mock_response

        response = client.post_with_retry("https://api.example.com/data", json={"key": "value"})

        assert response.status_code == 200

    @patch("axiompy.io.http.requests.Session.post")
    @patch("time.sleep")
    def test_post_json_for_json_with_retry(self, mock_sleep, mock_post, client, mock_response):
        """Test POST JSON for JSON with retry and deserializer."""
        mock_post.return_value = mock_response
        deserializer = DeserializerFactory.create_json()

        result = client.post_with_retry(
            "https://api.example.com/data", json={"key": "value"}, deserializer=deserializer
        )

        assert result == {"result": "success"}

    @patch("axiompy.io.http.requests.Session.get")
    @patch("time.sleep")
    def test_retry_exhausts_attempts(self, mock_sleep, mock_get, client):
        """Test retry exhausts all attempts."""
        error_response = Mock(spec=requests.Response)
        error_response.status_code = 503
        error_response.ok = False
        error_response.text = "Service Unavailable"

        # Return error for all attempts
        mock_get.return_value = error_response

        retry_config = RetryConfig(max_attempts=2)

        with pytest.raises(HTTPRequestError):
            client.get_with_retry("https://api.example.com/data", retry_config=retry_config)

        # Verify we attempted twice
        assert mock_get.call_count == 2

    def test_client_destructor(self):
        """Test client cleanup."""
        settings = HTTPClientSettings()
        client = HTTPClient(settings)
        # Should not raise
        del client

    def test_check_response_error_with_unreadable_text(self, client):
        """Test check response when text is unreadable."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 500
        mock_response.ok = False
        mock_response.text = Mock()
        mock_response.text.__str__ = Mock(side_effect=Exception("Error"))

        with pytest.raises(HTTPRequestError):
            client._check_response(mock_response)

    @patch("axiompy.io.http.requests.Session.get")
    def test_retry_with_rate_limit_error(self, mock_get, client):
        """Test retry identifies rate limit errors."""
        error_response = Mock(spec=requests.Response)
        error_response.status_code = 429
        error_response.ok = False
        error_response.text = "HTTP 429: Too Many Requests"
        mock_get.return_value = error_response

        retry_config = RetryConfig(max_attempts=2)

        with pytest.raises(HTTPRequestError):
            client.get_with_retry("https://api.example.com/data", retry_config=retry_config)

    def test_should_retry_error_extracts_status_code(self, client):
        """Test error status code extraction in retry."""
        error = HTTPRequestError("HTTP 503: Service Unavailable")
        retry_config = RetryConfig()

        # Should identify the 503 status code
        should_retry = client._should_retry_error(error, retry_config)
        assert should_retry is True

    def test_should_retry_error_without_status_code(self, client):
        """Test error without recognizable status code."""
        error = HTTPRequestError("Connection timeout")
        retry_config = RetryConfig()

        # Should still retry on unrecognized error
        should_retry = client._should_retry_error(error, retry_config)
        assert should_retry is True


class TestHTTPClientFluentAPI:
    """Test HTTPClient fluent API for configuration."""

    def test_client_fluent_chain_headers(self):
        """Test fluent chaining with headers."""
        client = (
            HTTPClientFactory.create()
            .add_header("X-Custom", "value")
            .add_header("X-API-Version", "v2")
        )
        assert "X-Custom" in client._default_headers
        assert "X-API-Version" in client._default_headers

    def test_client_fluent_chain_auth(self):
        """Test fluent chaining with auth."""
        client = HTTPClientFactory.create().bearer_token("my_token")
        assert "Authorization" in client._default_headers
        assert "Bearer my_token" in client._default_headers["Authorization"]

    def test_client_fluent_chain_basic_auth(self):
        """Test fluent chaining with basic auth."""
        client = HTTPClientFactory.create().basic_auth("user", "pass")
        assert isinstance(client._auth, HTTPBasicAuth)

    def test_client_fluent_chain_digest_auth(self):
        """Test fluent chaining with digest auth."""
        client = HTTPClientFactory.create().digest_auth("user", "pass")
        assert isinstance(client._auth, HTTPDigestAuth)

    def test_client_fluent_chain_custom_auth(self):
        """Test fluent chaining with custom auth."""
        client = HTTPClientFactory.create().custom_auth("X-API-Key", "secret")
        assert client._default_headers["X-API-Key"] == "secret"

    def test_client_fluent_complete_chain(self):
        """Test complete fluent chaining with multiple settings."""
        client = (
            HTTPClientFactory.create(timeout_secs=60)
            .bearer_token("my_token")
            .add_header("X-API-Version", "v2")
            .add_header("User-Agent", "my-app/1.0")
        )
        assert client.settings.timeout_secs == 60
        assert "Authorization" in client._default_headers
        assert client._default_headers["X-API-Version"] == "v2"
        assert client._default_headers["User-Agent"] == "my-app/1.0"

    def test_factory_create_with_settings(self):
        """Test factory create with various settings."""
        client = HTTPClientFactory.create(timeout_secs=60, verify_ssl=False, allow_redirects=False)
        assert client.settings.timeout_secs == 60
        assert client.settings.verify_ssl is False
        assert client.settings.allow_redirects is False


class TestHTTPClientFactory:
    """Test HTTPClientFactory class."""

    def test_factory_create_default(self):
        """Test factory create with defaults."""
        client = HTTPClientFactory.create()
        assert isinstance(client, HTTPClient)
        assert client.settings.timeout_secs == 30

    def test_factory_create_with_timeout(self):
        """Test factory create with timeout."""
        client = HTTPClientFactory.create(timeout_secs=60)
        assert isinstance(client, HTTPClient)
        assert client.settings.timeout_secs == 60

    def test_factory_create_with_ssl_settings(self):
        """Test factory create with SSL settings."""
        client = HTTPClientFactory.create(verify_ssl=False, allow_redirects=False)
        assert client.settings.verify_ssl is False
        assert client.settings.allow_redirects is False

    def test_factory_fluent_chain(self):
        """Test factory with fluent method chaining."""
        client = (
            HTTPClientFactory.create(timeout_secs=60)
            .bearer_token("token")
            .add_header("X-Custom", "value")
        )
        assert isinstance(client, HTTPClient)
        assert client.settings.timeout_secs == 60
        assert "Authorization" in client._default_headers
        assert "X-Custom" in client._default_headers

    def test_factory_create_async_transport(self):
        """Async client via HTTPTransport.ASYNC (requires httpx)."""
        pytest.importorskip("httpx")
        from axiompy.io.http_async import AsyncHTTPClient

        client = HTTPClientFactory.create(
            transport=HTTPTransport.ASYNC,
            settings=HTTPClientSettings(timeout_secs=7),
        )
        assert isinstance(client, AsyncHTTPClient)
        assert client.settings.timeout_secs == 7


class TestHTTPClientExceptions:
    """Test exception classes."""

    def test_http_client_error(self):
        """Test HTTPClientError."""
        error = HTTPClientError("Test error")
        assert str(error) == "Test error"

    def test_http_connection_error(self):
        """Test HTTPConnectionError."""
        error = HTTPConnectionError("Connection failed")
        assert isinstance(error, HTTPClientError)

    def test_http_request_error(self):
        """Test HTTPRequestError."""
        error = HTTPRequestError("Request failed")
        assert isinstance(error, HTTPClientError)

    def test_http_auth_error(self):
        """Test HTTPAuthError."""
        error = HTTPAuthError("Auth failed")
        assert isinstance(error, HTTPClientError)


class TestHTTPClientIntegration:
    """Integration tests with multiple features."""

    @patch("axiompy.io.http.requests.Session.get")
    def test_client_with_all_features(self, mock_get):
        """Test client with headers, auth, and retry."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {"result": "success"}
        mock_get.return_value = mock_response

        client = (
            HTTPClientFactory.create(timeout_secs=30)
            .bearer_token("my_token")
            .add_header("X-Custom", "value")
        )

        retry_config = RetryConfig(max_attempts=3)
        deserializer = DeserializerFactory.create_json()
        result = client.get_with_retry(
            "https://api.example.com/data", retry_config=retry_config, deserializer=deserializer
        )

        assert result == {"result": "success"}
        assert "Authorization" in client._default_headers

    @patch("axiompy.io.http.requests.Session.post")
    def test_post_with_form_data(self, mock_post):
        """Test POST with form data."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.ok = True
        mock_post.return_value = mock_response

        client = HTTPClientFactory.create()
        response = client.post("https://api.example.com/data", data={"key": "value"})

        assert response.status_code == 200

    @patch("axiompy.io.http.requests.Session.get")
    def test_get_with_error_and_partial_text(self, mock_get):
        """Test error response with text truncation."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 500
        mock_response.ok = False
        # Simulate a long error message that gets truncated
        long_text = "A" * 300
        mock_response.text = long_text
        mock_get.return_value = mock_response

        client = HTTPClientFactory.create()

        with pytest.raises(HTTPRequestError) as exc_info:
            client.get("https://api.example.com/data")

        # Should contain only first 200 chars
        assert len(str(exc_info.value)) > 0

    @patch("axiompy.io.http.requests.Session.post")
    def test_post_json_for_json_parse_error(self, mock_post):
        """Test POST JSON for JSON with parse error."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        client = HTTPClientFactory.create()
        deserializer = DeserializerFactory.create_json()

        with pytest.raises(HTTPRequestError):
            client.post(
                "https://api.example.com/data", json={"key": "value"}, deserializer=deserializer
            )

    @patch("axiompy.io.http.requests.Session.put")
    def test_put_json_for_json_response(self, mock_put):
        """Test PUT JSON response."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.ok = True
        mock_put.return_value = mock_response

        client = HTTPClientFactory.create()

        response = client.put("https://api.example.com/data", json={"key": "value"})
        assert response.status_code == 200

    @patch("axiompy.io.http.requests.Session.delete")
    def test_delete_with_headers(self, mock_delete):
        """Test DELETE request with custom headers."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 204
        mock_response.ok = True
        mock_delete.return_value = mock_response

        client = HTTPClientFactory.create()
        headers = {"X-Custom": "value"}
        response = client.delete("https://api.example.com/data", headers=headers)

        assert response.status_code == 204

    @patch("axiompy.io.http.requests.Session.get")
    @patch("time.sleep")
    def test_get_json_retry_failure_multiple_attempts(self, mock_sleep, mock_get):
        """Test GET JSON retry with multiple failed attempts."""
        error_response = Mock(spec=requests.Response)
        error_response.status_code = 500
        error_response.ok = False
        error_response.text = "Server Error"

        mock_get.return_value = error_response

        client = HTTPClientFactory.create()
        retry_config = RetryConfig(max_attempts=3)
        deserializer = DeserializerFactory.create_json()

        with pytest.raises(HTTPRequestError):
            client.get_with_retry(
                "https://api.example.com/data", retry_config=retry_config, deserializer=deserializer
            )

        # Verify we made 3 attempts
        assert mock_get.call_count == 3
        # Verify we slept 2 times (between attempts)
        assert mock_sleep.call_count == 2

    @patch("axiompy.io.http.requests.Session.get")
    def test_get_with_non_retryable_error(self, mock_get):
        """Test GET request with non-retryable error response."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 400
        mock_response.ok = False
        mock_response.text = "Bad Request"
        mock_get.return_value = mock_response

        client = HTTPClientFactory.create()

        with pytest.raises(HTTPRequestError):
            client.get("https://api.example.com/data")

    def test_client_no_auth(self):
        """Test client without auth."""
        client = HTTPClientFactory.create()
        assert isinstance(client, HTTPClient)
        assert client._auth is None

    @patch("axiompy.io.http.requests.Session.post")
    def test_post_with_bytes_data(self, mock_post):
        """Test POST with bytes data."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.ok = True
        mock_post.return_value = mock_response

        client = HTTPClientFactory.create()
        response = client.post("https://api.example.com/data", data=b"binary_data")

        assert response.status_code == 200

    @patch("axiompy.io.http.requests.Session.post")
    def test_post_json_for_json_with_retry_succeeds(self, mock_post):
        """Test POST JSON for JSON with retry succeeds."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response

        client = HTTPClientFactory.create()
        deserializer = DeserializerFactory.create_json()
        result = client.post_with_retry(
            "https://api.example.com/data",
            json={"key": "value"},
            deserializer=deserializer,
        )

        assert result == {"result": "success"}

    @patch("axiompy.io.http.requests.Session.get")
    def test_get_request_success_response_code(self, mock_get):
        """Test successful GET response."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 201
        mock_response.ok = True
        mock_get.return_value = mock_response

        client = HTTPClientFactory.create()
        response = client.get("https://api.example.com/data")

        assert response.status_code == 201


# ============================================================================
# Missing Retry Methods Tests
# ============================================================================


class TestHTTPClientRetryMethods:
    """Test missing HTTP client retry methods."""

    @patch("axiompy.io.http.requests.Session.put")
    @patch("time.sleep")
    def test_put_with_retry_success_first_attempt(self, mock_sleep, mock_put):
        """Test PUT with retry succeeds on first attempt."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {"result": "success"}
        mock_put.return_value = mock_response

        client = HTTPClientFactory.create()
        retry_config = RetryConfig(max_attempts=3)
        result = client.put_with_retry(
            "https://api.example.com/data",
            json={"key": "value"},
            retry_config=retry_config,
            deserializer=DeserializerFactory.create_json(),
        )

        assert result == {"result": "success"}
        mock_put.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("axiompy.io.http.requests.Session.put")
    @patch("time.sleep")
    def test_put_with_retry_succeeds_after_failure(self, mock_sleep, mock_put):
        """Test PUT with retry succeeds after failure."""
        error_response = Mock(spec=requests.Response)
        error_response.status_code = 503
        error_response.ok = False

        success_response = Mock(spec=requests.Response)
        success_response.status_code = 200
        success_response.ok = True
        success_response.json.return_value = {"result": "success"}

        mock_put.side_effect = [error_response, success_response]

        client = HTTPClientFactory.create()
        retry_config = RetryConfig(max_attempts=3)
        result = client.put_with_retry(
            "https://api.example.com/data",
            json={"key": "value"},
            retry_config=retry_config,
            deserializer=DeserializerFactory.create_json(),
        )

        assert result == {"result": "success"}
        assert mock_put.call_count == 2
        mock_sleep.assert_called_once()

    @patch("axiompy.io.http.requests.Session.patch")
    @patch("time.sleep")
    def test_patch_with_retry_success_first_attempt(self, mock_sleep, mock_patch):
        """Test PATCH with retry succeeds on first attempt."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {"result": "patched"}
        mock_patch.return_value = mock_response

        client = HTTPClientFactory.create()
        retry_config = RetryConfig(max_attempts=3)
        result = client.patch_with_retry(
            "https://api.example.com/data",
            json={"key": "value"},
            retry_config=retry_config,
            deserializer=DeserializerFactory.create_json(),
        )

        assert result == {"result": "patched"}
        mock_patch.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("axiompy.io.http.requests.Session.patch")
    @patch("time.sleep")
    def test_patch_with_retry_succeeds_after_failure(self, mock_sleep, mock_patch):
        """Test PATCH with retry succeeds after failure."""
        error_response = Mock(spec=requests.Response)
        error_response.status_code = 502
        error_response.ok = False

        success_response = Mock(spec=requests.Response)
        success_response.status_code = 200
        success_response.ok = True
        success_response.json.return_value = {"result": "patched"}

        mock_patch.side_effect = [error_response, success_response]

        client = HTTPClientFactory.create()
        retry_config = RetryConfig(max_attempts=3)
        result = client.patch_with_retry(
            "https://api.example.com/data",
            json={"key": "value"},
            retry_config=retry_config,
            deserializer=DeserializerFactory.create_json(),
        )

        assert result == {"result": "patched"}
        assert mock_patch.call_count == 2

    @patch("axiompy.io.http.requests.Session.delete")
    @patch("time.sleep")
    def test_delete_with_retry_success_first_attempt(self, mock_sleep, mock_delete):
        """Test DELETE with retry succeeds on first attempt."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 204
        mock_response.ok = True
        mock_delete.return_value = mock_response

        client = HTTPClientFactory.create()
        retry_config = RetryConfig(max_attempts=3)
        response = client.delete_with_retry(
            "https://api.example.com/data",
            retry_config=retry_config,
        )

        assert response.status_code == 204
        mock_delete.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("axiompy.io.http.requests.Session.delete")
    @patch("time.sleep")
    def test_delete_with_retry_succeeds_after_failure(self, mock_sleep, mock_delete):
        """Test DELETE with retry succeeds after failure."""
        error_response = Mock(spec=requests.Response)
        error_response.status_code = 500
        error_response.ok = False

        success_response = Mock(spec=requests.Response)
        success_response.status_code = 204
        success_response.ok = True

        mock_delete.side_effect = [error_response, success_response]

        client = HTTPClientFactory.create()
        retry_config = RetryConfig(max_attempts=3)
        response = client.delete_with_retry(
            "https://api.example.com/data",
            retry_config=retry_config,
        )

        assert response.status_code == 204
        assert mock_delete.call_count == 2
        mock_sleep.assert_called_once()

    @patch("axiompy.io.http.requests.Session.delete")
    @patch("time.sleep")
    def test_delete_with_retry_exhausts_attempts(self, mock_sleep, mock_delete):
        """Test DELETE with retry exhausts attempts."""
        error_response = Mock(spec=requests.Response)
        error_response.status_code = 503
        error_response.ok = False

        mock_delete.return_value = error_response

        client = HTTPClientFactory.create()
        retry_config = RetryConfig(max_attempts=2)

        with pytest.raises(HTTPRequestError):
            client.delete_with_retry(
                "https://api.example.com/data",
                retry_config=retry_config,
            )

        assert mock_delete.call_count == 2
        assert mock_sleep.call_count == 1

    @patch("axiompy.io.http.requests.Session.put")
    @patch("time.sleep")
    def test_put_with_retry_rate_limit(self, mock_sleep, mock_put):
        """Test PUT with retry on rate limit."""
        error_response = Mock(spec=requests.Response)
        error_response.status_code = 429
        error_response.ok = False

        success_response = Mock(spec=requests.Response)
        success_response.status_code = 200
        success_response.ok = True
        success_response.json.return_value = {"result": "success"}

        mock_put.side_effect = [error_response, success_response]

        client = HTTPClientFactory.create()
        retry_config = RetryConfig(max_attempts=3)
        result = client.put_with_retry(
            "https://api.example.com/data",
            json={"key": "value"},
            retry_config=retry_config,
            deserializer=DeserializerFactory.create_json(),
        )

        assert result == {"result": "success"}

    @patch("axiompy.io.http.requests.Session.patch")
    @patch("time.sleep")
    def test_patch_with_retry_exhausts_attempts(self, mock_sleep, mock_patch):
        """Test PATCH with retry exhausts attempts."""
        error_response = Mock(spec=requests.Response)
        error_response.status_code = 502
        error_response.ok = False

        mock_patch.return_value = error_response

        client = HTTPClientFactory.create()
        retry_config = RetryConfig(max_attempts=2)

        with pytest.raises(HTTPRequestError):
            client.patch_with_retry(
                "https://api.example.com/data",
                json={"key": "value"},
                retry_config=retry_config,
                deserializer=DeserializerFactory.create_json(),
            )

        assert mock_patch.call_count == 2
