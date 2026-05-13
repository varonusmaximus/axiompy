"""
Comprehensive tests for JSON-RPC 2.0 server implementation.

Tests cover:
    - Settings validation
    - Request parsing (single, batch, errors)
    - Response handling
    - Method registration and execution
    - MCP server integration
    - Error handling
    - Factory pattern
    - Mock server for testing
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from axiompy.servers.jsonrpc import (
    HTTPJSONRPCServer,
    JSONRPCError,
    JSONRPCErrorCode,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCServer,
    JSONRPCServerError,
    JSONRPCServerFactory,
    JSONRPCSettings,
    JSONRPCTransport,
    MockJSONRPCServer,
    StdioJSONRPCServer,
)
from axiompy.servers.mcp import MCPServerSettings
from axiompy.validators import ValidationError


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def default_settings():
    """Default JSON-RPC settings for testing."""
    return JSONRPCSettings(
        host="127.0.0.1",
        port=8000,
        name="test-server",
        version="1.0.0",
    )


@pytest.fixture
def mock_server(default_settings):
    """Create a mock JSON-RPC server for testing."""
    return JSONRPCServerFactory.create_mock(default_settings)


class MockMCPServer:
    """Simple mock MCP server for testing JSON-RPC integration."""

    def __init__(self, settings):
        self.settings = settings
        self.tools = {}
        self._session_counter = 0

    def register_tool(self, name, func, description, **kwargs):
        """Register a tool."""
        from axiompy.servers.mcp import MCPTool

        self.tools[name] = MCPTool(name=name, func=func, description=description)
        return self

    def initialize(self):
        """Initialize the server."""
        pass

    def create_session(self, client_id):
        """Create a mock session."""
        self._session_counter += 1
        return MagicMock(id=f"session-{self._session_counter}")

    def execute_tool(self, tool_name, session, **kwargs):
        """Execute a tool."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")
        return self.tools[tool_name].func(**kwargs)


@pytest.fixture
def mcp_server():
    """Create a mock MCP server with test tools."""
    settings = MCPServerSettings(name="TestMCPServer")
    server = MockMCPServer(settings)
    server.register_tool("add", lambda a, b: a + b, "Add two numbers")
    server.register_tool("multiply", lambda x, y: x * y, "Multiply two numbers")
    server.register_tool("greet", lambda name: f"Hello, {name}!", "Greet someone")
    server.initialize()
    return server


@pytest.fixture
def mock_server_with_mcp(default_settings, mcp_server):
    """Create a mock JSON-RPC server wrapping MCP server."""
    return JSONRPCServerFactory.create_mock(default_settings, mcp_server)


# =============================================================================
# JSONRPCSettings Tests
# =============================================================================


class TestJSONRPCSettings:
    """Tests for JSONRPCSettings validation."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = JSONRPCSettings()
        assert settings.host == "127.0.0.1"
        assert settings.port == 8000
        assert settings.name == "jsonrpc-server"
        assert settings.version == "1.0.0"
        assert settings.extra_params == {}

    def test_custom_settings(self):
        """Test custom settings values."""
        settings = JSONRPCSettings(
            host="0.0.0.0",
            port=9000,
            name="custom-server",
            version="2.0.0",
            extra_params={"debug": True},
        )
        assert settings.host == "0.0.0.0"
        assert settings.port == 9000
        assert settings.name == "custom-server"
        assert settings.version == "2.0.0"
        assert settings.extra_params == {"debug": True}

    def test_port_validation_valid(self):
        """Test valid port numbers."""
        settings = JSONRPCSettings(port=0)  # Auto-assign
        assert settings.port == 0

        settings = JSONRPCSettings(port=65535)
        assert settings.port == 65535

    def test_port_validation_invalid(self):
        """Test invalid port numbers raise error."""
        with pytest.raises(ValidationError):
            JSONRPCSettings(port=-1)

        with pytest.raises(ValidationError):
            JSONRPCSettings(port=65536)

    def test_empty_name_raises_error(self):
        """Test empty server name raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            JSONRPCSettings(name="")


