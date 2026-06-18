# @!documentation

#!/usr/bin/env python3
"""
JSON-RPC 2.0 Server Examples

This file demonstrates how to use AxiomPy's JSON-RPC server to expose
MCP tools via JSON-RPC protocol. JSON-RPC enables integration with
Claude Desktop, Cursor, and other MCP-compatible clients.

Examples:
    1. Basic JSON-RPC server with MCP tools
    2. Custom method registration
    3. HTTP transport (FastAPI)
    4. Stdio transport (for Claude Desktop)
    5. Mock server for testing
    6. Python client example

Run examples:
    python examples/servers/jsonrpc_examples.py

For HTTP server:
    python examples/servers/jsonrpc_examples.py --http

For stdio server (Claude Desktop integration):
    python examples/servers/jsonrpc_examples.py --stdio
"""

import argparse
import json
import sys
from typing import Any, Dict

# =============================================================================
# Example 1: Basic JSON-RPC Server with MCP Tools
# =============================================================================


def example_basic_jsonrpc_server():
    """
    Create a JSON-RPC server that wraps MCP tools.

    This is the most common use case: you have MCP tools and want to
    expose them via JSON-RPC for client integration.
    """
    print("\n" + "=" * 60)
    print("Example 1: Basic JSON-RPC Server with MCP Tools")
    print("=" * 60)

    from axiompy.servers import (
        JSONRPCServerFactory,
        JSONRPCSettings,
        MCPServerSettings,
    )
    from axiompy.servers.mcp import MCPTool

    # Create a simple mock MCP server (avoiding SDK dependencies)
    class SimpleMCPServer:
        def __init__(self, settings):
            self.settings = settings
            self.tools: Dict[str, MCPTool] = {}

        def register_tool(self, name, func, description):
            self.tools[name] = MCPTool(name=name, func=func, description=description)
            return self

        def initialize(self):
            pass

        def create_session(self, client_id):
            class Session:
                id = f"session-{client_id}"

            return Session()

        def execute_tool(self, tool_name, session, **kwargs):
            return self.tools[tool_name].func(**kwargs)

    # Create MCP server with tools
    mcp = SimpleMCPServer(MCPServerSettings(name="MathTools"))
    mcp.register_tool("add", lambda a, b: a + b, "Add two numbers")
    mcp.register_tool("multiply", lambda x, y: x * y, "Multiply two numbers")
    mcp.register_tool("greet", lambda name: f"Hello, {name}!", "Greet someone")
    mcp.initialize()

    # Create JSON-RPC server (mock for demo)
    settings = JSONRPCSettings(name="demo-server", port=8000)
    server = JSONRPCServerFactory.create_mock(settings, mcp_server=mcp)

    # Test requests
    print("\n--- Testing JSON-RPC Requests ---\n")

    # Initialize
    request = json.dumps({"jsonrpc": "2.0", "method": "initialize", "id": 1})
    response = server.handle_request(request)
    print("Request:  initialize")
    print(f"Response: {json.loads(response)['result']['serverInfo']}\n")

    # List tools
    request = json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 2})
    response = server.handle_request(request)
    tools = json.loads(response)["result"]["tools"]
    print("Request:  tools/list")
    print(f"Response: {[t['name'] for t in tools]}\n")

    # Call add tool
    request = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "add", "arguments": {"a": 5, "b": 3}},
            "id": 3,
        }
    )
    response = server.handle_request(request)
    result = json.loads(response)["result"]["content"][0]["text"]
    print("Request:  tools/call(add, a=5, b=3)")
    print(f"Response: {result}\n")

    # Call greet tool
    request = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "greet", "arguments": {"name": "World"}},
            "id": 4,
        }
    )
    response = server.handle_request(request)
    result = json.loads(response)["result"]["content"][0]["text"]
    print("Request:  tools/call(greet, name='World')")
    print(f"Response: {result}")


# =============================================================================
# Example 2: Custom Method Registration
# =============================================================================


