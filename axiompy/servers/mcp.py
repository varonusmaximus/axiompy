# @!mcp

"""
MCP (Model Context Protocol) Server abstraction layer with support for multiple AI agent frameworks.

Provides a unified interface for creating MCP servers that work with:
    - OpenAI (AgentKit, GPT agents)
    - Google Agent Development Kit (ADK)
    - Anthropic Claude (Claude agents via MCP)

Key Benefits:
    - Framework-agnostic MCP server implementation
    - Consistent API across different agent frameworks
    - Easy mocking for unit testing
    - Dependency injection-friendly design
    - Tool registry and session management
    - Built-in error handling and logging

Architecture:
    - MCPTool: Represents a callable tool with metadata
    - MCPSession: Session context for tool execution
    - MCPServer: Abstract base class defining the MCP interface
    - Concrete implementations: OpenAIMCPServer, GoogleADKMCPServer, AnthropicMCPServer
    - MCPServerFactory: Factory for creating MCP server instances

Quick Example:
    >>> from axiompy.servers import MCPServerFactory, MCPServerType, MCPServerSettings
    >>>
    >>> def add(a: int, b: int) -> int:
    ...     return a + b
    >>>
    >>> settings = MCPServerSettings(name="MyTools")
    >>> server = MCPServerFactory.create(MCPServerType.OPENAI, settings)
    >>> server.register_tool("add", add, description="Add two numbers")
    >>> server.initialize()
    >>> session = server.create_session("agent")
    >>> result = server.execute_tool("add", session, a=5, b=3)
    >>> print(result)  # Output: 8

For comprehensive examples, see:
    - examples/mcp_usage.py - Production usage examples
    - examples/mcp_testing.py - Unit testing patterns
"""

import inspect
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from axiompy.loggers import LoggerFactory
from axiompy.validators import ensure_in_range

logger = LoggerFactory.create_logger(__name__)


class MCPServerType(Enum):
    """Supported MCP server frameworks."""

    OPENAI = "openai"
    GOOGLE_ADK = "google_adk"
    ANTHROPIC = "anthropic"


class MCPServerError(Exception):
    """Base exception for MCP server errors."""

    pass


class MCPToolError(MCPServerError):
    """Exception raised when tool execution fails."""

    pass


class MCPSessionError(MCPServerError):
    """Exception raised when session operations fail."""

    pass


@dataclass
class MCPTool:
    """
    Represents an MCP tool that can be called by AI agents.

    Attributes:
        name: Unique identifier for the tool
        func: Callable that implements the tool
        description: Human-readable description of what the tool does
        parameters: Dict describing tool parameters (schema-like)
        return_type: Expected return type description
        tags: Optional tags for organizing tools
    """

    name: str
    func: Callable
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    return_type: str = "any"
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate tool after initialization."""
        if not callable(self.func):
            raise MCPToolError(f"Tool {self.name}: func must be callable")
        if not self.name:
            raise MCPToolError("Tool name cannot be empty")
        if not self.description:
            raise MCPToolError(f"Tool {self.name}: description cannot be empty")

        # Extract parameters from function signature if not provided
        if not self.parameters:
            sig = inspect.signature(self.func)
            self.parameters = {
                param_name: {
                    "type": (
                        str(param.annotation)
                        if param.annotation != inspect.Parameter.empty
                        else "any"
                    )
                }
                for param_name, param in sig.parameters.items()
            }

        logger.debug(f"MCPTool validated: {self.name}")

    def execute(self, **kwargs: Any) -> Any:
        """
        Execute the tool with provided arguments.

        Args:
            **kwargs: Arguments to pass to the tool function

        Returns:
            Result from executing the tool

        Raises:
            MCPToolError: If execution fails
        """
        try:
            result = self.func(**kwargs)
            logger.debug(f"Tool {self.name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool {self.name} execution failed: {str(e)}")
            raise MCPToolError(f"Tool {self.name} execution failed: {str(e)}")


@dataclass
class MCPSession:
    """
    Session context for MCP tool execution.

    Attributes:
        session_id: Unique identifier for this session
        agent_name: Name of the agent using this session
        metadata: Additional session metadata
        created_at: Session creation timestamp
    """

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: __import__("time").time())

    def __post_init__(self):
        """Validate session after initialization."""
        if not self.session_id:
            raise MCPSessionError("Session ID cannot be empty")
        logger.debug(f"MCPSession created: {self.session_id} for agent: {self.agent_name}")


@dataclass
class MCPServerSettings:
    """
    MCP server configuration.

    Attributes:
        name: Server name (default: "MCPServer")
        version: Server version (default: "1.0.0")
        description: Server description
        enable_logging: Enable detailed logging (default: True)
        max_tool_timeout: Maximum tool execution timeout in seconds
        extra_params: Additional framework-specific parameters
    """

    name: str = "MCPServer"
    version: str = "1.0.0"
    description: str = "MCP Server instance"
    enable_logging: bool = True
    max_tool_timeout: int = 30
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate settings after initialization."""
        ensure_in_range(
            self.max_tool_timeout,
            1,
            3600,
            f"max_tool_timeout {self.max_tool_timeout} must be between 1 and 3600",
        )
        logger.debug("MCPServerSettings validated successfully")


