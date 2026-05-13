"""Demo: SQL Validation with Automatic Retry

This demonstrates the QueryAgent's intelligent retry mechanism:
1. AI generates SQL
2. Validation catches errors (syntax, columns, database)
3. AI receives error feedback and retries automatically
4. Process repeats until valid SQL or max retries reached

This prevents wasted time on invalid queries and improves success rate!
"""

import sqlite3

from axiompy.reasoning import (
    AIClient,
    DatasetMetadata,
    ExampleMetadata,
    QueryAgent,
    ScopeMetadata,
    TableSchemaMetadata,
)
from axiompy.reasoning.base import BaseDatasetService


class MockDatasetService(BaseDatasetService):
    """Mock dataset service for testing validation and retry logic."""

    dataset_name = "test_db"
    description = "Test database for validation demo"

    def __init__(self, db_path=":memory:"):
        """Initialize with in-memory database."""
        self.conn = sqlite3.connect(db_path)
        self._setup_schema()

    def _setup_schema(self):
        """Create test schema."""
        self.conn.execute(
            """
            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                signup_date DATE,
                country TEXT
            )
        """
        )
        self.conn.execute(
            """
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                product_name TEXT,
                total_amount REAL,
                order_date DATE,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            )
        """
        )

        # Insert sample data
        self.conn.execute(
            "INSERT INTO customers VALUES (1, 'Alice', 'alice@example.com', '2023-01-15', 'USA')"
        )
        self.conn.execute(
            "INSERT INTO customers VALUES (2, 'Bob', 'bob@example.com', '2023-02-20', 'UK')"
        )
        self.conn.execute("INSERT INTO orders VALUES (1, 1, 'Widget', 99.99, '2023-03-01')")
        self.conn.execute("INSERT INTO orders VALUES (2, 1, 'Gadget', 149.99, '2023-03-15')")
        self.conn.execute("INSERT INTO orders VALUES (3, 2, 'Doohickey', 79.99, '2023-03-20')")
        self.conn.commit()

    @property
    def db(self):
        """Expose connection for validation."""
        return self.conn

    def query(self, sql: str, limit: int = None) -> list[dict]:
        """Execute SQL query."""
        cursor = self.conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row, strict=False)))
        return results[:limit] if limit else results

    def get_capabilities(self) -> list[str]:
        """Get dataset capabilities."""
        return ["customer_analysis", "order_analysis", "sales_trends"]

    def get_metadata(self) -> DatasetMetadata:
        """Get dataset metadata for AI reasoning."""
        return DatasetMetadata(
            dataset="test_db",
            description="Test database with customers and orders",
            scope=ScopeMetadata(geographic="Global", temporal="2023", domain="E-commerce"),
            schema={
                "customers": TableSchemaMetadata(
                    columns={
                        "customer_id": "INTEGER PRIMARY KEY",
                        "name": "TEXT",
                        "email": "TEXT",
                        "signup_date": "DATE",
                        "country": "TEXT",
                    },
                    description="Customer information",
                    row_count=2,
                ),
                "orders": TableSchemaMetadata(
                    columns={
                        "order_id": "INTEGER PRIMARY KEY",
                        "customer_id": "INTEGER",
                        "product_name": "TEXT",
                        "total_amount": "REAL",
                        "order_date": "DATE",
                    },
                    description="Order transactions",
                    row_count=3,
                ),
            },
            examples=[
                ExampleMetadata(
                    question="Who are our customers?",
                    sql="SELECT name, email, country FROM customers",
                    expected_results="Returns customer list",
                ),
                ExampleMetadata(
                    question="What's the total revenue?",
                    sql="SELECT SUM(total_amount) AS total_revenue FROM orders",
                    expected_results="Returns sum of all orders",
                ),
                ExampleMetadata(
                    question="Show customer orders",
                    sql="SELECT c.name, o.product_name, o.total_amount FROM customers c JOIN orders o ON c.customer_id = o.customer_id",
                    expected_results="Returns customer names with their orders",
                ),
            ],
        )