# =============================================================================
# JSONRPCRequest Tests
# =============================================================================


class TestJSONRPCRequest:
    """Tests for JSONRPCRequest data class."""

    def test_request_with_id(self):
        """Test request with id is not a notification."""
        request = JSONRPCRequest(jsonrpc="2.0", method="test", id=1)
        assert not request.is_notification
        assert request.id == 1

    def test_notification_without_id(self):
        """Test request without id is a notification."""
        request = JSONRPCRequest(jsonrpc="2.0", method="test")
        assert request.is_notification
        assert request.id is None

    def test_request_with_params(self):
        """Test request with parameters."""
        request = JSONRPCRequest(jsonrpc="2.0", method="add", params={"a": 1, "b": 2}, id=1)
        assert request.params == {"a": 1, "b": 2}


# =============================================================================
# JSONRPCResponse Tests
# =============================================================================


class TestJSONRPCResponse:
    """Tests for JSONRPCResponse data class."""

    def test_success_response(self):
        """Test success response serialization."""
        response = JSONRPCResponse(id=1, result=42)
        d = response.to_dict()
        assert d == {"jsonrpc": "2.0", "id": 1, "result": 42}

    def test_error_response(self):
        """Test error response serialization."""
        response = JSONRPCResponse(id=1, error={"code": -32601, "message": "Method not found"})
        d = response.to_dict()
        assert d == {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32601, "message": "Method not found"},
        }

    def test_response_with_null_id(self):
        """Test response with null id (for parse errors)."""
        response = JSONRPCResponse(id=None, result="test")
        d = response.to_dict()
        assert d["id"] is None


# =============================================================================
# JSONRPCError Tests
# =============================================================================


class TestJSONRPCError:
    """Tests for JSONRPCError exception."""

    def test_error_creation(self):
        """Test error creation and attributes."""
        error = JSONRPCError(JSONRPCErrorCode.METHOD_NOT_FOUND, "Method 'foo' not found")
        assert error.code == JSONRPCErrorCode.METHOD_NOT_FOUND
        assert error.message == "Method 'foo' not found"
        assert error.data is None

    def test_error_with_data(self):
        """Test error with additional data."""
        error = JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "Invalid params",
            data={"missing": ["a", "b"]},
        )
        assert error.data == {"missing": ["a", "b"]}

    def test_error_to_dict(self):
        """Test error serialization."""
        error = JSONRPCError(JSONRPCErrorCode.PARSE_ERROR, "Invalid JSON")
        d = error.to_dict()
        assert d == {"code": -32700, "message": "Invalid JSON"}

    def test_error_to_dict_with_data(self):
        """Test error serialization with data."""
        error = JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, "Server error", data={"trace": "..."})
        d = error.to_dict()
        assert d == {
            "code": -32603,
            "message": "Server error",
            "data": {"trace": "..."},
        }


# =============================================================================
# JSONRPCErrorCode Tests
# =============================================================================


class TestJSONRPCErrorCode:
    """Tests for JSON-RPC error codes."""

    def test_standard_error_codes(self):
        """Test standard JSON-RPC 2.0 error codes."""
        assert JSONRPCErrorCode.PARSE_ERROR.value == -32700
        assert JSONRPCErrorCode.INVALID_REQUEST.value == -32600
        assert JSONRPCErrorCode.METHOD_NOT_FOUND.value == -32601
        assert JSONRPCErrorCode.INVALID_PARAMS.value == -32602
        assert JSONRPCErrorCode.INTERNAL_ERROR.value == -32603

    def test_server_error_codes(self):
        """Test server-specific error codes."""
        assert JSONRPCErrorCode.SERVER_ERROR.value == -32000
        assert JSONRPCErrorCode.TOOL_NOT_FOUND.value == -32001
        assert JSONRPCErrorCode.TOOL_EXECUTION_ERROR.value == -32002