def example_custom_methods():
    """
    Register custom JSON-RPC methods without MCP tools.

    Useful for creating JSON-RPC APIs that don't need MCP protocol.
    """
    print("\n" + "=" * 60)
    print("Example 2: Custom Method Registration")
    print("=" * 60)

    from axiompy.servers import JSONRPCServerFactory, JSONRPCSettings

    # Create server without MCP
    settings = JSONRPCSettings(name="custom-server")
    server = JSONRPCServerFactory.create_mock(settings)

    # Register custom methods with chaining
    (
        server.register_method("echo", lambda p: p.get("message", ""))
        .register_method("sum", lambda p: sum(p.get("numbers", [])))
        .register_method("reverse", lambda p: p.get("text", "")[::-1])
        .register_method(
            "info",
            lambda p: {
                "server": "custom-server",
                "version": "1.0.0",
                "methods": ["echo", "sum", "reverse", "info"],
            },
        )
    )

    print("\n--- Testing Custom Methods ---\n")

    # Echo
    request = json.dumps(
        {"jsonrpc": "2.0", "method": "echo", "params": {"message": "Hello, JSON-RPC!"}, "id": 1}
    )
    response = server.handle_request(request)
    print(f"echo('Hello, JSON-RPC!') = {json.loads(response)['result']}")

    # Sum
    request = json.dumps(
        {"jsonrpc": "2.0", "method": "sum", "params": {"numbers": [1, 2, 3, 4, 5]}, "id": 2}
    )
    response = server.handle_request(request)
    print(f"sum([1,2,3,4,5]) = {json.loads(response)['result']}")

    # Reverse
    request = json.dumps(
        {"jsonrpc": "2.0", "method": "reverse", "params": {"text": "JSON-RPC"}, "id": 3}
    )
    response = server.handle_request(request)
    print(f"reverse('JSON-RPC') = {json.loads(response)['result']}")

    # Info
    request = json.dumps({"jsonrpc": "2.0", "method": "info", "id": 4})
    response = server.handle_request(request)
    print(f"info() = {json.loads(response)['result']}")


# =============================================================================
# Example 3: Batch Requests
# =============================================================================


def example_batch_requests():
    """
    Demonstrate JSON-RPC batch requests.

    Batch requests allow multiple method calls in a single HTTP request,
    improving efficiency for clients that need multiple operations.
    """
    print("\n" + "=" * 60)
    print("Example 3: Batch Requests")
    print("=" * 60)

    from axiompy.servers import JSONRPCServerFactory, JSONRPCSettings

    settings = JSONRPCSettings(name="batch-server")
    server = JSONRPCServerFactory.create_mock(settings)

    server.register_method("double", lambda p: p.get("n", 0) * 2)
    server.register_method("square", lambda p: p.get("n", 0) ** 2)

    print("\n--- Batch Request ---\n")

    # Batch request: multiple operations in one call
    batch_request = json.dumps(
        [
            {"jsonrpc": "2.0", "method": "double", "params": {"n": 5}, "id": 1},
            {"jsonrpc": "2.0", "method": "square", "params": {"n": 5}, "id": 2},
            {"jsonrpc": "2.0", "method": "double", "params": {"n": 10}, "id": 3},
            {"jsonrpc": "2.0", "method": "square", "params": {"n": 10}, "id": 4},
        ]
    )

    print("Request (batch of 4):")
    print("  - double(5)")
    print("  - square(5)")
    print("  - double(10)")
    print("  - square(10)")

    response = server.handle_request(batch_request)
    results = json.loads(response)

    print("\nResponse:")
    for r in results:
        print(f"  - id={r['id']}: {r['result']}")


# =============================================================================
# Example 4: Notifications (No Response Expected)
# =============================================================================


def example_notifications():
    """
    Demonstrate JSON-RPC notifications.

    Notifications are requests without an 'id' field. The server
    processes them but doesn't send a response.
    """
    print("\n" + "=" * 60)
    print("Example 4: Notifications")
    print("=" * 60)

    from axiompy.servers import JSONRPCServerFactory, JSONRPCSettings

    settings = JSONRPCSettings(name="notification-server")
    server = JSONRPCServerFactory.create_mock(settings)

    # Track logged messages
    logs = []

    def log_handler(params):
        message = params.get("message", "")
        logs.append(message)
        print(f"  [LOG] {message}")
        return None

    server.register_method("log", log_handler)
    server.register_method("get_logs", lambda p: logs)

    print("\n--- Sending Notifications ---\n")

    # Notifications (no 'id' field)
    notifications = [
        {"jsonrpc": "2.0", "method": "log", "params": {"message": "User logged in"}},
        {"jsonrpc": "2.0", "method": "log", "params": {"message": "Page viewed: /home"}},
        {"jsonrpc": "2.0", "method": "log", "params": {"message": "Button clicked: submit"}},
    ]

    for notif in notifications:
        response = server.handle_request(json.dumps(notif))
        assert response is None, "Notifications should not return a response"

    print("\n--- Retrieving Logs ---\n")

    # Regular request to get logs
    request = json.dumps({"jsonrpc": "2.0", "method": "get_logs", "id": 1})
    response = server.handle_request(request)
    print(f"All logs: {json.loads(response)['result']}")


