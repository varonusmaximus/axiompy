# @!documentation

"""
Examples of exposing MCPServer via HTTP using Service Layer Pattern with ROP.

This demonstrates how to use MCPToolService with web route handlers to:
1. Create MCP tools programmatically
2. Expose them via REST API (Flask or FastAPI)
3. Allow external HTTP clients to discover and execute tools
4. Use Railway-Oriented Programming (ROP) for clean error handling
5. Use dependency injection to provide MCPToolService to route handlers

Architecture Pattern (following api_template best practices):
    HTTP Route Handler (ROP: Result type handling)
        ↓ (dependency injection)
    MCPToolService (business logic)
        ↓
    MCPServer (tool management)
        ↓
    Registered Tools

Railway-Oriented Programming Benefits:
    - Automatic error propagation with .map() and .then()
    - Clean composition of operations
    - Type-safe error handling
    - No try/except blocks needed
    - Consistent with axiompy patterns

Key Use Cases:
    - Build AI agent tools once, expose to multiple frameworks
    - REST API layer for external tool consumption
    - HTTP-accessible tool server for distributed systems
    - Microservice architecture with shared tool infrastructure
    - Clean separation of concerns (service layer, not exposer)
"""

import json
from typing import Any, Dict

from axiompy.result import Err, Ok, Result
from axiompy.servers import (
    MCPServerFactory,
    MCPServerSettings,
    MCPServerType,
    MCPToolService,
    MCPToolServiceSettings,
    ServerFactory,
    ServerSettings,
    ServerType,
)

# ============================================================================
# Example 1: FastAPI with MCPToolService
# ============================================================================


