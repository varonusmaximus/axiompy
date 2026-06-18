# @!documentation

"""
MCP Server Testing Example

Demonstrates how to test MCP servers without SDK dependencies
using mock implementations.

This is the recommended approach for unit testing code that uses
MCP servers.

Usage:
    python examples/mcp_testing.py
"""

from axiompy.servers import (
    MCPServer,
    MCPServerError,
    MCPServerSettings,
    MCPToolError,
)


class MockMCPServer(MCPServer):
    """Mock MCP server for testing - no framework dependencies."""

    def initialize(self):
        """Mock initialization."""
        self._initialized = True

    def execute_tool(self, tool_name, session, **kwargs):
        """Execute tool - raises MCPToolError if not found."""
        tool = self.get_tool(tool_name)
        if not tool:
            raise MCPToolError(f"Tool '{tool_name}' not found")
        return tool.execute(**kwargs)

    def shutdown(self):
        """Mock shutdown."""
        self._initialized = False


class UserService:
    """Service that depends on MCP server."""

    def __init__(self, server: MCPServer):
        self.server = server
        self._setup_tools()

    def _setup_tools(self):
        """Register tools for user management."""
        self.server.register_tool(
            "get_user",
            self._get_user,
            "Get user by ID",
            parameters={"user_id": {"type": "int"}},
            return_type="dict",
        )

        self.server.register_tool(
            "create_user",
            self._create_user,
            "Create a new user",
            parameters={"name": {"type": "str"}, "email": {"type": "str"}},
            return_type="dict",
        )

        self.server.register_tool(
            "list_users",
            self._list_users,
            "List all users",
            return_type="list",
        )

    def _get_user(self, user_id: int):
        """Get user by ID."""
        users = {1: {"id": 1, "name": "Alice", "email": "alice@example.com"}}
        if user_id not in users:
            raise ValueError(f"User {user_id} not found")
        return users[user_id]

    def _create_user(self, name: str, email: str):
        """Create new user."""
        if not email or "@" not in email:
            raise ValueError("Invalid email")
        return {"id": 2, "name": name, "email": email}

    def _list_users(self):
        """List all users."""
        return [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
        ]

    def get_user_via_mcp(self, user_id: int):
        """Get user through MCP server."""
        session = self.server.create_session("service")
        try:
            return self.server.execute_tool("get_user", session, user_id=user_id)
        finally:
            self.server.close_session(session.session_id)

    def create_user_via_mcp(self, name: str, email: str):
        """Create user through MCP server."""
        session = self.server.create_session("service")
        try:
            return self.server.execute_tool("create_user", session, name=name, email=email)
        finally:
            self.server.close_session(session.session_id)

    def list_users_via_mcp(self):
        """List users through MCP server."""
        session = self.server.create_session("service")
        try:
            return self.server.execute_tool("list_users", session)
        finally:
            self.server.close_session(session.session_id)


def test_basic_tool_execution():
    """Test basic tool registration and execution."""
    print("\n" + "=" * 60)
    print("TEST 1: Basic Tool Execution")
    print("=" * 60)

    # Setup
    settings = MCPServerSettings(name="TestServer")
    server = MockMCPServer(settings)
    server.register_tool("add", lambda a, b: a + b, "Add two numbers")
    server.initialize()

    session = server.create_session("test_agent")

    # Test
    print("\nTest: Execute 'add' tool")
    result = server.execute_tool("add", session, a=5, b=3)
    assert result == 8, f"Expected 8, got {result}"
    print(f"✓ PASS: add(5, 3) = {result}")

    # Cleanup
    server.close_session(session.session_id)
    server.shutdown()


def test_tool_not_found():
    """Test that MCPToolError is raised for non-existent tools."""
    print("\n" + "=" * 60)
    print("TEST 2: Tool Not Found Error")
    print("=" * 60)

    # Setup
    settings = MCPServerSettings(name="TestServer")
    server = MockMCPServer(settings)
    server.register_tool("multiply", lambda a, b: a * b, "Multiply numbers")
    server.initialize()

    session = server.create_session("test_agent")

    # Test
    print("\nTest: Execute non-existent tool")
    try:
        server.execute_tool("divide", session, a=10, b=2)
        print("✗ FAIL: Expected MCPToolError")
    except MCPToolError as e:
        print(f"✓ PASS: MCPToolError raised: {e}")

    # Cleanup
    server.close_session(session.session_id)
    server.shutdown()


def test_tool_with_parameters():
    """Test tools with validated parameters."""
    print("\n" + "=" * 60)
    print("TEST 3: Tools with Parameter Validation")
    print("=" * 60)

    def divide_safe(a, b):
        if b == 0:
            raise ValueError("Division by zero")
        return a / b

    # Setup
    settings = MCPServerSettings(name="TestServer")
    server = MockMCPServer(settings)
    server.register_tool(
        "divide",
        divide_safe,
        "Divide two numbers",
        parameters={"a": {"type": "float"}, "b": {"type": "float"}},
    )
    server.initialize()

    session = server.create_session("test_agent")

    # Test success
    print("\nTest 1: Valid division")
    result = server.execute_tool("divide", session, a=10, b=2)
    assert result == 5, f"Expected 5, got {result}"
    print(f"✓ PASS: divide(10, 2) = {result}")

    # Test failure
    print("\nTest 2: Division by zero")
    try:
        server.execute_tool("divide", session, a=10, b=0)
        print("✗ FAIL: Expected MCPToolError")
    except MCPToolError as e:
        print("✓ PASS: MCPToolError raised for zero division")

    # Cleanup
    server.close_session(session.session_id)
    server.shutdown()


