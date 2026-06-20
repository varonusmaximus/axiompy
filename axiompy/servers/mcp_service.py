# @!mcp

"""
MCP Service Layer - Business logic for exposing MCP servers via HTTP.

Wraps MCPServer functionality with session management and HTTP-specific concerns.
Designed to be injected into web routes for framework-agnostic HTTP access to MCP tools.

Key Components:
    - MCPToolService: High-level service for MCP tool operations
    - Session tracking for HTTP clients
    - Execution history tracking
    - Error handling and validation
    - And other things to come...

Architecture:
    HTTP Route Handler
        ↓ (dependency injection)
    MCPToolService
        ↓
    MCPServer
        ↓
    Registered Tools

Features:
    - Clean separation of concerns (service layer, not exposer)
    - Dependency injection friendly
    - Session persistence across requests
    - Execution history tracking
    - Comprehensive validation
    - Framework-agnostic (works with Flask, FastAPI, etc.)

Usage Example:
    >>> from axiompy.servers import MCPServerFactory, MCPServerType, MCPServerSettings
    >>> from axiompy.servers.mcp_service import MCPToolService, MCPToolServiceSettings
    >>>
    >>> # Create MCP server
    >>> mcp_settings = MCPServerSettings(name="MyTools")
    >>> mcp_server = MCPServerFactory.create(MCPServerType.OPENAI, mcp_settings)
    >>> mcp_server.register_tool("add", lambda a, b: a + b, "Add two numbers")
    >>> mcp_server.initialize()
    >>>
    >>> # Create service (wraps MCP server)
    >>> service_settings = MCPToolServiceSettings()
    >>> service = MCPToolService(mcp_server, service_settings)
    >>>
    >>> # Use in route handlers
    >>> def execute_tool_route(tool_name: str, params: dict):
    >>>     return service.execute_tool(tool_name, params)

For comprehensive examples, see:
    - examples/servers/mcp_service_examples.py
"""

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from axiompy.decorators import LogExecutionTime
from axiompy.loggers import LoggerFactory
from axiompy.servers.mcp import MCPServer, MCPSession, MCPToolError
from axiompy.validators import (
    ValidationError,
    ensure_in_range,
    ensure_instance_of,
    ensure_not_none,
)

logger = LoggerFactory.create_logger(__name__)


@dataclass
class MCPToolServiceSettings:
    """
    Configuration for MCPToolService.

    Attributes:
        enable_history: Track tool execution history (default: True)
        max_session_timeout: Session timeout in seconds (default: 3600)
    """

    enable_history: bool = True
    max_session_timeout: int = 3600

    def __post_init__(self):
        """Validate settings."""
        ensure_in_range(
            self.max_session_timeout,
            1,
            86400,
            f"max_session_timeout {self.max_session_timeout} must be between 1 and 86400",
        )
        logger.debug("MCPToolServiceSettings validated successfully")


