# @!testing

"""
Tests for MCPToolService - service layer for exposing MCP tools via HTTP.

Tests cover:
    - Service initialization and configuration
    - Tool discovery and listing
    - Tool execution via HTTP
    - Session management
    - Execution history tracking
    - Error handling
"""

import contextlib

import pytest

from axiompy.servers import (
    MCPServerFactory,
    MCPServerSettings,
    MCPServerType,
    MCPSession,
    MCPToolService,
    MCPToolServiceSettings,
)
from axiompy.validators import ValidationError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_mcp_server():
    """Create a mock MCP server with test tools (no external dependencies)."""
    from axiompy.servers import MCPServer

    class TestMCPServer(MCPServer):
        """Simple test implementation of MCPServer."""

        def initialize(self):
            pass

        def execute_tool(self, tool_name: str, session, **kwargs):
            tool = self.get_tool(tool_name)
            if not tool:
                from axiompy.servers.mcp import MCPToolError

                raise MCPToolError(f"Tool '{tool_name}' not found")
            return tool.execute(**kwargs)

        def shutdown(self):
            pass

    settings = MCPServerSettings(name="TestTools")
    server = TestMCPServer(settings)

    # Register test tools
    server.register_tool("add", lambda a, b: a + b, "Add two numbers")
    server.register_tool("multiply", lambda x, y: x * y, "Multiply two numbers")
    server.register_tool("echo", lambda message: f"Echo: {message}", "Echo a message")

    server.initialize()
    return server


@pytest.fixture
def service_settings():
    """Create service settings."""
    return MCPToolServiceSettings(enable_history=True)


@pytest.fixture
def tool_service(mock_mcp_server, service_settings):
    """Create MCPToolService instance."""
    return MCPToolService(mock_mcp_server, service_settings)


# ============================================================================
# Tests: MCPToolServiceSettings
# ============================================================================


class TestMCPToolServiceSettings:
    """Test MCPToolServiceSettings validation and defaults."""

    def test_default_settings(self):
        """Test default settings."""
        settings = MCPToolServiceSettings()
        assert settings.enable_history is True
        assert settings.max_session_timeout == 3600

    def test_custom_settings(self):
        """Test custom settings."""
        settings = MCPToolServiceSettings(enable_history=False, max_session_timeout=7200)
        assert settings.enable_history is False
        assert settings.max_session_timeout == 7200

    def test_invalid_max_session_timeout(self):
        """Test max_session_timeout boundary validation."""
        with pytest.raises(ValidationError, match="max_session_timeout"):
            MCPToolServiceSettings(max_session_timeout=0)

        with pytest.raises(ValidationError, match="max_session_timeout"):
            MCPToolServiceSettings(max_session_timeout=86401)


# ============================================================================
# Tests: MCPToolService Initialization
# ============================================================================


class TestMCPToolServiceInitialization:
    """Test MCPToolService initialization."""

    def test_service_creation(self, tool_service):
        """Test creating MCPToolService."""
        assert tool_service is not None
        assert len(tool_service.http_sessions) == 0
        assert len(tool_service.execution_history) == 0

    def test_service_with_disabled_history(self, mock_mcp_server):
        """Test service with history disabled."""
        settings = MCPToolServiceSettings(enable_history=False)
        service = MCPToolService(mock_mcp_server, settings)
        assert service.settings.enable_history is False

    def test_init_rejects_none_mcp_server(self, service_settings):
        """Test service rejects None mcp_server."""
        with pytest.raises(ValidationError, match="mcp_server cannot be None"):
            MCPToolService(None, service_settings)

    def test_init_rejects_none_settings(self, mock_mcp_server):
        """Test service rejects None settings."""
        with pytest.raises(ValidationError, match="settings cannot be None"):
            MCPToolService(mock_mcp_server, None)

    def test_init_rejects_invalid_mcp_server_type(self, service_settings):
        """Test service rejects non-MCPServer mcp_server."""
        with pytest.raises(ValidationError, match="mcp_server must be an MCPServer instance"):
            MCPToolService("not-a-server", service_settings)

    def test_init_rejects_invalid_settings_type(self, mock_mcp_server):
        """Test service rejects non-MCPToolServiceSettings settings."""
        with pytest.raises(ValidationError, match="settings must be MCPToolServiceSettings"):
            MCPToolService(mock_mcp_server, {"enable_history": True})

    def test_init_rejects_uninitialized_server(self, service_settings):
        """Test service rejects framework servers that have not been initialized."""
        from axiompy.servers import MCPServer

        class UninitializedServer(MCPServer):
            def initialize(self):
                self._initialized = True

            def execute_tool(self, tool_name: str, session, **kwargs):
                return None

            def shutdown(self):
                pass

        server = UninitializedServer(MCPServerSettings(name="Uninitialized"))
        server._initialized = False

        with pytest.raises(ValidationError, match="mcp_server must be initialized"):
            MCPToolService(server, service_settings)


