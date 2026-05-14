"""
AxiomPy Reasoning Example - AI-Powered Query Agent

This example demonstrates how to build an AI-powered query agent using AxiomPy's
reasoning components without external dependencies.

Features:
- Multiple dataset services with self-describing metadata
- Provider-agnostic AI client (works with Ollama, OpenAI, Anthropic)
- Intelligent dataset routing based on keywords
- Dynamic SQL generation from natural language
- SQL validation before execution
- AI-generated insights from results

Requirements:
- Python 3.10+
- AxiomPy (installed)
- An AI provider (Ollama running locally, or OpenAI/Anthropic API key)

Setup:
1. Install dependencies: pip install -r requirements.txt
2. Start Ollama: ollama serve (in another terminal)
3. Pull a model: ollama pull mistral
4. Run this example: python examples/reasoning_example.py
"""

import logging
from typing import Any

from axiompy.reasoning import (
    BaseDatasetService,
    DatasetMetadata,
    ReasoningFactory,
    ScopeMetadata,
    TableSchemaMetadata,
)
from axiompy.reasoning.agents import QueryAgent

# AxiomPy imports
from axiompy.io.database import DatabaseFactory, DatabaseSettings, DatabaseType

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==================== Dataset Services ====================


class SalesDataService(BaseDatasetService):
    """
    Sales data service demonstrating BaseDatasetService implementation.

    This is a simple in-memory example that could easily be backed by
    a real database.
    """

    dataset_name = "sales"
    description = "E-commerce Sales Data (2023-2024)"

    def __init__(self):
        """Initialize with sample data."""
        self.data = [
            {
                "date": "2024-01",
                "region": "North",
                "product": "Laptop",
                "amount": 1200,
                "quantity": 3,
            },
            {
                "date": "2024-01",
                "region": "South",
                "product": "Mouse",
                "amount": 150,
                "quantity": 50,
            },
            {
                "date": "2024-02",
                "region": "North",
                "product": "Monitor",
                "amount": 800,
                "quantity": 8,
            },
            {
                "date": "2024-02",
                "region": "East",
                "product": "Keyboard",
                "amount": 300,
                "quantity": 30,
            },
            {
                "date": "2024-03",
                "region": "West",
                "product": "Laptop",
                "amount": 2400,
                "quantity": 2,
            },
        ]

    def query(self, sql: str, limit: int = None) -> list[dict[str, Any]]:
        """
        Execute query on in-memory data.

        For demonstration, supports simple filtering:
        - SELECT * FROM sales
        - SELECT * FROM sales WHERE region = 'North'
        """
        # Simple query implementation for demo
        results = self.data.copy()

        # Filter by WHERE clause (very basic)
        if "WHERE region =" in sql:
            region = sql.split("WHERE region =")[1].strip().strip("'\"")
            results = [r for r in results if r["region"] == region]

        # Apply limit
        if limit:
            results = results[:limit]

        return results

    def get_capabilities(self) -> list[str]:
        """List supported operations."""
        return [
            "regional_analysis",
            "product_analysis",
            "temporal_trends",
            "sales_forecasting",
            "revenue_analysis",
        ]

    def get_metadata(self) -> DatasetMetadata:
        """Return rich metadata for AI reasoning."""
        return DatasetMetadata(
            dataset="sales",
            description="E-commerce sales data with regional and product dimensions",
            scope=ScopeMetadata(
                geographic="Multi-region (North, South, East, West)",
                temporal="2024 (January-March)",
                domain="E-commerce / Retail",
            ),
            schema={
                "sales": TableSchemaMetadata(
                    columns={
                        "date": "VARCHAR - Month in YYYY-MM format",
                        "region": "VARCHAR - Geographic region (North, South, East, West)",
                        "product": "VARCHAR - Product name",
                        "amount": "DECIMAL - Sales amount in USD",
                        "quantity": "INTEGER - Number of items sold",
                    },
                    description="Sales transaction data",
                    row_count=5,
                )
            },
            capabilities=self.get_capabilities(),
            keywords={
                "regions": ["north", "south", "east", "west"],
                "products": ["laptop", "monitor", "keyboard", "mouse"],
                "metrics": ["sales", "revenue", "quantity", "amount"],
            },
            constraints=[
                "Data available for 2024 Q1 only",
                "Amounts are in USD",
                "Monthly granularity",
            ],
        )