class MCPToolService:
    """
    Service layer for exposing MCP tools via HTTP.

    Wraps MCPServer with additional session management and HTTP-specific concerns.
    Designed for dependency injection into web route handlers.

    Example with FastAPI:
        >>> service = MCPToolService(mcp_server, settings)
        >>>
        >>> @app.post("/tools/{tool_name}/execute")
        >>> async def execute(tool_name: str, request: dict):
        ...     return service.execute_tool(tool_name, request["params"])

    Example with Flask:
        >>> service = MCPToolService(mcp_server, settings)
        >>>
        >>> @app.route("/tools/<tool_name>/execute", methods=["POST"])
        >>> def execute(tool_name):
        ...     data = request.get_json()
        ...     return service.execute_tool(tool_name, data.get("params", {}))
    """

    def __init__(self, mcp_server: MCPServer, settings: MCPToolServiceSettings):
        """
        Initialize MCPToolService.

        Args:
            mcp_server: MCPServer instance providing tools
            settings: Service configuration

        Raises:
            ValidationError: If arguments are invalid or the server is not initialized
        """
        ensure_not_none(mcp_server, "mcp_server cannot be None")
        ensure_instance_of(mcp_server, MCPServer, "mcp_server must be an MCPServer instance")
        ensure_not_none(settings, "settings cannot be None")
        ensure_instance_of(
            settings, MCPToolServiceSettings, "settings must be MCPToolServiceSettings"
        )
        if hasattr(mcp_server, "_initialized") and not mcp_server._initialized:
            raise ValidationError("mcp_server must be initialized before creating MCPToolService")

        self.mcp_server = mcp_server
        self.settings = settings
        self.http_sessions: Dict[str, MCPSession] = {}
        self.execution_history: Dict[str, List[Dict[str, Any]]] = {}
        logger.info(f"MCPToolService initialized for server: {mcp_server.settings.name}")

    # ========================================================================
    # Session Management
    # ========================================================================

    @LogExecutionTime(logger, message_template="create_session completed in {elapsed:.4f}s")
    def create_session(self, client_id: Optional[str] = None) -> str:
        """
        Create a new HTTP session.

        Args:
            client_id: Optional identifier for the client

        Returns:
            Session ID string
        """
        session_id = str(uuid.uuid4())
        session = self.mcp_server.create_session(
            agent_name=client_id or "http_client",
            metadata={"http_session": True},
        )
        self.http_sessions[session_id] = session
        if session_id not in self.execution_history:
            self.execution_history[session_id] = []
        logger.debug(f"Created HTTP session: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[MCPSession]:
        """Get an existing HTTP session."""
        return self.http_sessions.get(session_id)

    def get_or_create_session(self, session_id: Optional[str] = None) -> Tuple[str, MCPSession]:
        """Get existing session or create new one."""
        if session_id and session_id in self.http_sessions:
            return session_id, self.http_sessions[session_id]
        new_session_id = self.create_session()
        return new_session_id, self.http_sessions[new_session_id]

    def close_session(self, session_id: str) -> None:
        """Close a session."""
        if session_id in self.http_sessions:
            session = self.http_sessions[session_id]
            self.mcp_server.close_session(session.session_id)
            del self.http_sessions[session_id]
            logger.debug(f"Closed HTTP session: {session_id}")

    # ========================================================================
    # Tool Information
    # ========================================================================

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        return {
            "name": self.mcp_server.settings.name,
            "version": self.mcp_server.settings.version,
            "description": self.mcp_server.settings.description,
            "tools_count": len(self.mcp_server.tools),
            "active_sessions": len(self.http_sessions),
        }

    def list_tools(self) -> Dict[str, Any]:
        """List all available tools with metadata."""
        tools = []
        for tool_name in self.mcp_server.tools:
            tool_info = self.get_tool_info(tool_name)
            if tool_info:
                tools.append(tool_info)

        return {
            "tools": tools,
            "total": len(tools),
            "server": self.mcp_server.settings.name,
        }

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tool."""
        tool = self.mcp_server.get_tool(tool_name)
        if not tool:
            return None

        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
            "return_type": tool.return_type,
            "tags": tool.tags,
        }

    # ========================================================================
    # Tool Execution
    # ========================================================================

    def execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a tool via HTTP request.

        Args:
            tool_name: Name of the tool to execute
            params: Tool parameters
            session_id: Optional existing session ID

        Returns:
            Dict with execution result and session info

        Raises:
            ValueError: If tool not found or execution fails
        """
        try:
            session_id, session = self.get_or_create_session(session_id)

            result = self.mcp_server.execute_tool(tool_name, session, **params)

            # Record execution in history
            if self.settings.enable_history:
                self.execution_history[session_id].append(
                    {
                        "tool": tool_name,
                        "params": params,
                        "result": result,
                        "success": True,
                    }
                )

            logger.debug(f"Tool '{tool_name}' executed successfully via HTTP")

            return {"result": result, "session_id": session_id, "success": True}

        except MCPToolError as e:
            error_msg = str(e)
            if self.settings.enable_history:
                self.execution_history[session_id].append(
                    {
                        "tool": tool_name,
                        "params": params,
                        "error": error_msg,
                        "success": False,
                    }
                )
            raise ValueError(f"Tool execution failed: {error_msg}")
        except Exception as e:
            error_msg = str(e)
            if self.settings.enable_history and session_id in self.execution_history:
                self.execution_history[session_id].append(
                    {
                        "tool": tool_name,
                        "params": params,
                        "error": error_msg,
                        "success": False,
                    }
                )
            raise ValueError(f"Unexpected error: {error_msg}")

    # ========================================================================
    # Session Information
    # ========================================================================

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about an HTTP session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found")

        history = self.execution_history.get(session_id, []) if self.settings.enable_history else []

        return {
            "session_id": session_id,
            "agent_name": session.agent_name,
            "metadata": session.metadata,
            "execution_history": history,
            "total_executions": len(history),
        }

    # ========================================================================
    # Health Check
    # ========================================================================

    def health_check(self) -> Dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "server_name": self.mcp_server.settings.name,
            "tools_count": len(self.mcp_server.tools),
            "active_sessions": len(self.http_sessions),
        }