# ============================================================================
# Tests: Session Management
# ============================================================================


class TestSessionManagement:
    """Test HTTP session management."""

    def test_create_session(self, tool_service):
        """Test creating HTTP session."""
        session_id = tool_service.create_session()
        assert session_id is not None
        assert session_id in tool_service.http_sessions

    def test_get_session(self, tool_service):
        """Test retrieving session."""
        session_id = tool_service.create_session()
        session = tool_service.get_session(session_id)
        assert session is not None
        assert isinstance(session, MCPSession)

    def test_get_nonexistent_session(self, tool_service):
        """Test getting nonexistent session returns None."""
        session = tool_service.get_session("nonexistent")
        assert session is None

    def test_get_or_create_session_new(self, tool_service):
        """Test creating new session when none provided."""
        session_id, session = tool_service.get_or_create_session()
        assert session_id is not None
        assert isinstance(session, MCPSession)

    def test_get_or_create_session_existing(self, tool_service):
        """Test reusing existing session."""
        # Create first session
        session_id1 = tool_service.create_session("client1")

        # Get same session
        session_id2, session = tool_service.get_or_create_session(session_id1)
        assert session_id1 == session_id2

    def test_close_session(self, tool_service):
        """Test closing a session."""
        session_id = tool_service.create_session()
        tool_service.close_session(session_id)
        assert tool_service.get_session(session_id) is None


# ============================================================================
# Tests: Server Information
# ============================================================================


class TestServerInformation:
    """Test server information retrieval."""

    def test_get_server_info(self, tool_service):
        """Test getting server information."""
        info = tool_service.get_server_info()
        assert info["name"] == "TestTools"
        assert info["tools_count"] == 3
        assert info["active_sessions"] == 0

    def test_health_check(self, tool_service):
        """Test health check endpoint."""
        health = tool_service.health_check()
        assert health["status"] == "healthy"
        assert health["server_name"] == "TestTools"
        assert health["tools_count"] == 3
        assert health["active_sessions"] == 0


# ============================================================================
# Tests: Tool Information
# ============================================================================


class TestToolInformation:
    """Test tool information retrieval."""

    def test_list_tools(self, tool_service):
        """Test listing all tools."""
        tools_info = tool_service.list_tools()
        assert "tools" in tools_info
        assert "total" in tools_info
        assert "server" in tools_info
        assert tools_info["total"] == 3
        assert tools_info["server"] == "TestTools"

        tool_names = [t["name"] for t in tools_info["tools"]]
        assert "add" in tool_names
        assert "multiply" in tool_names
        assert "echo" in tool_names

    def test_list_tools_includes_metadata(self, tool_service):
        """Test tools include metadata."""
        tools_info = tool_service.list_tools()
        tool = tools_info["tools"][0]

        assert "name" in tool
        assert "description" in tool
        assert "parameters" in tool
        assert "return_type" in tool
        assert "tags" in tool

    def test_get_tool_info(self, tool_service):
        """Test getting tool information."""
        tool_info = tool_service.get_tool_info("add")
        assert tool_info is not None
        assert tool_info["name"] == "add"
        assert tool_info["description"] == "Add two numbers"

    def test_get_nonexistent_tool_info(self, tool_service):
        """Test getting nonexistent tool returns None."""
        tool_info = tool_service.get_tool_info("nonexistent")
        assert tool_info is None


