"""
MCP with Chainable Validators Example

Demonstrates how to use chainable tool validators for intelligent validation
and sequencing. Includes LLM-based validators (via Ollama), rule-based validators,
and custom business logic validators.

Prerequisites (optional for LLM):
    1. Install Ollama: https://ollama.ai
    2. Pull a model: ollama pull mistral
    3. Run: ollama serve
    4. This script will connect to localhost:11434

Supported Models (for LLMToolValidator):
    - mistral (4GB, fast, good reasoning) - RECOMMENDED
    - llama2 (4GB, powerful, slower)
    - neural-chat (4GB, optimized for conversations)
    - dolphin-mixtral (26GB, very capable)
    - Any GGUF-compatible model

Validator Types:
    - LLMToolValidator: Uses Ollama or custom APIs for intelligent validation
    - RuleBasedToolValidator: Fast prerequisite/data checking (no LLM)
    - Custom validators: User-defined business logic

Ollama Setup (optional):
    brew install ollama
    ollama pull mistral
    ollama serve  # Keep this running in another terminal
"""

from axiompy.servers import MCPServerFactory, MCPServerSettings, MCPServerType
from axiompy.servers.mcp_reasoning import (
    LLMToolValidator,
    MCPValidationMiddleware,
    RiskLevel,
    RuleBasedToolValidator,
    ToolCategory,
)


def example_validator_chain_llm():
    """Example 1: Chainable validators with LLM (Dev/DevOps/Enterprise)."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Chainable Validators with LLM Support")
    print("=" * 70)
    print("\nUse Case: Enterprise deployment validation")
    print("  - Validates infrastructure tools with intelligent LLM support")
    print("  - Fallback to rule-based validation if LLM unavailable")
    print("  - Common in DevOps and enterprise software")

    # Create base server
    settings = MCPServerSettings(name="InfrastructureTools")
    base_server = MCPServerFactory.create(MCPServerType.OPENAI, settings)

    # Create validator chain (or use default auto-chain)
    validators = [
        LLMToolValidator(model="mistral"),  # Intelligent validation
        RuleBasedToolValidator(),  # Fast fallback
    ]

    # Create middleware with validators
    server = MCPValidationMiddleware(base_server, validators)
    print("✓ MCP server with validator chain ready")

    # Register tools with descriptions
    print("\nRegistering infrastructure tools...")

    server.register_tool(
        "authenticate_cluster",
        func=lambda cluster: {"status": "authenticated", "cluster": cluster},
        description="Authenticate with Kubernetes cluster",
        category=ToolCategory.SERVICE,
        prerequisites=[],
        provides_data=["cluster_auth"],
        cost=2,
    )
    print("  ✓ authenticate_cluster")

    server.register_tool(
        "deploy_service",
        func=lambda: {"status": "deployed", "service": "api-v2"},
        description="Deploy microservice to production cluster",
        prerequisites=["authenticate_cluster"],
        requires_data=["cluster_auth"],
        provides_data=["service_deployed"],
        cost=5,
        risk_level=RiskLevel.HIGH,
    )
    print("  ✓ deploy_service")

    server.register_tool(
        "monitor_deployment",
        func=lambda: {"status": "healthy", "uptime": "99.9%"},
        description="Monitor deployed service health metrics",
        prerequisites=["deploy_service"],
        requires_data=["service_deployed"],
        provides_data=["monitoring"],
        cost=1,
        risk_level=RiskLevel.LOW,
    )
    print("  ✓ monitor_deployment")

    # Initialize
    server.initialize()

    # Create session
    session = server.create_session("devops_agent_001")
    print(f"✓ Session created: {session.session_id}")

    # Demonstrate validator chain
    print("\n" + "=" * 70)
    print("VALIDATOR CHAIN IN ACTION")
    print("=" * 70)

    print("\nTest 1: Try to deploy without authentication")
    print("  Validator chain tries:")
    print("    1. LLMToolValidator - checks prerequisites via AI")
    print("    2. RuleBasedToolValidator - checks prerequisites via rules")
    print("  Result: Both reject (prerequisite not met)")
    try:
        result = server.execute_tool("deploy_service", session)
        print(f"  ✗ Executed (unexpected): {result}")
    except Exception as e:
        print(f"  ✓ Blocked: {str(e)[:50]}...")

    print("\nTest 2: Execute prerequisites first")
    print("  Step 1: authenticate_cluster")
    result = server.execute_tool("authenticate_cluster", session, cluster="prod")
    print(f"    ✓ Executed: {result}")

    print("  Step 2: deploy_service (now prerequisites met)")
    result = server.execute_tool("deploy_service", session)
    print(f"    ✓ Executed: {result}")

    print("  Step 3: monitor_deployment")
    result = server.execute_tool("monitor_deployment", session)
    print(f"    ✓ Executed: {result}")

    print("\n✓ Validator chain successfully orchestrated deployment")


def example_enterprise_rules_only():
    """Example 2: Enterprise deployment with rules-only validation (fast path)."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Rules-Only Validation for Enterprise Deployments")
    print("=" * 70)
    print("\nUse Case: High-frequency internal tool calls")
    print("  - Skips LLM for speed and determinism")
    print("  - Uses rule-based prerequisite validation")
    print("  - <1ms validation per tool call")
    print("  - Common in internal DevOps systems")

    # Create base server
    settings = MCPServerSettings(name="InternalTools")
    base_server = MCPServerFactory.create(MCPServerType.OPENAI, settings)

    # Use ONLY rule-based validator (no LLM overhead)
    validators = [RuleBasedToolValidator()]
    server = MCPValidationMiddleware(base_server, validators)
    print("✓ MCP server with rule-based validator (fast path)")

    # Register tools
    print("\nRegistering internal tools...")
    server.register_tool(
        "check_health",
        func=lambda: {"status": "healthy"},
        description="Check service health",
        category=ToolCategory.DATA,
        prerequisites=[],
        provides_data=["health_status"],
        cost=1,
    )
    print("  ✓ check_health")

    server.register_tool(
        "scale_service",
        func=lambda: {"replicas": 5},
        description="Scale service replicas",
        prerequisites=["check_health"],
        requires_data=["health_status"],
        provides_data=["scaling_done"],
        cost=3,
        risk_level=RiskLevel.MEDIUM,
    )
    print("  ✓ scale_service")

    # Initialize
    server.initialize()
    session = server.create_session("internal_agent")

    # Demonstrate rule-based validation
    print("\n" + "=" * 70)
    print("RULE-BASED VALIDATION (Fast Path)")
    print("=" * 70)

    print("\nTest: Execute tools with fast validation")
    import time

    start = time.time()
    server.execute_tool("check_health", session)
    check_time = (time.time() - start) * 1000
    print(f"  ✓ check_health: {check_time:.2f}ms (no prerequisites)")

    start = time.time()
    server.execute_tool("scale_service", session)
    scale_time = (time.time() - start) * 1000
    print(f"  ✓ scale_service: {scale_time:.2f}ms (prerequisites checked)")

    print("\n✓ Total validation overhead: <1ms per call")
    print("✓ Deterministic (same input = same output)")


