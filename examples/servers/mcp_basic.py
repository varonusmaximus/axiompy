"""
Basic MCP Server Example

Demonstrates simple tool registration and execution with MCP servers.
This example works with OpenAI, Google ADK, and Anthropic Claude.

Usage:
    python examples/mcp_basic.py
"""

from axiompy.servers import (
    MCPServerFactory,
    MCPServerSettings,
    MCPServerType,
)


def example_basic_calculator():
    """Simple calculator with MCP server."""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Basic Calculator")
    print("=" * 60)

    # Create MCP server (using mock so no SDK required)
    from axiompy.servers import MCPServer, MCPServerError

    class MockMCPServer(MCPServer):
        def initialize(self):
            pass

        def execute_tool(self, tool_name, session, **kwargs):
            tool = self.get_tool(tool_name)
            if not tool:
                raise MCPServerError(f"Tool '{tool_name}' not found")
            return tool.execute(**kwargs)

        def shutdown(self):
            pass

    # Create server with settings
    settings = MCPServerSettings(
        name="Calculator",
        version="1.0.0",
        description="Simple calculator with basic operations",
    )
    server = MockMCPServer(settings)

    # Register tools
    print("\nRegistering tools...")
    server.register_tool(
        "add",
        lambda a, b: a + b,
        "Add two numbers",
        parameters={"a": {"type": "int"}, "b": {"type": "int"}},
        return_type="int",
        tags=["math", "arithmetic"],
    )

    server.register_tool(
        "subtract",
        lambda a, b: a - b,
        "Subtract two numbers",
        parameters={"a": {"type": "int"}, "b": {"type": "int"}},
        return_type="int",
        tags=["math", "arithmetic"],
    )

    server.register_tool(
        "multiply",
        lambda a, b: a * b,
        "Multiply two numbers",
        parameters={"a": {"type": "int"}, "b": {"type": "int"}},
        return_type="int",
        tags=["math", "arithmetic"],
    )

    # List tools
    print("\nAvailable tools:")
    for tool_info in server.list_tools():
        print(f"  • {tool_info['name']}: {tool_info['description']}")

    # Initialize server
    print("\nInitializing server...")
    server.initialize()

    # Create session
    print("Creating session...")
    session = server.create_session(
        agent_name="calculator_agent",
        metadata={"mode": "basic", "precision": 2},
    )
    print(f"  Session ID: {session.session_id}")

    # Execute tools
    print("\nExecuting tools...")
    result_add = server.execute_tool("add", session, a=10, b=5)
    print(f"  add(10, 5) = {result_add}")

    result_subtract = server.execute_tool("subtract", session, a=20, b=8)
    print(f"  subtract(20, 8) = {result_subtract}")

    result_multiply = server.execute_tool("multiply", session, a=6, b=7)
    print(f"  multiply(6, 7) = {result_multiply}")

    # Cleanup
    print("\nCleaning up...")
    server.close_session(session.session_id)
    server.shutdown()
    print("✓ Done!")


def example_framework_agnostic():
    """Same code with different frameworks."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Framework-Agnostic Design")
    print("=" * 60)

    # Mock server for demo (no SDK required)
    from axiompy.servers import MCPServer

    class MockMCPServer(MCPServer):
        def initialize(self):
            pass

        def execute_tool(self, tool_name, session, **kwargs):
            tool = self.get_tool(tool_name)
            return tool.execute(**kwargs)

        def shutdown(self):
            pass

    def setup_tools(server):
        """Register same tools with any server."""
        server.register_tool(
            "greet",
            lambda name: f"Hello, {name}!",
            "Greet a person",
            parameters={"name": {"type": "str"}},
            return_type="str",
        )

        server.register_tool(
            "format_name",
            lambda first, last: f"{first.capitalize()} {last.capitalize()}",
            "Format a person's name",
            parameters={"first": {"type": "str"}, "last": {"type": "str"}},
            return_type="str",
        )

    # In real usage, you would use:
    # server = MCPServerFactory.create(MCPServerType.OPENAI, settings)
    # server = MCPServerFactory.create(MCPServerType.GOOGLE_ADK, settings)
    # server = MCPServerFactory.create(MCPServerType.ANTHROPIC, settings)

    # For this demo, using mock server
    settings = MCPServerSettings(name="Greeter")
    server = MockMCPServer(settings)

    print("\nSetting up tools (works with any framework)...")
    setup_tools(server)

    print("Initializing server...")
    server.initialize()

    session = server.create_session("greeting_agent")

    print("\nExecuting tools with mock server:")
    print(f"  greet('Alice') = {server.execute_tool('greet', session, name='Alice')}")
    print(
        f"  format_name('john', 'doe') = {server.execute_tool('format_name', session, first='john', last='doe')}"
    )

    server.shutdown()
    print("✓ Same tools work with OpenAI, Google ADK, and Anthropic!")


def example_session_management():
    """Demonstrate session tracking."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Session Management")
    print("=" * 60)

    from axiompy.servers import MCPServer

    class MockMCPServer(MCPServer):
        def __init__(self, settings):
            super().__init__(settings)
            self.call_count = 0

        def initialize(self):
            pass

        def execute_tool(self, tool_name, session, **kwargs):
            self.call_count += 1
            tool = self.get_tool(tool_name)
            return tool.execute(**kwargs)

        def shutdown(self):
            pass

    settings = MCPServerSettings(name="SessionDemo")
    server = MockMCPServer(settings)

    # Tool that uses session metadata
    def process_with_context(data):
        return f"Processed: {data.upper()}"

    server.register_tool(
        "process",
        process_with_context,
        "Process data with session context",
        parameters={"data": {"type": "str"}},
        return_type="str",
    )

    server.initialize()

    # Create multiple sessions for different agents
    print("\nCreating sessions for different agents...")

    session1 = server.create_session(
        agent_name="data_processor_1",
        metadata={"priority": "high", "timeout": 30},
    )
    print(f"  Session 1 (data_processor_1): {session1.session_id[:8]}...")

    session2 = server.create_session(
        agent_name="data_processor_2",
        metadata={"priority": "low", "timeout": 60},
    )
    print(f"  Session 2 (data_processor_2): {session2.session_id[:8]}...")

    # Execute with different sessions
    print("\nExecuting tools with different sessions...")

    result1 = server.execute_tool("process", session1, data="hello")
    print(f"  Session 1 result: {result1}")

    result2 = server.execute_tool("process", session2, data="world")
    print(f"  Session 2 result: {result2}")

    # List sessions
    print(f"\nActive sessions: {len(server.sessions)}")
    for sid, session in server.sessions.items():
        print(f"  • {session.agent_name}: {sid[:8]}... (metadata: {session.metadata})")

    # Retrieve specific session
    print("\nRetrieving session 1...")
    retrieved = server.get_session(session1.session_id)
    print(f"  Agent: {retrieved.agent_name}")
    print(f"  Metadata: {retrieved.metadata}")

    # Close session
    print("\nClosing session 1...")
    server.close_session(session1.session_id)
    print(f"Active sessions now: {len(server.sessions)}")

    server.shutdown()
    print("✓ Done!")


if __name__ == "__main__":
    print("=" * 60)
    print("MCP SERVER - BASIC EXAMPLES")
    print("=" * 60)

    example_basic_calculator()
    example_framework_agnostic()
    example_session_management()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