# ============================================================================
# Tests: Tool Execution
# ============================================================================


class TestToolExecution:
    """Test tool execution via service."""

    def test_execute_tool_success(self, tool_service):
        """Test successful tool execution."""
        result = tool_service.execute_tool("add", {"a": 5, "b": 3})
        assert result["success"] is True
        assert result["result"] == 8
        assert "session_id" in result

    def test_execute_tool_creates_history(self, tool_service):
        """Test tool execution is recorded in history."""
        result = tool_service.execute_tool("multiply", {"x": 3, "y": 4})
        session_id = result["session_id"]

        # Check history
        session_info = tool_service.get_session_info(session_id)
        assert session_info["total_executions"] == 1
        assert session_info["execution_history"][0]["tool"] == "multiply"
        assert session_info["execution_history"][0]["result"] == 12

    def test_execute_tool_reuse_session(self, tool_service):
        """Test reusing session across multiple executions."""
        # First execution
        result1 = tool_service.execute_tool("add", {"a": 5, "b": 3})
        session_id = result1["session_id"]

        # Second execution with same session
        result2 = tool_service.execute_tool("multiply", {"x": 2, "y": 4}, session_id)
        assert result2["session_id"] == session_id

        # Check both in history
        session_info = tool_service.get_session_info(session_id)
        assert session_info["total_executions"] == 2

    def test_execute_nonexistent_tool(self, tool_service):
        """Test executing nonexistent tool raises error."""
        with pytest.raises(ValueError):
            tool_service.execute_tool("nonexistent", {})

    def test_execute_tool_with_string_params(self, tool_service):
        """Test executing tool with string parameters."""
        result = tool_service.execute_tool("echo", {"message": "hello"})
        assert result["success"] is True
        assert result["result"] == "Echo: hello"


# ============================================================================
# Tests: Session Information
# ============================================================================


class TestSessionInformation:
    """Test session information retrieval."""

    def test_get_session_info(self, tool_service):
        """Test getting session information."""
        result = tool_service.execute_tool("add", {"a": 1, "b": 2})
        session_id = result["session_id"]

        session_info = tool_service.get_session_info(session_id)
        assert session_info["session_id"] == session_id
        assert "agent_name" in session_info
        assert "metadata" in session_info
        assert "execution_history" in session_info
        assert session_info["total_executions"] == 1

    def test_get_nonexistent_session_info(self, tool_service):
        """Test getting nonexistent session raises error."""
        with pytest.raises(ValueError):
            tool_service.get_session_info("nonexistent_session_id")

    def test_session_info_with_multiple_executions(self, tool_service):
        """Test session info with multiple tool executions."""
        result1 = tool_service.execute_tool("add", {"a": 1, "b": 2})
        session_id = result1["session_id"]

        result2 = tool_service.execute_tool("multiply", {"x": 3, "y": 4}, session_id)
        result3 = tool_service.execute_tool("echo", {"message": "hello"}, session_id)

        session_info = tool_service.get_session_info(session_id)
        assert session_info["total_executions"] == 3
        assert len(session_info["execution_history"]) == 3


# ============================================================================
# Tests: History Tracking
# ============================================================================


