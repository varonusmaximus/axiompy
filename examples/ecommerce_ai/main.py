#!/usr/bin/env python
"""Main demo script for E-commerce AI Intelligence System.

Demonstrates AxiomPy reasoning framework on realistic e-commerce data.
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from axiompy.reasoning import ReasoningFactory
from axiompy.reasoning.agents import QueryAgent
from ecommerce.config.settings import (
    AI_MODEL,
    AI_PROVIDER,
    DATABASE_PATH,
    DATABASE_TYPE,
    ENABLE_INSIGHTS,
    ENABLE_PLANNING,
)
from ecommerce.services.ecommerce_service import EcommerceService

from axiompy.io.database import DatabaseFactory, DatabaseSettings, DatabaseType


def demo_ecommerce_reasoning():
    """Demo AxiomPy reasoning on e-commerce data."""

    print("\n" + "=" * 80)
    print("🛍️  E-Commerce Data Intelligence Demo - AxiomPy Reasoning Framework")
    print("=" * 80)

    # Check if database exists
    if not DATABASE_PATH.exists():
        print("\n❌ Database not found!")
        print(f"   Expected: {DATABASE_PATH}")
        print("   Run this first: python setup.py")
        return

    try:
        # 1. Connect to database
        print("\n1️⃣  Connecting to database...")
        db_settings = DatabaseSettings(database=str(DATABASE_PATH))
        db = DatabaseFactory.create(DatabaseType.SQLITE, db_settings)
        service = EcommerceService(db)
        db_size_mb = DATABASE_PATH.stat().st_size / (1024 * 1024)
        print(f"   ✓ Connected to {DATABASE_PATH.name} ({db_size_mb:.1f} MB)")

        # 2. Create AI client
        print("\n2️⃣  Setting up AI client...")
        print(f"   Provider: {AI_PROVIDER.upper()}")
        print(f"   Model: {AI_MODEL}")

        try:
            if AI_PROVIDER == "ollama":
                ai = ReasoningFactory.create_ollama(model=AI_MODEL)
            elif AI_PROVIDER == "openai":
                ai = ReasoningFactory.create_openai(model=AI_MODEL)
            elif AI_PROVIDER == "anthropic":
                ai = ReasoningFactory.create_anthropic(model=AI_MODEL)
            else:
                raise ValueError(f"Unknown provider: {AI_PROVIDER}")
            print(f"   ✓ Using {AI_PROVIDER}")
        except Exception as e:
            print(f"   ⚠️  AI provider not available: {e}")
            print("   (This is okay for demo - will show SQL without insights)")
            ai = None

        # 3. Create QueryAgent
        print("\n3️⃣  Creating intelligent query agent...")
        agent = QueryAgent(
            ai_client=ai or ReasoningFactory.create_ollama(),
            datasets={"ecommerce": service},
            enable_planning=ENABLE_PLANNING,
            enable_insights=ENABLE_INSIGHTS and bool(ai),
            max_retries=2,
        )
        print("   ✓ Agent ready")

        # 4. Show capabilities
        print("\n4️⃣  Dataset Capabilities:")
        for cap in service.get_capabilities():
            print(f"   ✓ {cap}")

        # 5. Show metadata
        print("\n5️⃣  Dataset Metadata:")
        metadata = service.get_metadata()
        print(f"   • Scope: {metadata.scope.geographic}, {metadata.scope.temporal}")
        print(f"   • Tables: {', '.join(metadata.schema.keys())}")
        total_records = sum(t.row_count for t in metadata.schema.values() if t.row_count)
        print(f"   • Total Records: {total_records:,}")

        # 6. Sample queries
        print("\n6️⃣  Sample Queries:")
        sample_queries = [
            "What are the top 5 product categories by revenue?",
            "How many customers do we have in each country?",
            "What is the average order value?",
        ]

        for i, query in enumerate(sample_queries, 1):
            print(f"   {i}. {query}")

        # 7. Execute sample query
        print("\n7️⃣  Executing First Query...")
        print(f'   Question: "{sample_queries[0]}"')

        if ai:
            try:
                result = agent.execute_query(sample_queries[0])

                print("\n   📊 Results:")
                print(f"   Generated SQL:\n   {result['sql']}\n")

                if result["results"]:
                    print("   Data:")
                    for row in result["results"][:5]:
                        print(f"   • {row}")

                if result["insights"]:
                    print(f"\n   🤖 AI Insights:\n   {result['insights']}")
            except Exception as e:
                print(f"   ⚠️  AI query failed ({e}), showing direct SQL instead...\n")
                query_result = service.query(
                    """
                    SELECT p.category, COUNT(*) as order_count, SUM(o.total_amount) as total_revenue
                    FROM orders o
                    JOIN products p ON o.product_id = p.product_id
                    WHERE o.status = 'Delivered'
                    GROUP BY p.category
                    ORDER BY total_revenue DESC
                    LIMIT 5
                """
                )

                print("   📊 Top Categories by Revenue:")
                for row in query_result:
                    print(
                        f"   • {row['category']}: {row['order_count']} orders, ${row['total_revenue']:,.2f}"
                    )
        else:
            print("   Running Direct SQL Query (AI not available)...")
            query_result = service.query(
                """
                SELECT p.category, COUNT(*) as order_count, SUM(o.total_amount) as total_revenue
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                WHERE o.status = 'Delivered'
                GROUP BY p.category
                ORDER BY total_revenue DESC
                LIMIT 5
            """
            )

            print("\n   📊 Top Categories by Revenue:")
            for row in query_result:
                print(
                    f"   • {row['category']}: {row['order_count']} orders, ${row['total_revenue']:,.2f}"
                )

        print("\n" + "=" * 80)
        print("✅ Demo Complete!")
        print("=" * 80)

        print("\n💡 What This Demonstrates:")
        print("   ✓ BaseDatasetService implementation")
        print("   ✓ AIClient with provider selection")
        print("   ✓ QueryAgent intelligent routing")
        print("   ✓ Natural language to SQL conversion")
        print("   ✓ SQL validation before execution")
        print("   ✓ AI insight generation")
        print("   ✓ Large-scale data handling (1M records)")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    demo_ecommerce_reasoning()
