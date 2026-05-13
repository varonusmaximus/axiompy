# Server Examples

This folder contains comprehensive examples for both **Web Servers** (Flask/FastAPI) and **MCP Servers** (AI Agent Tools with intelligent validation).

## 📁 File Structure

```
examples/servers/
├── README.md                      # This file
├── Web Server Examples
│   ├── simple_server.py           # Minimal Flask/FastAPI setup
│   ├── server_usage.py            # Production patterns & best practices
│   └── server_testing.py          # Testing strategies with mocks
├── MCP Server Examples
│   ├── mcp_basic.py               # Simple MCP server setup
│   ├── mcp_advanced.py            # Advanced features & patterns
│   ├── mcp_service_examples.py    # MCP service patterns
│   ├── mcp_testing.py             # Testing MCP servers
│   └── mcp_validators_examples.py # Chainable validators & LLM reasoning
├── JSON-RPC Server Examples
│   └── jsonrpc_examples.py        # JSON-RPC 2.0 server (HTTP & stdio)
```

---

## 🎯 Quick Navigation

### New to AxiomPy Servers?
1. **Start here**: [`simple_server.py`](#simple-web-server) (5 min)
2. **Then try**: [`mcp_basic.py`](#mcp-basic-server) (10 min)
3. **Next**: [`server_usage.py`](#production-patterns) (20 min)

### Building with AI Agents?
1. **Start here**: [`mcp_basic.py`](#mcp-basic-server)
2. **Add validation**: [`mcp_validators_examples.py`](#chainable-validators--llm-reasoning) (most important!)
3. **Production ready**: [`mcp_advanced.py`](#mcp-advanced-server)

### Writing Tests?
- [`server_testing.py`](#testing-mcp-servers) - Mock servers without HTTP
- [`mcp_testing.py`](#testing-mcp-servers) - Integration testing patterns

---

## 📖 Web Server Examples

### Simple Web Server

**File**: `simple_server.py`  
**Time**: 5 minutes  
**What you'll learn**: Basic Flask/FastAPI setup with AxiomPy abstraction

```python
from axiompy.servers import ServerFactory, ServerType, ServerSettings

# Create Flask server
settings = ServerSettings(host="127.0.0.1", port=5000)
server = ServerFactory.create(ServerType.FLASK, settings)

@server.route("/")
def home():
    return {"message": "Hello, World!"}

server.run()
```

**Key points**:
- ✅ Framework agnostic - same code works with FASTAPI
- ✅ Decorator syntax similar to Flask
- ✅ Automatic JSON conversion
- ✅ Clean, minimal setup

**Run it**:
```bash
cd examples/servers
python simple_server.py
# Visit http://localhost:5000
```

---

### Production Patterns

**File**: `server_usage.py`  
**Time**: 20 minutes  
**What you'll learn**: Production-ready patterns, middleware, services

Contains:
- ✅ Dependency injection patterns
- ✅ Service layer architecture
- ✅ Middleware setup
- ✅ Error handling
- ✅ Framework switching examples
- ✅ Database integration

**Key patterns**:
```python
# Pattern 1: Service Layer
class UserService:
    def __init__(self, server: Server, db: Database):
        self.server = server
        self.db = db
        self._setup_routes()

# Pattern 2: Framework Switching
for framework in [ServerType.FLASK, ServerType.FASTAPI]:
    server = ServerFactory.create(framework, settings)
    UserService(server, db)
    # Same code, different framework!

# Pattern 3: Middleware
server.add_middleware(logging_middleware)
server.add_middleware(error_handler_middleware)
```

**Run it**:
```bash
python server_usage.py
```

---

### Testing Strategies

**File**: `server_testing.py`  
**Time**: 15 minutes  
**What you'll learn**: Testing without HTTP overhead, mocking servers

Contains:
- ✅ MockServer for unit tests
- ✅ Flask TestClient pattern
- ✅ FastAPI TestClient pattern
- ✅ Service isolation patterns
- ✅ Database mocking

**Key pattern**:
```python
# No HTTP overhead, fast tests
mock_server = MockServer()
service = UserService(mock_server, mock_db)

# Test business logic directly
result = mock_server.call_route("/users", "GET")
assert "users" in result
```

**Run it**:
```bash
pytest server_testing.py -v
```

---

## 🤖 MCP Server Examples

### MCP Basic Server

**File**: `mcp_basic.py`  
**Time**: 10 minutes  
**What you'll learn**: Basic MCP tool registration and execution

```python
from axiompy.servers import MCPServerFactory, MCPServerType, MCPServerSettings

# Create MCP server
settings = MCPServerSettings(name="MathTools")
server = MCPServerFactory.create(MCPServerType.OPENAI, settings)

# Register tools
server.register_tool(
    "add",
    lambda a, b: a + b,
    "Add two numbers",
    parameters={"a": {"type": "int"}, "b": {"type": "int"}},
    return_type="int"
)

# Execute
server.initialize()
session = server.create_session("my_agent")
result = server.execute_tool("add", session, a=5, b=3)  # 8
```

**Key concepts**:
- ✅ Tools are just Python functions
- ✅ Metadata helps AI agents understand purpose
- ✅ Sessions track execution context
- ✅ Framework-agnostic (works with OpenAI, Google, Anthropic)

**Run it**:
```bash
python mcp_basic.py
```

---

### MCP Advanced Server

**File**: `mcp_advanced.py`  
**Time**: 30 minutes  
**What you'll learn**: Complex workflows, sessions, error handling

Contains:
- ✅ Multi-step tool workflows
- ✅ Session state management
- ✅ Complex error handling
- ✅ Real-world service integration
- ✅ Tool discovery patterns
- ✅ Advanced metadata

**Key patterns**:
```python
# Pattern 1: Workflow with prerequisites
server.register_tool(
    "send_offer",
    send_offer_impl,
    prerequisites=["get_customer", "check_inventory"]
)

# Pattern 2: Session tracking
session = server.create_session("agent_001")
result1 = server.execute_tool("get_customer", session, id=123)
result2 = server.execute_tool("send_offer", session, ...)

# Pattern 3: Tool discovery
tools = server.list_tools()
for tool in tools:
    print(f"{tool['name']}: {tool['description']}")
```

**Run it**:
```bash
python mcp_advanced.py
```

---

### Chainable Validators & LLM Reasoning

**File**: `mcp_validators_examples.py`  
**Time**: 45 minutes  
**What you'll learn**: THE MOST IMPORTANT PATTERN for enterprise MCP servers

This is the **core pattern** for intelligent tool validation with optional LLM support.

#### What Makes This Special

```
Tool Request
    ↓
Validator Chain (first match wins):
  1. LLMToolValidator - AI reasoning about dependencies
  2. RuleBasedToolValidator - Fast prerequisite checking
  3. Custom Validators - Business logic overrides
    ↓
Decision: Allow or Block
```

#### 5 Production-Ready Examples

**Example 1: Infrastructure Validation (DevOps)**
```python
# Purpose: DevOps automation with safety checks
# Use case: Kubernetes deployments, infrastructure as code
# Validators: [LLMToolValidator(), RuleBasedToolValidator()]

# Tools: authenticate_cluster → deploy_service → monitor
# Result: Intelligent validation with LLM support + fast fallback

from axiompy.servers.mcp_reasoning import (
    MCPValidationMiddleware,
    LLMToolValidator,
    RuleBasedToolValidator
)

validators = [
    LLMToolValidator(model="mistral"),
    RuleBasedToolValidator()
]
middleware = MCPValidationMiddleware(base_server, validators)
```

**When to use**: DevOps automation, infrastructure tools, safety gates

---

**Example 2: Fast Path (Internal Services)**
```python
# Purpose: High-frequency operations (<1ms latency)
# Use case: Real-time monitoring, auto-scaling, internal services
# Validators: [RuleBasedToolValidator()] (no LLM)

# Result: <1ms validation, no external calls, deterministic

validators = [RuleBasedToolValidator()]
middleware = MCPValidationMiddleware(base_server, validators)
```

**When to use**: Internal service calls, real-time operations, latency-critical paths

---

**Example 3: Distributed Enterprise Deployment**
```python
# Purpose: Multi-region with shared LLM backend
# Use case: Large enterprises, cost optimization, network restrictions
# Shows: 4 deployment topologies

# 1. Local development (auto-detect)
LLMToolValidator(model="mistral")

# 2. Remote GPU server (shared)
LLMToolValidator(
    model="llama2",
    backend_url="http://inference-gpu.internal:11434"
)

# 3. On-disk GGUF (air-gapped networks)
LLMToolValidator(
    model_path="/models/production.gguf",
    backend_url="http://localhost:11434"
)

# 4. Custom LLM API (proprietary)
LLMToolValidator(
    model="enterprise-model",
    backend_url="http://internal-llm.corp.com",
    backend_type="custom"
)
```

**When to use**: Multi-region deployments, shared backends, network-restricted environments

---

**Example 4: Graceful Degradation (SLA Compliance)**
```python
# Purpose: Production resilience when LLM fails
# Use case: SLA requirements (99.9%+), production stability
# Validators: [LLMToolValidator(), RuleBasedToolValidator()]

# Scenarios:
# - Normal: LLM validates (~500ms) → full intelligence
# - LLM Down: Falls to rules (~1ms) → reduced but operational
# - Result: SLA maintained

validators = [
    LLMToolValidator(model="mistral"),
    RuleBasedToolValidator()
]
middleware = MCPValidationMiddleware(base_server, validators)
```

**When to use**: Production systems, enterprise reliability, always-operational requirements

---

**Example 5: Custom Policy Validators**
```python
# Purpose: Governance, compliance, approval workflows
# Use case: Regulated industries, approval gates, audit requirements
# Shows: How to build custom validators

class ApprovalPolicyValidator(MCPToolValidator):
    def validate_tool(self, tool_name, params, session, tool_metadata):
        if tool_metadata.risk_level == RiskLevel.HIGH:
            if not session.metadata.get("approved"):
                return Err("Requires executive approval")
        return Ok(True)

validators = [
    ApprovalPolicyValidator(),     # Policies first
    LLMToolValidator(),            # Intelligence second
    RuleBasedToolValidator()       # Speed guarantee third
]
middleware = MCPValidationMiddleware(base_server, validators)
```

**When to use**: Enterprise policies, compliance, approval workflows, governance

---

#### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│ Agent calls: execute_tool("send_offer", session, ...)  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ MCPValidationMiddleware      │
        │                              │
        │ Validator Chain:             │
        │  1. Try LLMToolValidator     │
        │     ↓ if Ok(True) → EXECUTE  │
        │     ↓ if Err → next          │
        │  2. Try RuleBasedValidator   │
        │     ↓ if Ok(True) → EXECUTE  │
        │     ↓ if Err → next          │
        │  3. Try CustomValidator      │
        │     ↓ if Ok(True) → EXECUTE  │
        │     ↓ if Err → BLOCK         │
        └──────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
   EXECUTE TOOL            BLOCK WITH ERROR
   (Send offer)            (Prerequisites not met)
```

#### Key Concepts Illustrated

**1. Validator Chaining**
```
First validator to return Ok(True) wins
↓
Enables graceful degradation
↓
Enables flexible policies
```

**2. Performance Tuning**
```
LLM: ~500ms, highly intelligent
Rules: <1ms, deterministic, guaranteed
Custom: <1ms, business logic
```

**3. Enterprise Patterns**
```
Policies first (custom)
Intelligence second (LLM)
Speed guarantee third (rules)
```

**4. Resilience**
```
LLM optional, never required
Always falls back
Production-ready by design
```

#### Optional: LLM Setup

LLM reasoning is **optional** - validators work with or without Ollama!

```bash
# To enable LLM (optional):
brew install ollama
ollama pull mistral
ollama serve  # Keep running in another terminal
```

Then use:
```python
LLMToolValidator(model="mistral")  # Auto-detects Ollama
```

If Ollama not available, gracefully falls back to rules.

#### Configuration Examples

```python
# Auto-chain (recommended for most cases)
middleware = MCPValidationMiddleware(base_server)
# Gets: [LLMToolValidator(), RuleBasedToolValidator()]

# Custom chain (for specific requirements)
validators = [
    LLMToolValidator(model="llama2"),
    RuleBasedToolValidator()
]
middleware = MCPValidationMiddleware(base_server, validators)

# Rules only (maximum performance)
validators = [RuleBasedToolValidator()]
middleware = MCPValidationMiddleware(base_server, validators)

# Custom policy first
validators = [
    ApprovalPolicyValidator(),
    LLMToolValidator(),
    RuleBasedToolValidator()
]
middleware = MCPValidationMiddleware(base_server, validators)
```

**Run examples**:
```bash
python mcp_validators_examples.py
```

---

### Testing MCP Servers

**File**: `mcp_testing.py`  
**Time**: 20 minutes  
**What you'll learn**: Testing MCP servers with mocks and integration patterns

Contains:
- ✅ MockMCPServer for unit tests
- ✅ Integration testing patterns
- ✅ Tool mocking strategies
- ✅ Session testing
- ✅ Error handling in tests

**Key pattern**:
```python
# No SDK dependencies needed
mock_server = MockMCPServer(settings)
mock_server.register_tool("add", lambda a, b: a + b, "Add")

session = mock_server.create_session("test_agent")
result = mock_server.execute_tool("add", session, a=2, b=3)
assert result == 5
```

**Run it**:
```bash
pytest mcp_testing.py -v
```

---

## 🚀 Common Workflows

### Scenario 1: Build a Simple Web API

1. Start with [`simple_server.py`](simple_server.py)
2. Add routes with [`server_usage.py`](server_usage.py) patterns
3. Test with [`server_testing.py`](server_testing.py)

```bash
python simple_server.py
# Visit http://localhost:5000/api/users
```

### Scenario 2: Build an AI Agent with MCP Tools

1. Start with [`mcp_basic.py`](mcp_basic.py) - basic setup
2. **Add validation**: [`mcp_validators_examples.py`](mcp_validators_examples.py) - MOST IMPORTANT
3. Build complex workflows with [`mcp_advanced.py`](mcp_advanced.py)
4. Test with [`mcp_testing.py`](mcp_testing.py)

```bash
# Example 1: DevOps with intelligent validation
python mcp_validators_examples.py

# Then run your MCP server
python mcp_basic.py
```

### Scenario 3: Production Deployment

1. **Web servers**: Use [`server_usage.py`](server_usage.py) patterns
2. **MCP agents**: Use [`mcp_validators_examples.py`](mcp_validators_examples.py) + [`mcp_advanced.py`](mcp_advanced.py)
3. **Testing**: Use [`server_testing.py`](server_testing.py) + [`mcp_testing.py`](mcp_testing.py)

```bash
# Deploy with intelligent validation
python mcp_advanced.py
# Tools automatically validated through validator chain
```

---

## 📚 Learning Path by Role

### Web Developer (REST APIs)
1. `simple_server.py` (5 min) - Basic setup
2. `server_usage.py` (20 min) - Production patterns
3. `server_testing.py` (15 min) - Testing

**Total**: 40 minutes to production-ready REST API

### AI Engineer (Agent Tools)
1. `mcp_basic.py` (10 min) - Basic MCP tools
2. `mcp_validators_examples.py` (45 min) - **CRITICAL** validation patterns
3. `mcp_advanced.py` (30 min) - Complex workflows
4. `mcp_testing.py` (20 min) - Testing

**Total**: 105 minutes to production MCP agent

### DevOps Engineer (Infrastructure as Code)
1. `mcp_validators_examples.py` - Example 1 (infrastructure validation)
2. `mcp_advanced.py` - Integration patterns
3. `server_usage.py` - Production patterns

**Total**: 60 minutes to production infrastructure agent

### QA Engineer (Testing)
1. `server_testing.py` (15 min) - Web server testing
2. `mcp_testing.py` (20 min) - MCP testing

**Total**: 35 minutes to comprehensive testing

---

## 🔧 Installation & Setup

### Prerequisites
```bash
python 3.8+
pip install axiompy
```

### Optional: LLM Support (for intelligent validation)
```bash
# For MacOS
brew install ollama
ollama pull mistral

# For Linux/Windows - download from https://ollama.ai
ollama serve
```

### Run Examples

```bash
# Web servers
cd examples/servers
python simple_server.py
python server_usage.py
python server_testing.py

# MCP servers
python mcp_basic.py
python mcp_advanced.py
python mcp_validators_examples.py  # Most important!
python mcp_testing.py

# Run with pytest
pytest server_testing.py -v
pytest mcp_testing.py -v
```

---

## ✨ Key Takeaways

### Web Servers
- ✅ Framework agnostic (Flask ↔ FastAPI)
- ✅ Dependency injection friendly
- ✅ Easy to test with mocks
- ✅ Production-ready patterns included

### MCP Servers (AI Agents)
- ✅ Tool registration is simple (functions + metadata)
- ✅ Framework-agnostic (OpenAI ↔ Google ↔ Anthropic)
- ✅ **Validator chaining** is the CORE pattern
- ✅ Optional LLM support (Ollama)
- ✅ Graceful degradation built-in
- ✅ Production-ready error handling

### Validators (Most Important!)
- ✅ Chain multiple validation strategies
- ✅ LLM for intelligence (~500ms)
- ✅ Rules for speed (<1ms)
- ✅ Custom for governance
- ✅ First match wins
- ✅ Always has fallback

---

## 📖 Next Steps

1. **Pick a scenario** from "Common Workflows"
2. **Run the relevant examples**
3. **Adapt the code** to your use case
4. **Read the docstrings** in each example
5. **Check `/axiompy/servers/README.md`** for detailed API docs

---

## 🤝 Need Help?

- 📖 See [`axiompy/servers/README.md`](../../axiompy/servers/README.md) for API reference
- 🏗️ See [`axiompy/servers/ARCHITECTURE.md`](../../axiompy/servers/ARCHITECTURE.md) for deep dive
- 💬 Check docstrings in example files for explanations
- 🔍 Look at test files for usage patterns

---

## 📝 File Checklist

- ✅ `simple_server.py` - Minimal setup (5 min)
- ✅ `server_usage.py` - Production patterns (20 min)
- ✅ `server_testing.py` - Testing strategies (15 min)
- ✅ `mcp_basic.py` - MCP basics (10 min)
- ✅ `mcp_advanced.py` - Advanced workflows (30 min)
- ✅ `mcp_service_examples.py` - MCP service patterns (15 min)
- ✅ `mcp_validators_examples.py` - Validator chaining **[CORE PATTERN]** (45 min)
- ✅ `mcp_testing.py` - MCP testing (20 min)
- ✅ `jsonrpc_examples.py` - JSON-RPC 2.0 server (HTTP & stdio) (20 min)
- ✅ `README.md` - This file

**Total Learning Time**: ~2.5 hours to full proficiency

---

**Last Updated:** 2025-12-03