class EmployeeDataService(BaseDatasetService):
    """
    Employee data service demonstrating another dataset implementation.
    """

    dataset_name = "employees"
    description = "Company Employee Directory and Performance"

    def __init__(self):
        """Initialize with sample data."""
        self.data = [
            {
                "emp_id": 1,
                "name": "Alice Johnson",
                "department": "Engineering",
                "salary": 95000,
                "tenure": 5,
            },
            {"emp_id": 2, "name": "Bob Smith", "department": "Sales", "salary": 75000, "tenure": 3},
            {
                "emp_id": 3,
                "name": "Carol Williams",
                "department": "Engineering",
                "salary": 105000,
                "tenure": 7,
            },
            {"emp_id": 4, "name": "David Brown", "department": "HR", "salary": 65000, "tenure": 2},
            {"emp_id": 5, "name": "Eve Davis", "department": "Sales", "salary": 80000, "tenure": 4},
        ]

    def query(self, sql: str, limit: int = None) -> list[dict[str, Any]]:
        """Execute query on employee data."""
        results = self.data.copy()

        # Simple WHERE clause filtering
        if "WHERE department =" in sql:
            dept = sql.split("WHERE department =")[1].strip().strip("'\"")
            results = [r for r in results if r["department"] == dept]

        if limit:
            results = results[:limit]

        return results

    def get_capabilities(self) -> list[str]:
        """List supported operations."""
        return [
            "department_analysis",
            "compensation_analysis",
            "tenure_analysis",
            "headcount_reporting",
            "performance_metrics",
        ]

    def get_metadata(self) -> DatasetMetadata:
        """Return rich metadata for AI reasoning."""
        return DatasetMetadata(
            dataset="employees",
            description="Company employee directory with compensation and performance data",
            scope=ScopeMetadata(
                geographic="Corporate headquarters", domain="Human Resources / Company Operations"
            ),
            schema={
                "employees": TableSchemaMetadata(
                    columns={
                        "emp_id": "INTEGER - Employee ID",
                        "name": "VARCHAR - Full name",
                        "department": "VARCHAR - Department (Engineering, Sales, HR)",
                        "salary": "DECIMAL - Annual salary in USD",
                        "tenure": "INTEGER - Years with company",
                    },
                    description="Employee master data",
                    row_count=5,
                )
            },
            capabilities=self.get_capabilities(),
            keywords={
                "departments": ["engineering", "sales", "hr", "operations"],
                "roles": ["engineer", "sales", "manager", "analyst"],
                "metrics": ["salary", "tenure", "compensation", "headcount"],
            },
        )


# ==================== Main Example ====================


def main():
    """Run the reasoning example."""
    print("\n" + "=" * 80)
    print("AxiomPy Reasoning Example - AI-Powered Query Agent")
    print("=" * 80 + "\n")

    # Step 1: Create dataset services
    print("Step 1: Creating dataset services...")
    sales_service = SalesDataService()
    employees_service = EmployeeDataService()
    print("  ✓ Sales service created")
    print("  ✓ Employee service created")

    # Step 2: Create AI client
    print("\nStep 2: Creating AI client...")
    print("  Attempting to use local Ollama (make sure 'ollama serve' is running)...")
    try:
        ai_client = ReasoningFactory.create(ReasoningProvider.OLLAMA, model="mistral")
        print("  ✓ AI client created (Ollama)")
    except Exception as e:
        print(f"  ✗ Failed to connect to Ollama: {e}")
        print("\n  To use this example:")
        print("    1. Install Ollama: https://ollama.ai")
        print("    2. Start Ollama: ollama serve")
        print("    3. Pull a model: ollama pull mistral")
        print("    4. Run this script again")
        print("\n  Alternative: Use OpenAI")
        print("    ai_client = ReasoningFactory.create_openai(api_key='sk-...', model='gpt-4')")
        return

    # Step 3: Create query agent
    print("\nStep 3: Creating query agent...")
    agent = QueryAgent(
        ai_client=ai_client,
        datasets={"sales": sales_service, "employees": employees_service},
        enable_planning=True,
        enable_insights=True,
    )
    print("  ✓ Query agent created with 2 datasets")

    # Step 4: Show available datasets
    print("\nStep 4: Available datasets:")
    for name in agent.get_dataset_names():
        capabilities = agent.get_dataset_capabilities()[name]
        print(f"  • {name}: {', '.join(capabilities)}")

    # Step 5: Execute queries
    print("\nStep 5: Executing natural language queries...\n")

    queries = [
        "What are the sales by region?",
        "How many employees are in engineering?",
        "Show me the sales data",
    ]

    for i, question in enumerate(queries, 1):
        print(f"  Query {i}: {question}")
        try:
            result = agent.execute_query(question)

            print(f"    Dataset: {result['dataset']}")
            print(f"    Generated SQL: {result['sql'][:60]}...")
            print(f"    Results: {len(result['results'])} rows")

            if result["results"]:
                first_row = result["results"][0]
                print(f"    Sample: {first_row}")

            if result["insights"]:
                print(f"    Insights: {result['insights'][:100]}...")

            print()

        except Exception as e:
            print(f"    ✗ Error: {e}\n")

    # Step 6: Show metadata
    print("\nStep 6: Dataset Metadata (for AI reasoning):")
    for dataset_name, metadata in agent.get_datasets_metadata().items():
        print(f"\n  {dataset_name.upper()}:")
        print(f"    Scope: {metadata.scope.geographic}")
        if metadata.scope.domain:
            print(f"    Domain: {metadata.scope.domain}")
        print(f"    Tables: {', '.join(metadata.schema.keys())}")
        if metadata.keywords:
            all_keywords = []
            for kw_list in metadata.keywords.values():
                all_keywords.extend(kw_list)
            print(f"    Keywords: {', '.join(all_keywords[:5])}")

    print("\n" + "=" * 80)
    print("Example Complete!")
    print("=" * 80)
    print("\nKey Points:")
    print("  • BaseDatasetService provides standard interface for datasets")
    print("  • DatasetMetadata enables AI reasoning about data")
    print("  • QueryAgent intelligently routes questions to datasets")
    print("  • AIClient works with any LLM provider (Ollama, OpenAI, Anthropic)")
    print("  • No external data sources required - works with in-memory data")
    print("\nNext Steps:")
    print("  • Replace in-memory data with real database (using axiompy.io.database)")
    print("  • Add more complex SQL generation logic")
    print("  • Integrate with your application")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
