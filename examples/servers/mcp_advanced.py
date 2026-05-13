"""
Advanced MCP Server Example

Demonstrates advanced patterns including:
- Complex tool workflows
- Error handling
- Tool dependencies
- Metadata enrichment
- Performance tracking

Usage:
    python examples/mcp_advanced.py
"""

import json
import time
from dataclasses import dataclass
from typing import Dict, List

from axiompy.servers import (
    MCPServer,
    MCPServerError,
    MCPServerSettings,
    MCPToolError,
)


@dataclass
class UserData:
    """User information."""

    user_id: int
    name: str
    email: str
    role: str = "user"


class DataService:
    """Service that maintains mock data."""

    def __init__(self):
        self.users: Dict[int, UserData] = {
            1: UserData(1, "Alice Johnson", "alice@example.com", "admin"),
            2: UserData(2, "Bob Smith", "bob@example.com", "user"),
            3: UserData(3, "Carol White", "carol@example.com", "user"),
        }
        self.search_history: List[Dict] = []

    def get_user(self, user_id: int) -> UserData:
        """Get user by ID."""
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")
        return self.users[user_id]

    def search_users(self, query: str) -> List[UserData]:
        """Search users by name or email."""
        results = []
        query_lower = query.lower()
        for user in self.users.values():
            if query_lower in user.name.lower() or query_lower in user.email.lower():
                results.append(user)

        # Track search
        self.search_history.append(
            {"query": query, "results": len(results), "timestamp": time.time()}
        )
        return results

    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        return "@" in email and "." in email

    def create_user(self, name: str, email: str) -> UserData:
        """Create new user."""
        if not self.validate_email(email):
            raise ValueError(f"Invalid email: {email}")

        new_id = max(self.users.keys()) + 1
        user = UserData(new_id, name, email, "user")
        self.users[new_id] = user
        return user


