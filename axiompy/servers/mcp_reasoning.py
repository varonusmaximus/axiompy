# @!mcp

"""
MCP Tool Validation & Sequencing Layer

Provides intelligent tool validation and sequencing for MCP servers through middleware pattern.
Supports chainable reasoning strategies: LLM-based validation, rule-based validation, custom logic.

Key Components:
    - MCPToolValidator: Abstract base for validation strategies (chain-able)
    - LLMToolValidator: LLM-based validation using Ollama or custom APIs
    - RuleBasedToolValidator: Fast rule-based prerequisite/data validation
    - MCPPipelineConfig: Configure validation behavior
    - MCPValidationMiddleware: Wraps MCPServer with intelligent validation

Features:
    - Chainable validators for flexible reasoning strategies
    - LLM-based tool validation with multiple backend support
    - Fast rule-based prerequisite and data validation
    - Custom validator registration per-tool
    - Tool sequencing and cost estimation
    - Session-based execution tracking
    - Graceful fallback when validators unavailable
    - Optional middleware wrapping of any MCPServer

Architecture:
    Agent Request
        ↓
    MCPValidationMiddleware
        ↓
    MCPToolValidator Chain:
        1. LLMToolValidator (if available)
        2. RuleBasedToolValidator (fallback/secondary)
        3. Custom Validators (per-tool override)
        ↓
    Decision: Allow/Block
        ↓
    MCPServer Execute Tool

Usage:
    >>> from axiompy.servers import MCPServerFactory, MCPServerType
    >>> from axiompy.servers.mcp_validation import (
    ...     LLMToolValidator, RuleBasedToolValidator, MCPValidationMiddleware
    ... )
    >>>
    >>> # Create base server
    >>> base_server = MCPServerFactory.create(MCPServerType.OPENAI, settings)
    >>>
    >>> # Create validator chain
    >>> llm_validator = LLMToolValidator(model="mistral")
    >>> rule_validator = RuleBasedToolValidator()
    >>>
    >>> # Wrap server with validation middleware
    >>> middleware = MCPValidationMiddleware(
    ...     base_server,
    ...     validators=[llm_validator, rule_validator]
    ... )
    >>>
    >>> # Register tools with validation metadata
    >>> middleware.register_tool(
    ...     "send_offer",
    ...     func=send_offer_impl,
    ...     description="Send personalized offer to customer",
    ...     prerequisites=["get_customer_profile"],
    ...     requires_data=["customer"],
    ...     provides_data=["offer_sent"]
    ... )
    >>>
    >>> # Tool execution validated through validator chain
    >>> result = middleware.execute_tool("send_offer", session, customer_id="123")

For LLM setup (optional):
    1. Install Ollama: https://ollama.ai
    2. Pull a model: ollama pull mistral
    3. Run: ollama serve
    4. LLMToolValidator will auto-detect and use it
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from axiompy.loggers import LoggerFactory
from axiompy.result import Err, Ok, Result
from axiompy.servers.mcp import MCPServer, MCPServerSettings, MCPSession, MCPTool

logger = LoggerFactory.create_logger(__name__)


class ToolCategory(Enum):
    """Tool classification for reasoning."""

    DATA = "data"  # Reads data (safe)
    SERVICE = "service"  # Calls services (medium risk)
    ACTION = "action"  # Takes actions (high risk)


class RiskLevel(Enum):
    """Risk classification for tools."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class MCPToolReasoning:
    """Metadata for tool reasoning."""

    name: str
    category: ToolCategory
    prerequisites: List[str] = field(default_factory=list)
    provides_data: List[str] = field(default_factory=list)  # Data categories it provides
    requires_data: List[str] = field(default_factory=list)  # Data categories it needs
    risk_level: RiskLevel = RiskLevel.LOW
    cost: int = 1  # Relative cost 1-10
    requires_approval: bool = False
    description: str = ""

    def __post_init__(self):
        """Validate reasoning metadata."""
        if not 1 <= self.cost <= 10:
            raise ValueError(f"Cost must be 1-10, got {self.cost}")
        logger.debug(f"MCPToolReasoning created for tool: {self.name}")


@dataclass
class MCPToolCall:
    """Record of a tool execution."""

    tool_name: str
    parameters: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None
    success: bool = False


@dataclass
class MCPReasoningSession:
    """Session state for tool execution reasoning."""

    session_id: str
    tool_calls: List[MCPToolCall] = field(default_factory=list)
    data_available: Set[str] = field(default_factory=set)  # Data categories available
    total_cost: int = 0
    failed_tools: Set[str] = field(default_factory=set)


