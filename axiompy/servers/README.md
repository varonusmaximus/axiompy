# Server Abstraction Layer

Unified interfaces for building:
1. **Web Applications** with Flask or FastAPI
2. **AI Agent Tools** with MCP (Model Context Protocol) servers
3. **JSON-RPC 2.0 Servers** for MCP client integration (Claude Desktop, Cursor)

Write your application code once and switch between frameworks or AI platforms without changes.

## Table of Contents

### MCP Servers (AI Agents)
- [MCP Quick Start](#mcp-quick-start)
- [MCP Concepts](#mcp-concepts)
- [MCP API Reference](#mcp-api-reference)
- [MCP Examples](#mcp-examples)

### JSON-RPC Servers (MCP Protocol)
- [JSON-RPC Quick Start](#json-rpc-quick-start)
- [JSON-RPC Transports](#json-rpc-transports)
- [JSON-RPC API Reference](#json-rpc-api-reference)
- [JSON-RPC Examples](#json-rpc-examples)

### Web Servers (REST APIs)
- [Web Server Quick Start](#web-server-quick-start)
- [Why Use Web Server Abstraction?](#why-use-web-server-abstraction)
- [Installation](#installation)
- [Web Server Concepts](#web-server-concepts)
- [Web Server API Reference](#web-server-api-reference)
- [Flask Examples](#flask-examples)
- [FastAPI Examples](#fastapi-examples)
- [Testing](#testing)
- [Advanced Usage](#advanced-usage)
- [Best Practices](#best-practices)

---

## Why MCP Matters: Before & After

### Before MCP: Static AI
```python
# Old way: AI can only generate text
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "What's my account balance?"}]
)
# Response: "I don't have access to your account information.
#           Please log in to your bank's website..."
```

### After MCP: Agent AI That Takes Action
```python
# New way: AI can call tools and take real action
server.register_tool("get_balance", check_account_balance, "Check account balance")
session = server.create_session("customer_service_agent")
result = server.execute_tool("get_balance", session, account_id="12345")
# Response: "Your current balance is $5,432.10"
# ✅ Actual action taken, real data retrieved
```

---

## MCP Quick Start

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

# Initialize
server.initialize()

# Create session and execute tool
session = server.create_session("my_agent")
result = server.execute_tool("add", session, a=5, b=3)
print(result)  # 8

# Cleanup
server.shutdown()
```

**Switch to Google ADK or Anthropic?** Just change `MCPServerType.OPENAI` to another platform. All tool registration and execution code stays the same!

---

## MCP Architecture Overview

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AI AGENT LAYER                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │   OpenAI     │  │  Google ADK  │  │  Anthropic   │                 │
│  │   GPT-4      │  │   Gemini     │  │   Claude     │                 │
│  └──────────────┘  └──────────────┘  └──────────────┘                 │
│         │                  │                  │                        │
│         └──────────────────┼──────────────────┘                        │
│                            │ (Unified MCP Protocol)                    │
├─────────────────────────────────────────────────────────────────────────┤
│                    AXIOMPY MCP SERVER LAYER                              │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  MCPServerFactory: Create servers for any AI platform           │  │
│  │  ┌──────────────────────────────────────────────────────────┐   │  │
│  │  │  MCPServer: Unified tool management & execution          │   │  │
│  │  │  • Tool registry & validation                            │   │  │
│  │  │  • Session management & tracking                         │   │  │
│  │  │  • Error handling & logging                              │   │  │
│  │  └──────────────────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                            │                                            │
│  ┌───────────────┬─────────┼─────────┬──────────────┐                 │
│  │               │         │         │              │                 │
│  ▼               ▼         ▼         ▼              ▼                 │
│ Tools      Sessions   Logging    Error Handling   Metadata            │
└─────────────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   DATA TOOLS     │ │ SERVICE TOOLS    │ │ ACTION TOOLS     │
│ ─────────────    │ │ ────────────────  │ │ ──────────────── │
│ • Query DB       │ │ • API Calls      │ │ • Send Email     │
│ • Cache Data     │ │ • Transformations│ │ • Update Systems │
│ • Aggregate      │ │ • Validations    │ │ • Triggers       │
│ • Search         │ │ • Enrichment     │ │ • Notifications  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  UNDERLYING      │ │   BUSINESS       │ │    EXTERNAL      │
│  DATA SYSTEMS    │ │   SERVICES       │ │    SYSTEMS       │
│ ─────────────────│ │ ──────────────── │ │ ─────────────────│
│ • Databases      │ │ • ML Models      │ │ • Email Service  │
│ • Data Lakes     │ │ • Engines        │ │ • Slack/Teams    │
│ • Cache Layer    │ │ • Processors     │ │ • External APIs  │
│ • Search Index   │ │ • Rules Engine   │ │ • Webhooks       │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

### Data Flow: How Agents Use MCP Tools

```
User Query to Agent
        │
        ▼
┌─────────────────────────────────────────────┐
│ Agent: "Find products matching customer's   │
│ purchase history and suggest best option"   │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│ Agent calls MCP Server tool:                │
│ query_purchase_history(customer_id=12345)   │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│ AxiomPy MCP Server:                          │
│ ✓ Validates request                         │
│ ✓ Creates session context                   │
│ ✓ Logs execution                            │
│ ✓ Executes tool                             │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│ Data Tool: Queries customer database        │
│ SELECT * FROM purchases WHERE customer=X    │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│ Returns structured data:                    │
│ {products: [...], patterns: {...}}          │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│ Agent uses data to reason:                  │
│ "Customer bought athletic wear → recommend  │
│  similar products with seasonal discount"   │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│ Agent calls more tools as needed:           │
│ get_inventory(product_ids=[...])            │
│ check_discount_rules(customer_tier=premium) │
│ send_recommendation_email(customer_id=...)  │
└─────────────────────────────────────────────┘
```

## MCP Concepts

### What is MCP?

**Model Context Protocol (MCP)** is an open standard that enables AI agents and language models to safely call external tools, access data sources, and interact with the broader world. It's a standardized way to give AI systems capabilities beyond their training data.

Think of it like this:
- **Without MCP**: AI models can only generate text based on their training
- **With MCP**: AI models can call your tools to perform real actions (query databases, call APIs, run calculations, etc.)

#### Why MCP Matters

MCP solves a critical problem in AI development: **how do you safely give language models the ability to take actions?**

✅ **Safety**: Tools are explicitly registered and validated
✅ **Control**: You decide exactly what capabilities agents have
✅ **Integration**: Connect agents to any system or API
✅ **Standardization**: Works across different AI platforms
✅ **Transparency**: Agents must explicitly call tools (no hidden behavior)

#### Real-World Analogy

Imagine you're building a helpful assistant:
- Without MCP: The assistant can only talk to you, can't actually help beyond advice
- With MCP: The assistant can look up real data, send emails, execute code, update databases

AxiomPy's MCP abstraction lets you build the same tool once and use it with OpenAI, Google, Anthropic, or any other platform.

### Supported Platforms

#### **OpenAI** - Industry Leading AI Platform
- **Framework**: AgentKit & GPT-4 Agents
- **Use Cases**: Enterprise agents, autonomous workflows, reasoning tasks
- **Resources**:
  - 🔗 [OpenAI AgentKit Documentation](https://platform.openai.com/docs/agents)
  - 🔗 [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
  - 📺 [Video: Building Agents with OpenAI](https://www.youtube.com/results?search_query=openai+agents+tutorial)

#### **Google Agent Development Kit (ADK)** - Open-Source & Flexible
- **Framework**: Modular agent framework with multi-language support
- **Use Cases**: Custom workflows, specialized agents, research/experimentation
- **Resources**:
  - 🔗 [Google ADK GitHub](https://github.com/google/adk)
  - 🔗 [ADK Documentation](https://google.github.io/adk-docs/)
  - 🔗 [Getting Started Guide](https://google.github.io/adk-docs/guides/getting-started)
  - 📺 [Google I/O 2024: Agent Development](https://www.youtube.com/results?search_query=google+adk+agents)

#### **Anthropic Claude** - Reasoning & Context
- **Framework**: Claude API with native tool use
- **Use Cases**: Complex reasoning, multi-step tasks, high-context applications
- **Resources**:
  - 🔗 [Anthropic Claude Documentation](https://docs.anthropic.com/)
  - 🔗 [Tool Use Guide](https://docs.anthropic.com/claude/reference/tool-use)
  - 🔗 [Claude API Reference](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
  - 📺 [Video: Claude Tool Use Tutorial](https://www.youtube.com/results?search_query=anthropic+claude+tool+use)

### Industry Adoption & Trends

MCP is becoming the **de facto standard** for AI agent tool integration:

- 🚀 **Rapid Growth**: All major AI platforms now support MCP
- 🏢 **Enterprise Use**: Banking, healthcare, logistics adopting MCP agents
- 💡 **Innovation Hub**: Open-source community driving new capabilities
- 📈 **Market Maturity**: Moving from research to production deployments

---

## MCP Use Cases & Applications

### 🚚 Logistics & Supply Chain

AI agents for supply chain optimization and inventory management:

- **Shipment Tracking**: Real-time location, ETA, delivery status
- **Route Optimization**: Dynamic routing, driver assignment, cost optimization
- **Inventory Coordination**: Warehouse management, stock transfers, forecasting
- **Vendor Management**: Purchase orders, payment processing, performance tracking

**Example**: Logistics agent that tracks shipments, optimizes delivery routes, and manages inventory

### 🏢 Enterprise Software

AI agents for business process automation and intelligent workflows:

- **Data Integration**: Query databases, run reports, aggregate from multiple systems
- **Workflow Automation**: Document approval, notifications, task routing
- **Knowledge Management**: Search documentation, find experts, retrieve best practices
- **Compliance & Audit**: Generate reports, verify policies, maintain audit trails
- **Business Intelligence**: Access analytics, generate insights, create dashboards

**Example**: Enterprise assistant that searches documents, generates reports, and automates workflows

### 💻 Development & DevOps

AI agents for developer productivity and operational automation:

- **Code Management**: Search repositories, retrieve files, analyze code quality
- **Deployment Automation**: Check deployment status, deploy changes, rollback if needed
- **Infrastructure Monitoring**: Query metrics, check logs, alert on anomalies
- **Documentation**: Generate docs, find examples, maintain wikis
- **CI/CD Integration**: Trigger pipelines, check build status, analyze test results

**Example**: DevOps agent that deploys code, monitors health, and manages infrastructure

---

## Fluent API for Tool Registration

MCPServer supports fluent API chaining for elegant, readable tool registration:

### Traditional Approach
```python
server.register_tool("add", add_func, "Add two numbers")
server.register_tool("multiply", multiply_func, "Multiply numbers")
server.register_tool("divide", divide_func, "Divide numbers")
server.initialize()
```

### Fluent API Approach
```python
(server
    .register_tool("add", add_func, "Add two numbers")
    .register_tool("multiply", multiply_func, "Multiply numbers")
    .register_tool("divide", divide_func, "Divide numbers")
    .initialize())
```

**Benefits:**
- ✅ Cleaner, more readable code
- ✅ Less repetition of `server.`
- ✅ Single expression instead of multiple statements
- ✅ Maintains all functionality and validation

---

## Why Use AxiomPy's MCP Abstraction?

### Problem: Framework Lock-In

```python
# Different code for each platform - maintenance nightmare
if using_openai:
    from openai_specific import setup_tools
    openai_tools = [...]
    # 150 lines of OpenAI-specific code

elif using_google:
    from google_specific import setup_tools
    google_tools = [...]
    # 150 lines of Google-specific code

elif using_anthropic:
    from anthropic_specific import setup_tools
    anthropic_tools = [...]
    # 150 lines of Anthropic-specific code

# Total: 450+ lines of duplicated logic
# Problem: Every change needs to be made 3 times!
```

### With AxiomPy MCP

```python
from axiompy.servers import MCPServerFactory, MCPServerType, MCPServerSettings

# Define Acme's tools ONCE
def setup_example_tools(server):
    """Acme's agent tools - defined once, works everywhere"""

    # Data access tools
    server.register_tool(
        "query_inventory",
        query_product_inventory,
        "Query product availability by SKU, location, size",
        tags=["data", "inventory"]
    )

    server.register_tool(
        "get_customer_profile",
        get_customer_data,
        "Get customer purchase history and preferences",
        tags=["data", "customer"]
    )

    # Service tools
    server.register_tool(
        "get_recommendation",
        recommendation_service,
        "Get personalized product recommendations",
        tags=["service", "ai"]
    )

    server.register_tool(
        "optimize_pricing",
        pricing_engine,
        "Optimize pricing based on demand and inventory",
        tags=["service", "pricing"]
    )

    # Action tools
    server.register_tool(
        "send_offer",
        send_customer_offer,
        "Send personalized offer to customer",
        tags=["action", "engagement"]
    )

# Use with ANY platform - same code!
for platform in [MCPServerType.OPENAI, MCPServerType.GOOGLE_ADK, MCPServerType.ANTHROPIC]:
    settings = MCPServerSettings(
        name="Acme Agent Platform",
        version="1.0.0",
        description="Acme's AI agent with access to inventory, customer, and service data"
    )
    server = MCPServerFactory.create(platform, settings)
    setup_example_tools(server)  # ← Same tool setup!
    server.initialize()

# Total: ~50 lines of code, NOT 450!
# Problem solved: Change tools once, works everywhere!
```

### Acme Agent Workflow Example

```
Customer on Acme App:
"Show me running shoes that match my style and current inventory"

        │
        ▼
┌─────────────────────────────────────────────┐
│ Acme AI Agent (Powered by MCP)              │
│ "I'll check your profile and find matches"  │
└─────────────────────────────────────────────┘
        │
        ├─→ Call MCP Tool: get_customer_profile(customer_id)
        │   └─→ Acme Data Lake: Customer history, preferences
        │
        ├─→ Call MCP Tool: query_inventory(style="running", sizes=[...])
        │   └─→ Acme Inventory System: Real-time stock levels
        │
        ├─→ Call MCP Tool: get_recommendation(profile=[...], inventory=[...])
        │   └─→ Acme Recommendation Engine: ML-powered suggestions
        │
        └─→ Call MCP Tool: send_offer(customer_id, recommendations)
            └─→ Acme Customer Platform: Personalized offers

        ▼
┌─────────────────────────────────────────────┐
│ Result: Personalized recommendations        │
│ with real-time inventory and custom pricing │
└─────────────────────────────────────────────┘
```

### Acme Business Benefits

| Aspect | Benefit |
|--------|---------|
| **Time to Market** | Deploy agents to multiple platforms in weeks, not months |
| **Cost Efficiency** | One tool implementation serves all platforms, reduces dev costs |
| **Data Security** | All agent-data access flows through audited MCP layer |
| **Flexibility** | Switch agent platforms based on performance, cost, features |
| **Scalability** | Add new tools that automatically work across all platforms |
| **Maintenance** | Fix bugs once, benefit everywhere |
| **Compliance** | Centralized logging and access control for all agents |

### Acme Tool Categories

**Data Access Tools** (AxiomPy's data modules integrate seamlessly):
- Query product inventory from multiple sources (warehouses, retailers)
- Access customer data with privacy controls
- Retrieve supply chain status
- Query pricing and promotion data

**Intelligence Tools** (Leverage AxiomPy's ML integrations):
- Get product recommendations
- Predict demand
- Optimize inventory levels
- Suggest pricing strategies

**Action Tools** (Safe, logged, audited):
- Send offers and promotions
- Update customer preferences
- Trigger fulfillment
- Create support tickets

**Reporting Tools** (Built-in session tracking):
- Generate sales reports
- Audit agent decisions
- Track agent performance
- Analyze customer interactions

---

## Getting Started: 3 Paths

### Path 1: Quick Start (5 minutes)
```python
from axiompy.servers import MCPServerFactory, MCPServerType, MCPServerSettings

# 1. Create server
server = MCPServerFactory.create(MCPServerType.OPENAI, MCPServerSettings(name="MyTools"))

# 2. Add tools
server.register_tool("search", search_func, "Search something")

# 3. Use it
server.initialize()
session = server.create_session("agent")
result = server.execute_tool("search", session, query="python")
```

### Path 2: Learn by Doing (30 minutes)
See `examples/mcp_basic.py` for:
- Basic calculator with multiple tools
- Framework switching without code changes
- Session management

### Path 3: Go Deep (1-2 hours)
See `examples/mcp_advanced.py` for:
- Advanced error handling patterns
- Tool discovery and organization
- Session state management
- Real-world service integration

---

## Learning Resources & Community

### Official Documentation
- 📖 **Anthropic MCP Spec**: [Model Context Protocol](https://spec.modelcontextprotocol.io/)
- 📖 **OpenAI Agents**: [Agent Development Guide](https://platform.openai.com/docs/agents)
- 📖 **Google ADK**: [Agent Development Kit Docs](https://google.github.io/adk-docs/)

### Video Tutorials
- 🎥 **Getting Started with Agents**: Search "AI agents tutorial" on YouTube
- 🎥 **OpenAI Agents Workshop**: [OpenAI YouTube Channel](https://www.youtube.com/@OpenAIofficial)
- 🎥 **Google Developer Summit**: Search "agent development" on Google Developers channel

### Articles & Blog Posts
- 📝 **What is MCP?**: Read Anthropic's introduction to the protocol
- 📝 **Agent Architecture**: Explore design patterns for autonomous agents
- 📝 **Tool Design Best Practices**: Learn how to write effective tools for agents

### Community & Support
- 💬 **GitHub Discussions**: Join communities on official project repositories
- 💬 **Discord Servers**: Connect with developers building AI agents
- 💬 **Stack Overflow**: Tag questions with `ai-agents` or `mcp`

---

## Comparison: Vendor Platforms

| Feature | OpenAI | Google ADK | Anthropic | AxiomPy |
|---------|--------|-----------|-----------|--------|
| **Tool Support** | ✅ Function calling | ✅ Tool use | ✅ Tool use | ✅ All |
| **Learning Curve** | 📈 Medium | 📈 Medium | 📊 Low | 📊 Low |
| **Documentation** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Pricing Transparency** | High | Medium | High | N/A (framework) |
| **Enterprise Ready** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Open Source** | ❌ No | ✅ Yes | ❌ No | ✅ Yes |
| **Multi-Platform** | ❌ Only OpenAI | ❌ Only Google | ❌ Only Anthropic | ✅ **All 3** |

**AxiomPy Advantage**: Write your MCP tools once, deploy to any platform!

---

### MCPTool
Represents a callable tool with metadata that can be executed by AI agents.

```python
from axiompy.servers import MCPTool

tool = MCPTool(
    name="multiply",
    func=lambda a, b: a * b,
    description="Multiply two numbers",
    parameters={"a": {"type": "int"}, "b": {"type": "int"}},
    return_type="int",
    tags=["math"]
)

# Execute tool
result = tool.execute(a=5, b=3)  # 15
```

### MCPSession
Session context for tool execution with agent tracking and metadata.

```python
from axiompy.servers import MCPSession

# Create session
session = MCPSession(
    agent_name="calculator_agent",
    metadata={"model": "gpt-4", "temperature": 0.7}
)

# Use session ID to track execution
print(session.session_id)  # UUID tracking this session
```

### MCPServerSettings
Configuration for MCP servers.

```python
from axiompy.servers import MCPServerSettings

settings = MCPServerSettings(
    name="MyAgentTools",
    version="1.0.0",
    description="Tools for AI agents",
    enable_logging=True,
    max_tool_timeout=30,
    extra_params={}  # Framework-specific options
)
```

### MCPServer
Abstract interface all implementations follow.

```python
from axiompy.servers import MCPServer, MCPServerFactory, MCPServerType

# Create any framework server - same interface
server = MCPServerFactory.create(MCPServerType.OPENAI, settings)

# All servers support these methods:
# - register_tool(name, func, description, ...)
# - execute_tool(tool_name, session, **kwargs)
# - create_session(agent_name, metadata)
# - list_tools()
# - shutdown()
```

---

## MCP API Reference

### MCPServerFactory

The factory for creating MCP server instances.

```python
from axiompy.servers import MCPServerFactory, MCPServerType, MCPServerSettings

# Create a server
settings = MCPServerSettings(name="Tools")
server = MCPServerFactory.create(MCPServerType.OPENAI, settings)

# Register custom framework implementation
class CustomMCPServer(MCPServer):
    def initialize(self): ...
    def execute_tool(self, tool_name, session, **kwargs): ...
    def shutdown(self): ...

MCPServerFactory.register_server(MCPServerType.CUSTOM, CustomMCPServer)
```

**Methods:**

#### `create(server_type: MCPServerType, settings: MCPServerSettings) -> MCPServer`

Create an MCP server instance for the specified platform.

```python
settings = MCPServerSettings(name="MyTools")
server = MCPServerFactory.create(MCPServerType.OPENAI, settings)
```

#### `register_server(server_type: MCPServerType, server_class: type) -> None`

Register a custom MCP server implementation.

```python
MCPServerFactory.register_server(MCPServerType.CUSTOM, CustomMCPServer)
```

### MCPServer Methods

#### `register_tool(name, func, description, parameters=None, return_type="any", tags=None) -> MCPTool`

Register a tool that can be called by AI agents.

```python
server.register_tool(
    "search",
    lambda query: [{"result": query}],
    "Search documents",
    parameters={"query": {"type": "str"}},
    return_type="list",
    tags=["search", "documents"]
)
```

#### `execute_tool(tool_name: str, session: MCPSession, **kwargs) -> Any`

Execute a registered tool within a session context.

```python
session = server.create_session("agent")
result = server.execute_tool("search", session, query="python")
```

#### `create_session(agent_name: str = "default", metadata: Dict = None) -> MCPSession`

Create a session for tracking tool execution context.

```python
session = server.create_session(
    agent_name="research_agent",
    metadata={"user_id": 123, "context": "research"}
)
```

#### `list_tools() -> List[Dict]`

Get metadata for all registered tools.

```python
tools = server.list_tools()
# Returns: [{"name": "search", "description": "...", "parameters": {...}, ...}]
```

#### `get_session(session_id: str) -> Optional[MCPSession]`

Retrieve a session by ID.

```python
session = server.get_session(session_id)
```

#### `close_session(session_id: str) -> None`

Clean up a session.

```python
server.close_session(session_id)
```

#### `initialize() -> None`

Initialize the server with its framework. Must be called before executing tools.

```python
server.initialize()
```

#### `shutdown() -> None`

Shutdown the server and cleanup resources.

```python
server.shutdown()
```

---

## MCP Examples

**👉 For comprehensive, runnable examples, see [`examples/servers/README.md`](../../examples/servers/README.md)**

That guide includes:
- 📝 Web server examples (Flask/FastAPI)
- 🤖 MCP server examples (basic → advanced)
- ✅ **Chainable validators & LLM reasoning** (most important!)
- 🧪 Testing patterns
- 📚 Learning paths by role

---

### Example 1: Simple Calculator

```python
from axiompy.servers import MCPServerFactory, MCPServerType, MCPServerSettings

# Create server
settings = MCPServerSettings(name="Calculator")
server = MCPServerFactory.create(MCPServerType.OPENAI, settings)

# Register tools
server.register_tool(
    "add",
    lambda a, b: a + b,
    "Add two numbers",
    parameters={"a": {"type": "int"}, "b": {"type": "int"}},
    return_type="int"
)

server.register_tool(
    "subtract",
    lambda a, b: a - b,
    "Subtract two numbers",
    parameters={"a": {"type": "int"}, "b": {"type": "int"}},
    return_type="int"
)

# Initialize and use
server.initialize()
session = server.create_session("calculator_agent")

result1 = server.execute_tool("add", session, a=10, b=5)      # 15
result2 = server.execute_tool("subtract", session, a=10, b=3)  # 7

server.shutdown()
```

### Example 2: Framework Switching

```python
from axiompy.servers import MCPServerFactory, MCPServerType, MCPServerSettings

def setup_agent_tools(server_type):
    """Setup same tools for any framework"""
    settings = MCPServerSettings(name="Tools")
    server = MCPServerFactory.create(server_type, settings)

    # Register same tools regardless of framework
    server.register_tool(
        "fetch_user",
        lambda user_id: {"id": user_id, "name": f"User {user_id}"},
        "Fetch user by ID",
        parameters={"user_id": {"type": "int"}},
        return_type="dict"
    )

    return server

# Works identically with all frameworks
for platform in [MCPServerType.OPENAI, MCPServerType.GOOGLE_ADK, MCPServerType.ANTHROPIC]:
    server = setup_agent_tools(platform)
    server.initialize()

    session = server.create_session(f"{platform.value}_agent")
    result = server.execute_tool("fetch_user", session, user_id=123)
    print(f"{platform.value}: {result}")

    server.shutdown()
```

### Example 3: Testing with Mock Server

```python
from axiompy.servers import MCPServer, MCPServerSettings, MCPServerError, MCPToolError

# Mock server for testing - no SDK dependencies needed
class MockMCPServer(MCPServer):
    def initialize(self):
        pass

    def execute_tool(self, tool_name, session, **kwargs):
        tool = self.get_tool(tool_name)
        if not tool:
            raise MCPToolError(f"Tool '{tool_name}' not found")
        return tool.execute(**kwargs)

    def shutdown(self):
        pass

# Test without OpenAI/Google/Anthropic SDKs
server = MockMCPServer(MCPServerSettings(name="Test"))
server.register_tool("add", lambda a, b: a + b, "Add")
session = server.create_session("test_agent")
result = server.execute_tool("add", session, a=2, b=3)
assert result == 5
print("✓ Test passed!")
```

---

## MCP Validation Middleware (Chainable Tool Validators)

The validation middleware is an **optional layer** that wraps any `MCPServer` implementation to add **intelligent tool validation and sequencing**. It uses **chainable validators** to intelligently validate tool execution:
- **LLM-based validation** (via Ollama or custom APIs) for intelligent reasoning
- **Rule-based validation** for fast prerequisite/data checking
- **Custom validators** for business logic and overrides

Follows AxiomPy's **middleware pattern** - non-invasive, composable, and decoupled from the base server.

### Architecture: Chainable Validators

```
Tool Request
    ↓
MCPValidationMiddleware
    ↓
Validator Chain (first match wins):
  1. LLMToolValidator - AI-powered intelligent validation
  2. RuleBasedToolValidator - Fast prerequisite/data checking
  3. Custom Validators - Per-tool business logic overrides
    ↓
Decision: Allow or Block Execution
```

### What Makes It Different

- **Pluggable Validators**: Chain multiple validation strategies
- **LLM-Based Intelligence** (optional): Uses Ollama to understand tool purposes
- **Fast Fallback**: Rule-based validation works without LLM
- **Extensible**: Easy to add SecurityValidator, AuditValidator, MLValidator, etc.
- **Graceful Degradation**: LLM unavailable? Falls back to rules
- **Zero Cost LLM**: Runs locally via Ollama - no API calls

### Architecture: LLM-Powered Middleware

```
MCPServer (Base)
    ↓
MCPReasoningMiddleware (Wrapper)
    ├─ LLM-powered validation (via Ollama)
    ├─ Intelligent prerequisite checking
    ├─ Context-aware sequencing
    ├─ Tracks execution costs & data flow
    └─ Delegates to base server

Local LLM (Ollama)
    ├─ mistral (fast, recommended)
    ├─ llama2 (powerful)
    └─ neural-chat (conversation-optimized)
```

### Setup: Installing Ollama

```bash
# 1. Install Ollama
brew install ollama          # macOS
# or download from https://ollama.ai

# 2. Pull a model (one-time)
ollama pull mistral          # ~4GB, very fast & good
# OR
ollama pull llama2           # ~4GB, more powerful
# OR
ollama pull neural-chat      # ~4GB, optimized for conversations

# 3. Run Ollama server (keep running)
ollama serve                 # Starts at http://localhost:11434
```

### Quick Start: Tool Validation with Chainable Validators

**🚀 See full production examples at [`examples/servers/mcp_validators_examples.py`](../../examples/servers/mcp_validators_examples.py)**

That file includes 5 complete examples:
1. Infrastructure validation (DevOps)
2. Fast path (internal services, <1ms)
3. Distributed enterprise deployment
4. Graceful degradation (SLA compliance)
5. Custom policy validators

```python
from axiompy.servers import MCPServerFactory, MCPServerType, MCPServerSettings
from axiompy.servers.mcp_reasoning import (
    MCPValidationMiddleware,
    LLMToolValidator,
    RuleBasedToolValidator
)

# 1. Create base MCP server
settings = MCPServerSettings(name="ExampleTools")
base_server = MCPServerFactory.create(MCPServerType.OPENAI, settings)

# 2. Create validator chain (or use default auto-chain)
validators = [
    LLMToolValidator(model="mistral"),      # LLM-powered validation (optional)
    RuleBasedToolValidator()                # Fast fallback validation
]

# 3. Wrap with validation middleware
server = MCPValidationMiddleware(base_server, validators)

# 3. Register tools with dependencies
server.register_tool(
    "get_customer_profile",
    func=lambda: {"name": "John"},
    description="Fetch customer profile",
    provides_data=["customer"],
    cost=2
)

server.register_tool(
    "send_offer",
    func=lambda: {"status": "sent"},
    description="Send personalized offer",
    prerequisites=["get_customer_profile"],  # Must run first!
    requires_data=["customer"],
    cost=1,
    risk_level=RiskLevel.HIGH,
    requires_approval=True
)

# 4. Execute with automatic validation
server.initialize()
session = server.create_session("agent_001")
result = server.execute_tool("send_offer", session)
# Validation fails automatically - prerequisites not met!
```

### Middleware Features

**Optional & Non-Invasive**
- Wraps any MCPServer without modifying it
- Disable reasoning with `MCPPipelineConfig(enable_validation=False)`
- Base server works identically if middleware not used

**Automatic Validation**
- Prerequisites checking (topological sort)
- Data availability tracking
- Risk level classification
- Approval requirements

**Request Pipelining**
- Multi-stage tool workflows
- Data flow tracking
- Cost estimation
- Automatic sequencing

**Session Tracking**
- Complete execution history
- Success/failure tracking
- Cost totals
- Data availability per session

### How LLM Reasoning Works

When you execute a tool:

```python
result = server.execute_tool("send_offer", session, offer_id="123")
```

The LLM reasoning validates it by asking:

1. **Are prerequisites met?** "Has get_customer_profile already run?"
2. **Is data available?** "Do we have customer and discount data?"
3. **Does it make sense?** "Is this the right time to send the offer?"

The LLM uses natural language understanding to make these decisions, not just rule-based checks.

Example LLM validation for "send_offer":

```
Tool: send_offer
Description: Send personalized offer to customer
Prerequisites: [get_customer_profile, apply_discount]
Required data: [customer, discount]

Already executed: [get_customer_profile, apply_discount]
Available data: [customer, discount, inventory]

LLM Response: "YES. All prerequisites met. Customer data and discount
calculated. Ready to send offer."
```

### Tool Metadata: Extended Parameters

When registering tools with the middleware, add reasoning parameters:

```python
server.register_tool(
    "send_offer",
    func=send_offer_impl,
    description="Send offer to customer",  # ← LLM reads this to understand purpose
    # Base MCP parameters
    parameters={"offer_id": {"type": "string"}},
    return_type="dict",
    tags=["customer", "action"],
    # Extended reasoning parameters for LLM
    prerequisites=["get_customer_profile", "apply_discount"],  # ← LLM checks these
    provides_data=["offer_sent"],  # ← Data this tool creates
    requires_data=["customer", "discount"],  # ← Data the LLM validates is available
    cost=1,  # Relative cost (1-10)
    risk_level=RiskLevel.HIGH,  # ← LLM considers risk level
    requires_approval=True  # ← Needs human review
)
```

### Tool Categories & Risk Levels

```python
# Categories (auto-inferred from risk_level)
ToolCategory.DATA       # Read-only operations (RiskLevel.LOW)
ToolCategory.SERVICE    # Computations (RiskLevel.MEDIUM)
ToolCategory.ACTION     # State changes (RiskLevel.HIGH)

# Risk levels
RiskLevel.LOW           # No validation needed
RiskLevel.MEDIUM        # Should be tracked
RiskLevel.HIGH          # Requires approval
```

### Custom Validation Logic

Override default validation for business rules:

```python
def validate_premium_only(tool_metadata, parameters):
    """Custom: only apply discount for premium customers."""
    tier = parameters.get("customer_tier")
    if tier != "premium":
        return Err("Discounts only for premium customers")
    return Ok(True)

server.register_custom_validator("apply_discount", validate_premium_only)
```

### Custom Sequencing Logic

Replace default topological sort with custom logic (ML-ready):

```python
def ml_sequencer(goal, reasoning_session):
    """Use ML model to predict optimal tool sequence."""
    from my_ml import predict_sequence
    sequence = predict_sequence(goal, reasoning_session.data_available)
    return Ok(sequence)

server.register_custom_sequencer(ml_sequencer)
```

### Example: Acme Personalized Offers with LLM Reasoning

```python
from axiompy.servers import MCPServerFactory, MCPServerType, MCPServerSettings
from axiompy.servers.mcp_reasoning import SimpleMCPReasoning, MCPReasoningMiddleware

# Setup with Ollama-powered reasoning
base_server = MCPServerFactory.create(MCPServerType.OPENAI, MCPServerSettings("Acme"))
reasoning = SimpleMCPReasoning(model="mistral")
server = MCPReasoningMiddleware(base_server, reasoning)

# Register Acme tools with descriptions (LLM reads these)
server.register_tool(
    "get_customer_profile",
    func=example_data.get_customer,
    description="Fetch customer profile including loyalty tier and preferences",
    provides_data=["customer"],
    cost=2
)

server.register_tool(
    "query_inventory",
    func=example_inventory.query,
    description="Check product availability across all warehouses",
    provides_data=["inventory"],
    cost=3
)

server.register_tool(
    "get_recommendation",
    func=example_ml.recommend,
    description="Get ML-powered product recommendations based on customer",
    prerequisites=["get_customer_profile"],
    requires_data=["customer"],
    provides_data=["recommendation"],
    cost=5,
    risk_level=RiskLevel.MEDIUM
)

server.register_tool(
    "apply_discount",
    func=example_commerce.calculate_discount,
    description="Calculate eligible discount based on customer loyalty",
    prerequisites=["get_customer_profile"],
    requires_data=["customer"],
    provides_data=["discount"],
    cost=2,
    risk_level=RiskLevel.MEDIUM
)

server.register_tool(
    "send_offer",
    func=example_comms.send_email,
    description="Send personalized offer to customer email",
    prerequisites=["get_recommendation", "apply_discount"],
    requires_data=["recommendation", "discount"],
    provides_data=["offer_sent"],
    cost=1,
    risk_level=RiskLevel.HIGH,
    requires_approval=True
)

# Initialize
server.initialize()

# LLM now intelligently validates tool execution:
session = server.create_session("example_agent_001")

# ✓ LLM allows this (recommendations and discount ready)
result = server.execute_tool("send_offer", session, customer_id="12345")

# LLM workflow:
# 1. Reads tool descriptions
# 2. Checks prerequisites ("get_recommendation" and "apply_discount" ran)
# 3. Verifies data available ("recommendation" and "discount" in session)
# 4. Considers context ("Is now a good time to send?")
# 5. Returns: "YES - all conditions met"
```

**LLM Reasoning in Action:**

When you call `send_offer`, the LLM reasons:
```
Tool: send_offer
Purpose: Send personalized offer to customer

Prerequisites check:
- get_recommendation: ✓ Executed
- apply_discount: ✓ Executed

Data check:
- recommendation: ✓ Available
- discount: ✓ Available

Context:
- We have customer data
- We have recommendations
- We have calculated discount
- Right time to send offer

Decision: YES - Execute send_offer
```

### Session Summary

```python
# Get execution report
summary_result = server.get_session_summary(session)

if summary_result.is_ok():
    summary = summary_result.unwrap()
    print(f"Total calls: {summary['total_calls']}")
    print(f"Successful: {summary['successful_calls']}")
    print(f"Failed: {summary['failed_calls']}")
    print(f"Total cost: {summary['total_cost']}")
    print(f"Data available: {summary['data_available']}")
```

### Configuration: LLM Settings

```python
from axiompy.servers.mcp_reasoning import SimpleMCPReasoning

# Option 1: Local Ollama with default Mistral model
reasoning = SimpleMCPReasoning()

# Option 2: Different Ollama model
reasoning = SimpleMCPReasoning(model="llama2")

# Option 3: Remote Ollama server
reasoning = SimpleMCPReasoning(
    model="neural-chat",
    backend_url="http://192.168.1.100:11434"
)

# Option 4: On-disk GGUF model
reasoning = SimpleMCPReasoning(
    model_path="/models/mistral.gguf",
    backend_url="http://localhost:11434"
)

# Option 5: Custom LLM API
reasoning = SimpleMCPReasoning(
    model="gpt-like-model",
    backend_url="http://custom-llm.example.com",
    backend_type="custom"
)

# Adjust timeout for slow models or connections
reasoning = SimpleMCPReasoning(
    model="llama2",
    timeout=60  # 60 seconds, default is 30
)

# Disable LLM (fast rule-based validation only)
reasoning = SimpleMCPReasoning(enable_llm=False)
```

### Pipeline Configuration

```python
from axiompy.servers.mcp_reasoning import MCPPipelineConfig

config = MCPPipelineConfig(
    enable_validation=True,        # Use LLM to validate tools
    enable_sequencing=True,        # Suggest optimal tool order
    enable_cost_tracking=True,     # Track execution costs
    enable_session_tracking=True,  # Record all calls
    max_pipeline_depth=100         # Prevent infinite loops
)

server = MCPReasoningMiddleware(base_server, reasoning, config)
```

### When Ollama Is Unavailable

If Ollama is not running:

```
⚠️  Ollama not available at http://localhost:11434.
    Falling back to rule-based validation.
    To use LLM reasoning, start Ollama: ollama serve
```

The middleware gracefully falls back to fast rule-based validation:
- Still checks prerequisites
- Still validates data availability
- Still sequences tools
- Just without AI reasoning

Your code works identically - no errors, just less intelligent validation.

### Disabling Reasoning Entirely

```python
# Use base server without any reasoning
base_server = MCPServerFactory.create(MCPServerType.OPENAI, settings)
result = base_server.execute_tool("send_offer", session)  # No validation

# Or disable LLM but keep rule-based validation
reasoning = SimpleMCPReasoning(enable_llm=False)
server = MCPReasoningMiddleware(base_server, reasoning)
```

---

## 📖 Complete Guides & Examples

### Documentation
- **Architecture Deep Dive**: [ARCHITECTURE.md](ARCHITECTURE.md) - Technical implementation details
- **Quick Reference**: This README

### 🎯 Examples & Learning Paths

**⭐ START HERE**: [`examples/servers/README.md`](../../examples/servers/README.md)
- Comprehensive examples organized by use case
- 5-minute quick starts to 2-hour deep dives
- Learning paths by role (Web Dev, AI Engineer, DevOps, QA)

**Example Files**:
- **Web Servers**: `examples/servers/simple_server.py`, `server_usage.py`, `server_testing.py`
- **MCP Basic**: `examples/servers/mcp_basic.py`
- **MCP Advanced**: `examples/servers/mcp_advanced.py`
- **🔑 MCP Validators** (CORE PATTERN): `examples/servers/mcp_validators_examples.py` ← **Most Important!**
- **MCP Testing**: `examples/servers/mcp_testing.py`
- **Legacy**: `examples/mcp_reasoning_example.py` (see `mcp_validators_examples.py` instead)

---

## Web Server Quick Start

```python
from axiompy.servers import ServerFactory, ServerType, ServerSettings

# Create server (Flask or FastAPI)
settings = ServerSettings(host="0.0.0.0", port=8000)
server = ServerFactory.create(ServerType.FASTAPI, settings)

# Define routes
@server.route("/")
def home():
    return {"message": "Hello, World!"}

@server.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id: int):
    return {"id": user_id, "name": f"User {user_id}"}

@server.route("/users", methods=["POST"])
def create_user(data: dict):
    return {"id": 123, "name": data["name"]}, 201

# Start server
server.run()
```

**Switch to Flask?** Just change `ServerType.FASTAPI` to `ServerType.FLASK`. Everything else stays the same!

---

## Why Use This Abstraction?

### ✅ Framework Agnostic
Write application logic once, switch frameworks without code changes.

### ✅ Easy Testing
Mock the server interface for fast unit tests without HTTP overhead.

### ✅ Consistent API
Same decorator syntax and patterns across Flask and FastAPI.

### ✅ Auto JSON Handling
Automatically converts dict/list returns to JSON responses.

### ✅ Dependency Injection
Services depend on the `Server` interface, not specific frameworks.

### ✅ Status Code Support
Return tuples like `(data, 404)` for custom status codes.

---

## Installation

Base `axiompy` includes **Pydantic** and framework-agnostic **`axiompy.web`** helpers. Flask and FastAPI require the **`[servers]`** extra (there is no separate `[fastapi]` extra).

```bash
pip install axiompy
pip install "axiompy[servers]"   # Flask, FastAPI, uvicorn, httpx
pip install "axiompy[dev,io,servers]"   # local development (see root README)
```

Legacy one-off installs still work but prefer extras:

```bash
pip install axiompy flask                    # same as [servers] for Flask only
pip install axiompy fastapi uvicorn httpx    # partial [servers] set
```

---

## Core Concepts

### Server Types

```python
from axiompy.servers import ServerType

ServerType.FLASK    # Flask framework
ServerType.FASTAPI  # FastAPI framework
```

### Server Settings

```python
from axiompy.servers import ServerSettings

settings = ServerSettings(
    host="0.0.0.0",           # Server host
    port=8000,                # Server port
    debug=True,               # Debug mode
    reload=True,              # Auto-reload (FastAPI)
    workers=4,                # Worker processes
    extra_params={            # Framework-specific config
        "title": "My API",    # FastAPI title
        "version": "1.0.0"    # FastAPI version
    }
)
```

### Route Registration

```python
# GET request (default)
@server.route("/users")
def list_users():
    return {"users": [...]}

# Multiple methods
@server.route("/users/<int:user_id>", methods=["GET", "PUT", "DELETE"])
def handle_user(user_id: int):
    return {"id": user_id}

# With request data
@server.route("/users", methods=["POST"])
def create_user(data: dict):
    # 'data' automatically populated from request
    return {"id": 1, "name": data["name"]}

# Custom status codes
@server.route("/error")
def error_handler():
    return {"error": "Not found"}, 404
```

---

## API Reference

### ServerFactory

#### `create(server_type: ServerType, settings: ServerSettings) -> Server`

Create a server instance.

```python
from axiompy.servers import ServerFactory, ServerType, ServerSettings

settings = ServerSettings(port=8000)
server = ServerFactory.create(ServerType.FLASK, settings)
```

#### `register_server(server_type: ServerType, server_class: type) -> None`

Register custom server implementation.

```python
ServerFactory.register_server(CustomType.CUSTOM, CustomServer)
```

### Server Interface

#### `route(path: str, methods: List[str] = None, **kwargs) -> Callable`

Register a route handler.

**Parameters:**
- `path`: URL path (e.g., "/users", "/users/<int:id>")
- `methods`: HTTP methods (default: ["GET"])
- `**kwargs`: Framework-specific options

**Returns:** Decorator function

```python
@server.route("/api/items/<int:item_id>", methods=["GET", "PUT"])
def handle_item(item_id: int):
    return {"item_id": item_id}
```

#### `add_middleware(middleware: Callable, **kwargs) -> None`

Add middleware to the server.

```python
async def logging_middleware(request, call_next):
    print(f"Request: {request.url.path}")
    response = await call_next(request)
    return response

server.add_middleware(logging_middleware)
```

#### `run(host: str = None, port: int = None, **kwargs) -> None`

Start the server.

```python
server.run()  # Use settings
server.run(host="127.0.0.1", port=5000)  # Override
```

#### `get_app() -> Any`

Get underlying framework app (for advanced usage, testing).

```python
app = server.get_app()
# Flask: use app.test_client()
# FastAPI: use TestClient(app)
```

---

## Flask Examples

### Basic Flask Application

```python
from axiompy.servers import ServerFactory, ServerType, ServerSettings

settings = ServerSettings(host="127.0.0.1", port=5000, debug=True)
server = ServerFactory.create(ServerType.FLASK, settings)

@server.route("/")
def home():
    return {"message": "Flask API"}

@server.route("/users/<int:user_id>")
def get_user(user_id):
    return {"id": user_id, "name": f"User {user_id}"}

server.run()
```

### Flask with Custom Configuration

```python
settings = ServerSettings(
    port=5000,
    extra_params={
        "JSON_SORT_KEYS": False,
        "MAX_CONTENT_LENGTH": 16 * 1024 * 1024  # 16MB
    }
)
server = ServerFactory.create(ServerType.FLASK, settings)
```

### Flask Middleware

```python
def before_middleware():
    print("Before request")

def after_middleware(response):
    print("After request")
    return response

before_middleware.__name__ = "before_request_middleware"
after_middleware.__name__ = "after_request_middleware"

server.add_middleware(before_middleware)
server.add_middleware(after_middleware)
```

---

## FastAPI Examples

### `axiompy.web` errors with FastAPI

`ResultErrorHandler.handle_error` raises **`HttpResponseError`** (not `fastapi.HTTPException`). Register a handler once on the app:

```python
from axiompy.servers import register_fastapi_http_response_handler

app = server.get_app()
register_fastapi_http_response_handler(app)
```

For manual conversion in a route: `from axiompy.servers import raise_fastapi_http_exception`.

See [`axiompy/web.py`](../web.py) and [`fastapi_web.py`](fastapi_web.py). Tests: `tests/test_web.py`, `tests/test_fastapi_web.py`.

### Basic FastAPI Application

```python
from axiompy.servers import ServerFactory, ServerType, ServerSettings

settings = ServerSettings(
    host="0.0.0.0",
    port=8000,
    reload=True  # Auto-reload during development
)
server = ServerFactory.create(ServerType.FASTAPI, settings)

@server.route("/")
def home():
    return {"message": "FastAPI"}

@server.route("/users/{user_id}")
def get_user(user_id: int):
    return {"id": user_id, "name": f"User {user_id}"}

server.run()
# Visit http://localhost:8000/docs for automatic API documentation!
```

### FastAPI with Custom Configuration

```python
settings = ServerSettings(
    port=8000,
    workers=4,
    extra_params={
        "title": "My Custom API",
        "description": "API built with AxiomPy",
        "version": "2.0.0"
    }
)
server = ServerFactory.create(ServerType.FASTAPI, settings)
```

### FastAPI Middleware

```python
async def logging_middleware(request, call_next):
    print(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"Response: {response.status_code}")
    return response

server.add_middleware(logging_middleware)
```

---

## Testing

### Mock Server for Unit Tests

```python
from axiompy.servers import Server, ServerSettings

class MockServer(Server):
    """Mock server for testing without HTTP overhead."""

    def __init__(self, settings=None):
        super().__init__(settings or ServerSettings())
        self.routes = []

    def route(self, path, methods=None, **kwargs):
        def decorator(handler):
            self.routes.append({
                "path": path,
                "methods": methods,
                "handler": handler
            })
            return handler
        return decorator

    def add_middleware(self, middleware, **kwargs):
        pass

    def run(self, host=None, port=None, **kwargs):
        pass

    def get_app(self):
        return None

    def _cleanup(self):
        pass

    # Helper for testing
    def call_route(self, path, method="GET", **kwargs):
        for route in self.routes:
            if route["path"] == path and method in route["methods"]:
                return route["handler"](**kwargs)
        raise ValueError(f"Route not found: {method} {path}")
```

### Testing with Mock Server

```python
def test_user_api():
    # Arrange
    mock_server = MockServer()

    @mock_server.route("/users/<int:user_id>", methods=["GET"])
    def get_user(user_id: int):
        return {"id": user_id, "name": f"User {user_id}"}

    # Act
    result = mock_server.call_route("/users/<int:user_id>", "GET", user_id=123)

    # Assert
    assert result["id"] == 123
    assert result["name"] == "User 123"
```

### Testing with Flask Test Client

```python
from axiompy.servers import ServerFactory, ServerType, ServerSettings

def test_flask_api():
    settings = ServerSettings()
    server = ServerFactory.create(ServerType.FLASK, settings)

    @server.route("/health")
    def health():
        return {"status": "healthy"}

    # Get Flask test client
    app = server.get_app()
    client = app.test_client()

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "healthy"
```

### Testing with FastAPI Test Client

```python
from fastapi.testclient import TestClient
from axiompy.servers import ServerFactory, ServerType, ServerSettings

def test_fastapi_api():
    settings = ServerSettings()
    server = ServerFactory.create(ServerType.FASTAPI, settings)

    @server.route("/health")
    def health():
        return {"status": "healthy"}

    # Get FastAPI test client
    app = server.get_app()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

---

## Advanced Usage

### Framework-Agnostic Application Class

```python
from axiompy.servers import Server

class UserAPI:
    """Application that works with any server framework."""

    def __init__(self, server: Server):
        self.server = server
        self.users = {}
        self._next_id = 1
        self._setup_routes()

    def _setup_routes(self):
        self.server.route("/users", methods=["GET"])(self.list_users)
        self.server.route("/users", methods=["POST"])(self.create_user)
        self.server.route("/users/<int:user_id>", methods=["GET"])(self.get_user)
        self.server.route("/users/<int:user_id>", methods=["PUT"])(self.update_user)
        self.server.route("/users/<int:user_id>", methods=["DELETE"])(self.delete_user)

    def list_users(self):
        return {"users": list(self.users.values())}

    def get_user(self, user_id: int):
        user = self.users.get(user_id)
        if not user:
            return {"error": "User not found"}, 404
        return user

    def create_user(self, data: dict):
        user = {
            "id": self._next_id,
            "name": data["name"],
            "email": data["email"]
        }
        self.users[self._next_id] = user
        self._next_id += 1
        return user, 201

    def update_user(self, user_id: int, data: dict):
        if user_id not in self.users:
            return {"error": "User not found"}, 404

        user = self.users[user_id]
        user.update(data)
        return user

    def delete_user(self, user_id: int):
        if user_id not in self.users:
            return {"error": "User not found"}, 404

        del self.users[user_id]
        return {"message": "User deleted"}

# Use with Flask
from axiompy.servers import ServerFactory, ServerType, ServerSettings

flask_server = ServerFactory.create(ServerType.FLASK, ServerSettings(port=5000))
flask_api = UserAPI(flask_server)
# flask_server.run()

# Or use with FastAPI - same code!
fastapi_server = ServerFactory.create(ServerType.FASTAPI, ServerSettings(port=8000))
fastapi_api = UserAPI(fastapi_server)
# fastapi_server.run()
```

### Dependency Injection

```python
from axiompy.servers import Server
from axiompy.io.database import Database

class ProductService:
    """Service with database and server dependencies."""

    def __init__(self, server: Server, database: Database):
        self.server = server
        self.db = database
        self._setup_routes()

    def _setup_routes(self):
        self.server.route("/products", methods=["GET"])(self.list_products)
        self.server.route("/products/<int:id>", methods=["GET"])(self.get_product)

    def list_products(self):
        products = self.db.get_all("products")
        return {"products": products}

    def get_product(self, id: int):
        product = self.db.get("products", id)
        if not product:
            return {"error": "Product not found"}, 404
        return product

# Inject dependencies
from axiompy.io.database import DatabaseFactory, DatabaseType, DatabaseSettings

db_settings = DatabaseSettings(database=":memory:")
db = DatabaseFactory.create(DatabaseType.SQLITE, db_settings)

server_settings = ServerSettings(port=8000)
server = ServerFactory.create(ServerType.FASTAPI, server_settings)

service = ProductService(server, db)
```

### Custom Status Codes and Headers

```python
@server.route("/download")
def download_file():
    # Return tuple: (data, status_code)
    return {"file": "data.json"}, 200

@server.route("/created")
def create_resource():
    return {"id": 1, "name": "Resource"}, 201

@server.route("/error")
def server_error():
    return {"error": "Internal server error"}, 500
```

### Path Parameters

```python
# Integer parameter
@server.route("/users/<int:user_id>")
def get_user(user_id: int):
    return {"id": user_id}

# String parameter
@server.route("/posts/<string:slug>")
def get_post(slug: str):
    return {"slug": slug}

# Multiple parameters
@server.route("/users/<int:user_id>/posts/<int:post_id>")
def get_user_post(user_id: int, post_id: int):
    return {"user_id": user_id, "post_id": post_id}
```

### Request Data Handling

```python
# Automatic data injection
@server.route("/users", methods=["POST"])
def create_user(data: dict):
    # 'data' automatically contains request JSON
    return {
        "id": 1,
        "name": data.get("name"),
        "email": data.get("email")
    }

# Without data parameter
@server.route("/info", methods=["GET"])
def get_info():
    # No request data needed
    return {"info": "Server information"}
```

---

## Best Practices

### 1. Use Dependency Injection

✅ **Good:**
```python
class UserService:
    def __init__(self, server: Server):
        self.server = server
        self._setup_routes()
```

❌ **Bad:**
```python
from flask import Flask
app = Flask(__name__)  # Tightly coupled to Flask
```

### 2. Keep Routes Thin

✅ **Good:**
```python
class UserRepository:
    def __init__(self, server: Server, db: Database):
        self.server = server
        self.db = db
        self._setup_routes()

    def _setup_routes(self):
        self.server.route("/users")(self.list_users)

    def list_users(self):
        # Business logic here
        return self.db.get_all("users")
```

❌ **Bad:**
```python
@server.route("/users")
def list_users():
    # Complex business logic directly in route
    # Hard to test and maintain
    pass
```

### 3. Use Type Hints

✅ **Good:**
```python
def get_user(user_id: int) -> dict:
    return {"id": user_id}

def create_user(data: dict) -> tuple:
    return {"id": 1}, 201
```

### 4. Handle Errors Gracefully

✅ **Good:**
```python
@server.route("/users/<int:user_id>")
def get_user(user_id: int):
    user = db.get("users", user_id)
    if not user:
        return {"error": "User not found"}, 404
    return user
```

### 5. Test with Mocks

✅ **Good:**
```python
def test_user_service():
    mock_server = MockServer()
    service = UserService(mock_server)

    # Test business logic without HTTP overhead
    result = mock_server.call_route("/users", "GET")
    assert "users" in result
```

### 6. Keep Configuration Separate

✅ **Good:**
```python
# config.py
FLASK_SETTINGS = ServerSettings(
    host="127.0.0.1",
    port=5000,
    debug=True
)

FASTAPI_SETTINGS = ServerSettings(
    host="0.0.0.0",
    port=8000,
    reload=True
)

# app.py
from config import FASTAPI_SETTINGS
server = ServerFactory.create(ServerType.FASTAPI, FASTAPI_SETTINGS)
```

### 7. Use Framework-Specific Features Sparingly

The abstraction provides common functionality. For advanced framework-specific features, access the underlying app:

```python
# When you really need Flask-specific features
app = server.get_app()
if isinstance(app, Flask):
    app.config["SPECIAL_FLASK_OPTION"] = True
```

But prefer keeping your code framework-agnostic when possible.

---

## Complete Example

See the comprehensive examples in:
- `examples/server_usage.py` - Production usage patterns
- `examples/server_testing.py` - Testing patterns with mocks

---

## Troubleshooting

### ImportError: No module named 'flask'

Install Flask:
```bash
pip install flask
```

### ImportError: No module named 'fastapi'

Install the servers extra (includes FastAPI, uvicorn, Flask, httpx):
```bash
pip install "axiompy[servers]"
```

### Routes not registering correctly

Make sure function names are unique - Flask uses function names as endpoint names:

✅ **Good:**
```python
@server.route("/users")
def list_users():
    pass

@server.route("/posts")
def list_posts():  # Different name
    pass
```

❌ **Bad:**
```python
@server.route("/users")
def list_items():
    pass

@server.route("/posts")
def list_items():  # Name collision!
    pass
```

### Status codes not working with FastAPI

The abstraction handles this automatically. Make sure you return tuples:

```python
@server.route("/error")
def error_handler():
    return {"error": "Not found"}, 404  # Tuple with status code
```

---

## Contributing

To add a new server framework:

1. Create a new `ServerType` enum value
2. Implement the `Server` abstract class
3. Register with `ServerFactory.register_server()`
4. Add tests

Example:
```python
class CustomServer(Server):
    def __init__(self, settings: ServerSettings):
        super().__init__(settings)
        # Initialize your framework

    def route(self, path, methods=None, **kwargs):
        # Implement route registration
        pass

    # Implement other abstract methods...

# Register
ServerFactory.register_server(ServerType.CUSTOM, CustomServer)
```

---

## MCP Service Layer - Exposing Tools via HTTP

### Overview

MCPToolService provides a **clean, repeatable service layer pattern** for exposing MCP tools via HTTP. This is the same layered architecture pattern used successfully in production APIs (see `examples/api_template/`), adapted for AI agent tools.

### Repeatable Layered Architecture Pattern

AxiomPy applies consistent layering across all components:

```
┌─────────────────────────────────────────────────────┐
│ HTTP LAYER                                          │
│ ┌────────────────────────────────────────────────┐ │
│ │ Route Handlers (thin adapters)                 │ │
│ │  @app.get("/tools")                            │ │
│ │  @app.post("/tools/{name}/execute")            │ │
│ └────────────────────────────────────────────────┘ │
│                      ↓                              │
│ Dependency Injection ↓                              │
└─────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────┐
│ BUSINESS LOGIC LAYER                                │
│ ┌────────────────────────────────────────────────┐ │
│ │ MCPToolService                                 │ │
│ │  - Session management                         │ │
│ │  - Execution history                          │ │
│ │  - Error handling & validation                │ │
│ └────────────────────────────────────────────────┘ │
│                      ↓                              │
└─────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────┐
│ TOOL MANAGEMENT LAYER                               │
│ ┌────────────────────────────────────────────────┐ │
│ │ MCPServer                                      │ │
│ │  - Tool registry                              │ │
│ │  - Session context                           │ │
│ │  - Execution orchestration                    │ │
│ └────────────────────────────────────────────────┘ │
│                      ↓                              │
└─────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────┐
│ TOOL LAYER                                          │
│ ┌────────────────────────────────────────────────┐ │
│ │ Registered Tools (your implementations)       │ │
│ │  - query_database(sql)                        │ │
│ │  - send_email(to, subject, body)             │ │
│ │  - analyze_sentiment(text)                   │ │
│ └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Key Pattern Benefits

This **layered, repeatable pattern** provides:

| Layer | Responsibility | Technology |
|-------|-----------------|-----------|
| **HTTP** | Request/Response handling, route decoration | FastAPI/Flask |
| **Service** | Business logic, session management, history | MCPToolService |
| **Tool Management** | Tool registry, execution context | MCPServer |
| **Tools** | Domain-specific implementations | Your functions |

**Why This Pattern?**
- ✅ **Testable**: Mock each layer independently
- ✅ **Maintainable**: Clear separation of concerns
- ✅ **Reusable**: Same pattern across all APIs
- ✅ **Scalable**: Add layers (caching, auth, etc.) without breaking existing code
- ✅ **Framework-Agnostic**: Works with Flask, FastAPI, FastMCP, etc.

### Key Benefits

- **Clean Separation of Concerns**: Service layer handles HTTP-specific logic
- **Dependency Injection**: Easy to inject service into route handlers
- **Framework-Agnostic**: Works with FastAPI, Flask, or any web framework
- **Session Management**: HTTP clients get persistent sessions across requests
- **Execution History**: Track all tool executions with full history
- **Testable**: Mock the service layer independently

### Quick Example

```python
from axiompy.servers import (
    MCPServerFactory, MCPServerType, MCPServerSettings,
    ServerFactory, ServerType, ServerSettings,
    MCPToolService, MCPToolServiceSettings
)

# 1. Create MCP server
mcp_server = MCPServerFactory.create(
    MCPServerType.OPENAI,
    MCPServerSettings(name="MyTools")
)
mcp_server.register_tool("add", lambda a, b: a + b, "Add numbers")
mcp_server.initialize()

# 2. Create web server
web_server = ServerFactory.create(
    ServerType.FASTAPI,
    ServerSettings(host="0.0.0.0", port=8000)
)

# 3. Create service (wraps MCP server)
service = MCPToolService(
    mcp_server,
    MCPToolServiceSettings()
)

# 4. Create route handlers with service via DI
class ToolRoutes:
    def __init__(self, service: MCPToolService):
        self.service = service

    async def list_tools(self):
        return self.service.list_tools()

    async def execute(self, tool_name: str, params: dict):
        return self.service.execute_tool(tool_name, params)

routes = ToolRoutes(service)

# 5. Register routes
@web_server.route("/tools", methods=["GET"])
async def list_tools():
    return routes.list_tools()

@web_server.route("/tools/{tool_name}/execute", methods=["POST"])
async def execute(tool_name: str, data: dict):
    return routes.execute(tool_name, data.get("params", {}))

web_server.run()
```

### REST API Endpoints

The service provides these HTTP endpoints:

```
GET  /mcp/health               - Server health check
GET  /mcp/tools                - List all available tools
GET  /mcp/tools/{tool_name}    - Get tool details
POST /mcp/tools/{tool_name}/execute - Execute tool
GET  /mcp/sessions/{session_id} - Get session information
```

### MCPToolService API

#### `create_session(client_id: Optional[str]) -> str`
Create a new HTTP session.

#### `get_session(session_id: str) -> Optional[MCPSession]`
Get an existing session.

#### `get_or_create_session(session_id: Optional[str]) -> tuple[str, MCPSession]`
Get existing session or create new one.

#### `execute_tool(tool_name: str, params: dict, session_id: Optional[str]) -> dict`
Execute a tool and return result.

#### `get_session_info(session_id: str) -> dict`
Get session information and execution history.

#### `list_tools() -> dict`
List all available tools with metadata.

#### `health_check() -> dict`
Get server health status.

### Session Management

Sessions are automatically created and persist across multiple tool executions:

```python
# First execution creates session
result1 = service.execute_tool("add", {"a": 5, "b": 3})
session_id = result1["session_id"]

# Reuse same session for next execution
result2 = service.execute_tool(
    "multiply",
    {"x": 2, "y": 4},
    session_id  # ← Pass existing session
)

# Get full session history
session_info = service.get_session_info(session_id)
print(session_info["total_executions"])  # 2
print(session_info["execution_history"])  # [add, multiply]
```

### Execution History

With `enable_history=True` (default), all tool executions are tracked:

```python
# Each execution is recorded with full context
history_entry = {
    "tool": "add",
    "params": {"a": 5, "b": 3},
    "result": 8,
    "success": True
}
```

### Railway-Oriented Programming (ROP) for Error Handling

The examples use **Railway-Oriented Programming** for clean, composable error handling:

#### Without ROP (traditional try/except):
```python
def execute_tool(self, tool_name: str, request_data: dict):
    try:
        params = request_data.get("params", {})
        result = self.service.execute_tool(tool_name, params)
        return result, 200
    except ValueError as e:
        return {"error": str(e)}, 400
    except Exception as e:
        return {"error": "Internal error"}, 500
```

#### With ROP (clean Result types):
```python
def execute_tool(
    self, tool_name: str, request_data: dict
) -> Result[Dict[str, Any], str]:
    try:
        params = request_data.get("params", {})
        result = self.service.execute_tool(tool_name, params)
        return Ok(result)  # ← Success track
    except ValueError as e:
        return Err(str(e))  # ← Error track
    except Exception as e:
        return Err(f"Unexpected error: {str(e)}")

# In route handler:
result = await tool_routes.execute_tool(tool_name, request_data)
# Automatically handles both Ok and Err cases
return to_http_response(result)  # Converts Result to (body, status_code)
```

#### ROP Benefits:
- ✅ **No try/except blocks** - Automatic error propagation
- ✅ **Composable** - Chain operations with `.map()` and `.then()`
- ✅ **Type-safe** - Result[T, E] at compile time
- ✅ **Clean separation** - Business logic (handlers) vs HTTP adaptation (routes)
- ✅ **Testable** - Return Result types for easy unit testing

#### Common ROP Operations:
```python
from axiompy.result import Ok, Err

# Create results
success = Ok({"data": "value"})
failure = Err("Something went wrong")

# Check result
if success.is_ok():
    value = success.unwrap()

if failure.is_err():
    error = failure.unwrap_err()

# Transform on success
result = Ok(5).map(lambda x: x * 2)  # Ok(10)

# Transform on error
result = Err("bad").map_err(lambda e: f"Error: {e}")  # Err("Error: bad")

# Provide default
value = Err("fail").unwrap_or(0)  # 0

# Chain operations
result = (
    Ok({"a": 5, "b": 3})
    .map(lambda data: add_numbers(data))
    .map(lambda result: result["result"])
    .unwrap_or(0)
)
```

### Composing MCPServer with ServerFactory (Layered Architecture)

MCPServer can be composed with ServerFactory to create production APIs that expose MCP tools via HTTP. This creates a clean **layered architecture**:

```
┌─────────────────────────────────────────────────┐
│ HTTP LAYER (ServerFactory)                      │
│ FastAPI or Flask web server                     │
├─────────────────────────────────────────────────┤
│ SERVICE LAYER (MCPToolService)                  │
│ Business logic, session management, history     │
├─────────────────────────────────────────────────┤
│ TOOL MANAGEMENT LAYER (MCPServer)               │
│ Tool registry, execution, OpenAI/Google/Anthro  │
├─────────────────────────────────────────────────┤
│ TOOL LAYER                                      │
│ Your implementations (functions, services)      │
└─────────────────────────────────────────────────┘
```

**Complete Example: DevOps API with HTTP Exposure**

```python
from axiompy.servers import (
    MCPServerFactory, MCPServerType, MCPServerSettings,
    ServerFactory, ServerType, ServerSettings,
    MCPToolService, MCPToolServiceSettings
)
from axiompy.result import Ok, Err

# Step 1: Create MCP server with DevOps tools
mcp_server = MCPServerFactory.create(
    MCPServerType.OPENAI,
    MCPServerSettings(name="DevOpsTools", version="1.0.0")
)

# Register DevOps tools (tools layer)
mcp_server.register_tool(
    "deploy",
    lambda service, version: f"Deployed {service}:{version}",
    "Deploy service"
)
mcp_server.register_tool(
    "health_check",
    lambda service: {"status": "healthy", "uptime": "99.9%"},
    "Check service health"
)
mcp_server.initialize()

# Step 2: Create HTTP server
web_server = ServerFactory.create(
    ServerType.FASTAPI,
    ServerSettings(host="0.0.0.0", port=8000)
)
app = web_server.get_app()

# Step 3: Create service layer (MCPToolService)
service = MCPToolService(
    mcp_server,
    MCPToolServiceSettings(enable_history=True)
)

# Step 4: Create route handlers with dependency injection + ROP
class DevOpsRoutes:
    """DevOps API routes with service layer and ROP error handling."""

    def __init__(self, service: MCPToolService):
        self.service = service

    async def deploy(self, service_name: str, version: str):
        """Deploy endpoint - returns Result for ROP."""
        try:
            result = self.service.execute_tool(
                "deploy",
                {"service": service_name, "version": version}
            )
            return Ok(result)
        except Exception as e:
            return Err(f"Deployment failed: {str(e)}")

    async def health(self, service_name: str):
        """Health check endpoint - returns Result."""
        try:
            result = self.service.execute_tool(
                "health_check",
                {"service": service_name}
            )
            return Ok(result)
        except Exception as e:
            return Err(f"Health check failed: {str(e)}")

routes = DevOpsRoutes(service)

# Step 5: Register HTTP endpoints (routes layer)
def to_response(result):
    """Convert Result to HTTP response."""
    if result.is_ok():
        return result.unwrap(), 200
    return {"error": result.unwrap_err()}, 400

@app.post("/api/deploy/{service_name}/{version}")
async def deploy(service_name: str, version: str):
    result = await routes.deploy(service_name, version)
    return to_response(result)

@app.get("/api/health/{service_name}")
async def health(service_name: str):
    result = await routes.health(service_name)
    return to_response(result)

# Run the layered API
web_server.run()
```

**Benefits of This Layered Composition:**

| Layer | Benefit |
|-------|---------|
| **HTTP** | Framework-agnostic (FastAPI/Flask) routing |
| **Service** | Business logic, session management, history |
| **Tool Management** | Framework support (OpenAI/Google/Anthropic) |
| **Tools** | Your domain logic - tests easily in isolation |

**Key Advantages:**
- ✅ Each layer is independently testable
- ✅ Easy to mock layers for testing
- ✅ Clean separation of concerns
- ✅ Consistent with `examples/api_template/` patterns
- ✅ Railway-Oriented Programming (ROP) for error handling
- ✅ Works with any ServerFactory implementation (FastAPI, Flask, etc.)

### For Comprehensive Examples

See:
- `examples/servers/mcp_service_examples.py` - Complete FastAPI and Flask examples with ROP and layering
- `tests/test_mcp_service.py` - Full test coverage (93.75%, 27 tests)

---

## JSON-RPC 2.0 Server

AxiomPy provides a standards-compliant JSON-RPC 2.0 server for exposing MCP tools to clients like Claude Desktop, Cursor, and other MCP-compatible applications.

### JSON-RPC Quick Start

```python
from axiompy.servers import (
    JSONRPCServerFactory, JSONRPCTransport, JSONRPCSettings,
    MCPServerFactory, MCPServerType, MCPServerSettings
)

# 1. Create MCP server with tools
mcp = MCPServerFactory.create(MCPServerType.OPENAI, MCPServerSettings(name="MyTools"))
mcp.register_tool("add", lambda a, b: a + b, "Add two numbers")
mcp.register_tool("greet", lambda name: f"Hello, {name}!", "Greet someone")
mcp.initialize()

# 2. Wrap with JSON-RPC server (HTTP transport)
settings = JSONRPCSettings(host="0.0.0.0", port=8000, name="MyJSONRPCServer")
server = JSONRPCServerFactory.create(JSONRPCTransport.HTTP, settings, mcp_server=mcp)

# 3. Run server
server.run()  # Starts FastAPI server at http://localhost:8000/jsonrpc
```

### JSON-RPC Transports

| Transport | Use Case | Example |
|-----------|----------|---------|
| **HTTP** | Web APIs, remote access | `JSONRPCTransport.HTTP` |
| **Stdio** | Claude Desktop, Cursor, local MCP clients | `JSONRPCTransport.STDIO` |

#### HTTP Transport

```python
# Exposes POST /jsonrpc endpoint
server = JSONRPCServerFactory.create(JSONRPCTransport.HTTP, settings, mcp_server=mcp)
server.run()

# Client usage:
# curl -X POST http://localhost:8000/jsonrpc \
#   -H "Content-Type: application/json" \
#   -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

#### Stdio Transport

```python
# For MCP client integration (Claude Desktop, Cursor)
server = JSONRPCServerFactory.create(JSONRPCTransport.STDIO, settings, mcp_server=mcp)
server.run()  # Reads from stdin, writes to stdout
```

### JSON-RPC Protocol Methods

When wrapping an MCP server, these methods are automatically registered:

| Method | Description | Example |
|--------|-------------|---------|
| `initialize` | Initialize MCP session | `{"method": "initialize"}` |
| `initialized` | Client ready notification | `{"method": "initialized"}` |
| `tools/list` | List available tools | `{"method": "tools/list"}` |
| `tools/call` | Execute a tool | `{"method": "tools/call", "params": {"name": "add", "arguments": {"a": 5, "b": 3}}}` |
| `ping` | Health check | `{"method": "ping"}` |

### Custom Methods

Register custom methods alongside MCP protocol methods:

```python
server = JSONRPCServerFactory.create(JSONRPCTransport.HTTP, settings, mcp_server=mcp)

# Add custom methods with chaining
(server
    .register_method("echo", lambda p: p.get("message"))
    .register_method("time", lambda p: {"time": "2025-12-05T10:00:00Z"})
    .register_method("version", lambda p: {"version": "1.0.0"}))

server.run()
```

### JSON-RPC Request/Response Format

#### Single Request
```json
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {"name": "add", "arguments": {"a": 5, "b": 3}},
    "id": 1
}
```

#### Single Response
```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {"content": [{"type": "text", "text": "8"}]}
}
```

#### Batch Request
```json
[
    {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "add", "arguments": {"a": 1, "b": 2}}, "id": 1},
    {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "add", "arguments": {"a": 3, "b": 4}}, "id": 2}
]
```

#### Batch Response
```json
[
    {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "3"}]}},
    {"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": "7"}]}}
]
```

#### Notification (no response)
```json
{"jsonrpc": "2.0", "method": "log", "params": {"message": "User action"}}
```

### JSON-RPC Error Codes

| Code | Name | Description |
|------|------|-------------|
| -32700 | Parse error | Invalid JSON |
| -32600 | Invalid Request | Not a valid Request object |
| -32601 | Method not found | Method doesn't exist |
| -32602 | Invalid params | Invalid method parameters |
| -32603 | Internal error | Internal JSON-RPC error |
| -32001 | Tool not found | MCP tool doesn't exist |
| -32002 | Tool execution error | Tool execution failed |

### JSON-RPC API Reference

#### JSONRPCSettings

```python
@dataclass
class JSONRPCSettings:
    host: str = "127.0.0.1"      # HTTP transport only
    port: int = 8000             # HTTP transport only
    name: str = "jsonrpc-server" # Server name
    version: str = "1.0.0"       # Server version
    extra_params: Dict = {}      # Additional params
```

#### JSONRPCServerFactory

```python
# Create HTTP or Stdio server
server = JSONRPCServerFactory.create(
    transport: JSONRPCTransport,  # HTTP or STDIO
    settings: JSONRPCSettings,
    mcp_server: Optional[MCPServer] = None
)

# Create mock server for testing
mock = JSONRPCServerFactory.create_mock(
    settings: Optional[JSONRPCSettings] = None,
    mcp_server: Optional[MCPServer] = None
)
```

#### JSONRPCServer Methods

```python
# Register custom method (returns self for chaining)
server.register_method(name: str, handler: Callable) -> JSONRPCServer

# Handle JSON-RPC request string
response = server.handle_request(data: str) -> Optional[str]

# Start server (transport-specific)
server.run() -> None
```

### JSON-RPC Examples

#### Python Client

```python
import requests
import json

class JSONRPCClient:
    def __init__(self, url: str):
        self.url = url
        self.request_id = 0

    def call(self, method: str, params: dict = None) -> dict:
        self.request_id += 1
        response = requests.post(self.url, json={
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        })
        return response.json().get("result")

# Usage
client = JSONRPCClient("http://localhost:8000/jsonrpc")
tools = client.call("tools/list")
result = client.call("tools/call", {"name": "add", "arguments": {"a": 5, "b": 3}})
```

#### Testing with MockJSONRPCServer

```python
from axiompy.servers import JSONRPCServerFactory, JSONRPCSettings
import json

# Create mock server for testing
server = JSONRPCServerFactory.create_mock()
server.register_method("echo", lambda p: p.get("msg"))

# Test request handling
request = json.dumps({"jsonrpc": "2.0", "method": "echo", "params": {"msg": "hello"}, "id": 1})
response = server.handle_request(request)
parsed = json.loads(response)

assert parsed["result"] == "hello"
assert parsed["id"] == 1

# Mock tracks requests/responses
assert len(server.requests_received) == 1
assert len(server.responses_sent) == 1
```

#### Claude Desktop Integration

Create a stdio-based MCP server for Claude Desktop:

```python
#!/usr/bin/env python3
# my_mcp_server.py

from axiompy.servers import (
    JSONRPCServerFactory, JSONRPCTransport, JSONRPCSettings,
    MCPServerFactory, MCPServerType, MCPServerSettings
)

# Create tools
mcp = MCPServerFactory.create(MCPServerType.OPENAI, MCPServerSettings(name="MyTools"))
mcp.register_tool("search", lambda query: f"Results for: {query}", "Search the web")
mcp.register_tool("calculate", lambda expr: eval(expr), "Calculate expression")
mcp.initialize()

# Create stdio server
settings = JSONRPCSettings(name="my-mcp-server")
server = JSONRPCServerFactory.create(JSONRPCTransport.STDIO, settings, mcp_server=mcp)

if __name__ == "__main__":
    server.run()
```

Add to Claude Desktop config (`~/.config/claude/config.json`):
```json
{
    "mcpServers": {
        "my-tools": {
            "command": "python",
            "args": ["/path/to/my_mcp_server.py"]
        }
    }
}
```

---

## 🚧 Future Roadmap

### Upcoming Features

- [ ] **FastMCP Implementation**: Native FastAPI integration for MCP servers
  - Direct FastAPI/Starlette support for streaming responses
  - Built-in WebSocket support for real-time tool execution
  - OpenAI SDK compatibility for agent frameworks
  - Server-Sent Events (SSE) support for long-running operations

- [ ] **Integration Tests**: Live Ollama integration testing
  - Docker-based Ollama test environment
  - Real LLM reasoning validation
  - Performance benchmarks

- [ ] **Acme-Specific Adapters**: Production hardening for Acme use cases
  - Supply chain data access tools
  - Customer intelligence workflows
  - Inventory optimization patterns
  - Multi-region deployment support

- [ ] **Advanced Features**:
  - Custom sequencing strategies with ML models
  - Distributed session management
  - Real-time tool monitoring and metrics
  - Advanced audit logging and compliance tracking

---

## License

Part of the AxiomPy library. See main README for license information.

---

**Last Updated:** 2025-12-05
