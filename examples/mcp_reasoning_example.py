# @!documentation

"""
MCP Reasoning Middleware Examples

Demonstrates how to add reasoning capabilities to MCP servers:
1. Wrapping a base server with reasoning middleware
2. Default SLM (Simple Logic Model) behavior
3. Custom validators
4. Custom sequencers
5. Request pipelining

The reasoning middleware pattern allows optional tool validation
and sequencing without modifying the base MCP server implementation.
"""

from axiompy.result import Err, Ok
from axiompy.servers import MCPServerFactory, MCPServerSettings, MCPServerType
from axiompy.servers.mcp_reasoning import (
    MCPPipelineConfig,
    MCPReasoningMiddleware,
    RiskLevel,
    SimpleMCPReasoning,
    ToolCategory,
)


def example_default_reasoning():
    """Example 1: Using default SLM reasoning with middleware."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Default SLM Reasoning Middleware")
    print("=" * 70)

    # Create base MCP server
    settings = MCPServerSettings(name="ExampleAgentTools")
    base_server = MCPServerFactory.create(MCPServerType.OPENAI, settings)

    # Wrap with reasoning middleware
    reasoning = SimpleMCPReasoning()
    server = MCPReasoningMiddleware(base_server, reasoning)
    print(f"✓ Created middleware-wrapped server: {server.settings.name}")

    # Register tools with dependencies (via middleware)
    print("\nRegistering tools with dependencies...")

    server.register_tool(
        "get_customer_profile",
        func=lambda: {"id": "cust_123", "name": "John Doe"},
        description="Fetch customer profile from database",
        prerequisites=[],
        provides_data=["customer"],
        cost=2,
    )

    server.register_tool(
        "query_inventory",
        func=lambda: {"product": "Acme Air Max", "stock": 50},
        description="Check product inventory",
        prerequisites=[],
        provides_data=["inventory"],
        cost=3,
    )

    server.register_tool(
        "get_recommendation",
        func=lambda: {"products": ["Acme Air Max", "Acme React"]},
        description="Get recommendation engine results",
        prerequisites=["get_customer_profile"],
        requires_data=["customer"],
        provides_data=["recommendation"],
        cost=5,
    )

    server.register_tool(
        "apply_discount",
        func=lambda: {"discount": 0.15},
        description="Calculate applicable discounts",
        prerequisites=["get_customer_profile"],
        requires_data=["customer"],
        provides_data=["discount"],
        cost=2,
        risk_level=RiskLevel.MEDIUM,
    )

    server.register_tool(
        "send_offer",
        func=lambda: {"status": "sent", "offer_id": "offer_456"},
        description="Send personalized offer to customer",
        prerequisites=["get_recommendation", "apply_discount"],
        requires_data=["recommendation", "discount"],
        cost=1,
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
    )

    # Initialize server
    server.initialize()

    # Create session
    session = server.create_session("example_agent_001")
    print(f"✓ Session created: {session.session_id}")

    # Suggest tool sequence
    print("\nSuggesting tool sequence...")
    sequence_result = server.suggest_tool_sequence("Send personalized offer", session)

    if sequence_result.is_ok():
        sequence = sequence_result.unwrap()
        print("✓ Suggested sequence:")
        for i, tool in enumerate(sequence, 1):
            tool_info = server.reasoning_metadata.get(tool)
            if tool_info:
                print(f"  {i}. {tool} (cost: {tool_info.cost}, risk: {tool_info.risk_level.value})")
            else:
                print(f"  {i}. {tool}")
    else:
        print(f"✗ Error: {sequence_result.get_error()}")

    # Estimate cost
    if sequence_result.is_ok():
        cost_result = server.estimate_cost(sequence_result.unwrap())
        if cost_result.is_ok():
            print(f"\n✓ Total estimated cost: {cost_result.unwrap()}")

    # Try to execute send_offer first (should fail - prerequisites not met)
    print("\n1. Attempting to send offer first (should fail - prerequisites not met):")
    try:
        result = server.execute_tool("send_offer", session)
        print(f"   Result: ✓ {result}")
    except Exception as e:
        print(f"   Result: ✗ Failed (as expected): {str(e)[:50]}...")

    # Execute in correct order
    print("\n2. Executing in correct sequence:")
    tools_to_execute = ["get_customer_profile", "get_recommendation", "apply_discount"]
    for tool_name in tools_to_execute:
        try:
            result = server.execute_tool(tool_name, session)
            print(f"   ✓ {tool_name} succeeded: {str(result)[:40]}...")
        except Exception as e:
            print(f"   ✗ {tool_name} failed: {str(e)[:40]}...")

    # Show session summary
    summary_result = server.get_session_summary(session)
    if summary_result.is_ok():
        summary = summary_result.unwrap()
        print("\n✓ Session Summary:")
        print(f"   Total calls: {summary['total_calls']}")
        print(f"   Successful: {summary['successful_calls']}")
        print(f"   Failed: {summary['failed_calls']}")
        print(f"   Total cost: {summary['total_cost']}")


def example_custom_validator():
    """Example 2: Using custom validators for business logic."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Custom Validators with Middleware")
    print("=" * 70)

    # Create base server and wrap with reasoning
    settings = MCPServerSettings(name="DiscountTools")
    base_server = MCPServerFactory.create(MCPServerType.OPENAI, settings)
    reasoning = SimpleMCPReasoning()
    server = MCPReasoningMiddleware(base_server, reasoning)

    # Register tools via middleware
    server.register_tool(
        "get_customer_profile",
        func=lambda: {"id": "cust_123", "age": 25},
        description="Get customer profile",
        provides_data=["customer"],
        cost=2,
    )

    server.register_tool(
        "apply_discount",
        func=lambda age=25: {"discount": 0.15},
        description="Apply discount to customer",
        prerequisites=["get_customer_profile"],
        requires_data=["customer"],
        provides_data=["discount"],
        cost=2,
        risk_level=RiskLevel.MEDIUM,
    )

    # Register CUSTOM validator for discount business rule
    def validate_discount_eligible(tool_meta, parameters):
        """Custom validator: only apply discount if customer age >= 18."""
        customer_age = parameters.get("age", 0)
        if customer_age < 18:
            return Err("Customer must be 18+ for discount eligibility")
        return Ok(True)

    server.register_custom_validator("apply_discount", validate_discount_eligible)
    print("✓ Registered custom validator for 'apply_discount'")

    # Initialize and create session
    server.initialize()
    session = server.create_session("discount_test")

    # Test with valid age
    print("\nTest 1: Customer age 25 (should pass)")
    try:
        result = server.execute_tool("apply_discount", session, age=25)
        print(f"Result: ✓ Valid - {result}")
    except Exception as e:
        print(f"Result: ✗ Invalid - {str(e)[:50]}...")

    # Test with invalid age
    print("\nTest 2: Customer age 16 (should fail)")
    try:
        result = server.execute_tool("apply_discount", session, age=16)
        print(f"Result: ✓ Valid - {result}")
    except Exception as e:
        print(f"Result: ✗ Invalid (as expected) - {str(e)[:50]}...")


