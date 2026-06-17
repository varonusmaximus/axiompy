# @!code-style

"""
JSON-RPC 2.0 Server implementation with multiple transport support.

Provides a standards-compliant JSON-RPC server that can:
    - Wrap existing MCPServer tools
    - Run over HTTP or stdio
    - Handle batch requests
    - Support MCP protocol methods

Key Benefits:
    - JSON-RPC 2.0 compliant
    - Compatible with Claude Desktop, Cursor, and MCP clients
    - Batch request support for efficiency
    - Multiple transport options (HTTP, stdio)
    - Easy integration with existing MCPServer tools

Architecture:
    - JSONRPCServer: Abstract base class handling JSON-RPC 2.0 protocol
    - HTTPJSONRPCServer: HTTP transport using FastAPI
    - StdioJSONRPCServer: Stdio transport for MCP client integration
    - JSONRPCServerFactory: Factory for creating server instances

Quick Example:
    >>> from axiompy.servers import JSONRPCServerFactory, JSONRPCTransport, JSONRPCSettings
    >>> from axiompy.servers import MCPServerFactory, MCPServerType, MCPServerSettings
    >>>
    >>> # Create MCP server with tools
    >>> mcp = MCPServerFactory.create(MCPServerType.OPENAI, MCPServerSettings(name="Tools"))
    >>> mcp.register_tool("add", lambda a, b: a + b, "Add two numbers")
    >>> mcp.initialize()
    >>>
    >>> # Wrap with JSON-RPC server
    >>> settings = JSONRPCSettings(port=8000)
    >>> server = JSONRPCServerFactory.create(JSONRPCTransport.HTTP, settings, mcp_server=mcp)
    >>> server.run()

For comprehensive examples, see:
    - examples/servers/jsonrpc_examples.py - Usage examples
    - tests/test_jsonrpc.py - Test patterns
"""

import json
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from axiompy.loggers import LoggerFactory
from axiompy.result import Err, Ok, Result
from axiompy.servers.mcp import MCPServer, MCPSession
from axiompy.validators import ensure_in_range

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
        -32001: Tool not found (MCP-specific)
        -32002: Tool execution error (MCP-specific)
    """

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    # Server errors: -32000 to -32099
    SERVER_ERROR = -32000
    TOOL_NOT_FOUND = -32001
    TOOL_EXECUTION_ERROR = -32002


# =============================================================================
# Transport Types
# =============================================================================


class JSONRPCTransport(Enum):
    """Supported JSON-RPC transport types."""

    HTTP = "http"
    STDIO = "stdio"


# =============================================================================
# Settings and Configuration
# =============================================================================


@dataclass
class JSONRPCSettings:
    """
    JSON-RPC server configuration.

    Attributes:
        host: Server host address (HTTP transport only, default: "127.0.0.1")
        port: Server port number (HTTP transport only, default: 8000)
        name: Server name for identification (default: "jsonrpc-server")
        version: Server version string (default: "1.0.0")
        extra_params: Additional transport-specific parameters
    """

    host: str = "127.0.0.1"
    port: int = 8000
    name: str = "jsonrpc-server"
    version: str = "1.0.0"
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate settings after initialization."""
        ensure_in_range(self.port, 0, 65535, f"port {self.port} must be between 0 and 65535")
        if not self.name:
            raise ValueError("Server name cannot be empty")
        logger.debug("JSONRPCSettings validated successfully")


# =============================================================================
# Request/Response Data Classes
# =============================================================================


@dataclass
class JSONRPCRequest:
    """
    Parsed JSON-RPC 2.0 request.

    Attributes:
        jsonrpc: Protocol version (must be "2.0")
        method: Method name to invoke
        params: Optional parameters (dict or list)
        id: Request identifier (None for notifications)
    """

    jsonrpc: str
    method: str
    params: Optional[Union[Dict[str, Any], List[Any]]] = None
    id: Optional[Union[str, int]] = None

    @property
    def is_notification(self) -> bool:
        """Check if this is a notification (no response expected)."""
        return self.id is None