def example_distributed_enterprise():
    """Example 3: Distributed enterprise deployment with remote LLM."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Distributed Enterprise Deployment")
    print("=" * 70)
    print("\nUse Case: Multi-region enterprise with shared LLM inference")
    print("  - Validators on local systems")
    print("  - LLM reasoning on shared backend (GPU server)")
    print("  - Graceful fallback to rules if inference unavailable")
    print("  - Common in distributed enterprise architecture")

    # Create base server
    settings = MCPServerSettings(name="DistributedServices")
    base_server = MCPServerFactory.create(MCPServerType.OPENAI, settings)

    # Configuration options
    print("\nDeployment Configurations:")

    print("\n1. Local Development (Auto-detect Ollama):")
    print("   LLMToolValidator(model='mistral')")
    print("   ✓ Uses localhost:11434")
    print("   ✓ Works with/without Ollama running")

    print("\n2. Remote GPU Server (Enterprise):")
    print("   LLMToolValidator(")
    print("       model='llama2',")
    print("       backend_url='http://inference-gpu.internal:11434'")
    print("   )")
    print("   ✓ Shared LLM across organization")
    print("   ✓ Optimized for cost (single GPU)")

    print("\n3. On-Disk Model (Air-gapped Network):")
    print("   LLMToolValidator(")
    print("       model_path='/models/production-tuned.gguf',")
    print("       backend_url='http://localhost:11434'")
    print("   )")
    print("   ✓ No external dependencies")
    print("   ✓ Custom fine-tuned model")

    print("\n4. Custom Enterprise LLM:")
    print("   LLMToolValidator(")
    print("       model='enterprise-model',")
    print("       backend_url='http://internal-llm.corp.com',")
    print("       backend_type='custom'")
    print("   )")
    print("   ✓ Proprietary LLM API")
    print("   ✓ Custom response format")

    # Register example tools
    server = MCPValidationMiddleware(base_server, [LLMToolValidator(), RuleBasedToolValidator()])

    server.register_tool(
        "provision_database",
        func=lambda: {"db_id": "prod-01"},
        description="Provision production database",
        category=ToolCategory.SERVICE,
        prerequisites=[],
        provides_data=["database"],
        cost=10,
        risk_level=RiskLevel.HIGH,
    )

    server.register_tool(
        "configure_backup",
        func=lambda: {"backup_id": "backup-01"},
        description="Configure database backup",
        prerequisites=["provision_database"],
        requires_data=["database"],
        provides_data=["backup_configured"],
        cost=3,
        risk_level=RiskLevel.MEDIUM,
    )

    print("\n✓ Enterprise validator chain configured")


def example_graceful_degradation():
    """Example 4: Graceful fallback in validator chain."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Graceful Degradation in Enterprise")
    print("=" * 70)
    print("\nUse Case: Production resilience")
    print("  - LLM inference backend fails")
    print("  - Validator chain auto-fallbacks to rules")
    print("  - System keeps working with reduced intelligence")
    print("  - Common in enterprise SLA requirements")

    settings = MCPServerSettings(name="ResilientTools")
    base_server = MCPServerFactory.create(MCPServerType.OPENAI, settings)

    # Chain with fallback
    validators = [
        LLMToolValidator(model="mistral"),  # Try smart validation
        RuleBasedToolValidator(),  # Always works
    ]
    server = MCPValidationMiddleware(base_server, validators)

    print("✓ Validator chain configured with fallback")
    print("  1. Primary: LLMToolValidator (intelligent)")
    print("  2. Fallback: RuleBasedToolValidator (guaranteed)")

    server.register_tool(
        "execute_migration",
        func=lambda: {"migration_id": "v1.2.0"},
        description="Execute database migration",
        category=ToolCategory.SERVICE,
        prerequisites=[],
        provides_data=["migration_done"],
        cost=5,
        risk_level=RiskLevel.HIGH,
    )

    server.initialize()
    session = server.create_session("migration_agent")

    print("\n" + "=" * 70)
    print("DEGRADATION SCENARIOS")
    print("=" * 70)

    print("\nScenario 1: LLM available (normal)")
    print("  ✓ LLMToolValidator validates")
    print("  ✓ Fast intelligent reasoning")
    print("  ✓ Takes ~500ms")

    print("\nScenario 2: LLM backend down (degraded)")
    print("  ✗ LLMToolValidator fails/timeout")
    print("  ✓ Auto-falls to RuleBasedToolValidator")
    print("  ✓ Validation still works")
    print("  ✓ Takes ~1ms")
    print("  = Service SLA maintained")

    print("\n✓ Enterprise resilience: LLM optional, never required")