@dataclass
class MCPPipelineConfig:
    """Configuration for reasoning middleware."""

    enable_validation: bool = True
    enable_sequencing: bool = True
    enable_cost_tracking: bool = True
    enable_session_tracking: bool = True
    max_pipeline_depth: int = 100  # Prevent infinite loops


class MCPToolValidator(ABC):
    """
    Abstract base class for tool validators (chain-able).

    Validators are responsible for determining if a tool should execute.
    Multiple validators can be chained, each having a chance to validate
    before the tool runs.

    Implementations:
        - LLMToolValidator: Uses LLM for intelligent validation
        - RuleBasedToolValidator: Uses prerequisite/data checks
        - Custom validators: User-defined business logic
    """

    @abstractmethod
    def validate_tool(  # pragma: no cover
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        session: "MCPReasoningSession",
        tool_metadata: Optional["MCPToolReasoning"] = None,
    ) -> Result[bool, str]:
        """
        Validate if tool should execute.

        Args:
            tool_name: Name of tool to validate
            parameters: Tool parameters
            session: Session context
            tool_metadata: Tool metadata (if available)

        Returns:
            Result[bool, str] - Ok(True) if valid, Err(reason) if invalid
        """
        pass  # pragma: no cover

    @abstractmethod
    def register_tool(  # pragma: no cover
        self,
        name: str,
        category: ToolCategory,
        prerequisites: Optional[List[str]] = None,
        provides_data: Optional[List[str]] = None,
        requires_data: Optional[List[str]] = None,
        risk_level: RiskLevel = RiskLevel.LOW,
        cost: int = 1,
        requires_approval: bool = False,
        description: str = "",
    ) -> None:
        """Register tool metadata for validation."""
        pass  # pragma: no cover

    @abstractmethod
    def suggest_tool_sequence(  # pragma: no cover
        self, goal: str, session: "MCPReasoningSession"
    ) -> Result[List[str], str]:
        """Suggest optimal tool sequence for a goal."""
        pass  # pragma: no cover


