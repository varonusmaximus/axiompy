# @!servers

"""
Web server abstractions for Flask and FastAPI, MCP server abstractions for AI agent frameworks,
and JSON-RPC 2.0 server implementations.

This module provides unified interfaces for:
- Web servers (Flask, FastAPI)
- MCP servers (OpenAI, Google ADK, Anthropic)
- JSON-RPC servers (HTTP, stdio)
"""

from axiompy.servers.fastapi_web import (
    raise_fastapi_http_exception,
    register_fastapi_http_response_handler,
)
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
from axiompy.servers.mcp import (
    MCPServer,
    MCPServerError,
    MCPServerFactory,
    MCPServerSettings,
    MCPServerType,
    MCPSession,
    MCPSessionError,
    MCPTool,
    MCPToolError,
)
from axiompy.servers.mcp_service import (
    MCPToolService,
    MCPToolServiceSettings,
)
from axiompy.servers.server import (
    RouteHandler,
    Server,
    ServerError,
    ServerFactory,
    ServerSettings,
    ServerType,
)

__all__ = [
    # Web Servers
    "Server",
    "ServerSettings",
    "ServerType",
    "ServerFactory",
    "ServerError",
    "RouteHandler",
    "raise_fastapi_http_exception",
    "register_fastapi_http_response_handler",
    # MCP Servers
    "MCPServer",
    "MCPServerSettings",
    "MCPServerType",
    "MCPServerFactory",
    "MCPServerError",
    "MCPSession",
    "MCPTool",
    "MCPToolError",
    "MCPSessionError",
    # MCP Service (HTTP layer)
    "MCPToolService",
    "MCPToolServiceSettings",
    # JSON-RPC Servers
    "JSONRPCServer",
    "JSONRPCSettings",
    "JSONRPCTransport",
    "JSONRPCServerFactory",
    "JSONRPCServerError",
    "JSONRPCError",
    "JSONRPCErrorCode",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "HTTPJSONRPCServer",
    "StdioJSONRPCServer",
    "MockJSONRPCServer",
]