def example_advanced_workflow():
    """Advanced workflow with error handling."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Advanced Workflow with Error Handling")
    print("=" * 70)

    class AdvancedMCPServer(MCPServer):
        """MCP server with execution tracking."""

        def __init__(self, settings):
            super().__init__(settings)
            self.service = DataService()
            self.execution_log = []

        def initialize(self):
            pass

        def execute_tool(self, tool_name, session, **kwargs):
            start_time = time.time()
            try:
                tool = self.get_tool(tool_name)
                if not tool:
                    raise MCPToolError(f"Tool '{tool_name}' not found")

                result = tool.execute(**kwargs)

                # Log execution
                duration = time.time() - start_time
                self.execution_log.append(
                    {
                        "tool": tool_name,
                        "session": session.session_id[:8],
                        "status": "success",
                        "duration": duration,
                    }
                )

                return result

            except MCPToolError:
                raise
            except Exception as e:
                # Log error
                duration = time.time() - start_time
                self.execution_log.append(
                    {
                        "tool": tool_name,
                        "session": session.session_id[:8],
                        "status": "error",
                        "error": str(e),
                        "duration": duration,
                    }
                )
                raise MCPToolError(f"Tool execution failed: {str(e)}")

        def shutdown(self):
            pass

    # Create server
    settings = MCPServerSettings(
        name="AdvancedUserService",
        version="2.0.0",
        description="Advanced user management service",
        enable_logging=True,
    )
    server = AdvancedMCPServer(settings)

    # Register tools
    print("\nRegistering advanced tools...")

    server.register_tool(
        "get_user",
        lambda user_id: {
            "user_id": server.service.get_user(user_id).user_id,
            "name": server.service.get_user(user_id).name,
            "email": server.service.get_user(user_id).email,
            "role": server.service.get_user(user_id).role,
        },
        "Get user by ID",
        parameters={"user_id": {"type": "int"}},
        return_type="dict",
        tags=["user", "retrieval"],
    )

    server.register_tool(
        "search_users",
        lambda query: [
            {"user_id": u.user_id, "name": u.name, "email": u.email}
            for u in server.service.search_users(query)
        ],
        "Search users by name or email",
        parameters={"query": {"type": "str"}},
        return_type="list",
        tags=["user", "search"],
    )

    server.register_tool(
        "create_user",
        lambda name, email: {
            "user_id": server.service.create_user(name, email).user_id,
            "name": server.service.create_user(name, email).name,
            "email": server.service.create_user(name, email).email,
        },
        "Create new user",
        parameters={"name": {"type": "str"}, "email": {"type": "str"}},
        return_type="dict",
        tags=["user", "creation"],
    )

    # Initialize
    server.initialize()
    session = server.create_session("admin_agent", metadata={"admin": True})

    print("\n📋 Executing workflow...")

    # Successful retrieval
    print("\n1. Retrieve user (success):")
    try:
        user = server.execute_tool("get_user", session, user_id=1)
        print(f"   ✓ {user['name']} ({user['email']})")
    except MCPToolError as e:
        print(f"   ✗ Error: {e}")

    # Search
    print("\n2. Search users:")
    try:
        results = server.execute_tool("search_users", session, query="alice")
        print(f"   ✓ Found {len(results)} user(s)")
        for user in results:
            print(f"      - {user['name']} ({user['email']})")
    except MCPToolError as e:
        print(f"   ✗ Error: {e}")

    # Failed retrieval (not found)
    print("\n3. Retrieve non-existent user (error):")
    try:
        user = server.execute_tool("get_user", session, user_id=999)
        print(f"   ✓ {user['name']}")
    except MCPToolError as e:
        print(f"   ✗ Expected error: {e}")

    # Create with invalid email (error)
    print("\n4. Create user with invalid email (error):")
    try:
        user = server.execute_tool("create_user", session, name="Test User", email="invalid")
        print(f"   ✓ Created: {user['name']}")
    except MCPToolError as e:
        print(f"   ✗ Expected error: {e}")

    # Create successfully
    print("\n5. Create user successfully:")
    try:
        user = server.execute_tool(
            "create_user", session, name="Diana Prince", email="diana@example.com"
        )
        print(f"   ✓ Created user ID: {user['user_id']} - {user['name']}")
    except MCPToolError as e:
        print(f"   ✗ Error: {e}")

    # Show execution log
    print("\n📊 Execution Log:")
    print("   Tool              | Status  | Duration")
    print("   " + "-" * 40)
    for log in server.execution_log:
        duration_ms = f"{log['duration'] * 1000:.2f}ms"
        status = "✓" if log["status"] == "success" else "✗"
        print(f"   {log['tool']:<17} | {status} {log['status']:<5} | {duration_ms:>10}")

    server.shutdown()
    print("\n✓ Advanced workflow completed!")


def example_tool_organization():
    """Tools organized by tags and categories."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Tool Organization and Discovery")
    print("=" * 70)

    class DiscoveryMCPServer(MCPServer):
        def initialize(self):
            pass

        def execute_tool(self, tool_name, session, **kwargs):
            tool = self.get_tool(tool_name)
            return tool.execute(**kwargs)

        def shutdown(self):
            pass

        def list_tools_by_tag(self, tag: str):
            """Get all tools with a specific tag."""
            return [t for t in self.list_tools() if tag in t["tags"]]

    settings = MCPServerSettings(name="ToolDiscovery")
    server = DiscoveryMCPServer(settings)

    # Register tools with tags
    print("\nRegistering tools with tags...")

    tools_config = [
        ("add", lambda a, b: a + b, "Add numbers", "math", ["arithmetic", "basic"]),
        ("subtract", lambda a, b: a - b, "Subtract numbers", "math", ["arithmetic", "basic"]),
        ("multiply", lambda a, b: a * b, "Multiply numbers", "math", ["arithmetic", "advanced"]),
        (
            "divide",
            lambda a, b: a / b if b != 0 else None,
            "Divide numbers",
            "math",
            ["arithmetic", "advanced"],
        ),
        ("uppercase", lambda s: s.upper(), "Convert to uppercase", "string", ["text", "transform"]),
        ("lowercase", lambda s: s.lower(), "Convert to lowercase", "string", ["text", "transform"]),
    ]

    for name, func, desc, category, tags in tools_config:
        server.register_tool(name, func, desc, tags=tags)
        print(f"   • {name}: {', '.join(tags)}")

    server.initialize()

    # Discover by tag
    print("\n🔍 Tool Discovery:")

    print("\n   Tools tagged 'arithmetic':")
    for tool in server.list_tools_by_tag("arithmetic"):
        print(f"      - {tool['name']}: {tool['description']}")

    print("\n   Tools tagged 'text':")
    for tool in server.list_tools_by_tag("text"):
        print(f"      - {tool['name']}: {tool['description']}")

    print("\n   Tools tagged 'advanced':")
    for tool in server.list_tools_by_tag("advanced"):
        print(f"      - {tool['name']}: {tool['description']}")

    # Show all tools
    print("\n📚 All Available Tools:")
    all_tools = server.list_tools()
    print(f"   Total: {len(all_tools)}")
    for tool in all_tools:
        print(f"      - {tool['name']}: {tool['tags']}")

    server.shutdown()
    print("\n✓ Tool discovery completed!")