# =============================================================================
# Request Parsing Tests
# =============================================================================


class TestRequestParsing:
    """Tests for JSON-RPC request parsing."""

    def test_parse_valid_request(self, mock_server):
        """Test parsing valid JSON-RPC request."""
        data = json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 1})
        result = mock_server.parse_request(data)
        assert result.is_ok()
        request = result.unwrap()
        assert isinstance(request, JSONRPCRequest)
        assert request.method == "ping"
        assert request.id == 1

    def test_parse_request_with_params(self, mock_server):
        """Test parsing request with parameters."""
        data = json.dumps({"jsonrpc": "2.0", "method": "add", "params": {"a": 1, "b": 2}, "id": 1})
        result = mock_server.parse_request(data)
        assert result.is_ok()
        request = result.unwrap()
        assert request.params == {"a": 1, "b": 2}

    def test_parse_notification(self, mock_server):
        """Test parsing notification (no id)."""
        data = json.dumps({"jsonrpc": "2.0", "method": "log", "params": {"msg": "hi"}})
        result = mock_server.parse_request(data)
        assert result.is_ok()
        request = result.unwrap()
        assert request.is_notification

    def test_parse_batch_request(self, mock_server):
        """Test parsing batch request."""
        data = json.dumps(
            [
                {"jsonrpc": "2.0", "method": "ping", "id": 1},
                {"jsonrpc": "2.0", "method": "ping", "id": 2},
            ]
        )
        result = mock_server.parse_request(data)
        assert result.is_ok()
        requests = result.unwrap()
        assert isinstance(requests, list)
        assert len(requests) == 2
        assert requests[0].id == 1
        assert requests[1].id == 2

    def test_parse_invalid_json(self, mock_server):
        """Test parsing invalid JSON returns error."""
        result = mock_server.parse_request("not valid json")
        assert result.is_err()
        error = result.get_error()
        assert error.code == JSONRPCErrorCode.PARSE_ERROR

    def test_parse_missing_jsonrpc_version(self, mock_server):
        """Test parsing request without jsonrpc field."""
        data = json.dumps({"method": "ping", "id": 1})
        result = mock_server.parse_request(data)
        assert result.is_err()
        error = result.get_error()
        assert error.code == JSONRPCErrorCode.INVALID_REQUEST

    def test_parse_wrong_jsonrpc_version(self, mock_server):
        """Test parsing request with wrong version."""
        data = json.dumps({"jsonrpc": "1.0", "method": "ping", "id": 1})
        result = mock_server.parse_request(data)
        assert result.is_err()
        error = result.get_error()
        assert error.code == JSONRPCErrorCode.INVALID_REQUEST

    def test_parse_missing_method(self, mock_server):
        """Test parsing request without method."""
        data = json.dumps({"jsonrpc": "2.0", "id": 1})
        result = mock_server.parse_request(data)
        assert result.is_err()
        error = result.get_error()
        assert error.code == JSONRPCErrorCode.INVALID_REQUEST

    def test_parse_empty_batch(self, mock_server):
        """Test parsing empty batch array."""
        data = json.dumps([])
        result = mock_server.parse_request(data)
        assert result.is_err()
        error = result.get_error()
        assert error.code == JSONRPCErrorCode.INVALID_REQUEST

    def test_parse_non_object_request(self, mock_server):
        """Test parsing non-object request."""
        data = json.dumps("string request")
        result = mock_server.parse_request(data)
        assert result.is_err()


# =============================================================================
# Request Handling Tests
# =============================================================================