# =============================================================================
# Example 5: Error Handling
# =============================================================================


def example_error_handling():
    """
    Demonstrate JSON-RPC error handling.

    Shows standard error codes and custom errors.
    """
    print("\n" + "=" * 60)
    print("Example 5: Error Handling")
    print("=" * 60)

    from axiompy.servers import JSONRPCServerFactory, JSONRPCSettings
    from axiompy.servers.jsonrpc import JSONRPCError, JSONRPCErrorCode

    settings = JSONRPCSettings(name="error-server")
    server = JSONRPCServerFactory.create_mock(settings)

    def divide(params):
        a = params.get("a", 0)
        b = params.get("b", 0)
        if b == 0:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS, "Division by zero", data={"a": a, "b": b}
            )
        return a / b

    server.register_method("divide", divide)

    print("\n--- Error Examples ---\n")

    # Method not found
    request = json.dumps({"jsonrpc": "2.0", "method": "unknown", "id": 1})
    response = server.handle_request(request)
    error = json.loads(response)["error"]
    print("Method not found:")
    print(f"  Code: {error['code']}")
    print(f"  Message: {error['message']}\n")

    # Invalid params (division by zero)
    request = json.dumps(
        {"jsonrpc": "2.0", "method": "divide", "params": {"a": 10, "b": 0}, "id": 2}
    )
    response = server.handle_request(request)
    error = json.loads(response)["error"]
    print("Division by zero:")
    print(f"  Code: {error['code']}")
    print(f"  Message: {error['message']}")
    print(f"  Data: {error.get('data')}\n")

    # Parse error
    response = server.handle_request("not valid json")
    error = json.loads(response)["error"]
    print("Parse error:")
    print(f"  Code: {error['code']}")
    print(f"  Message: {error['message'][:50]}...")


# =============================================================================
# Example 6: Python Client
# =============================================================================


def example_python_client():
    """
    Demonstrate a simple Python JSON-RPC client.

    This client can be used to call any JSON-RPC server.
    """
    print("\n" + "=" * 60)
    print("Example 6: Python JSON-RPC Client")
    print("=" * 60)

    from axiompy.servers import JSONRPCServerFactory, JSONRPCSettings

    # Simple JSON-RPC client class
    class JSONRPCClient:
        """Simple JSON-RPC 2.0 client."""

        def __init__(self, handler):
            """
            Initialize client.

            In real usage, handler would be an HTTP client.
            Here we use a mock handler for demonstration.
            """
            self.handler = handler
            self.request_id = 0

        def call(self, method: str, params: Dict[str, Any] = None) -> Any:
            """Make a JSON-RPC call and return result."""
            self.request_id += 1
            request = json.dumps(
                {"jsonrpc": "2.0", "id": self.request_id, "method": method, "params": params or {}}
            )
            response = self.handler(request)
            parsed = json.loads(response)
            if "error" in parsed:
                raise Exception(f"RPC Error: {parsed['error']['message']}")
            return parsed.get("result")

        def notify(self, method: str, params: Dict[str, Any] = None) -> None:
            """Send a notification (no response expected)."""
            request = json.dumps({"jsonrpc": "2.0", "method": method, "params": params or {}})
            self.handler(request)

        def batch(self, calls: list) -> list:
            """Make batch request."""
            requests = []
            for method, params in calls:
                self.request_id += 1
                requests.append(
                    {
                        "jsonrpc": "2.0",
                        "id": self.request_id,
                        "method": method,
                        "params": params or {},
                    }
                )
            response = self.handler(json.dumps(requests))
            return [r.get("result") for r in json.loads(response)]

    # Create server
    settings = JSONRPCSettings(name="client-demo")
    server = JSONRPCServerFactory.create_mock(settings)
    server.register_method("add", lambda p: p["a"] + p["b"])
    server.register_method("multiply", lambda p: p["x"] * p["y"])

    # Create client using server's handle_request as handler
    client = JSONRPCClient(server.handle_request)

    print("\n--- Client Usage ---\n")

    # Single calls
    result = client.call("add", {"a": 10, "b": 20})
    print(f"client.call('add', a=10, b=20) = {result}")

    result = client.call("multiply", {"x": 5, "y": 7})
    print(f"client.call('multiply', x=5, y=7) = {result}")

    # Batch call
    results = client.batch(
        [
            ("add", {"a": 1, "b": 2}),
            ("add", {"a": 3, "b": 4}),
            ("multiply", {"x": 2, "y": 3}),
        ]
    )
    print(f"client.batch([add(1,2), add(3,4), multiply(2,3)]) = {results}")