def example_session_context():
    """Using session context for state management."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Session Context and State Management")
    print("=" * 70)

    class StatefulMCPServer(MCPServer):
        """Server with session-based state."""

        def __init__(self, settings):
            super().__init__(settings)
            self.session_state: Dict[str, Dict] = {}

        def initialize(self):
            pass

        def execute_tool(self, tool_name, session, **kwargs):
            tool = self.get_tool(tool_name)
            result = tool.execute(**kwargs)

            # Update session state
            if session.session_id not in self.session_state:
                self.session_state[session.session_id] = {"calls": 0, "results": []}

            self.session_state[session.session_id]["calls"] += 1
            self.session_state[session.session_id]["results"].append(
                {"tool": tool_name, "result": result}
            )

            return result

        def shutdown(self):
            pass

        def get_session_stats(self, session_id: str):
            """Get statistics for a session."""
            if session_id not in self.session_state:
                return None
            return self.session_state[session_id]

    settings = MCPServerSettings(name="StatefulService")
    server = StatefulMCPServer(settings)

    # Register tools
    server.register_tool("square", lambda x: x**2, "Square a number")
    server.register_tool("double", lambda x: x * 2, "Double a number")
    server.register_tool("increment", lambda x: x + 1, "Increment a number")

    server.initialize()

    # Create sessions
    print("\nCreating sessions for different workflows...")

    session_math = server.create_session("math_workflow", metadata={"workflow": "calculations"})
    session_stats = server.create_session("stats_workflow", metadata={"workflow": "statistics"})

    # Math workflow
    print("\n1️⃣  Math Workflow:")
    print("   Executing: square(5) -> double(...) -> increment(...)")

    result1 = server.execute_tool("square", session_math, x=5)
    print(f"      Step 1: square(5) = {result1}")

    result2 = server.execute_tool("double", session_math, x=result1)
    print(f"      Step 2: double({result1}) = {result2}")

    result3 = server.execute_tool("increment", session_math, x=result2)
    print(f"      Step 3: increment({result2}) = {result3}")

    # Stats workflow
    print("\n2️⃣  Stats Workflow:")
    print("   Executing: double(10) -> double(...)")

    result1 = server.execute_tool("double", session_stats, x=10)
    print(f"      Step 1: double(10) = {result1}")

    result2 = server.execute_tool("double", session_stats, x=result1)
    print(f"      Step 2: double({result1}) = {result2}")

    # Show session stats
    print("\n📊 Session Statistics:")

    math_stats = server.get_session_stats(session_math.session_id)
    print("\n   Math Workflow:")
    print(f"      Tool calls: {math_stats['calls']}")
    print("      Call history:")
    for i, call in enumerate(math_stats["results"], 1):
        print(f"         {i}. {call['tool']}() → {call['result']}")

    stats_stats = server.get_session_stats(session_stats.session_id)
    print("\n   Stats Workflow:")
    print(f"      Tool calls: {stats_stats['calls']}")
    print("      Call history:")
    for i, call in enumerate(stats_stats["results"], 1):
        print(f"         {i}. {call['tool']}() → {call['result']}")

    server.shutdown()
    print("\n✓ Session context example completed!")


if __name__ == "__main__":
    print("=" * 70)
    print("MCP SERVER - ADVANCED EXAMPLES")
    print("=" * 70)

    example_advanced_workflow()
    example_tool_organization()
    example_session_context()

    print("\n" + "=" * 70)
    print("All advanced examples completed successfully!")
    print("=" * 70)