class TestRequestHandling:
    """Tests for JSON-RPC request handling."""

    def test_handle_valid_request(self, mock_server):
        """Test handling valid request."""
        mock_server.register_method("echo", lambda p: p.get("msg"))
        data = json.dumps({"jsonrpc": "2.0", "method": "echo", "params": {"msg": "hello"}, "id": 1})
        response = mock_server.handle_request(data)
        assert response is not None
        parsed = json.loads(response)
        assert parsed["result"] == "hello"
        assert parsed["id"] == 1

    def test_handle_notification(self, mock_server):
        """Test handling notification returns None."""
        mock_server.register_method("log", lambda p: None)
        data = json.dumps({"jsonrpc": "2.0", "method": "log", "params": {"msg": "hello"}})
        response = mock_server.handle_request(data)
        assert response is None

    def test_handle_method_not_found(self, mock_server):
        """Test handling unknown method."""
        data = json.dumps({"jsonrpc": "2.0", "method": "unknown", "id": 1})
        response = mock_server.handle_request(data)
        parsed = json.loads(response)
        assert "error" in parsed
        assert parsed["error"]["code"] == JSONRPCErrorCode.METHOD_NOT_FOUND.value

    def test_handle_batch_request(self, mock_server):
        """Test handling batch request."""
        mock_server.register_method("double", lambda p: p.get("n", 0) * 2)
        data = json.dumps(
            [
                {"jsonrpc": "2.0", "method": "double", "params": {"n": 5}, "id": 1},
                {"jsonrpc": "2.0", "method": "double", "params": {"n": 10}, "id": 2},
            ]
        )
        response = mock_server.handle_request(data)
        parsed = json.loads(response)
        assert isinstance(parsed, list)
        assert len(parsed) == 2
        assert parsed[0]["result"] == 10
        assert parsed[1]["result"] == 20

    def test_handle_mixed_batch(self, mock_server):
        """Test batch with notifications and requests."""
        mock_server.register_method("echo", lambda p: p.get("msg"))
        data = json.dumps(
            [
                {"jsonrpc": "2.0", "method": "echo", "params": {"msg": "a"}, "id": 1},
                {"jsonrpc": "2.0", "method": "echo", "params": {"msg": "b"}},  # notification
                {"jsonrpc": "2.0", "method": "echo", "params": {"msg": "c"}, "id": 2},
            ]
        )
        response = mock_server.handle_request(data)
        parsed = json.loads(response)
        # Should only have 2 responses (notifications don't return)
        assert len(parsed) == 2
        assert parsed[0]["id"] == 1
        assert parsed[1]["id"] == 2

    def test_handle_all_notifications_batch(self, mock_server):
        """Test batch of only notifications returns None."""
        mock_server.register_method("log", lambda p: None)
        data = json.dumps(
            [
                {"jsonrpc": "2.0", "method": "log", "params": {"msg": "a"}},
                {"jsonrpc": "2.0", "method": "log", "params": {"msg": "b"}},
            ]
        )
        response = mock_server.handle_request(data)
        assert response is None

    def test_handle_parse_error(self, mock_server):
        """Test handling parse error."""
        response = mock_server.handle_request("invalid json")
        parsed = json.loads(response)
        assert "error" in parsed
        assert parsed["error"]["code"] == JSONRPCErrorCode.PARSE_ERROR.value

    def test_handle_method_raises_jsonrpc_error(self, mock_server):
        """Test method that raises JSONRPCError."""

        def failing_method(params):
            raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing required param")

        mock_server.register_method("fail", failing_method)
        data = json.dumps({"jsonrpc": "2.0", "method": "fail", "id": 1})
        response = mock_server.handle_request(data)
        parsed = json.loads(response)
        assert parsed["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value

    def test_handle_method_raises_exception(self, mock_server):
        """Test method that raises generic exception."""

        def error_method(params):
            raise RuntimeError("Something went wrong")

        mock_server.register_method("error", error_method)
        data = json.dumps({"jsonrpc": "2.0", "method": "error", "id": 1})
        response = mock_server.handle_request(data)
        parsed = json.loads(response)
        assert parsed["error"]["code"] == JSONRPCErrorCode.INTERNAL_ERROR.value


# =============================================================================
# Method Registration Tests
# =============================================================================


class TestMethodRegistration:
    """Tests for method registration."""

    def test_register_method(self, mock_server):
        """Test registering a method."""
        mock_server.register_method("test", lambda p: "ok")
        assert "test" in mock_server.methods

    def test_register_method_chaining(self, mock_server):
        """Test method chaining on registration."""
        result = (
            mock_server.register_method("a", lambda p: 1)
            .register_method("b", lambda p: 2)
            .register_method("c", lambda p: 3)
        )
        assert result is mock_server
        assert "a" in mock_server.methods
        assert "b" in mock_server.methods
        assert "c" in mock_server.methods

    def test_override_method(self, mock_server):
        """Test overriding an existing method."""
        mock_server.register_method("test", lambda p: "old")
        mock_server.register_method("test", lambda p: "new")

        data = json.dumps({"jsonrpc": "2.0", "method": "test", "id": 1})
        response = mock_server.handle_request(data)
        parsed = json.loads(response)
        assert parsed["result"] == "new"


# =============================================================================
# MCP Integration Tests
# =============================================================================


class TestMCPIntegration:
    """Tests for MCP server integration."""

    def test_mcp_methods_registered(self, mock_server_with_mcp):
        """Test MCP protocol methods are registered."""
        assert "initialize" in mock_server_with_mcp.methods
        assert "initialized" in mock_server_with_mcp.methods
        assert "tools/list" in mock_server_with_mcp.methods
        assert "tools/call" in mock_server_with_mcp.methods
        assert "ping" in mock_server_with_mcp.methods

    def test_initialize(self, mock_server_with_mcp):
        """Test initialize method."""
        data = json.dumps({"jsonrpc": "2.0", "method": "initialize", "id": 1})
        response = mock_server_with_mcp.handle_request(data)
        parsed = json.loads(response)
        assert "result" in parsed
        assert "protocolVersion" in parsed["result"]
        assert "serverInfo" in parsed["result"]
        assert "capabilities" in parsed["result"]

    def test_tools_list(self, mock_server_with_mcp):
        """Test tools/list method."""
        data = json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 1})
        response = mock_server_with_mcp.handle_request(data)
        parsed = json.loads(response)
        tools = parsed["result"]["tools"]
        assert len(tools) == 3
        tool_names = [t["name"] for t in tools]
        assert "add" in tool_names
        assert "multiply" in tool_names
        assert "greet" in tool_names

    def test_tools_call_success(self, mock_server_with_mcp):
        """Test tools/call method success."""
        data = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "add", "arguments": {"a": 5, "b": 3}},
                "id": 1,
            }
        )
        response = mock_server_with_mcp.handle_request(data)
        parsed = json.loads(response)
        assert "result" in parsed
        assert parsed["result"]["content"][0]["text"] == "8"

    def test_tools_call_tool_not_found(self, mock_server_with_mcp):
        """Test tools/call with unknown tool."""
        data = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "unknown", "arguments": {}},
                "id": 1,
            }
        )
        response = mock_server_with_mcp.handle_request(data)
        parsed = json.loads(response)
        assert "error" in parsed
        assert parsed["error"]["code"] == JSONRPCErrorCode.TOOL_NOT_FOUND.value

    def test_tools_call_missing_name(self, mock_server_with_mcp):
        """Test tools/call without tool name."""
        data = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"arguments": {}},
                "id": 1,
            }
        )
        response = mock_server_with_mcp.handle_request(data)
        parsed = json.loads(response)
        assert "error" in parsed
        assert parsed["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value

    def test_tools_call_missing_params(self, mock_server_with_mcp):
        """Test tools/call without params."""
        data = json.dumps({"jsonrpc": "2.0", "method": "tools/call", "id": 1})
        response = mock_server_with_mcp.handle_request(data)
        parsed = json.loads(response)
        assert "error" in parsed
        assert parsed["error"]["code"] == JSONRPCErrorCode.INVALID_PARAMS.value

    def test_ping(self, mock_server_with_mcp):
        """Test ping method."""
        data = json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 1})
        response = mock_server_with_mcp.handle_request(data)
        parsed = json.loads(response)
        assert "result" in parsed
        assert parsed["result"] == {}

    def test_tools_list_without_mcp(self, mock_server):
        """Test tools/list without MCP server returns empty."""
        mock_server.register_method("tools/list", lambda p: {"tools": []})
        data = json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 1})
        response = mock_server.handle_request(data)
        parsed = json.loads(response)
        assert parsed["result"]["tools"] == []