@dataclass
class JSONRPCResponse:
    """
    JSON-RPC 2.0 response.

    Attributes:
        jsonrpc: Protocol version (always "2.0")
        id: Request identifier (matches request)
        result: Success result (mutually exclusive with error)
        error: Error object (mutually exclusive with result)
    """

    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary for JSON serialization."""
        response: Dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            response["error"] = self.error
        else:
            response["result"] = self.result
        return response


# =============================================================================
# Exceptions
# =============================================================================


class JSONRPCError(Exception):
    """
    JSON-RPC error with code, message, and optional data.

    Used internally and can be raised by method handlers to return
    structured errors to clients.
    """

    def __init__(self, code: JSONRPCErrorCode, message: str, data: Optional[Any] = None):
        """
        Initialize JSON-RPC error.

        Args:
            code: Error code from JSONRPCErrorCode enum
            message: Human-readable error message
            data: Optional additional error data
        """
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        error: Dict[str, Any] = {"code": self.code.value, "message": self.message}
        if self.data is not None:
            error["data"] = self.data
        return error


class JSONRPCServerError(Exception):
    """Base exception for JSON-RPC server errors."""

    pass


# =============================================================================
# Abstract Base Server
# =============================================================================


class JSONRPCServer(ABC):
    """
    Abstract base class for JSON-RPC 2.0 servers.

    Handles protocol parsing, method dispatch, and response formatting.
    Subclasses implement transport-specific communication (HTTP, stdio, etc.).

    Features:
        - Full JSON-RPC 2.0 compliance
        - Single and batch request support
        - Notification support (requests without id)
        - MCP protocol method registration
        - Custom method registration
        - Railway-Oriented Programming for error handling

    Example Usage:
        >>> class MyService:
        ...     def __init__(self, server: JSONRPCServer):
        ...         self.server = server
        ...         server.register_method("greet", self.greet)
        ...
        ...     def greet(self, params: dict) -> str:
        ...         return f"Hello, {params.get('name', 'World')}!"
    """

    def __init__(self, settings: JSONRPCSettings, mcp_server: Optional[MCPServer] = None):
        """
        Initialize JSON-RPC server.

        Args:
            settings: Server configuration
            mcp_server: Optional MCPServer to wrap with JSON-RPC interface
        """
        self.settings = settings
        self.mcp_server = mcp_server
        self.methods: Dict[str, Callable] = {}
        self._session: Optional[MCPSession] = None

        # Register built-in MCP methods if mcp_server provided
        if mcp_server:
            self._register_mcp_methods()

        logger.info(f"JSONRPCServer '{settings.name}' initialized")

    def _register_mcp_methods(self) -> None:
        """Register standard MCP protocol methods."""
        self.register_method("initialize", self._handle_initialize)
        self.register_method("initialized", self._handle_initialized)
        self.register_method("tools/list", self._handle_tools_list)
        self.register_method("tools/call", self._handle_tools_call)
        self.register_method("ping", self._handle_ping)
        logger.debug("MCP protocol methods registered")

    def register_method(self, name: str, handler: Callable) -> "JSONRPCServer":
        """
        Register a method handler.

        Args:
            name: Method name (e.g., "tools/list", "my_method")
            handler: Callable that accepts params dict and returns result

        Returns:
            Self for method chaining

        Example:
            >>> server.register_method("echo", lambda p: p.get("message"))
            >>> server.register_method("add", lambda p: p["a"] + p["b"])
        """
        self.methods[name] = handler
        logger.debug(f"Registered method: {name}")
        return self

    # =========================================================================
    # MCP Protocol Handlers
    # =========================================================================

    def _handle_initialize(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Handle MCP initialize request."""
        if self.mcp_server:
            self._session = self.mcp_server.create_session("jsonrpc-client")

        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": self.settings.name, "version": self.settings.version},
            "capabilities": {"tools": {"listChanged": False}},
        }

    def _handle_initialized(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Handle MCP initialized notification."""
        logger.debug("Client initialized notification received")
        return {}

    def _handle_tools_list(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Handle tools/list request."""
        if not self.mcp_server:
            return {"tools": []}

        tools = []
        for name, tool in self.mcp_server.tools.items():
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": {"type": "object", "properties": tool.parameters},
                }
            )
        return {"tools": tools}

    def _handle_tools_call(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Handle tools/call request."""
        if not self.mcp_server:
            raise JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, "No MCP server configured")

        if params is None:
            raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing parameters")

        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing 'name' parameter")

        if tool_name not in self.mcp_server.tools:
            raise JSONRPCError(JSONRPCErrorCode.TOOL_NOT_FOUND, f"Tool '{tool_name}' not found")

        try:
            if not self._session:
                self._session = self.mcp_server.create_session("jsonrpc-client")
            result = self.mcp_server.execute_tool(tool_name, self._session, **arguments)
            return {"content": [{"type": "text", "text": str(result)}]}
        except Exception as e:
            raise JSONRPCError(
                JSONRPCErrorCode.TOOL_EXECUTION_ERROR,
                f"Tool execution failed: {str(e)}",
            )

    def _handle_ping(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Handle ping request."""
        return {}

    # =========================================================================
    # Request Parsing
    # =========================================================================

    def parse_request(
        self, data: str
    ) -> Result[Union[JSONRPCRequest, List[JSONRPCRequest]], JSONRPCError]:
        """
        Parse JSON-RPC request(s) from string.

        Args:
            data: JSON string containing request or batch of requests

        Returns:
            Result containing parsed request(s) or error
        """
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as e:
            return Err(JSONRPCError(JSONRPCErrorCode.PARSE_ERROR, f"Invalid JSON: {e}"))

        # Batch request (array)
        if isinstance(parsed, list):
            if not parsed:
                return Err(JSONRPCError(JSONRPCErrorCode.INVALID_REQUEST, "Empty batch"))
            requests = []
            for item in parsed:
                req_result = self._parse_single_request(item)
                if req_result.is_err():
                    return req_result
                requests.append(req_result.unwrap())
            return Ok(requests)

        # Single request
        return self._parse_single_request(parsed)

    def _parse_single_request(self, data: Any) -> Result[JSONRPCRequest, JSONRPCError]:
        """Parse a single JSON-RPC request object."""
        if not isinstance(data, dict):
            return Err(JSONRPCError(JSONRPCErrorCode.INVALID_REQUEST, "Request must be object"))

        if data.get("jsonrpc") != "2.0":
            return Err(JSONRPCError(JSONRPCErrorCode.INVALID_REQUEST, "Invalid jsonrpc version"))

        method = data.get("method")
        if not method or not isinstance(method, str):
            return Err(JSONRPCError(JSONRPCErrorCode.INVALID_REQUEST, "Invalid method"))

        return Ok(
            JSONRPCRequest(
                jsonrpc="2.0",
                method=method,
                params=data.get("params"),
                id=data.get("id"),
            )
        )

    # =========================================================================
    # Request Handling
    # =========================================================================

    def handle_request(self, data: str) -> Optional[str]:
        """
        Handle a JSON-RPC request and return response.

        Args:
            data: JSON string containing request

        Returns:
            JSON response string, or None for notifications
        """
        parse_result = self.parse_request(data)

        if parse_result.is_err():
            error = parse_result.get_error()
            response = JSONRPCResponse(error=error.to_dict())
            return json.dumps(response.to_dict())

        request = parse_result.unwrap()

        # Batch request
        if isinstance(request, list):
            responses = []
            for req in request:
                resp = self._execute_request(req)
                if resp:  # Skip notifications
                    responses.append(resp.to_dict())
            return json.dumps(responses) if responses else None

        # Single request
        response = self._execute_request(request)
        if response is None:  # Notification
            return None
        return json.dumps(response.to_dict())

    def _execute_request(self, request: JSONRPCRequest) -> Optional[JSONRPCResponse]:
        """Execute a single request and return response."""
        try:
            if request.method not in self.methods:
                if request.is_notification:
                    return None
                return JSONRPCResponse(
                    id=request.id,
                    error=JSONRPCError(
                        JSONRPCErrorCode.METHOD_NOT_FOUND,
                        f"Method '{request.method}' not found",
                    ).to_dict(),
                )

            handler = self.methods[request.method]
            result = handler(request.params)

            if request.is_notification:
                return None

            return JSONRPCResponse(id=request.id, result=result)

        except JSONRPCError as e:
            if request.is_notification:
                return None
            return JSONRPCResponse(id=request.id, error=e.to_dict())
        except Exception as e:
            logger.error(f"Internal error handling {request.method}: {e}")
            if request.is_notification:
                return None
            return JSONRPCResponse(
                id=request.id,
                error=JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, str(e)).to_dict(),
            )

    @abstractmethod
    def run(self) -> None:
        """Start the server. Implementation depends on transport."""
        pass