def demo_validation_features():
    """Demonstrate the validation features."""
    print("=" * 70)
    print("SQL VALIDATION & RETRY DEMO")
    print("=" * 70)

    print("\n📋 Key Features:")
    print("  ✓ Syntax validation (catches malformed SQL)")
    print("  ✓ Column validation (prevents hallucinated columns)")
    print("  ✓ Database dry-run (validates against actual schema)")
    print("  ✓ Automatic retry with error feedback")
    print("  ✓ Max 3 attempts (configurable)")

    print("\n" + "=" * 70)
    print("HOW IT WORKS")
    print("=" * 70)

    print("\n1️⃣  AI generates SQL from your question")
    print("2️⃣  Validation runs 3 checks:")
    print("    - Syntax: Is the SQL structurally valid?")
    print("    - Columns: Do all columns exist in schema?")
    print("    - Database: Does EXPLAIN validate successfully?")
    print("\n3️⃣  If validation fails:")
    print("    - AI receives detailed error feedback")
    print("    - AI regenerates SQL with corrections")
    print("    - Process repeats (max 3 attempts)")
    print("\n4️⃣  If validation passes:")
    print("    - SQL is executed")
    print("    - Results returned")

    print("\n" + "=" * 70)
    print("CONFIGURATION")
    print("=" * 70)
    print("\nQueryAgent parameters:")
    print("  - enable_db_validation=True   # Enable database dry-run")
    print("  - max_retries=2               # Max retry attempts (0-based)")
    print("  - enable_planning=True        # Auto-select dataset")
    print("  - enable_insights=True        # Generate AI insights")

    print("\n" + "=" * 70)
    print("EXAMPLE: Retry on Syntax Error")
    print("=" * 70)

    print("\nScenario: AI generates 'SELECT * LIMIT 10' (missing FROM)")
    print("\nAttempt 1:")
    print("  Generated: SELECT * LIMIT 10")
    print("  ❌ Syntax Error: LIMIT clause found without FROM clause")
    print("\nAttempt 2 (with feedback):")
    print("  AI receives: 'LIMIT requires FROM clause before it'")
    print("  Generated: SELECT * FROM customers LIMIT 10")
    print("  ✅ Validation passed!")

    print("\n" + "=" * 70)
    print("EXAMPLE: Retry on Column Error")
    print("=" * 70)

    print("\nScenario: AI invents non-existent 'address' column")
    print("\nAttempt 1:")
    print("  Generated: SELECT name, address FROM customers")
    print("  ❌ Column Error: Column 'address' not found")
    print("\nAttempt 2 (with feedback):")
    print("  AI receives: 'Valid columns: customer_id, name, email, signup_date, country'")
    print("  Generated: SELECT name, email FROM customers")
    print("  ✅ Validation passed!")

    print("\n" + "=" * 70)
    print("EXAMPLE: Retry on Database Error")
    print("=" * 70)

    print("\nScenario: AI generates JOIN with unqualified columns")
    print("\nAttempt 1:")
    print("  Generated: SELECT name, total_amount FROM customers JOIN orders...")
    print("  ❌ Database Error: Ambiguous column name 'name'")
    print("\nAttempt 2 (with feedback):")
    print("  AI receives: 'All columns in SELECT with JOIN must be qualified'")
    print("  Generated: SELECT c.name, o.total_amount FROM customers c JOIN orders o...")
    print("  ✅ Validation passed!")

    print("\n" + "=" * 70)
    print("BENEFITS")
    print("=" * 70)

    print("\n✨ Faster Results:")
    print("   - No waiting 30+ minutes for invalid SQL")
    print("   - Errors caught in milliseconds, not minutes")

    print("\n🎯 Higher Success Rate:")
    print("   - AI learns from validation errors")
    print("   - Automatic correction without manual intervention")

    print("\n💡 Better Debugging:")
    print("   - Clear error messages with hints")
    print("   - Logged attempts show what went wrong")

    print("\n🔒 Safety:")
    print("   - Invalid SQL never reaches database")
    print("   - EXPLAIN validates without data access")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    demo_validation_features()

    print("\n" + "=" * 70)
    print("✓ Demo complete!")
    print("=" * 70)
    print("\nTo use in your code:")
    print(
        """
from axiompy.reasoning import AIClient, QueryAgent

# Create AI client
ai_client = AIClient(
    provider="ollama",
    model="sqlcoder:7b",  # Fast SQL-optimized model
    endpoint="http://localhost:11434/api/generate"
)

# Create agent with validation enabled
agent = QueryAgent(
    ai_client=ai_client,
    datasets={"my_data": my_dataset_service},
    enable_db_validation=True,  # Enable database validation
    max_retries=2  # Allow 2 retries (3 total attempts)
)

# Execute query - validation and retry happen automatically!
result = agent.execute_query("Show me the top 10 customers")
print(result["sql"])      # The validated SQL
print(result["results"])  # The query results
    """
    )
    print()