# =============================================================================
# Factory Tests
# =============================================================================


class TestJSONRPCServerFactory:
    """Tests for JSONRPCServerFactory."""

    def test_create_http_server(self, default_settings):
        """Test creating HTTP transport server."""
        server = JSONRPCServerFactory.create(JSONRPCTransport.HTTP, default_settings)
        assert isinstance(server, HTTPJSONRPCServer)

    def test_create_stdio_server(self, default_settings):
        """Test creating stdio transport server."""
        server = JSONRPCServerFactory.create(JSONRPCTransport.STDIO, default_settings)
        assert isinstance(server, StdioJSONRPCServer)

    def test_create_with_mcp_server(self, default_settings, mcp_server):
        """Test creating server with MCP server."""
        server = JSONRPCServerFactory.create(
            JSONRPCTransport.HTTP, default_settings, mcp_server=mcp_server
        )
        assert server.mcp_server is mcp_server
        assert "tools/list" in server.methods

    def test_create_mock_server(self, default_settings):
        """Test creating mock server."""
        server = JSONRPCServerFactory.create_mock(default_settings)
        assert isinstance(server, MockJSONRPCServer)

    def test_create_mock_with_defaults(self):
        """Test creating mock server with default settings."""
        server = JSONRPCServerFactory.create_mock()
        assert isinstance(server, MockJSONRPCServer)
        assert server.settings.name == "mock-server"

    def test_create_mock_with_mcp(self, default_settings, mcp_server):
        """Test creating mock server with MCP server."""
        server = JSONRPCServerFactory.create_mock(default_settings, mcp_server)
        assert server.mcp_server is mcp_server

    def test_invalid_transport_raises_error(self, default_settings):
        """Test invalid transport raises ValueError."""

        # Create a mock invalid transport type
        class FakeTransport:
            pass

        with pytest.raises(ValueError, match="Unsupported transport"):
            JSONRPCServerFactory.create(FakeTransport(), default_settings)