# =============================================================================
# HTTP Transport Implementation
# =============================================================================


class HTTPJSONRPCServer(JSONRPCServer):
    """
    JSON-RPC server over HTTP using FastAPI.

    Exposes a POST /jsonrpc endpoint for JSON-RPC requests
    and a GET /health endpoint for health checks.
    """

    def run(self) -> None:
        """Start HTTP server."""
        try:
            import uvicorn
            from fastapi import FastAPI, Request
            from fastapi.responses import JSONResponse
        except ImportError:
            raise JSONRPCServerError(
                "FastAPI required for HTTP transport: pip install fastapi uvicorn"
            )

        app = FastAPI(title=self.settings.name)

        @app.post("/jsonrpc")
        async def jsonrpc_endpoint(request: Request):
            body = await request.body()
            response = self.handle_request(body.decode())
            if response is None:
                return JSONResponse(content={}, status_code=204)
            return JSONResponse(content=json.loads(response))

        @app.get("/health")
        async def health():
            return {"status": "ok", "server": self.settings.name}

        logger.info(f"Starting HTTP JSON-RPC server on {self.settings.host}:{self.settings.port}")
        uvicorn.run(app, host=self.settings.host, port=self.settings.port)


# =============================================================================
# Stdio Transport Implementation
# =============================================================================


