# MCP Server Architecture & Design

Low-level design documentation for AxiomPy's MCP (Model Context Protocol) server implementation, including the reasoning layer.

## Table of Contents

1. [Core MCP Architecture](#core-mcp-architecture)
2. [Reasoning Layer Design](#reasoning-layer-design)
3. [Tool Lifecycle](#tool-lifecycle)
4. [Session Management](#session-management)
5. [Error Handling](#error-handling)
6. [Extension Points](#extension-points)
7. [Implementation Details](#implementation-details)

---

## Core MCP Architecture with Optional Reasoning Middleware

### Component Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                    MCP Server Layer                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           MCPServerFactory                              │   │
│  │  Creates platform-specific implementations              │   │
│  │  - OpenAIMCPServer                                      │   │
│  │  - GoogleADKMCPServer                                   │   │
│  │  - AnthropicMCPServer                                   │   │
│  └──────────────────┬──────────────────────────────────────┘   │
│                     │ creates                                    │
│                     ▼                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           MCPServer (Abstract Base)                     │   │
│  │  ├─ register_tool(name, func, desc, params)            │   │
│  │  ├─ execute_tool(name, session, kwargs)                │   │
│  │  ├─ create_session(agent_name, metadata)               │   │
│  │  ├─ list_tools() -> List[MCPTool]                       │   │
│  │  ├─ initialize() / shutdown()                           │   │
│  │  └─ _execute_impl(name, session, kwargs)               │   │
│  └──────────────────┬──────────────────────────────────────┘   │
│                     │                                            │
│           ┌─────────┴──────────┐                                │
│           │ (Optional Wrapping)│                                │
│           ▼                    ▼                                │
│  ┌──────────────────┐  ┌────────────────────────────────────┐  │
│  │ Use Directly     │  │ MCPValidationMiddleware            │  │
│  │ (No validation)  │  │ ├─ Wraps base MCPServer            │  │
│  │                  │  │ ├─ Implements MCPServer interface  │  │
│  │                  │  │ ├─ Transparent to callers          │  │
│  │                  │  │ └─ Delegates to validator chain    │  │
│  │                  │  │   • Validates prerequisites        │  │
│  │                  │  │   • Tracks data availability       │  │
│  │                  │  │   • Sequences tool calls           │  │
│  │                  │  │   • Estimates costs                │  │
│  │                  │  └────────────┬─────────────────────┘  │
│  │                  │               │ chains validators       │
│  │                  │               ▼                           │
│  │                  │  ┌────────────────────────────────────┐  │
│  │                  │  │  MCPToolValidator (Abstract)       │  │
│  │                  │  │  ├─ LLMToolValidator (Ollama/API)  │  │
│  │                  │  │  └─ RuleBasedToolValidator (Logic) │  │
│  │                  │  │     ├─ register_tool(metadata)    │  │
│  │                  │  │     ├─ validate_tool(...)         │  │
│  │                  │  │     ├─ suggest_tool_sequence(...) │  │
│  │                  │  │     ├─ estimate_cost(...)         │  │
│  │                  │  │     └─ record_tool_call(...)      │  │
│  │                  │  └────────────────────────────────────┘  │
│  └──────────────────┘                                           │
│                                                                  │
│  Usage Decision:                                                │
│  ├─ Simple tools → Use MCPServer directly                      │
│  ├─ Complex workflows → Wrap with MCPValidationMiddleware      │
│  └─ Disable features → MCPPipelineConfig(enable_validation=...) │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Key Types

#### MCPServerType Enum
```python
class MCPServerType(Enum):
    OPENAI = "openai"           # OpenAI GPT agents
    GOOGLE_ADK = "google_adk"   # Google Agent Development Kit
    ANTHROPIC = "anthropic"     # Anthropic Claude agents
```

#### MCPTool Dataclass
```python
@dataclass
class MCPTool:
    name: str                          # Unique tool identifier
    func: Callable                     # Implementation function
    description: str                   # Human-readable description
    parameters: Dict[str, Any]        # JSON Schema of parameters
    return_type: str = "any"          # Return type hint
    tags: List[str] = field(default_factory=list)  # Categorization
    created_at: datetime = field(default_factory=datetime.now)

    def execute(self, **kwargs) -> Any:
        """Execute tool with given parameters."""
        return self.func(**kwargs)
```

#### MCPSession Dataclass
```python
@dataclass
class MCPSession:
    session_id: str                    # UUID for this session
    agent_name: str                    # Name of agent using tools
    metadata: Dict[str, Any]           # Custom context
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    # Session lifecycle tracks all tool invocations
```

#### MCPServerSettings Dataclass
```python
@dataclass
class MCPServerSettings:
    name: str                          # Server name
    version: str = "1.0.0"            # Version
    description: str = ""              # Description
    tags: List[str] = field(default_factory=list)  # Categorization
    config: Dict[str, Any] = field(default_factory=dict)  # Platform-specific
    enable_logging: bool = True        # Enable debug logging
    max_sessions: Optional[int] = None # Limit concurrent sessions
```

---

## Reasoning Layer Design

### Architecture: Middleware + Validator Chain Pattern

The reasoning layer is implemented using **two key patterns**:

**1. Middleware Wrapper Pattern (MCPValidationMiddleware)**
- Implements MCPServer interface (transparency to callers)
- Wraps a base MCPServer without modifying it
- Intercepts execute_tool() and register_tool() calls
- Chains validators before delegating to base server
- Can be disabled or reconfigured per-instance

**2. Validator Chain Pattern (MCPToolValidator ABC)**
- Abstract base class for pluggable validators
- Multiple validators can be chained for validation
- First validator to pass wins (short-circuit evaluation)
- Each validator handles different concerns

This follows AxiomPy's pattern: optional, composable, decoupled.

### MCPToolValidator: Abstract Interface

The validator layer is abstraction-based, similar to ServerFactory pattern:

```python
class MCPToolValidator(ABC):
    """Abstract interface for tool validation strategies."""

    @abstractmethod
    def register_tool(name, category, prerequisites, ...) -> None: ...

    @abstractmethod
    def validate_tool(tool_name, parameters, session) -> Result[bool, str]: ...

    @abstractmethod
    def suggest_tool_sequence(goal, session) -> Result[List[str], str]: ...

    @abstractmethod
    def estimate_cost(tool_sequence) -> Result[int, str]: ...

    @abstractmethod
    def create_session(session_id) -> MCPReasoningSession: ...

    @abstractmethod
    def record_tool_call(session_id, tool_name, params, result, error) -> None: ...
```

This allows different validation implementations (rule-based, LLM-based, etc.) without changing the middleware.

### Validator Implementations: LLMToolValidator & RuleBasedToolValidator

**LLMToolValidator** - Uses Ollama or custom LLM backends
```
├─ Backend Options:
│  ├─ Ollama (local or remote)
│  ├─ Custom API endpoint
│  └─ On-disk GGUF models
├─ Smart Validation:
│  ├─ LLM reasoning for complex scenarios
│  └─ Fallback to rule-based if LLM unavailable
└─ Configuration:
   ├─ model: Model name
   ├─ model_path: Path to GGUF file
   ├─ backend_url: Server endpoint
   ├─ backend_type: "ollama" or "custom"
   └─ timeout: Request timeout
```

**RuleBasedToolValidator** - Deterministic validation
```
├─ Prerequisite Checking:
│  ├─ Topological sort (Kahn's algorithm)
│  ├─ Circular dependency detection
│  └─ Sequential ordering
├─ Data Flow Validation:
│  ├─ Track available data
│  ├─ Validate required data present
│  └─ Cost-based optimization
└─ Session Management:
   ├─ Per-session state tracking
   └─ Cost accumulation
```

### MCPToolReasoning: Tool Metadata

```python
@dataclass
class MCPToolReasoning:
    name: str                          # Tool identifier
    category: ToolCategory             # DATA, SERVICE, or ACTION
    prerequisites: List[str]           # Tools that must run first
    provides_data: List[str]           # Data this tool produces
    requires_data: List[str]           # Data this tool needs
    risk_level: RiskLevel              # LOW, MEDIUM, or HIGH
    cost: int                          # Execution cost (1-10)
    requires_approval: bool            # Human review required?
    description: str                   # Purpose and usage
```

### ToolCategory Classification

```python
ToolCategory.DATA      # Read-only operations
                       # Examples: query_database, fetch_api, get_config
                       # Risk: LOW
                       # State change: NO
                       # Requires approval: NO

ToolCategory.SERVICE   # Computations and transformations
                       # Examples: calculate_price, generate_recommendation
                       # Risk: MEDIUM (depends on implementation)
                       # State change: NO (but may access external services)
                       # Requires approval: Configurable

ToolCategory.ACTION    # Operations that modify state
                       # Examples: send_email, create_order, delete_record
                       # Risk: HIGH
                       # State change: YES
                       # Requires approval: YES (by default)
```

### RiskLevel Classification

```python
RiskLevel.LOW          # Safe to execute without review
                       # Examples: read operations, queries
                       # Default: requires_approval = False

RiskLevel.MEDIUM       # Should be reviewed for business logic
                       # Examples: calculations, recommendations
                       # Default: requires_approval = False
                       # Can be overridden per-tool

RiskLevel.HIGH         # Must be reviewed before execution
                       # Examples: mutations, deletions, external calls
                       # Default: requires_approval = True
```

### Validation Pipeline

```
Tool Call Request
    │
    ├─ 1. Check if tool registered
    │     └─ Err: Tool not found
    │
    ├─ 2. Check prerequisites met
    │     └─ Err: Prerequisite not completed
    │
    ├─ 3. Check data available
    │     └─ Err: Required data not available
    │
    ├─ 4. Check custom validator (if registered)
    │     └─ Err: Custom validation failed
    │
    └─ 5. Execute tool
         ├─ Success → Record result & update session state
         └─ Failure → Record error & mark as failed
```

### Sequencing Algorithm (Default SLM)

**Topological Sort by Dependencies**

```
Input: Goal (string) and Session context
Output: Optimal tool sequence List[str]

Algorithm:
1. Build dependency graph from prerequisites
2. Initialize in-degree count for each tool
3. Queue tools with no dependencies (in-degree = 0)
4. While queue not empty:
   a. Sort queue by cost (cheaper first) for same level
   b. Pop tool from queue
   c. Add to sequence
   d. Decrement in-degree for dependent tools
   e. Add newly available tools to queue
5. Return sequence if all tools processed, else error (circular dependency)

Time Complexity: O(V + E) where V = tools, E = dependencies
Space Complexity: O(V + E)
```

**Example Sequencing:**

```
Tools registered:
  A: prerequisites=[]
  B: prerequisites=[]
  C: prerequisites=[A]
  D: prerequisites=[B, C]
  E: prerequisites=[D]

In-degree:
  A: 0  ┐
  B: 0  ├─ Queue: [A, B]
  C: 1  │
  D: 2  │
  E: 1  ┘

Process A (cost 3):
  Sequence: [A]
  Add C to queue (A's only dependent)
  Queue: [B, C] → Sort by cost → Process cheaper first

Result sequence: [A, B, C, D, E] (or [B, A, C, D, E] if same cost)
```

---

## Tool Lifecycle

### Registration Phase

```
Tool Definition
    ↓
register_tool(name, func, description, parameters, ...)
    ├─ Create MCPTool instance
    ├─ Store in server's tools registry
    ├─ (Optional) Register reasoning metadata
    └─ Log registration event
```

### Session Creation Phase

```
Agent starts / request arrives
    ↓
create_session(agent_name, metadata)
    ├─ Generate UUID for session_id
    ├─ Create MCPSession instance
    ├─ (Optional) Create MCPReasoningSession
    └─ Return session object for tool calls
```

### Execution Phase

```
Agent calls tool: execute_tool(tool_name, session, **kwargs)
    ├─ 1. Look up tool in registry
    │     └─ If not found: raise MCPToolNotFound
    │
    ├─ 2. (Optional) Run reasoning validation
    │     ├─ Validate prerequisites
    │     ├─ Validate data availability
    │     ├─ Run custom validators
    │     └─ If invalid: return Err(reason)
    │
    ├─ 3. Execute tool function
    │     ├─ Call func(**kwargs)
    │     └─ Catch exceptions → wrap in Result
    │
    ├─ 4. (Optional) Record in reasoning session
    │     ├─ Store tool_call record
    │     ├─ Update data_available
    │     ├─ Add to cost total
    │     └─ Mark as success/failure
    │
    └─ 5. Return result to caller
         ├─ Ok(result) on success
         └─ Err(error) on failure
```

### Shutdown Phase

```
Agent finishes / session expires
    ├─ Get session summary (if reasoning enabled)
    ├─ Log execution stats
    ├─ Clean up resources
    ├─ (Optional) Archive session
    └─ Call server.shutdown()
```

---

## Session Management

### Session Lifecycle

```
Created (create_session)
    ↓
    ├─ tool_calls: []
    ├─ data_available: {}
    ├─ total_cost: 0
    ├─ failed_tools: set()
    └─ last_activity: now

Active (tool executions)
    ↓
Each execution:
    ├─ Append to tool_calls
    ├─ Update data_available
    ├─ Increment total_cost
    ├─ Add to failed_tools if error
    └─ Update last_activity

Completed (shutdown)
    ↓
    get_session_summary()
    ├─ total_calls
    ├─ successful_calls
    ├─ failed_calls
    ├─ total_cost
    ├─ data_available
    └─ failed_tools
```

### Data Tracking

```
Tool provides_data: ["customer", "preferences"]
    ├─ Declares: "I produce these data types"
    └─ Updates session.data_available when successful

Tool requires_data: ["customer"]
    ├─ Declares: "I need these data types"
    └─ Validation: Check session.data_available before execution
```

**Example:**

```
Register tool A:
  provides_data=["customer"]

Register tool B:
  requires_data=["customer"]

Session execution:
  1. Execute A → success
     data_available: {"customer"}

  2. Validate B:
     requires_data ["customer"] ⊆ data_available {"customer"} ✓

  3. Execute B
```

---

## Error Handling

### Result Type (Railway-Oriented Programming)

All reasoning operations return `Result[T, E]`:

```python
Result[bool, str]           # Validation result
Result[List[str], str]      # Sequencing result
Result[Any, str]            # Tool execution result
Result[Dict, str]           # Summary result
```

**Benefits:**
- Explicit error handling
- No exceptions for expected failures
- Chainable operations with `.then()`
- Type-safe error propagation

### Validation Errors

```python
# Tool not found
Err("Tool 'unknown_tool' not registered")

# Prerequisite not met
Err("Prerequisite 'get_customer_profile' not met for tool 'send_offer'")

# Data not available
Err("Required data 'customer' not available for tool 'send_offer'")

# Custom validation failed
Err("Discounts only for premium customers")

# Circular dependency
Err("Circular dependency detected in tool prerequisites")
```

### Execution Errors

```python
# Tool exception
Err("Tool execution failed: TypeError: unsupported operand type(s)")

# Session not found
Err("Session 'unknown_session' not found")

# Tool not found
Err("Tool 'unknown_tool' not found")
```

---

## Extension Points

### 1. Custom Validators

**Purpose:** Override default validation with business logic

```python
def custom_validator(tool_metadata: MCPToolReasoning,
                    parameters: Dict[str, Any]) -> Result[bool, str]:
    # Access tool metadata
    tool_name = tool_metadata.name
    risk = tool_metadata.risk_level

    # Implement custom logic
    if risk == RiskLevel.HIGH and parameters.get('amount') > 10000:
        return Err("High-risk operations over $10k require manager approval")

    return Ok(True)

reasoning.register_custom_validator("transfer_funds", custom_validator)
```

**When called:**
- After prerequisite and data validation
- Before tool execution
- Can access tool metadata and parameters

### 2. Custom Sequencers

**Purpose:** Replace topological sort with custom logic (ML, heuristics, etc.)

```python
def ml_sequencer(goal: str, session: MCPReasoningSession) -> Result[List[str], str]:
    # Use ML model to predict optimal sequence
    from my_ml_module import predict_sequence

    available_tools = list(reasoning.tool_metadata.keys())
    sequence = predict_sequence(goal, session.data_available, available_tools)

    return Ok(sequence)

reasoning.register_custom_sequencer(ml_sequencer)
```

**Called by:**
- `suggest_tool_sequence(goal, session)`

**Should return:**
- `Ok(sequence)` - valid tool sequence
- `Err(reason)` - if sequence can't be determined

### 3. Custom Tool Implementations

**For platform-specific logic:**

```python
class CustomMCPServer(MCPServer):
    def _execute_impl(self, tool_name: str, session: MCPSession, kwargs: Dict) -> Any:
        # Platform-specific execution
        # Called after standard validation

        if tool_name == "special_tool":
            # Custom logic for OpenAI, Google ADK, etc.
            return self.platform_specific_execute(tool_name, kwargs)

        return super()._execute_impl(tool_name, session, kwargs)
```

### 4. Middleware Wrapping

**Add cross-cutting concerns:**

```python
class AuthenticationMiddleware:
    def __init__(self, reasoning: SimpleMCPReasoning):
        self.reasoning = reasoning

    def validate_and_record(self, session_id, tool_name, parameters,
                           execute_func) -> Result[Any, str]:
        # Check authentication first
        if not self.is_authenticated(session_id):
            return Err("Not authenticated")

        # Then apply reasoning validation
        return MCPReasoningMiddleware(self.reasoning).validate_and_record(
            session_id, tool_name, parameters, execute_func
        )
```

---

## Implementation Details

### File Structure

```
axiompy/servers/
├── __init__.py                 # Public API exports
├── server.py                   # ServerFactory (Web servers)
├── mcp.py                      # MCP server implementations
├── mcp_reasoning.py            # Reasoning engine
├── README.md                   # User-facing documentation
└── ARCHITECTURE.md             # This file
```

### Key Classes in `mcp.py`

```python
# Enums
MCPServerType(Enum)            # Platform type selector
MCPExceptionType(Enum)         # Exception classification

# Data Classes
MCPTool(dataclass)             # Tool definition
MCPSession(dataclass)          # Session tracking
MCPServerSettings(dataclass)   # Configuration

# Abstract Base
MCPServer(ABC)                 # Interface definition
  ├─ initialize()
  ├─ shutdown()
  ├─ register_tool()
  ├─ execute_tool()
  ├─ create_session()
  ├─ list_tools()
  └─ _execute_impl()  # For subclasses

# Implementations
OpenAIMCPServer(MCPServer)     # OpenAI adapter
GoogleADKMCPServer(MCPServer)  # Google ADK adapter
AnthropicMCPServer(MCPServer)  # Anthropic adapter

# Factory
MCPServerFactory               # Creation and registration
  ├─ create()
  ├─ register_server()
  └─ _servers (class-level registry)

# Exceptions
MCPToolNotFound(MCPException)
MCPSessionNotFound(MCPException)
MCPInvalidParameters(MCPException)
```

### Key Classes in `mcp_reasoning.py`

```python
# Enums
ToolCategory(Enum)             # DATA, SERVICE, ACTION
RiskLevel(Enum)                # LOW, MEDIUM, HIGH

# Data Classes
MCPToolReasoning(dataclass)    # Tool metadata for reasoning
MCPToolCall(dataclass)         # Recorded tool execution
MCPReasoningSession(dataclass) # Session state for reasoning

# Main Engine
SimpleMCPReasoning             # Reasoning logic
  ├─ register_tool()
  ├─ validate_tool()
  ├─ suggest_tool_sequence()
  ├─ estimate_cost()
  ├─ record_tool_call()
  ├─ register_custom_validator()
  ├─ register_custom_sequencer()
  └─ _topological_sort()  # Internal algorithm

# Middleware
MCPReasoningMiddleware         # Wraps server
  └─ validate_and_record()  # Entry point for validation
```

### Type Hints & Documentation

**100% Type Coverage:**
- All functions have parameter and return type hints
- All complex types documented with comments
- Result type used for explicit error handling

**100% Docstring Coverage:**
- Module docstrings explaining purpose
- Class docstrings with usage examples
- Method docstrings with parameters and returns

### Logging Strategy

Uses `LoggerFactory.create_logger(__name__)`:

```python
logger.debug("Tool registered: add")           # Low-level detail
logger.info("Registered tool reasoning: add")  # Important events
logger.warning("Circular dependency detected") # Potential issues
logger.error("Tool execution failed: ...")     # Failures
```

---

## Acme Use Case: Technical Deep Dive

### Problem: Multi-Platform Tool Duplication

```
Before MCP:

OpenAI Version (450 lines):
├─ get_customer_profile()         [OpenAI SDK]
├─ query_inventory()              [OpenAI SDK]
├─ get_recommendation()           [OpenAI SDK]
├─ apply_discount()               [OpenAI SDK]
└─ send_offer()                   [OpenAI SDK]

Google ADK Version (450 lines):
├─ get_customer_profile()         [Google ADK]
├─ query_inventory()              [Google ADK]
├─ get_recommendation()           [Google ADK]
├─ apply_discount()               [Google ADK]
└─ send_offer()                   [Google ADK]

Anthropic Version (450 lines):
├─ get_customer_profile()         [Anthropic SDK]
├─ query_inventory()              [Anthropic SDK]
├─ get_recommendation()           [Anthropic SDK]
├─ apply_discount()               [Anthropic SDK]
└─ send_offer()                   [Anthropic SDK]

Total: 1,350 lines of duplicated code
```

### Solution: AxiomPy MCP with Reasoning

```
After MCP (50 lines):

settings = MCPServerSettings(name="ExampleTools")
server = MCPServerFactory.create(MCPServerType.OPENAI, settings)

server.register_tool("get_customer_profile",
                    example_data.get_customer, "Get customer profile")
server.register_tool("query_inventory",
                    example_inventory.query, "Query product inventory")
server.register_tool("get_recommendation",
                    example_ml.recommend, "Get recommendation")
server.register_tool("apply_discount",
                    example_commerce.discount, "Apply discount")
server.register_tool("send_offer",
                    example_comms.send_offer, "Send offer to customer")

server.initialize()

# Switch to Google ADK: Just change MCPServerType.OPENAI to MCPServerType.GOOGLE_ADK
# No code changes needed for tool definitions!
```

**With Reasoning:**

```
# Register reasoning metadata
reasoning = SimpleMCPReasoning()

reasoning.register_tool("get_customer_profile",
    category=ToolCategory.DATA,
    provides_data=["customer"],
    cost=2
)

reasoning.register_tool("send_offer",
    category=ToolCategory.ACTION,
    prerequisites=["get_customer_profile"],
    requires_data=["customer"],
    risk_level=RiskLevel.HIGH,
    requires_approval=True
)

# Reasoning ensures:
# 1. Can't send offer without customer profile
# 2. High-risk operations are flagged
# 3. Approval required before sending
# 4. Complete audit trail of all operations
```

### Acme Data Tools

```
get_customer_profile
├─ Category: DATA
├─ Provides: customer (name, segment, preferences)
├─ Risk: LOW
└─ Usage: Get customer context before personalization

query_inventory
├─ Category: DATA
├─ Provides: inventory (product, stock, availability)
├─ Risk: LOW
└─ Usage: Check what's available for recommendation

get_recommendation
├─ Category: SERVICE
├─ Requires: customer (segment, preferences)
├─ Provides: recommendation (products, ranking)
├─ Risk: MEDIUM
└─ Usage: ML-powered product recommendation

apply_discount
├─ Category: SERVICE
├─ Requires: customer (loyalty tier, history)
├─ Provides: discount (percentage, max_amount)
├─ Risk: MEDIUM
└─ Usage: Calculate eligible discount

send_offer
├─ Category: ACTION
├─ Requires: recommendation, discount
├─ Risk: HIGH
├─ Requires Approval: YES
└─ Usage: Send personalized offer to customer
```

---

## Future Enhancements

1. **Distributed Tracing**: Integrate with OpenTelemetry
2. **Caching Layer**: Cache tool results based on parameters
3. **Rate Limiting**: Per-tool and per-session limits
4. **Analytics**: Track tool usage, performance metrics
5. **A/B Testing**: Compare different sequencing strategies
6. **ML Integration**: ML-based custom sequencers (included in examples)