# =============================================================================
# MockJSONRPCServer Tests
# =============================================================================


class TestMockJSONRPCServer:
    """Tests for MockJSONRPCServer."""

    def test_mock_tracks_requests(self, mock_server):
        """Test mock server tracks requests."""
        mock_server.register_method("test", lambda p: "ok")
        data = json.dumps({"jsonrpc": "2.0", "method": "test", "id": 1})
        mock_server.handle_request(data)
        assert len(mock_server.requests_received) == 1
        assert data in mock_server.requests_received

    def test_mock_tracks_responses(self, mock_server):
        """Test mock server tracks responses."""
        mock_server.register_method("test", lambda p: "ok")
        data = json.dumps({"jsonrpc": "2.0", "method": "test", "id": 1})
        mock_server.handle_request(data)
        assert len(mock_server.responses_sent) == 1

    def test_mock_run_is_noop(self, mock_server):
        """Test mock run does nothing."""
        # Should not raise
        mock_server.run()


# =============================================================================
# Transport Tests
# =============================================================================


class TestHTTPJSONRPCServer:
    """Tests for HTTPJSONRPCServer."""

    def test_http_server_creation(self, default_settings):
        """Test HTTP server creation."""
        server = HTTPJSONRPCServer(default_settings)
        assert isinstance(server, HTTPJSONRPCServer)
        assert server.settings == default_settings