class StdioJSONRPCServer(JSONRPCServer):
    """
    JSON-RPC server over stdio.

    Reads JSON-RPC requests from stdin (one per line) and writes
    responses to stdout. Used for MCP client integration with
    Claude Desktop, Cursor, and similar tools.
    """

    def run(self) -> None:
        """Run stdio server (blocking)."""
        logger.info("Starting stdio JSON-RPC server")

        while True:
            try:
                # Read line from stdin
                line = sys.stdin.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                # Process request
                response = self.handle_request(line)

                # Write response to stdout
                if response:
                    sys.stdout.write(response + "\n")
                    sys.stdout.flush()

            except KeyboardInterrupt:
                logger.info("Stdio server interrupted")
                break
            except Exception as e:
                logger.error(f"Stdio error: {e}")
                error_response = JSONRPCResponse(
                    error=JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, str(e)).to_dict()
                )
                sys.stdout.write(json.dumps(error_response.to_dict()) + "\n")
                sys.stdout.flush()


# =============================================================================
# Mock Server for Testing
# =============================================================================


class MockJSONRPCServer(JSONRPCServer):
    """
    Mock JSON-RPC server for unit testing.

    Does not start any actual server; allows direct method invocation
    and request handling for testing purposes.
    """

    def __init__(self, settings: JSONRPCSettings, mcp_server: Optional[MCPServer] = None):
        super().__init__(settings, mcp_server)
        self.requests_received: List[str] = []
        self.responses_sent: List[str] = []

    def run(self) -> None:
        """Mock run does nothing."""
        logger.info("MockJSONRPCServer.run() called (no-op)")

    def handle_request(self, data: str) -> Optional[str]:
        """Track requests and responses for testing."""
        self.requests_received.append(data)
        response = super().handle_request(data)
        if response:
            self.responses_sent.append(response)
        return response


# =============================================================================
# Factory
# =============================================================================


class JSONRPCServerFactory:
    """
    Factory for creating JSON-RPC servers.

    Provides a unified interface for creating servers with different
    transport types while maintaining consistent configuration.

    Example:
        >>> settings = JSONRPCSettings(port=8000, name="MyServer")
        >>> server = JSONRPCServerFactory.create(
        ...     JSONRPCTransport.HTTP,
        ...     settings,
        ...     mcp_server=my_mcp_server
        ... )
        >>> server.run()
    """

    @staticmethod
    def create(
        transport: JSONRPCTransport,
        settings: JSONRPCSettings,
        mcp_server: Optional[MCPServer] = None,
    ) -> JSONRPCServer:
        """
        Create a JSON-RPC server instance.

        Args:
            transport: Transport type (HTTP, STDIO)
            settings: Server configuration
            mcp_server: Optional MCPServer to wrap with JSON-RPC interface

        Returns:
            Configured JSONRPCServer instance

        Raises:
            ValueError: If transport type is not supported
        """
        if transport == JSONRPCTransport.HTTP:
            logger.info("Creating JSONRPCServer with transport: http")
            return HTTPJSONRPCServer(settings, mcp_server)
        elif transport == JSONRPCTransport.STDIO:
            logger.info("Creating JSONRPCServer with transport: stdio")
            return StdioJSONRPCServer(settings, mcp_server)
        else:
            raise ValueError(f"Unsupported transport: {transport}")

    @staticmethod
    def create_mock(
        settings: Optional[JSONRPCSettings] = None,
        mcp_server: Optional[MCPServer] = None,
    ) -> MockJSONRPCServer:
        """
        Create a mock JSON-RPC server for testing.

        Args:
            settings: Optional server configuration (defaults provided)
            mcp_server: Optional MCPServer to wrap

        Returns:
            MockJSONRPCServer instance for testing
        """
        if settings is None:
            settings = JSONRPCSettings(name="mock-server")
        return MockJSONRPCServer(settings, mcp_server)