class LLMToolValidator(MCPToolValidator):
    """
    LLM-based reasoning engine supporting multiple backends.

    Uses language models to intelligently validate and sequence tool execution.
    Supports multiple sources for models:
        1. Ollama local server (default)
        2. Remote Ollama servers
        3. Custom LLM URLs (any LLM-as-a-service API)
        4. On-disk GGUF models (via Ollama or compatible tools)

    Supported Model Sources:
        - Ollama local: mistral, llama2, neural-chat, dolphin-mixtral, etc.
        - Ollama remote: http://hostname:11434
        - Custom LLM APIs: any compatible endpoint
        - GGUF files: /path/to/model.gguf

    Features:
        - LLM-based validation of tool execution appropriateness
        - Natural language goal understanding
        - Intelligent prerequisite reasoning
        - Context-aware tool sequencing
        - Graceful fallback to rule-based validation if LLM unavailable
        - Support for on-disk models, remote servers, or custom APIs
        - Custom validators can override LLM decisions

    Examples:
        >>> # Using Ollama local (default Mistral)
        >>> reasoning = SimpleMCPReasoning()
        >>>
        >>> # Using Ollama with different model
        >>> reasoning = SimpleMCPReasoning(model="llama2")
        >>>
        >>> # Using remote Ollama server
        >>> reasoning = SimpleMCPReasoning(
        ...     model="mistral",
        ...     backend_url="http://192.168.1.100:11434"
        ... )
        >>>
        >>> # Using on-disk GGUF model via local Ollama
        >>> reasoning = SimpleMCPReasoning(
        ...     model_path="/models/my-model.gguf",
        ...     backend_url="http://localhost:11434"
        ... )
        >>>
        >>> # Using custom LLM API endpoint
        >>> reasoning = SimpleMCPReasoning(
        ...     model="gpt-like-model",
        ...     backend_url="http://custom-llm.example.com/v1"
        ... )
    """

    def __init__(
        self,
        model: Optional[str] = None,
        model_path: Optional[str] = None,
        backend_url: str = "http://localhost:11434",
        backend_type: str = "ollama",
        timeout: int = 30,
        enable_llm: bool = True,
    ):
        """
        Initialize LLM-based reasoning engine.

        Args:
            model: Model name (for Ollama or API backends)
                   Examples: "mistral", "llama2", "gpt-4", etc.
                   Default: "mistral" if model_path not provided
            model_path: Path to on-disk GGUF model file
                       Examples: "/models/mistral.gguf", "./model.gguf"
                       If provided, takes precedence over model name
            backend_url: URL to LLM backend
                        Ollama: http://localhost:11434 (default)
                        Remote: http://192.168.1.100:11434
                        Custom: http://custom-llm.example.com
            backend_type: Type of backend ("ollama", "custom", "api")
                         Default: "ollama"
            timeout: Timeout for LLM requests in seconds
            enable_llm: Whether to use LLM (if False, falls back to rule-based)

        Raises:
            ValueError: If neither model nor model_path provided
        """
        if not model and not model_path:
            model = "mistral"  # Default to mistral

        if model_path and not model_path.strip():
            raise ValueError("Model path cannot be empty string")

        if model and not model.strip():
            raise ValueError("Model name cannot be empty string")

        self.model = model
        self.model_path = model_path
        self.backend_url = backend_url.rstrip("/")  # Remove trailing slash
        self.backend_type = backend_type
        self.timeout = timeout
        self.enable_llm = enable_llm

        self.tool_metadata: Dict[str, MCPToolReasoning] = {}
        self.sessions: Dict[str, MCPReasoningSession] = {}
        self.custom_validators: Dict[str, Callable] = {}
        self.custom_sequencers: Optional[Callable] = None

        self.llm_available = self._check_llm_availability()

        if not self.llm_available and self.enable_llm:
            model_desc = model_path or model
            logger.warning(
                f"LLM not available: {model_desc} at {backend_url}. "
                f"Falling back to rule-based validation. "
                f"To use LLM reasoning:"
                f"\n  - For Ollama: ollama serve"
                f"\n  - For on-disk models: ensure model at {model_path}"
                f"\n  - For custom API: ensure endpoint is running"
            )

    def _check_llm_availability(self) -> bool:
        """Check if LLM backend is accessible."""
        if not self.enable_llm:
            return False

        try:
            import requests

            # Different health checks based on backend type
            if self.backend_type == "ollama":
                response = requests.get(
                    f"{self.backend_url}/api/tags",
                    timeout=2,
                )
                return response.status_code == 200
            else:
                # For custom backends, try to reach the base URL
                response = requests.get(
                    self.backend_url,
                    timeout=2,
                )
                return response.status_code in [200, 404, 405]  # Accept various responses
        except Exception as e:
            logger.debug(f"LLM availability check failed: {str(e)}")
            return False

    def _call_llm(self, prompt: str) -> Optional[str]:
        """
        Call LLM for reasoning.

        Args:
            prompt: Natural language prompt

        Returns:
            LLM response or None if unavailable
        """
        if not self.llm_available or not self.enable_llm:
            return None

        try:
            import requests

            if self.backend_type == "ollama":
                return self._call_ollama(prompt, requests)
            elif self.backend_type == "custom":
                return self._call_custom_api(prompt, requests)
            else:
                logger.warning(f"Unknown backend type: {self.backend_type}")
                return None
        except Exception as e:
            logger.warning(f"LLM call failed: {str(e)}. Using rule-based validation.")
            return None

    def _call_ollama(self, prompt: str, requests_module: Any) -> Optional[str]:
        """Call Ollama API."""
        model_name = self.model
        if self.model_path:
            # For GGUF models, extract model name from path if model not set
            import os

            if not self.model:
                model_name = os.path.splitext(os.path.basename(self.model_path))[0]
            else:
                model_name = self.model

        response = requests_module.post(
            f"{self.backend_url}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.3,  # Lower temperature for consistent validation
            },
            timeout=self.timeout,
        )

        if response.status_code == 200:
            return response.json().get("response", "").strip()
        else:
            logger.warning(f"Ollama request failed with status {response.status_code}")
            return None

    def _call_custom_api(self, prompt: str, requests_module: Any) -> Optional[str]:
        """Call custom LLM API."""
        # Generic API call - backends should handle standard formats
        response = requests_module.post(
            f"{self.backend_url}/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "temperature": 0.3,
            },
            timeout=self.timeout,
        )

        if response.status_code == 200:
            data = response.json()
            # Try common response formats
            return (
                data.get("response", "") or data.get("text", "") or data.get("completion", "")
            ).strip()
        else:
            logger.warning(f"Custom API request failed with status {response.status_code}")
            return None

    def register_tool(
        self,
        name: str,
        category: ToolCategory,
        prerequisites: Optional[List[str]] = None,
        provides_data: Optional[List[str]] = None,
        requires_data: Optional[List[str]] = None,
        risk_level: RiskLevel = RiskLevel.LOW,
        cost: int = 1,
        requires_approval: bool = False,
        description: str = "",
    ) -> None:
        """Register tool metadata for reasoning."""
        self.tool_metadata[name] = MCPToolReasoning(
            name=name,
            category=category,
            prerequisites=prerequisites or [],
            provides_data=provides_data or [],
            requires_data=requires_data or [],
            risk_level=risk_level,
            cost=cost,
            requires_approval=requires_approval,
            description=description,
        )
        logger.info(f"Registered tool reasoning: {name}")

    def create_session(self, session_id: str) -> MCPReasoningSession:
        """Create a new reasoning session."""
        session = MCPReasoningSession(session_id=session_id)
        self.sessions[session_id] = session
        logger.debug(f"Created reasoning session: {session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[MCPReasoningSession]:
        """Get existing reasoning session."""
        return self.sessions.get(session_id)

    def register_custom_validator(
        self, tool_name: str, validator: Callable[[MCPToolReasoning, Dict], Result[bool, str]]
    ) -> None:
        """
        Register custom validation logic for a tool.

        Users can override default validation with their own business logic.

        Args:
            tool_name: Name of tool to validate
            validator: Function that takes (tool_metadata, parameters) -> Result[bool, str]
        """
        self.custom_validators[tool_name] = validator
        logger.info(f"Registered custom validator for tool: {tool_name}")

    def register_custom_sequencer(
        self, sequencer: Callable[[str, MCPReasoningSession], Result[List[str], str]]
    ) -> None:
        """
        Register custom tool sequencing logic.

        Users can override default sequencing with ML models, heuristics, etc.

        Args:
            sequencer: Function that takes (goal, session) -> Result[List[str], str]
        """
        self.custom_sequencers = sequencer
        logger.info("Registered custom tool sequencer")

    def validate_prerequisites(
        self, tool_name: str, session: MCPReasoningSession
    ) -> Result[bool, str]:
        """
        Validate that prerequisites are met (default SLM logic).

        This is the simple default - users can override with custom logic.
        """
        tool = self.tool_metadata.get(tool_name)
        if not tool:
            return Err(f"Tool '{tool_name}' not registered")

        # Check prerequisites
        for prereq in tool.prerequisites:
            prereq_calls = [c for c in session.tool_calls if c.tool_name == prereq and c.success]
            if not prereq_calls:
                return Err(f"Prerequisite '{prereq}' not met for tool '{tool_name}'")

        logger.debug(f"Prerequisites validated for tool: {tool_name}")
        return Ok(True)

    def validate_data_available(
        self, tool_name: str, session: MCPReasoningSession
    ) -> Result[bool, str]:
        """
        Validate that required data is available (default SLM logic).

        This is the simple default - users can override with custom logic.
        """
        tool = self.tool_metadata.get(tool_name)
        if not tool:
            return Err(f"Tool '{tool_name}' not registered")

        # Check data availability
        for data_type in tool.requires_data:
            if data_type not in session.data_available:
                return Err(f"Required data '{data_type}' not available for tool '{tool_name}'")

        logger.debug(f"Data validated for tool: {tool_name}")
        return Ok(True)

    def validate_tool(
        self, tool_name: str, parameters: Dict[str, Any], session: MCPReasoningSession
    ) -> Result[bool, str]:
        """
        Validate if tool call is allowed.

        Uses LLM reasoning if available, custom validator if registered,
        falls back to rule-based validation.

        Args:
            tool_name: Name of tool to validate
            parameters: Tool parameters
            session: Session context

        Returns:
            Result[bool, str] - validation result
        """
        # Step 1: Check if custom validator exists (highest priority)
        if tool_name in self.custom_validators:
            tool = self.tool_metadata.get(tool_name)
            if tool:
                return self.custom_validators[tool_name](tool, parameters)

        # Step 2: Try LLM-based validation if available
        if self.llm_available and self.enable_llm:
            llm_result = self._validate_tool_with_llm(tool_name, parameters, session)
            if llm_result is not None:
                return llm_result

        # Step 3: Fall back to rule-based validation
        result = self.validate_prerequisites(tool_name, session).then(
            lambda _: self.validate_data_available(tool_name, session)
        )

        return result

    def _validate_tool_with_llm(
        self, tool_name: str, parameters: Dict[str, Any], session: MCPReasoningSession
    ) -> Optional[Result[bool, str]]:
        """
        Use LLM to validate if tool should execute.

        Args:
            tool_name: Tool name
            parameters: Tool parameters
            session: Session context

        Returns:
            Result[bool, str] if LLM provided answer, None otherwise
        """
        tool = self.tool_metadata.get(tool_name)
        if not tool:
            return Err(f"Tool '{tool_name}' not registered")

        # Build context for LLM
        executed_tools = [c.tool_name for c in session.tool_calls if c.success]
        available_data = list(session.data_available)

        prompt = f"""
You are a tool execution validator for an AI agent system.

Tool to validate: {tool_name}
Tool description: {tool.description}
Tool category: {tool.category.value}
Tool risk level: {tool.risk_level.value}

Prerequisites (must be executed first):
- {", ".join(tool.prerequisites) if tool.prerequisites else "None"}

Required data (must be available):
- {", ".join(tool.requires_data) if tool.requires_data else "None"}

Already executed tools:
- {", ".join(executed_tools) if executed_tools else "None yet"}

Currently available data:
- {", ".join(available_data) if available_data else "None yet"}

Tool parameters to be used:
{parameters}

Should this tool be executed now? Answer only "YES" or "NO" with a brief reason.
Consider:
1. Are all prerequisites met (tools already executed)?
2. Is all required data available?
3. Does it make sense to run this tool at this point?
4. Are the parameters valid?
"""

        llm_response = self._call_llm(prompt)

        if llm_response:
            logger.debug(f"LLM validation for {tool_name}: {llm_response}")

            # Parse LLM response
            if "yes" in llm_response.lower()[:3]:  # Check first few chars for YES
                return Ok(True)
            else:
                # Extract reason from LLM response
                reason = llm_response[llm_response.find(".") + 1 :].strip()
                if not reason:
                    reason = "LLM determined tool should not execute now"
                return Err(f"LLM validation failed: {reason}")

        return None

    def suggest_tool_sequence(
        self, goal: str, session: MCPReasoningSession
    ) -> Result[List[str], str]:
        """
        Suggest optimal tool sequence for a goal.

        Uses custom sequencer if registered, otherwise default logic.
        """
        # Check if custom sequencer exists
        if self.custom_sequencers:
            return self.custom_sequencers(goal, session)

        # Default SLM: topological sort based on prerequisites
        try:
            sequence = self._topological_sort()
            logger.debug(f"Tool sequence suggested for goal '{goal}': {sequence}")
            return Ok(sequence)
        except ValueError as e:
            return Err(f"Cannot sequence tools: {str(e)}")

    def _topological_sort(self) -> List[str]:
        """Sort tools by dependencies (default SLM logic)."""
        # Build dependency graph
        graph = {}
        in_degree = {}

        for tool_name, tool in self.tool_metadata.items():
            graph[tool_name] = tool.prerequisites
            in_degree[tool_name] = len(tool.prerequisites)

        # Topological sort
        queue = [name for name, degree in in_degree.items() if degree == 0]
        sequence = []

        while queue:
            # Sort by cost (cheaper first) for same level
            queue.sort(key=lambda x: self.tool_metadata[x].cost)
            tool = queue.pop(0)
            sequence.append(tool)

            # Find dependent tools
            for name, deps in graph.items():
                if tool in deps:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)

        if len(sequence) != len(self.tool_metadata):
            raise ValueError("Circular dependency detected in tool prerequisites")

        return sequence

    def record_tool_call(
        self,
        session_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> Result[bool, str]:
        """Record a tool call in session."""
        session = self.get_session(session_id)
        if not session:
            return Err(f"Session '{session_id}' not found")

        success = error is None
        call = MCPToolCall(
            tool_name=tool_name,
            parameters=parameters,
            result=result,
            error=error,
            success=success,
        )

        session.tool_calls.append(call)

        # Update session state
        if success:
            tool = self.tool_metadata.get(tool_name)
            if tool:
                session.total_cost += tool.cost
                # Add provided data to available
                for data_type in tool.provides_data:
                    session.data_available.add(data_type)
        else:
            session.failed_tools.add(tool_name)

        return Ok(True)

    def estimate_cost(self, tool_sequence: List[str]) -> Result[int, str]:
        """Estimate total execution cost for a tool sequence."""
        total = 0
        for tool_name in tool_sequence:
            tool = self.tool_metadata.get(tool_name)
            if not tool:
                return Err(f"Tool '{tool_name}' not registered")
            total += tool.cost

        return Ok(total)

    def get_session_summary(self, session_id: str) -> Result[Dict[str, Any], str]:
        """Get summary of session execution."""
        session = self.get_session(session_id)
        if not session:
            return Err(f"Session '{session_id}' not found")

        return Ok(
            {
                "session_id": session_id,
                "total_calls": len(session.tool_calls),
                "successful_calls": sum(1 for c in session.tool_calls if c.success),
                "failed_calls": len(session.failed_tools),
                "total_cost": session.total_cost,
                "data_available": list(session.data_available),
                "failed_tools": list(session.failed_tools),
            }
        )


class RuleBasedToolValidator(MCPToolValidator):
    """
    Fast rule-based tool validator.

    Uses simple prerequisite and data availability checks.
    No LLM calls - very fast and deterministic.
    Useful as fallback or when LLM reasoning not needed.
    """

    def __init__(self):
        """Initialize rule-based validator."""
        self.tool_metadata: Dict[str, MCPToolReasoning] = {}
        self.sessions: Dict[str, MCPReasoningSession] = {}
        self.custom_validators: Dict[str, Callable] = {}
        self.custom_sequencers: Optional[Callable] = None

    def register_tool(
        self,
        name: str,
        category: ToolCategory,
        prerequisites: Optional[List[str]] = None,
        provides_data: Optional[List[str]] = None,
        requires_data: Optional[List[str]] = None,
        risk_level: RiskLevel = RiskLevel.LOW,
        cost: int = 1,
        requires_approval: bool = False,
        description: str = "",
    ) -> None:
        """Register tool metadata for validation."""
        self.tool_metadata[name] = MCPToolReasoning(
            name=name,
            category=category,
            prerequisites=prerequisites or [],
            provides_data=provides_data or [],
            requires_data=requires_data or [],
            risk_level=risk_level,
            cost=cost,
            requires_approval=requires_approval,
            description=description,
        )
        logger.info(f"Registered tool reasoning: {name}")

    def create_session(self, session_id: str) -> MCPReasoningSession:
        """Create a new reasoning session."""
        session = MCPReasoningSession(session_id=session_id)
        self.sessions[session_id] = session
        logger.debug(f"Created reasoning session: {session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[MCPReasoningSession]:
        """Get existing reasoning session."""
        return self.sessions.get(session_id)

    def validate_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        session: MCPReasoningSession,
        tool_metadata: Optional[MCPToolReasoning] = None,
    ) -> Result[bool, str]:
        """Validate tool using prerequisite and data checks."""
        # Check custom validator first
        if tool_name in self.custom_validators:
            tool = self.tool_metadata.get(tool_name)
            if tool:
                return self.custom_validators[tool_name](tool, parameters)

        # Rule-based validation
        result = self._validate_prerequisites(tool_name, session).then(
            lambda _: self._validate_data_available(tool_name, session)
        )
        return result

    def _validate_prerequisites(
        self, tool_name: str, session: MCPReasoningSession
    ) -> Result[bool, str]:
        """Validate that prerequisites are met."""
        tool = self.tool_metadata.get(tool_name)
        if not tool:
            return Err(f"Tool '{tool_name}' not registered")

        for prereq in tool.prerequisites:
            prereq_calls = [c for c in session.tool_calls if c.tool_name == prereq and c.success]
            if not prereq_calls:
                return Err(f"Prerequisite '{prereq}' not met for tool '{tool_name}'")

        logger.debug(f"Prerequisites validated for tool: {tool_name}")
        return Ok(True)

    def _validate_data_available(
        self, tool_name: str, session: MCPReasoningSession
    ) -> Result[bool, str]:
        """Validate that required data is available."""
        tool = self.tool_metadata.get(tool_name)
        if not tool:
            return Err(f"Tool '{tool_name}' not registered")

        for data_type in tool.requires_data:
            if data_type not in session.data_available:
                return Err(f"Required data '{data_type}' not available for tool '{tool_name}'")

        logger.debug(f"Data validated for tool: {tool_name}")
        return Ok(True)

    def suggest_tool_sequence(
        self, goal: str, session: MCPReasoningSession
    ) -> Result[List[str], str]:
        """Suggest tool sequence using topological sort."""
        try:
            sequence = self._topological_sort()
            logger.debug(f"Tool sequence suggested for goal '{goal}': {sequence}")
            return Ok(sequence)
        except ValueError as e:
            return Err(f"Cannot sequence tools: {str(e)}")

    def _topological_sort(self) -> List[str]:
        """Sort tools by dependencies (topological sort)."""
        graph = {}
        in_degree = {}

        for tool_name, tool in self.tool_metadata.items():
            graph[tool_name] = tool.prerequisites
            in_degree[tool_name] = len(tool.prerequisites)

        queue = [name for name, degree in in_degree.items() if degree == 0]
        sequence = []

        while queue:
            queue.sort(key=lambda x: self.tool_metadata[x].cost)
            tool = queue.pop(0)
            sequence.append(tool)

            for name, deps in graph.items():
                if tool in deps:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)

        if len(sequence) != len(self.tool_metadata):
            raise ValueError("Circular dependency detected in tool prerequisites")

        return sequence