class TestStdioJSONRPCServer:
    """Tests for StdioJSONRPCServer."""

    def test_stdio_server_creation(self, default_settings):
        """Test stdio server creation."""
        server = StdioJSONRPCServer(default_settings)
        assert isinstance(server, StdioJSONRPCServer)


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_string_id(self, mock_server):
        """Test request with string id."""
        mock_server.register_method("test", lambda p: "ok")
        data = json.dumps({"jsonrpc": "2.0", "method": "test", "id": "abc-123"})
        response = mock_server.handle_request(data)
        parsed = json.loads(response)
        assert parsed["id"] == "abc-123"

    def test_null_result(self, mock_server):
        """Test method returning None."""
        mock_server.register_method("void", lambda p: None)
        data = json.dumps({"jsonrpc": "2.0", "method": "void", "id": 1})
        response = mock_server.handle_request(data)
        parsed = json.loads(response)
        assert parsed["result"] is None

    def test_complex_result(self, mock_server):
        """Test method returning complex object."""
        mock_server.register_method(
            "complex", lambda p: {"nested": {"list": [1, 2, 3], "bool": True}}
        )
        data = json.dumps({"jsonrpc": "2.0", "method": "complex", "id": 1})
        response = mock_server.handle_request(data)
        parsed = json.loads(response)
        assert parsed["result"]["nested"]["list"] == [1, 2, 3]

    def test_method_with_list_params(self, mock_server):
        """Test method with list parameters (positional)."""
        mock_server.register_method("sum", lambda p: sum(p) if isinstance(p, list) else 0)
        data = json.dumps({"jsonrpc": "2.0", "method": "sum", "params": [1, 2, 3], "id": 1})
        response = mock_server.handle_request(data)
        parsed = json.loads(response)
        assert parsed["result"] == 6

    def test_error_in_notification_suppressed(self, mock_server):
        """Test errors in notifications don't return response."""

        def failing(p):
            raise RuntimeError("fail")

        mock_server.register_method("fail", failing)
        data = json.dumps({"jsonrpc": "2.0", "method": "fail", "params": {}})
        response = mock_server.handle_request(data)
        assert response is None

    def test_method_not_found_notification_suppressed(self, mock_server):
        """Test method not found in notification doesn't return response."""
        data = json.dumps({"jsonrpc": "2.0", "method": "unknown", "params": {}})
        response = mock_server.handle_request(data)
        assert response is None


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests combining multiple features."""

    def test_full_mcp_workflow(self, mock_server_with_mcp):
        """Test complete MCP workflow: initialize -> list -> call."""
        # Initialize
        init_data = json.dumps({"jsonrpc": "2.0", "method": "initialize", "id": 1})
        init_response = mock_server_with_mcp.handle_request(init_data)
        init_parsed = json.loads(init_response)
        assert "result" in init_parsed

        # List tools
        list_data = json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 2})
        list_response = mock_server_with_mcp.handle_request(list_data)
        list_parsed = json.loads(list_response)
        assert len(list_parsed["result"]["tools"]) == 3

        # Call tool
        call_data = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "greet", "arguments": {"name": "World"}},
                "id": 3,
            }
        )
        call_response = mock_server_with_mcp.handle_request(call_data)
        call_parsed = json.loads(call_response)
        assert call_parsed["result"]["content"][0]["text"] == "Hello, World!"

    def test_custom_and_mcp_methods_coexist(self, mock_server_with_mcp):
        """Test custom methods work alongside MCP methods."""
        mock_server_with_mcp.register_method("custom", lambda p: "custom result")

        # Custom method works
        custom_data = json.dumps({"jsonrpc": "2.0", "method": "custom", "id": 1})
        custom_response = mock_server_with_mcp.handle_request(custom_data)
        custom_parsed = json.loads(custom_response)
        assert custom_parsed["result"] == "custom result"

        # MCP method still works
        mcp_data = json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 2})
        mcp_response = mock_server_with_mcp.handle_request(mcp_data)
        mcp_parsed = json.loads(mcp_response)
        assert mcp_parsed["result"] == {}