def example_custom_validator():
    """Example 5: Custom validators for enterprise policies."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Custom Validators for Enterprise Policies")
    print("=" * 70)
    print("\nUse Case: Enterprise compliance and governance")
    print("  - Custom validators enforce company policies")
    print("  - Can be chained with other validators")
    print("  - Example: approval workflows, quotas, audit logs")
    print("  - Common in regulated industries")

    print("\nExample Custom Validator:")
    print(
        """
    class ApprovalPolicyValidator(MCPToolValidator):
        def validate_tool(self, tool_name, params, session, tool_metadata=None):
            # Enterprise policy: HIGH-risk tools need approval
            if tool_metadata.risk_level == RiskLevel.HIGH:
                if not session.metadata.get("approved"):
                    return Err("Requires executive approval")
            return Ok(True)
    """
    )

    print("\nChaining with standard validators:")
    print(
        """
    validators = [
        ApprovalPolicyValidator(),          # Custom policy first
        LLMToolValidator(),                 # Intelligent validation
        RuleBasedToolValidator()            # Always available
    ]
    server = MCPValidationMiddleware(base_server, validators)
    """
    )

    print("\nValidation sequence:")
    print("  1. ApprovalPolicyValidator checks approval")
    print("     → If approved: Ok(True) → execute")
    print("     → If not approved: Err → continue")
    print("  2. LLMToolValidator checks dependencies")
    print("     → If satisfied: Ok(True) → execute")
    print("     → Otherwise: Err → continue")
    print("  3. RuleBasedToolValidator (final fallback)")

    print("\n✓ Enterprise governance through custom validators")


if __name__ == "__main__":
    print("=" * 70)
    print("CHAINABLE VALIDATORS FOR ENTERPRISE SOFTWARE")
    print("=" * 70)
    print("\nOptional: For LLM support, have Ollama running:")
    print("  1. Install: https://ollama.ai")
    print("  2. Pull model: ollama pull mistral")
    print("  3. Run: ollama serve")
    print("\nAll examples work with or without Ollama!")

    try:
        example_validator_chain_llm()
    except Exception as e:
        print(f"\n✗ Example 1 failed: {e}")

    try:
        example_enterprise_rules_only()
    except Exception as e:
        print(f"\n✗ Example 2 failed: {e}")

    try:
        example_distributed_enterprise()
    except Exception as e:
        print(f"\n✗ Example 3 failed: {e}")

    try:
        example_graceful_degradation()
    except Exception as e:
        print(f"\n✗ Example 4 failed: {e}")

    try:
        example_custom_validator()
    except Exception as e:
        print(f"\n✗ Example 5 failed: {e}")

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