def test_session_management():
    """Test session creation and management."""
    print("\n" + "=" * 60)
    print("TEST 4: Session Management")
    print("=" * 60)

    # Setup
    settings = MCPServerSettings(name="TestServer")
    server = MockMCPServer(settings)
    server.register_tool("identity", lambda x: x, "Return input")
    server.initialize()

    # Test session creation
    print("\nTest 1: Create sessions")
    session1 = server.create_session("agent1", metadata={"type": "test"})
    session2 = server.create_session("agent2", metadata={"type": "test"})

    assert session1.agent_name == "agent1"
    assert session2.agent_name == "agent2"
    assert session1.session_id != session2.session_id
    print("✓ PASS: Created 2 sessions with different IDs")

    # Test session retrieval
    print("\nTest 2: Retrieve sessions")
    retrieved = server.get_session(session1.session_id)
    assert retrieved is not None
    assert retrieved.agent_name == "agent1"
    print("✓ PASS: Retrieved session for agent1")

    # Test session closure
    print("\nTest 3: Close sessions")
    initial_count = len(server.sessions)
    server.close_session(session1.session_id)
    assert len(server.sessions) == initial_count - 1
    print("✓ PASS: Session closed, count reduced")

    # Cleanup
    server.close_session(session2.session_id)
    server.shutdown()


def test_service_with_mcp_dependency():
    """Test a service that depends on MCP server."""
    print("\n" + "=" * 60)
    print("TEST 5: Service with MCP Dependency")
    print("=" * 60)

    # Setup
    settings = MCPServerSettings(name="TestServer")
    server = MockMCPServer(settings)
    service = UserService(server)
    server.initialize()

    # Test get user
    print("\nTest 1: Get existing user")
    user = service.get_user_via_mcp(1)
    assert user["id"] == 1
    assert user["name"] == "Alice"
    print(f"✓ PASS: Got user: {user['name']}")

    # Test get non-existent user
    print("\nTest 2: Get non-existent user")
    try:
        service.get_user_via_mcp(999)
        print("✗ FAIL: Expected error for non-existent user")
    except MCPToolError:
        print("✓ PASS: MCPToolError raised for non-existent user")

    # Test create user
    print("\nTest 3: Create user")
    user = service.create_user_via_mcp("Charlie", "charlie@example.com")
    assert user["name"] == "Charlie"
    print(f"✓ PASS: Created user: {user['name']}")

    # Test create user with invalid email
    print("\nTest 4: Create user with invalid email")
    try:
        service.create_user_via_mcp("Invalid", "notanemail")
        print("✗ FAIL: Expected error for invalid email")
    except MCPToolError:
        print("✓ PASS: MCPToolError raised for invalid email")

    # Test list users
    print("\nTest 5: List users")
    users = service.list_users_via_mcp()
    assert len(users) == 2
    print(f"✓ PASS: Listed {len(users)} users")

    # Cleanup
    server.shutdown()


def test_tool_registration_validation():
    """Test tool registration with validation."""
    print("\n" + "=" * 60)
    print("TEST 6: Tool Registration Validation")
    print("=" * 60)

    # Setup
    settings = MCPServerSettings(name="TestServer")
    server = MockMCPServer(settings)

    # Test 1: Register valid tool
    print("\nTest 1: Register valid tool")
    tool = server.register_tool("test", lambda: "result", "Test tool")
    assert tool.name == "test"
    print("✓ PASS: Registered tool 'test'")

    # Test 2: Duplicate registration error
    print("\nTest 2: Prevent duplicate registration")
    try:
        server.register_tool("test", lambda: "result", "Test tool")
        print("✗ FAIL: Expected error for duplicate registration")
    except MCPToolError:
        print("✓ PASS: MCPToolError raised for duplicate tool")

    # Test 3: List tools
    print("\nTest 3: List registered tools")
    tools = server.list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "test"
    print(f"✓ PASS: Listed {len(tools)} tool(s)")

    # Test 4: Unregister tool
    print("\nTest 4: Unregister tool")
    server.unregister_tool("test")
    tools = server.list_tools()
    assert len(tools) == 0
    print(f"✓ PASS: Tool unregistered, {len(tools)} tool(s) remaining")

    server.shutdown()


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MCP SERVER - TESTING EXAMPLES")
    print("=" * 60)

    tests = [
        test_basic_tool_execution,
        test_tool_not_found,
        test_tool_with_parameters,
        test_session_management,
        test_service_with_mcp_dependency,
        test_tool_registration_validation,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n✗ TEST FAILED: {test.__name__}")
            print(f"  Error: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total: {len(tests)}")
    print(f"Passed: {passed} ✓")
    print(f"Failed: {failed} ✗")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