def fastapi_service_example():
    """Expose MCP tools via FastAPI using service layer pattern."""
    print("=" * 70)
    print("FastAPI with MCPToolService Example")
    print("=" * 70)

    # Step 1: Create MCP server and register tools
    print("\n1. Creating MCP server with tools...")
    mcp_settings = MCPServerSettings(
        name="MathTools",
        version="1.0.0",
        description="Mathematical tools exposed via HTTP",
    )
    mcp_server = MCPServerFactory.create(MCPServerType.OPENAI, mcp_settings)

    # Register tools
    def add(a: int, b: int) -> int:
        return a + b

    def multiply(x: float, y: float) -> float:
        return x * y

    def power(base: float, exp: float) -> float:
        return base**exp

    # Use fluent API for clean tool registration
    (
        mcp_server.register_tool(
            "add",
            add,
            "Add two numbers",
            parameters={"a": {"type": "int"}, "b": {"type": "int"}},
            return_type="int",
        )
        .register_tool(
            "multiply",
            multiply,
            "Multiply two numbers",
            parameters={"x": {"type": "float"}, "y": {"type": "float"}},
            return_type="float",
        )
        .register_tool(
            "power",
            power,
            "Raise base to exponent",
            parameters={"base": {"type": "float"}, "exp": {"type": "float"}},
            return_type="float",
        )
        .initialize()
    )
    print("   ✓ Registered tools: add, multiply, power")

    # Step 2: Create web server
    print("\n2. Creating FastAPI web server...")
    web_settings = ServerSettings(
        host="127.0.0.1",
        port=8000,
        debug=True,
    )
    web_server = ServerFactory.create(ServerType.FASTAPI, web_settings)
    app = web_server.get_app()
    print("   ✓ FastAPI server created")

    # Step 3: Create MCPToolService (wraps MCP server)
    print("\n3. Creating MCPToolService...")
    service_settings = MCPToolServiceSettings(
        enable_history=True,
        max_session_timeout=3600,
    )
    service = MCPToolService(mcp_server, service_settings)
    print("   ✓ MCPToolService created")

    # Step 4: Add routes using Railway-Oriented Programming (ROP)
    print("\n4. Setting up routes with ROP pattern...")

    class ToolRoutes:
        """Route handlers using MCPToolService via DI with ROP for error handling."""

        def __init__(self, service: MCPToolService):
            self.service = service

        # ====================================================================
        # RAILWAY-ORIENTED PROGRAMMING (ROP) HANDLERS
        # ====================================================================
        # Each handler returns Result[T, E] which automatically propagates
        # errors through .map() and .then() chains without try/except

        async def health_check(self) -> Result[Dict[str, Any], str]:
            """Health check using ROP."""
            return Ok(self.service.health_check())

        async def list_tools(self) -> Result[Dict[str, Any], str]:
            """List tools using ROP."""
            return Ok(self.service.list_tools())

        async def get_tool_info(self, tool_name: str) -> Result[Dict[str, Any], str]:
            """Get tool info using ROP with validation."""
            # Railway track: if get_tool_info returns None, we switch to error track
            info = self.service.get_tool_info(tool_name)

            if info is None:
                return Err(f"Tool '{tool_name}' not found")

            return Ok(info)

        async def execute_tool(
            self, tool_name: str, request_data: dict
        ) -> Result[Dict[str, Any], str]:
            """Execute tool using ROP with error handling."""
            try:
                params = request_data.get("params", {})
                session_id = request_data.get("session_id")

                # Service call wrapped in Result
                result = self.service.execute_tool(tool_name, params, session_id)
                return Ok(result)
            except ValueError as e:
                # Automatic error track
                return Err(str(e))
            except Exception as e:
                return Err(f"Unexpected error: {str(e)}")

        async def get_session_info(self, session_id: str) -> Result[Dict[str, Any], str]:
            """Get session info using ROP."""
            try:
                return Ok(self.service.get_session_info(session_id))
            except ValueError as e:
                return Err(str(e))

    # Create route handler instance (DI happens here)
    tool_routes = ToolRoutes(service)

    # Helper to convert Result to HTTP response
    def to_http_response(result: Result[Dict, str], status_ok: int = 200):
        """Convert Result type to HTTP response tuple (body, status)."""
        if result.is_ok():
            return result.unwrap(), status_ok
        else:
            return {"error": result.unwrap_err()}, 400

    # ========================================================================
    # ROUTES WITH AUTOMATIC RESULT HANDLING
    # ========================================================================

    @app.get("/mcp/health")
    async def health():
        result = await tool_routes.health_check()
        return to_http_response(result)

    @app.get("/mcp/tools")
    async def list_tools():
        result = await tool_routes.list_tools()
        return to_http_response(result)

    @app.get("/mcp/tools/{tool_name}")
    async def get_tool(tool_name: str):
        result = await tool_routes.get_tool_info(tool_name)
        return to_http_response(result, 200) if result.is_ok() else (result.unwrap_err_dict(), 404)

    @app.post("/mcp/tools/{tool_name}/execute")
    async def execute_tool(tool_name: str, request_data: dict):
        result = await tool_routes.execute_tool(tool_name, request_data)
        return to_http_response(result)

    @app.get("/mcp/sessions/{session_id}")
    async def get_session(session_id: str):
        result = await tool_routes.get_session_info(session_id)
        return (
            to_http_response(result, 200)
            if result.is_ok()
            else ({"error": result.unwrap_err()}, 404)
        )

    @app.get("/")
    async def home():
        return {
            "message": "Math Tools API",
            "description": "Expose MCP tools via REST API",
            "documentation": "Available at /mcp/tools",
        }

    print("   ✓ Routes configured with service layer pattern")

    print("\n" + "=" * 70)
    print("Available Endpoints:")
    print("=" * 70)
    print("  GET  /mcp/health               - Server health check")
    print("  GET  /mcp/tools                - List all tools")
    print("  GET  /mcp/tools/{tool_name}    - Get tool details")
    print("  POST /mcp/tools/{tool_name}/execute - Execute tool")
    print("  GET  /mcp/sessions/{session_id}     - Get session info")
    print("\nExample cURL requests:")
    print("  curl http://localhost:8000/mcp/tools")
    print("  curl http://localhost:8000/mcp/tools/add")
    print("  curl -X POST http://localhost:8000/mcp/tools/add/execute \\")
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"params": {"a": 5, "b": 3}}\'')
    print("\nTo start the server, uncomment web_server.run() below")
    print("=" * 70)

    # Uncomment to run
    # web_server.run()


# ============================================================================
# Example 2: Flask with MCPToolService
# ============================================================================


