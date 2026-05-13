#!/usr/bin/env python3
"""
Quick test script to verify SQL generation and execution works.
This runs non-interactively for automated testing.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ecommerce.config.settings import (
    AI_MODEL,
    DATABASE_PATH,
)
from ecommerce.services.ecommerce_service import EcommerceService

from axiompy.io.database import DatabaseFactory, DatabaseSettings, DatabaseType
from axiompy.reasoning.agents.query import QueryAgent
from axiompy.reasoning.factory import ReasoningFactory


def main():
    """Run a test query to verify the fix."""
    print("=" * 80)
    print("Testing SQL Generation and Execution")
    print("=" * 80)

    # Initialize services
    print("\n1. Initializing AI client...")
    ai_client = ReasoningFactory.create_ollama(model=AI_MODEL)
    print(f"   ✓ Using model: {AI_MODEL}")

    print("\n2. Initializing database service...")
    db_settings = DatabaseSettings(database=str(DATABASE_PATH))
    db = DatabaseFactory.create(DatabaseType.SQLITE, db_settings)
    ecommerce_service = EcommerceService(db)
    print(f"   ✓ Database: {DATABASE_PATH}")

    print("\n3. Creating query agent...")
    agent = QueryAgent(
        ai_client=ai_client,
        datasets={"ecommerce": ecommerce_service},
    )
    print("   ✓ Agent ready")

    # Test queries
    test_queries = [
        "What are the top 5 products?",
        "Show me the top 5 categories by revenue",
        "Who are the top 3 customers by total spending?",
    ]

    for i, question in enumerate(test_queries, 1):
        print("\n" + "=" * 80)
        print(f"Test Query {i}: {question}")
        print("=" * 80)

        try:
            result = agent.execute_query(question)

            print("\n✓ Query executed successfully!")
            print("\nGenerated SQL:")
            print(f"  {result.get('sql', 'N/A')}")

            results = result.get("results", [])
            print(f"\nResults: {len(results)} rows")
            if results:
                print("\nTop 5 results:")
                for idx, row in enumerate(results[:5], 1):
                    print(f"  {idx}. {row}")

            insights = result.get("insights")
            if insights:
                print("\nInsights:")
                if isinstance(insights, dict):
                    print(f"  {insights.get('summary', 'N/A')}")
                else:
                    print(f"  {insights}")

        except Exception as e:
            print(f"\n✗ Query failed: {e}")
            import traceback

            traceback.print_exc()
            return 1

    print("\n" + "=" * 80)
    print("All tests passed! ✓")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