class MCPValidationMiddleware(MCPServer):
    """
    Middleware that wraps an MCP server with tool validation.

    This is a decorator-style wrapper that intercepts tool execution
    to add validation, sequencing, and pipelining. Implements MCPServer
    interface, so it's transparent to callers.

    Supports validator chains for flexible validation strategies.
    Multiple validators can be registered and will be tried in order.

    Pattern similar to ServerFactory - allows optional validation layer
    to be added to any MCPServer implementation without modification.

    Usage:
        >>> from axiompy.servers.mcp_validation import (
        ...     MCPValidationMiddleware, LLMToolValidator, RuleBasedToolValidator
        ... )
        >>>
        >>> base_server = MCPServerFactory.create(MCPServerType.OPENAI, settings)
        >>> validators = [LLMToolValidator(model="mistral"), RuleBasedToolValidator()]
        >>> server = MCPValidationMiddleware(base_server, validators, config)
        >>> server.register_tool("send_offer", ..., prerequisites=["get_profile"])
        >>> result = server.execute_tool("send_offer", session, customer_id="123")
    """

    def __init__(
        self,
        base_server: MCPServer,
        validators: Optional[List[MCPToolValidator]] = None,
        config: Optional[MCPPipelineConfig] = None,
    ):
        """
        Initialize validation middleware with validator chain.

        Args:
            base_server: The MCP server to wrap
            validators: List of validators to chain (first match wins)
                       If None, creates [LLMToolValidator(), RuleBasedToolValidator()]
            config: Optional configuration for validation behavior
        """
        # Don't call super().__init__() - we delegate to base_server
        self.base_server = base_server
        self.validators = validators or [LLMToolValidator(), RuleBasedToolValidator()]
        self.config = config or MCPPipelineConfig()
        self.validation_metadata: Dict[str, MCPToolReasoning] = {}
        logger.info(
            f"MCPValidationMiddleware wrapping server: {base_server.settings.name} "
            f"with {len(self.validators)} validators"
        )

    # Delegate standard MCPServer properties
    @property
    def settings(self) -> MCPServerSettings:
        """Get settings from wrapped server."""
        return self.base_server.settings

    @property
    def tools(self) -> Dict[str, MCPTool]:
        """Get tools from wrapped server."""
        return self.base_server.tools

    @property
    def sessions(self) -> Dict[str, MCPSession]:
        """Get sessions from wrapped server."""
        return self.base_server.sessions

    # Implement MCPServer interface, delegating to base_server
    def initialize(self) -> None:
        """Initialize wrapped server."""
        self.base_server.initialize()
        logger.info("MCPReasoningMiddleware initialized")

    def shutdown(self) -> None:
        """Shutdown wrapped server."""
        if hasattr(self.base_server, "shutdown"):
            self.base_server.shutdown()

    def register_tool(
        self,
        name: str,
        func: Callable,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        return_type: str = "any",
        tags: Optional[List[str]] = None,
        # Extended parameters for reasoning
        prerequisites: Optional[List[str]] = None,
        provides_data: Optional[List[str]] = None,
        requires_data: Optional[List[str]] = None,
        risk_level: RiskLevel = RiskLevel.LOW,
        cost: int = 1,
        requires_approval: bool = False,
    ) -> MCPTool:
        """
        Register a tool with optional reasoning metadata.

        Args:
            name: Tool name
            func: Callable implementation
            description: Tool description
            parameters: Parameter schema
            return_type: Return type description
            tags: Organization tags
            prerequisites: Tools that must run first
            provides_data: Data categories provided
            requires_data: Data categories required
            risk_level: RiskLevel classification
            cost: Execution cost (1-10)
            requires_approval: Needs human approval?

        Returns:
            Registered MCPTool
        """
        # Register with base server
        tool = self.base_server.register_tool(
            name, func, description, parameters, return_type, tags
        )

        # Register reasoning metadata if provided
        if self.config.enable_validation:
            for validator in self.validators:
                validator.register_tool(
                    name,
                    category=self._infer_category(risk_level),
                    prerequisites=prerequisites,
                    provides_data=provides_data,
                    requires_data=requires_data,
                    risk_level=risk_level,
                    cost=cost,
                    requires_approval=requires_approval,
                    description=description,
                )
            if self.validators:
                self.validation_metadata[name] = self.validators[0].tool_metadata.get(name)

        return tool

    def create_session(
        self, agent_name: str, metadata: Optional[Dict[str, Any]] = None
    ) -> MCPSession:
        """
        Create session with optional reasoning tracking.

        Args:
            agent_name: Name of agent
            metadata: Additional metadata

        Returns:
            MCPSession instance
        """
        session = self.base_server.create_session(agent_name, metadata)

        # Create reasoning session if tracking enabled
        if self.config.enable_session_tracking:
            for validator in self.validators:
                validator.create_session(session.session_id)

        return session

    def list_tools(self) -> List[MCPTool]:
        """List all registered tools."""
        return self.base_server.list_tools()

    def execute_tool(self, tool_name: str, session: MCPSession, **kwargs: Any) -> Any:
        """
        Execute tool with optional reasoning validation.

        Args:
            tool_name: Name of tool to execute
            session: Session context
            **kwargs: Tool parameters

        Returns:
            Tool execution result

        Raises:
            MCPToolError: If tool doesn't exist or validation fails
        """
        # If validation disabled, just delegate
        if not self.config.enable_validation:
            return self.base_server.execute_tool(tool_name, session, **kwargs)

        # Try validation through validator chain
        validation_result = None
        for validator in self.validators:
            if not hasattr(validator, "get_session"):
                continue

            val_session = validator.get_session(session.session_id)
            if not val_session:
                val_session = validator.create_session(session.session_id)

            # Try this validator
            result = validator.validate_tool(tool_name, kwargs, val_session)
            if result.is_ok():
                validation_result = result
                break
            # If this validator failed, continue to next one
            validation_result = result

        if validation_result and validation_result.is_err():
            error_msg = validation_result.get_error()
            logger.warning(f"Tool validation failed for {tool_name}: {error_msg}")
            raise Exception(f"Tool validation failed: {error_msg}")

        # Execute tool via base server
        try:
            result = self.base_server.execute_tool(tool_name, session, **kwargs)
            # Record success
            if self.config.enable_session_tracking:
                for validator in self.validators:
                    if hasattr(validator, "record_tool_call"):
                        validator.record_tool_call(
                            session.session_id, tool_name, kwargs, result=result
                        )
            return result
        except Exception as e:
            # Record failure
            if self.config.enable_session_tracking:
                for validator in self.validators:
                    if hasattr(validator, "record_tool_call"):
                        validator.record_tool_call(
                            session.session_id, tool_name, kwargs, error=str(e)
                        )
            raise

    def register_custom_validator(self, tool_name: str, validator: Callable) -> None:
        """Register custom validation logic for a tool."""
        for val in self.validators:
            if hasattr(val, "register_custom_validator"):
                val.register_custom_validator(tool_name, validator)

    def register_custom_sequencer(self, sequencer: Callable) -> None:
        """Register custom tool sequencing logic."""
        for validator in self.validators:
            if hasattr(validator, "register_custom_sequencer"):
                validator.register_custom_sequencer(sequencer)

    def suggest_tool_sequence(self, goal: str, session: MCPSession) -> Result[List[str], str]:
        """
        Suggest optimal tool sequence for a goal.

        Args:
            goal: Description of goal
            session: Session context

        Returns:
            Result[List[str], str] - suggested tool sequence or error
        """
        for validator in self.validators:
            if hasattr(validator, "get_session") and hasattr(validator, "suggest_tool_sequence"):
                reasoning_session = validator.get_session(session.session_id)
                if reasoning_session:
                    return validator.suggest_tool_sequence(goal, reasoning_session)

        return Err(f"No suitable validator found for sequencing in {session.session_id}")

    def estimate_cost(self, tool_sequence: List[str]) -> Result[int, str]:
        """Estimate cost of executing tool sequence."""
        for validator in self.validators:
            if hasattr(validator, "estimate_cost"):
                return validator.estimate_cost(tool_sequence)
        return Err("No suitable validator found for cost estimation")

    def get_session_summary(self, session: MCPSession) -> Result[Dict[str, Any], str]:
        """Get summary of session execution."""
        for validator in self.validators:
            if hasattr(validator, "get_session_summary"):
                return validator.get_session_summary(session.session_id)
        return Err("No suitable validator found for session summary")

    @staticmethod
    def _infer_category(risk_level: RiskLevel) -> ToolCategory:
        """Infer tool category from risk level."""
        if risk_level == RiskLevel.LOW:
            return ToolCategory.DATA
        elif risk_level == RiskLevel.MEDIUM:
            return ToolCategory.SERVICE
        else:
            return ToolCategory.ACTION