def flask_service_example():
    """Expose MCP tools via Flask using service layer pattern."""
    print("\n" + "=" * 70)
    print("Flask with MCPToolService Example")
    print("=" * 70)

    # Step 1: Create MCP server
    print("\n1. Creating MCP server with business tools...")
    mcp_settings = MCPServerSettings(
        name="BusinessTools",
        version="1.0.0",
        description="Business logic tools exposed via HTTP",
    )
    mcp_server = MCPServerFactory.create(MCPServerType.OPENAI, mcp_settings)

    # Register tools
    def calculate_discount(price: float, discount_percent: float) -> float:
        """Calculate discounted price."""
        return price * (1 - discount_percent / 100)

    def get_product_info(product_id: str) -> Dict[str, Any]:
        """Get product information (mock)."""
        products = {
            "P001": {"name": "Product A", "price": 99.99, "stock": 100},
            "P002": {"name": "Product B", "price": 149.99, "stock": 50},
            "P003": {"name": "Product C", "price": 199.99, "stock": 25},
        }
        return products.get(product_id, {"error": "Product not found"})

    # Use fluent API for clean tool registration
    (
        mcp_server.register_tool(
            "calculate_discount",
            calculate_discount,
            "Calculate discounted price",
            parameters={
                "price": {"type": "float", "description": "Original price"},
                "discount_percent": {"type": "float", "description": "Discount percentage"},
            },
            return_type="float",
        )
        .register_tool(
            "get_product_info",
            get_product_info,
            "Get product information",
            parameters={"product_id": {"type": "str", "description": "Product ID"}},
            return_type="dict",
            tags=["products", "business"],
        )
        .initialize()
    )
    print("   ✓ Registered tools: calculate_discount, get_product_info")

    # Step 2: Create Flask server
    print("\n2. Creating Flask web server...")
    web_settings = ServerSettings(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
    web_server = ServerFactory.create(ServerType.FLASK, web_settings)
    print("   ✓ Flask server created")

    # Step 3: Create MCPToolService
    print("\n3. Creating MCPToolService...")
    service_settings = MCPToolServiceSettings(enable_history=True)
    service = MCPToolService(mcp_server, service_settings)
    print("   ✓ MCPToolService created")

    # Step 4: Add routes using Railway-Oriented Programming (ROP)
    print("\n4. Setting up routes with ROP pattern...")

    class ToolRoutes:
        """Route handlers using MCPToolService with ROP for error handling."""

        def __init__(self, service: MCPToolService):
            self.service = service

        # ====================================================================
        # RAILWAY-ORIENTED PROGRAMMING (ROP) HANDLERS
        # ====================================================================
        # Each handler returns Result[T, E] which automatically propagates
        # errors through .map() and .then() chains without try/except

        def health_check(self) -> Result[Dict[str, Any], str]:
            """Health check using ROP."""
            return Ok(self.service.health_check())

        def list_tools(self) -> Result[Dict[str, Any], str]:
            """List tools using ROP."""
            return Ok(self.service.list_tools())

        def get_tool_info(self, tool_name: str) -> Result[Dict[str, Any], str]:
            """Get tool info using ROP with validation."""
            info = self.service.get_tool_info(tool_name)

            if info is None:
                return Err(f"Tool '{tool_name}' not found")

            return Ok(info)

        def execute_tool(self, tool_name: str, request_data: dict) -> Result[Dict[str, Any], str]:
            """Execute tool using ROP with error handling."""
            try:
                params = request_data.get("params", {})
                session_id = request_data.get("session_id")

                result = self.service.execute_tool(tool_name, params, session_id)
                return Ok(result)
            except ValueError as e:
                return Err(str(e))
            except Exception as e:
                return Err(f"Unexpected error: {str(e)}")

        def get_session_info(self, session_id: str) -> Result[Dict[str, Any], str]:
            """Get session info using ROP."""
            try:
                return Ok(self.service.get_session_info(session_id))
            except ValueError as e:
                return Err(str(e))

    tool_routes = ToolRoutes(service)

    # Helper to convert Result to Flask response tuple (body, status)
    def to_flask_response(result: Result[Dict, str], status_ok: int = 200, status_err: int = 400):
        """Convert Result type to Flask response tuple (body, status)."""
        if result.is_ok():
            return result.unwrap(), status_ok
        else:
            return {"error": result.unwrap_err()}, status_err

    # ========================================================================
    # ROUTES WITH AUTOMATIC RESULT HANDLING
    # ========================================================================

    @web_server.route("/mcp/health", methods=["GET"])
    def health():
        result = tool_routes.health_check()
        return to_flask_response(result)

    @web_server.route("/mcp/tools", methods=["GET"])
    def list_tools():
        result = tool_routes.list_tools()
        return to_flask_response(result)

    @web_server.route("/mcp/tools/<tool_name>", methods=["GET"])
    def get_tool(tool_name):
        result = tool_routes.get_tool_info(tool_name)
        return to_flask_response(result, status_ok=200, status_err=404)

    @web_server.route("/mcp/tools/<tool_name>/execute", methods=["POST"])
    def execute_tool(tool_name, data: dict):
        result = tool_routes.execute_tool(tool_name, data)
        return to_flask_response(result, status_ok=200, status_err=400)

    @web_server.route("/mcp/sessions/<session_id>", methods=["GET"])
    def get_session(session_id):
        result = tool_routes.get_session_info(session_id)
        return to_flask_response(result, status_ok=200, status_err=404)

    @web_server.route("/api/health", methods=["GET"])
    def api_health():
        return {"status": "healthy", "service": "business-api"}

    @web_server.route("/api/products", methods=["GET"])
    def list_products():
        return {
            "products": [
                {"id": "P001", "name": "Product A"},
                {"id": "P002", "name": "Product B"},
                {"id": "P003", "name": "Product C"},
            ]
        }

    print("   ✓ Routes configured with service layer pattern")

    print("\n" + "=" * 70)
    print("Available Endpoints:")
    print("=" * 70)
    print("  GET  /api/health")
    print("  GET  /api/products")
    print("  GET  /mcp/health")
    print("  GET  /mcp/tools")
    print("  GET  /mcp/tools/{tool_name}")
    print("  POST /mcp/tools/{tool_name}/execute")
    print("  GET  /mcp/sessions/{session_id}")
    print("\nTo start the server, uncomment web_server.run() below")
    print("=" * 70)

    # Uncomment to run
    # web_server.run()


# ============================================================================
# Example 3: Programmatic Client Usage
# ============================================================================


def programmatic_client_example():
    """Example of consuming exposed tools via HTTP."""
    print("\n" + "=" * 70)
    print("Programmatic Client Usage")
    print("=" * 70)

    print("\nExample code for consuming exposed tools programmatically:\n")

    example_code = """
import requests
import json

BASE_URL = "http://localhost:8000/mcp"

# 1. List all tools
response = requests.get(f"{BASE_URL}/tools")
tools = response.json()
print(f"Available tools: {[t['name'] for t in tools['tools']]}")

# 2. Execute a tool
payload = {
    "params": {
        "a": 10,
        "b": 5
    }
}
response = requests.post(
    f"{BASE_URL}/tools/add/execute",
    json=payload
)
result = response.json()
print(f"Result: {result['result']}")
print(f"Session: {result['session_id']}")

# 3. Reuse session for multiple operations
session_id = result['session_id']

# Execute multiply in same session
payload = {
    "params": {"x": 3.5, "y": 2.0},
    "session_id": session_id
}
response = requests.post(
    f"{BASE_URL}/tools/multiply/execute",
    json=payload
)
result = response.json()
print(f"Multiply result: {result['result']}")

# 4. Check session history
response = requests.get(f"{BASE_URL}/sessions/{session_id}")
session = response.json()
print(f"Total executions: {session['total_executions']}")
for execution in session['execution_history']:
    print(f"  - {execution['tool']}: {execution['params']} -> {execution['result']}")
"""

    print(example_code)
    print("=" * 70)


# ============================================================================
# Example 4: Architecture Overview
# ============================================================================


def architecture_example():
    """Show the architecture pattern."""
    print("\n" + "=" * 70)
    print("Architecture Pattern (Service Layer)")
    print("=" * 70)

    architecture = """
HTTP CLIENT
    ↓ (HTTP Request)

┌──────────────────────────────────────────────────────┐
│                FASTAPI / FLASK                        │
│                                                       │
│  @route("/mcp/tools/{tool_name}/execute")           │
│  async def execute_tool(tool_name, request_data):   │
│      return tool_routes.execute_tool(...)           │
│                                                       │
└──────────────────────────────────────────────────────┘
    ↓ (DI: MCPToolService instance)

┌──────────────────────────────────────────────────────┐
│            MCPTOOLSERVICE (Service Layer)            │
│                                                       │
│  - Session Management                               │
│  - Execution History                                │
│  - Validation & Error Handling                      │
│  - HTTP-specific concerns                           │
│                                                       │
└──────────────────────────────────────────────────────┘
    ↓

┌──────────────────────────────────────────────────────┐
│              MCPSERVER (Tool Management)             │
│                                                       │
│  - Tool Registry                                    │
│  - Session Context                                  │
│  - Execution Orchestration                          │
│                                                       │
└──────────────────────────────────────────────────────┘
    ↓

┌──────────────────────────────────────────────────────┐
│               REGISTERED TOOLS                       │
│                                                       │
│  - add(a, b)                                        │
│  - multiply(x, y)                                   │
│  - power(base, exp)                                 │
│  - etc.                                             │
│                                                       │
└──────────────────────────────────────────────────────┘
    ↓

HTTP RESPONSE (with result & session_id)

Key Benefits:
✓ Clean separation of concerns
✓ Dependency injection friendly
✓ Framework-agnostic
✓ Easy to test (mock MCPToolService)
✓ Consistent with api_template pattern
"""

    print(architecture)
    print("=" * 70)


# ============================================================================
# Main
# ============================================================================


# ============================================================================
# Example 5: Railway-Oriented Programming (ROP) Pattern Explanation
# ============================================================================


def rop_pattern_explanation():
    """Explain the Railway-Oriented Programming pattern used in examples."""
    print("\n" + "=" * 70)
    print("Railway-Oriented Programming (ROP) Pattern")
    print("=" * 70)

    explanation = """
WHAT IS ROP?
============
Railway-Oriented Programming is a functional error handling pattern that
treats errors as first-class values. Instead of throwing exceptions,
operations return Result[T, E] which is either Ok(value) or Err(error).

TWO TRACKS:
───────────
Success Track (Ok)  →  Continue with value
                    ↘
                     ⊗ (error check)
                    ↗
Error Track   (Err) →  Short-circuit to error handler

BENEFITS:
─────────
✓ No try/except blocks needed
✓ Automatic error propagation
✓ Composable with .map() and .then()
✓ Type-safe error handling
✓ Consistent with axiompy patterns

EXAMPLE IN THE MCPToolService:
──────────────────────────────

Without ROP (using try/except):
    def execute_tool(self, tool_name: str, request_data: dict):
        try:
            params = request_data.get("params", {})
            session_id = request_data.get("session_id")
            return self.service.execute_tool(tool_name, params, session_id)
        except ValueError as e:
            return {"error": str(e)}, 400
        except Exception as e:
            return {"error": "Internal error"}, 500

With ROP (clean and composable):
    def execute_tool(
        self, tool_name: str, request_data: dict
    ) -> Result[Dict[str, Any], str]:
        try:
            params = request_data.get("params", {})
            session_id = request_data.get("session_id")

            # Returns Ok(result) or Err(error) - no mixing with status codes
            result = self.service.execute_tool(tool_name, params, session_id)
            return Ok(result)
        except ValueError as e:
            return Err(str(e))  # Automatic error track
        except Exception as e:
            return Err(f"Unexpected error: {str(e)}")

    # In route handler:
    result = await tool_routes.execute_tool(tool_name, request_data)

    # Convert to HTTP response at the boundary
    return to_http_response(result)  # Handles Ok/Err automatically

ROP COMPOSABILITY (when needed):
─────────────────────────────────

# Chain multiple operations
result = (
    Ok({"a": 5, "b": 3})
    .map(lambda data: service.execute_tool("add", data))
    .map(lambda result: result["result"])
    .unwrap_or(0)  # Default to 0 on error
)

AXIOMPY ROP API:
───────────────
Ok(value)              - Create success result
Err(error)             - Create error result
result.is_ok()         - Check if success
result.is_err()        - Check if error
result.unwrap()        - Get value (panics if error)
result.unwrap_err()    - Get error value
result.unwrap_or(default) - Get value or default
result.map(fn)         - Transform success value
result.then(fn)        - Flat-map to another Result
result.map_err(fn)     - Transform error value

KEY TAKEAWAY:
─────────────
ROP separates:
  1. Business logic (handlers return Result types)
  2. HTTP adaptation (convert Result to response at route boundary)

This keeps handlers testable and routes focused on adaptation!
"""

    print(explanation)
    print("=" * 70)


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  MCPToolService Examples".center(68) + "║")
    print("║" + "  Service Layer Pattern + ROP for Exposing MCP Tools".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")

    fastapi_service_example()
    flask_service_example()
    architecture_example()
    rop_pattern_explanation()
    programmatic_client_example()

    print("\n✓ Examples completed! Check the code for details.\n")