class MCPServer(ABC):
    """
    Abstract base class for MCP servers.

    All server implementations provide a consistent interface for:
    - Registering tools
    - Managing sessions
    - Executing tool calls
    - Handling errors

    Design Advantages:
        - Dependency Injection: Code depends on interface, not implementations
        - Easy Testing: Create simple mocks without real framework dependencies
        - Swappable: Switch frameworks without changing application code
        - Extensible: Add new frameworks by implementing this interface

    Example Usage:
        >>> class AgentOrchestrator:
        ...     def __init__(self, server: MCPServer):
        ...         self.server = server
        ...         self._setup_tools()
        ...
        ...     def _setup_tools(self):
        ...         self.server.register_tool("search", self.search, "Search documents")
        ...         self.server.register_tool("calculate", self.calculate, "Perform calculation")
        ...
        ...     def search(self, query: str):
        ...         return [{"id": 1, "text": f"Result for {query}"}]
        ...
        ...     def calculate(self, expr: str):
        ...         return eval(expr)

        # Works with any MCPServer implementation (OpenAI, Google ADK, Anthropic, mock, etc.)
    """

    def __init__(self, settings: MCPServerSettings):
        """
        Initialize MCP server instance.

        Args:
            settings: Server configuration
        """
        self.settings = settings
        self.tools: Dict[str, MCPTool] = {}
        self.sessions: Dict[str, MCPSession] = {}
        logger.info(f"MCPServer '{settings.name}' initialized")

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the server with its framework.

        This should set up any framework-specific initialization,
        connect to external services, etc.

        Raises:
            MCPServerError: If initialization fails
        """
        pass

    @abstractmethod
    def execute_tool(self, tool_name: str, session: MCPSession, **kwargs: Any) -> Any:
        """
        Execute a registered tool.

        Args:
            tool_name: Name of the tool to execute
            session: Session context for execution
            **kwargs: Arguments to pass to the tool

        Returns:
            Result from tool execution

        Raises:
            MCPToolError: If tool doesn't exist or execution fails
        """
        pass

    def register_tool(
        self,
        name: str,
        func: Callable,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        return_type: str = "any",
        tags: Optional[List[str]] = None,
    ) -> "MCPServer":
        """
        Register a tool with the server.

        Supports fluent API chaining for convenient tool registration.

        Args:
            name: Unique tool identifier
            func: Callable that implements the tool
            description: Description of what the tool does
            parameters: Optional tool parameters schema
            return_type: Expected return type
            tags: Optional tags for organizing tools

        Returns:
            Self (MCPServer) for method chaining

        Raises:
            MCPToolError: If tool registration fails

        Example:
            >>> server = MCPServerFactory.create(MCPServerType.OPENAI, settings)
            >>> (server
            ...     .register_tool("add", lambda a, b: a + b, "Add two numbers")
            ...     .register_tool("multiply", lambda x, y: x * y, "Multiply numbers")
            ...     .register_tool("divide", lambda a, b: a / b, "Divide numbers")
            ...     .initialize())
        """
        if name in self.tools:
            raise MCPToolError(f"Tool '{name}' already registered")

        tool = MCPTool(
            name=name,
            func=func,
            description=description,
            parameters=parameters or {},
            return_type=return_type,
            tags=tags or [],
        )

        self.tools[name] = tool
        logger.info(f"Tool '{name}' registered successfully")
        return self

    def unregister_tool(self, name: str) -> None:
        """
        Unregister a tool from the server.

        Args:
            name: Name of the tool to unregister

        Raises:
            MCPToolError: If tool doesn't exist
        """
        if name not in self.tools:
            raise MCPToolError(f"Tool '{name}' not found")

        del self.tools[name]
        logger.info(f"Tool '{name}' unregistered successfully")

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of all registered tools.

        Returns:
            List of tool information dictionaries
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "return_type": tool.return_type,
                "tags": tool.tags,
            }
            for tool in self.tools.values()
        ]

    def create_session(
        self, agent_name: str = "default", metadata: Optional[Dict[str, Any]] = None
    ) -> MCPSession:
        """
        Create a new session for tool execution.

        Args:
            agent_name: Name of the agent using this session
            metadata: Optional session metadata

        Returns:
            MCPSession instance
        """
        session = MCPSession(agent_name=agent_name, metadata=metadata or {})
        self.sessions[session.session_id] = session
        logger.debug(f"Session created: {session.session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[MCPSession]:
        """
        Retrieve a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            MCPSession if found, None otherwise
        """
        return self.sessions.get(session_id)

    def close_session(self, session_id: str) -> None:
        """
        Close a session.

        Args:
            session_id: Session identifier to close
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.debug(f"Session closed: {session_id}")

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """
        Retrieve a tool by name.

        Args:
            name: Tool name

        Returns:
            MCPTool if found, None otherwise
        """
        return self.tools.get(name)

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the server and cleanup resources."""
        pass


class OpenAIMCPServer(MCPServer):
    """
    OpenAI MCP server implementation.

    Supports OpenAI's AgentKit and GPT agents with MCP protocol.
    Handles function calling through the OpenAI SDK.

    Example:
        >>> from axiompy.servers import MCPServerFactory, MCPServerType, MCPServerSettings
        >>> settings = MCPServerSettings(name="OpenAI Tools")
        >>> server = MCPServerFactory.create(MCPServerType.OPENAI, settings)
        >>> server.register_tool("greet", lambda name: f"Hello {name}", "Greet someone")
        >>> server.initialize()
    """

    def __init__(self, settings: MCPServerSettings):
        super().__init__(settings)

        try:
            import openai  # noqa: F401

        except ImportError:
            raise MCPServerError("OpenAI SDK not installed. Install with: pip install openai")

        self._openai_client = None
        self._initialized = False
        logger.info("OpenAI MCP server created")

    def initialize(self) -> None:
        """Initialize OpenAI client."""
        try:
            import openai

            self._openai_client = openai.Client()
            self._initialized = True
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            raise MCPServerError(f"Failed to initialize OpenAI client: {str(e)}")

    def execute_tool(self, tool_name: str, session: MCPSession, **kwargs: Any) -> Any:
        """
        Execute a tool through OpenAI MCP protocol.

        Args:
            tool_name: Name of the tool to execute
            session: Session context for execution
            **kwargs: Tool arguments

        Returns:
            Tool execution result

        Raises:
            MCPToolError: If tool doesn't exist or execution fails
        """
        if not self._initialized:
            raise MCPServerError("Server not initialized. Call initialize() first.")

        tool = self.get_tool(tool_name)
        if not tool:
            raise MCPToolError(f"Tool '{tool_name}' not found")

        try:
            result = tool.execute(**kwargs)
            logger.debug(f"OpenAI: Tool '{tool_name}' executed in session {session.session_id}")
            return result
        except MCPToolError:
            raise
        except Exception as e:
            raise MCPToolError(f"OpenAI execution failed: {str(e)}")

    def shutdown(self) -> None:
        """Shutdown OpenAI server."""
        self._initialized = False
        self._openai_client = None
        logger.info("OpenAI MCP server shutdown")


class GoogleADKMCPServer(MCPServer):
    """
    Google Agent Development Kit MCP server implementation.

    Supports Google's ADK agents with MCP protocol.
    Handles tool calling through Google's SDK.

    Example:
        >>> from axiompy.servers import MCPServerFactory, MCPServerType, MCPServerSettings
        >>> settings = MCPServerSettings(name="Google Tools")
        >>> server = MCPServerFactory.create(MCPServerType.GOOGLE_ADK, settings)
        >>> server.register_tool("search", lambda q: [{"result": q}], "Search")
        >>> server.initialize()
    """

    def __init__(self, settings: MCPServerSettings):
        super().__init__(settings)

        try:
            import google.genai  # noqa: F401

        except ImportError:
            raise MCPServerError(
                "Google GenAI SDK not installed. Install with: pip install google-genai"
            )

        self._google_client = None
        self._initialized = False
        logger.info("Google ADK MCP server created")

    def initialize(self) -> None:
        """Initialize Google GenAI client."""
        try:
            import google.genai

            self._google_client = google.genai.Client()
            self._initialized = True
            logger.info("Google GenAI client initialized successfully")
        except Exception as e:
            raise MCPServerError(f"Failed to initialize Google client: {str(e)}")

    def execute_tool(self, tool_name: str, session: MCPSession, **kwargs: Any) -> Any:
        """
        Execute a tool through Google ADK MCP protocol.

        Args:
            tool_name: Name of the tool to execute
            session: Session context for execution
            **kwargs: Tool arguments

        Returns:
            Tool execution result

        Raises:
            MCPToolError: If tool doesn't exist or execution fails
        """
        if not self._initialized:
            raise MCPServerError("Server not initialized. Call initialize() first.")

        tool = self.get_tool(tool_name)
        if not tool:
            raise MCPToolError(f"Tool '{tool_name}' not found")

        try:
            result = tool.execute(**kwargs)
            logger.debug(f"Google ADK: Tool '{tool_name}' executed in session {session.session_id}")
            return result
        except MCPToolError:
            raise
        except Exception as e:
            raise MCPToolError(f"Google ADK execution failed: {str(e)}")

    def shutdown(self) -> None:
        """Shutdown Google ADK server."""
        self._initialized = False
        self._google_client = None
        logger.info("Google ADK MCP server shutdown")


class AnthropicMCPServer(MCPServer):
    """
    Anthropic Claude MCP server implementation.

    Supports Anthropic Claude agents with MCP protocol.
    Handles tool use through Claude's SDK.

    Example:
        >>> from axiompy.servers import MCPServerFactory, MCPServerType, MCPServerSettings
        >>> settings = MCPServerSettings(name="Claude Tools")
        >>> server = MCPServerFactory.create(MCPServerType.ANTHROPIC, settings)
        >>> server.register_tool("analyze", lambda text: {"score": 0.85}, "Analyze text")
        >>> server.initialize()
    """

    def __init__(self, settings: MCPServerSettings):
        super().__init__(settings)

        try:
            import anthropic  # noqa: F401

        except ImportError:
            raise MCPServerError("Anthropic SDK not installed. Install with: pip install anthropic")

        self._anthropic_client = None
        self._initialized = False
        logger.info("Anthropic MCP server created")

    def initialize(self) -> None:
        """Initialize Anthropic client."""
        try:
            import anthropic

            self._anthropic_client = anthropic.Anthropic()
            self._initialized = True
            logger.info("Anthropic client initialized successfully")
        except Exception as e:
            raise MCPServerError(f"Failed to initialize Anthropic client: {str(e)}")

    def execute_tool(self, tool_name: str, session: MCPSession, **kwargs: Any) -> Any:
        """
        Execute a tool through Anthropic MCP protocol.

        Args:
            tool_name: Name of the tool to execute
            session: Session context for execution
            **kwargs: Tool arguments

        Returns:
            Tool execution result

        Raises:
            MCPToolError: If tool doesn't exist or execution fails
        """
        if not self._initialized:
            raise MCPServerError("Server not initialized. Call initialize() first.")

        tool = self.get_tool(tool_name)
        if not tool:
            raise MCPToolError(f"Tool '{tool_name}' not found")

        try:
            result = tool.execute(**kwargs)
            logger.debug(f"Anthropic: Tool '{tool_name}' executed in session {session.session_id}")
            return result
        except MCPToolError:
            raise
        except Exception as e:
            raise MCPToolError(f"Anthropic execution failed: {str(e)}")

    def shutdown(self) -> None:
        """Shutdown Anthropic server."""
        self._initialized = False
        self._anthropic_client = None
        logger.info("Anthropic MCP server shutdown")


class MCPServerFactory:
    """
    Factory for creating MCP server instances.

    Main entry point for creating MCP servers. The factory automatically creates
    the appropriate server implementation based on the specified type.

    Usage:
        >>> from axiompy.servers import MCPServerFactory, MCPServerType, MCPServerSettings
        >>>
        >>> settings = MCPServerSettings(name="MyTools")
        >>> server = MCPServerFactory.create(MCPServerType.OPENAI, settings)
        >>>
        >>> def greet(name: str) -> str:
        ...     return f"Hello, {name}!"
        >>>
        >>> server.register_tool("greet", greet, "Greet a person")
        >>> server.initialize()
        >>>
        >>> session = server.create_session("my_agent")
        >>> result = server.execute_tool("greet", session, name="World")
        >>> print(result)  # Output: Hello, World!

    Testing:
        For unit tests, create mock implementations directly:

        >>> class MockMCPServer(MCPServer):
        ...     def initialize(self): pass
        ...     def execute_tool(self, tool_name, session, **kwargs):
        ...         return self.get_tool(tool_name).execute(**kwargs)
        ...     def shutdown(self): pass
        >>>
        >>> mock = MockMCPServer(MCPServerSettings())
        >>> mock.register_tool("test", lambda: "result", "Test tool")
        >>> session = mock.create_session()
        >>> result = mock.execute_tool("test", session)
        >>> assert result == "result"
    """

    _server_map = {
        MCPServerType.OPENAI: OpenAIMCPServer,
        MCPServerType.GOOGLE_ADK: GoogleADKMCPServer,
        MCPServerType.ANTHROPIC: AnthropicMCPServer,
    }

    @classmethod
    def create(cls, server_type: MCPServerType, settings: MCPServerSettings) -> MCPServer:
        """
        Create an MCP server instance.

        Args:
            server_type: Type of MCP server to create
            settings: Configuration for the server

        Returns:
            MCPServer instance

        Raises:
            ValueError: If server type is not supported
            MCPServerError: If instance creation fails
        """
        if server_type not in cls._server_map:
            raise ValueError(
                f"Unsupported MCP server type: {server_type}. "
                f"Supported: {list(cls._server_map.keys())}"
            )

        server_class = cls._server_map[server_type]
        try:
            return server_class(settings)
        except MCPServerError:
            # Let MCP-specific errors pass through unchanged
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise MCPServerError(f"Failed to create {server_type.value} MCP server: {str(e)}")

    @classmethod
    def register_server(cls, server_type: MCPServerType, server_class: type) -> None:
        """
        Register a custom MCP server implementation.

        Allows extending the factory with new server types.

        Args:
            server_type: Server type enum value
            server_class: Class implementing MCPServer interface

        Raises:
            TypeError: If server_class doesn't inherit from MCPServer
        """
        if not issubclass(server_class, MCPServer):
            raise TypeError("server_class must inherit from MCPServer")

        cls._server_map[server_type] = server_class
        logger.info(f"Registered custom MCP server: {server_type.value}")