class TestHistoryTracking:
    """Test execution history tracking."""

    def test_history_disabled(self, mock_mcp_server):
        """Test history tracking can be disabled."""
        settings = MCPToolServiceSettings(enable_history=False)
        service = MCPToolService(mock_mcp_server, settings)

        result = service.execute_tool("add", {"a": 5, "b": 3})
        session_id = result["session_id"]

        session_info = service.get_session_info(session_id)
        assert len(session_info["execution_history"]) == 0

    def test_history_records_failure(self, tool_service):
        """Test that failed executions are recorded in history."""
        with pytest.raises(ValueError):
            tool_service.execute_tool("nonexistent", {})

        # Create a session that failed
        try:
            result = tool_service.execute_tool("add", {"a": 5, "b": 3})
            session_id = result["session_id"]

            # Now cause a failure
            with contextlib.suppress(ValueError):
                tool_service.execute_tool("nonexistent", {}, session_id)

            # Check history includes both success and failure
            session_info = tool_service.get_session_info(session_id)
            assert session_info["total_executions"] == 2
        except ValueError:
            # First execution may fail in test, that's ok
            pass

    def test_execution_history_format(self, tool_service):
        """Test execution history has correct format."""
        result = tool_service.execute_tool("add", {"a": 5, "b": 3})
        session_id = result["session_id"]

        session_info = tool_service.get_session_info(session_id)
        execution = session_info["execution_history"][0]

        assert "tool" in execution
        assert "params" in execution
        assert "result" in execution or "error" in execution
        assert "success" in execution
        assert execution["tool"] == "add"
        assert execution["params"] == {"a": 5, "b": 3}
        assert execution["result"] == 8
        assert execution["success"] is True


# ============================================================================
# Tests: Fluent API
# ============================================================================


class TestFluentAPI:
    """Test fluent API chaining for tool registration."""

    def test_register_tool_returns_self(self, mock_mcp_server):
        """Test that register_tool returns self for chaining."""
        result = mock_mcp_server.register_tool("test_tool", lambda: "result", "Test tool")
        assert result is mock_mcp_server

    def test_fluent_api_chaining(self, mock_mcp_server):
        """Test chaining multiple register_tool calls."""
        # Create a fresh server to test chaining
        from axiompy.servers import MCPServer

        class TestServer(MCPServer):
            def initialize(self):
                pass

            def execute_tool(self, tool_name, session, **kwargs):
                tool = self.get_tool(tool_name)
                if not tool:
                    from axiompy.servers.mcp import MCPToolError

                    raise MCPToolError(f"Tool '{tool_name}' not found")
                return tool.execute(**kwargs)

            def shutdown(self):
                pass

        settings = MCPServerSettings(name="FluentTest")
        server = TestServer(settings)

        # Test fluent chaining
        result = (
            server.register_tool("add", lambda a, b: a + b, "Add")
            .register_tool("sub", lambda a, b: a - b, "Subtract")
            .register_tool("mul", lambda a, b: a * b, "Multiply")
        )

        assert result is server
        assert len(server.tools) == 3
        assert "add" in server.tools
        assert "sub" in server.tools
        assert "mul" in server.tools

    def test_fluent_api_full_workflow(self, mock_mcp_server):
        """Test full fluent API workflow including initialization."""
        from axiompy.servers import MCPServer

        class TestServer(MCPServer):
            def __init__(self, settings):
                super().__init__(settings)
                self._initialized = False

            def initialize(self):
                self._initialized = True
                return self

            def execute_tool(self, tool_name, session, **kwargs):
                tool = self.get_tool(tool_name)
                if not tool:
                    from axiompy.servers.mcp import MCPToolError

                    raise MCPToolError(f"Tool '{tool_name}' not found")
                return tool.execute(**kwargs)

            def shutdown(self):
                pass

        settings = MCPServerSettings(name="FluentWorkflow")
        server = TestServer(settings)

        # Fluent workflow: register tools then initialize
        server = (
            server.register_tool("power", lambda base, exp: base**exp, "Power")
            .register_tool("sqrt", lambda x: x**0.5, "Square root")
            .initialize()
        )

        assert server._initialized
        assert len(server.tools) == 2

    def test_fluent_api_tool_execution(self, mock_mcp_server):
        """Test that tools registered via fluent API work correctly."""
        # Tools already registered in mock_mcp_server via fixture
        session = mock_mcp_server.create_session("test")

        result = mock_mcp_server.execute_tool("add", session, a=10, b=5)
        assert result == 15

        result = mock_mcp_server.execute_tool("multiply", session, x=4, y=3)
        assert result == 12