# =============================================================================
# HTTP Server (for production use)
# =============================================================================


def run_http_server():
    """
    Run JSON-RPC server over HTTP using FastAPI.

    This is the production configuration for web-accessible JSON-RPC APIs.
    """
    print("\n" + "=" * 60)
    print("Starting HTTP JSON-RPC Server")
    print("=" * 60)
    print("\nEndpoints:")
    print("  POST /jsonrpc - JSON-RPC endpoint")
    print("  GET  /health  - Health check")
    print("\nPress Ctrl+C to stop\n")

    from axiompy.servers import (
        JSONRPCServerFactory,
        JSONRPCSettings,
        JSONRPCTransport,
        MCPServerSettings,
    )
    from axiompy.servers.mcp import MCPTool

    # Create mock MCP server
    class SimpleMCPServer:
        def __init__(self, settings):
            self.settings = settings
            self.tools = {}

        def register_tool(self, name, func, description):
            self.tools[name] = MCPTool(name=name, func=func, description=description)
            return self

        def initialize(self):
            pass

        def create_session(self, client_id):
            class Session:
                id = f"session-{client_id}"

            return Session()

        def execute_tool(self, tool_name, session, **kwargs):
            return self.tools[tool_name].func(**kwargs)

    mcp = SimpleMCPServer(MCPServerSettings(name="HTTPTools"))
    mcp.register_tool("add", lambda a, b: a + b, "Add two numbers")
    mcp.register_tool("multiply", lambda x, y: x * y, "Multiply two numbers")
    mcp.register_tool("greet", lambda name: f"Hello, {name}!", "Greet someone")

    settings = JSONRPCSettings(host="127.0.0.1", port=8000, name="http-jsonrpc")
    server = JSONRPCServerFactory.create(JSONRPCTransport.HTTP, settings, mcp_server=mcp)
    server.run()


# =============================================================================
# Stdio Server (for Claude Desktop / Cursor)
# =============================================================================


def run_stdio_server():
    """
    Run JSON-RPC server over stdio.

    This is used for MCP client integration with Claude Desktop, Cursor, etc.
    The server reads JSON-RPC requests from stdin and writes responses to stdout.
    """
    from axiompy.servers import (
        JSONRPCServerFactory,
        JSONRPCSettings,
        JSONRPCTransport,
        MCPServerSettings,
    )
    from axiompy.servers.mcp import MCPTool

    # Create mock MCP server
    class SimpleMCPServer:
        def __init__(self, settings):
            self.settings = settings
            self.tools = {}

        def register_tool(self, name, func, description):
            self.tools[name] = MCPTool(name=name, func=func, description=description)
            return self

        def initialize(self):
            pass

        def create_session(self, client_id):
            class Session:
                id = f"session-{client_id}"

            return Session()

        def execute_tool(self, tool_name, session, **kwargs):
            return self.tools[tool_name].func(**kwargs)

    mcp = SimpleMCPServer(MCPServerSettings(name="StdioTools"))
    mcp.register_tool("add", lambda a, b: a + b, "Add two numbers")
    mcp.register_tool("multiply", lambda x, y: x * y, "Multiply two numbers")
    mcp.register_tool("greet", lambda name: f"Hello, {name}!", "Greet someone")

    settings = JSONRPCSettings(name="stdio-jsonrpc")
    server = JSONRPCServerFactory.create(JSONRPCTransport.STDIO, settings, mcp_server=mcp)
    server.run()


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="JSON-RPC Server Examples")
    parser.add_argument("--http", action="store_true", help="Run HTTP server")
    parser.add_argument("--stdio", action="store_true", help="Run stdio server")
    args = parser.parse_args()

    if args.http:
        run_http_server()
    elif args.stdio:
        run_stdio_server()
    else:
        # Run all examples
        example_basic_jsonrpc_server()
        example_custom_methods()
        example_batch_requests()
        example_notifications()
        example_error_handling()
        example_python_client()

        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)
        print("\nTo run HTTP server: python jsonrpc_examples.py --http")
        print("To run stdio server: python jsonrpc_examples.py --stdio")


if __name__ == "__main__":
    main()