def example_custom_sequencer():
    """Example 3: Using custom sequencer for ML-based tool ordering."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Custom Sequencer with Middleware")
    print("=" * 70)

    # Create base server and wrap with reasoning
    settings = MCPServerSettings(name="SequencingTools")
    base_server = MCPServerFactory.create(MCPServerType.OPENAI, settings)
    reasoning = SimpleMCPReasoning()
    server = MCPReasoningMiddleware(base_server, reasoning)

    # Register tools
    for tool_name in ["get_customer_profile", "query_inventory", "get_recommendation"]:
        server.register_tool(
            tool_name,
            func=lambda: {"status": "ok"},
            description=f"{tool_name} tool",
            cost=2,
        )

    # Custom sequencer: prioritize by cost efficiency
    def cost_optimized_sequencer(goal, reasoning_session):
        """Order tools by cost (cheapest first) for efficiency."""
        print(f"  → Custom sequencer invoked for goal: '{goal}'")
        available_tools = list(reasoning.tool_metadata.keys())
        sorted_tools = sorted(available_tools, key=lambda t: reasoning.tool_metadata[t].cost)
        return Ok(sorted_tools)

    server.register_custom_sequencer(cost_optimized_sequencer)
    print("✓ Registered custom sequencer (cost-optimized)")

    # Initialize and test sequencing
    server.initialize()
    session = server.create_session("sequencer_test")
    result = server.suggest_tool_sequence("Optimize by cost", session)

    if result.is_ok():
        print(f"\n✓ Tool sequence (cost-optimized): {result.unwrap()}")
    else:
        print(f"\n✗ Error: {result.get_error()}")


def example_pipelining():
    """Example 4: Request pipelining with reasoning middleware."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Request Pipelining with Middleware")
    print("=" * 70)

    # Create base server and wrap with reasoning
    settings = MCPServerSettings(name="DataProcessing")
    base_server = MCPServerFactory.create(MCPServerType.OPENAI, settings)
    reasoning = SimpleMCPReasoning()
    server = MCPReasoningMiddleware(base_server, reasoning)

    # Register tools with pipeline stages
    server.register_tool(
        "fetch_data",
        func=lambda: {"rows": 1000},
        description="Fetch raw data",
        provides_data=["raw_data"],
        cost=3,
    )

    server.register_tool(
        "transform_data",
        func=lambda: {"transformed_rows": 1000},
        description="Transform raw data",
        prerequisites=["fetch_data"],
        requires_data=["raw_data"],
        provides_data=["transformed_data"],
        cost=5,
    )

    server.register_tool(
        "validate_data",
        func=lambda: {"valid_rows": 950},
        description="Validate transformed data",
        prerequisites=["transform_data"],
        requires_data=["transformed_data"],
        provides_data=["validated_data"],
        cost=2,
    )

    server.register_tool(
        "store_data",
        func=lambda: {"stored": 950},
        description="Store validated data",
        prerequisites=["validate_data"],
        requires_data=["validated_data"],
        cost=1,
        risk_level=RiskLevel.MEDIUM,
    )

    # Initialize and create session
    server.initialize()
    session = server.create_session("pipeline_001")

    # Get pipeline sequence
    result = server.suggest_tool_sequence("Process data pipeline", session)
    if result.is_ok():
        pipeline = result.unwrap()
        print(f"✓ Data Pipeline Stages: {' → '.join(pipeline)}")

        # Estimate total cost
        cost_result = server.estimate_cost(pipeline)
        if cost_result.is_ok():
            print(f"✓ Total pipeline cost: {cost_result.unwrap()}")

        # Show each stage
        print("\nPipeline Stages:")
        for i, tool in enumerate(pipeline, 1):
            tool_meta = server.reasoning_metadata.get(tool)
            if tool_meta:
                print(
                    f"  Stage {i}: {tool}"
                    f"\n    → Requires: {tool_meta.requires_data or 'none'}"
                    f"\n    → Provides: {tool_meta.provides_data}"
                    f"\n    → Cost: {tool_meta.cost}"
                )
            else:
                print(f"  Stage {i}: {tool}")


if __name__ == "__main__":
    print("=" * 70)
    print("MCP REASONING LAYER - EXAMPLES")
    print("=" * 70)

    example_default_reasoning()
    example_custom_validator()
    example_custom_sequencer()
    example_pipelining()

    print("\n" + "=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)
