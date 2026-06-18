# @!documentation

"""
Arrow Database Examples

Demonstrates the Arrow-native database abstraction for analytics and ETL workloads.

This module shows:
    - Basic DuckDB usage with Arrow tables
    - Reading/writing files (Parquet, CSV, JSON)
    - In-memory data processing with registered Arrow tables
    - ETL pipeline patterns
    - Integration with pandas/polars

Prerequisites:
    pip install duckdb pyarrow pandas polars

For Snowflake/PostgreSQL examples, you'll need:
    pip install adbc-driver-snowflake  # for Snowflake
    pip install adbc-driver-postgresql  # for PostgreSQL
"""

# =============================================================================
# Imports
# =============================================================================

from pathlib import Path
from tempfile import TemporaryDirectory

# Check for optional dependencies
try:
    import duckdb
    import pyarrow as pa
    import pyarrow.parquet as pq

    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    print("⚠️  DuckDB/PyArrow not installed. Run: pip install duckdb pyarrow")

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import polars as pl

    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False


from axiompy.data import (
    ArrowDatabaseFactory,
    DuckDBArrowSettings,
    MockArrowDatabase,
    PostgresArrowSettings,
    SnowflakeArrowSettings,
)

# =============================================================================
# Example 1: Basic DuckDB Usage
# =============================================================================


def example_basic_duckdb() -> None:
    """
    Basic DuckDB usage with Arrow tables.

    Shows how to:
    - Create an in-memory DuckDB database
    - Execute queries and get Arrow tables
    - Work with SQL DDL/DML
    """
    print("\n" + "=" * 60)
    print("Example 1: Basic DuckDB Usage")
    print("=" * 60)

    if not DUCKDB_AVAILABLE:
        print("Skipping - DuckDB not installed")
        return

    # Create in-memory database
    settings = DuckDBArrowSettings(database=":memory:")
    db = ArrowDatabaseFactory.create(settings)

    try:
        # Execute simple query - returns Arrow table
        result = db.execute_arrow("SELECT 1 as id, 'hello' as message")
        print(f"\n✅ Simple query result: {result.num_rows} rows")
        print(f"   Columns: {result.column_names}")
        print(f"   Data: {result.to_pydict()}")

        # Create a table and insert data
        db.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name VARCHAR,
                email VARCHAR,
                created_at TIMESTAMP
            )
        """
        )

        db.execute(
            """
            INSERT INTO users VALUES
                (1, 'Alice', 'alice@example.com', '2026-01-01 10:00:00'),
                (2, 'Bob', 'bob@example.com', '2026-01-02 11:00:00'),
                (3, 'Charlie', 'charlie@example.com', '2026-01-03 12:00:00')
        """
        )

        # Query the table
        users = db.execute_arrow("SELECT * FROM users ORDER BY id")
        print(f"\n✅ Users table: {users.num_rows} rows")
        print(f"   Names: {users.column('name').to_pylist()}")

        # Get table schema
        schema = db.get_schema("users")
        print("\n✅ Table schema:")
        for field in schema:
            print(f"   {field.name}: {field.type}")

        # List tables
        tables = db.get_table_names()
        print(f"\n✅ Tables in database: {tables}")

    finally:
        db.close()
        print("\n✅ Connection closed")


# =============================================================================
# Example 2: Reading Files Directly
# =============================================================================


def example_read_files() -> None:
    """
    Read files directly with DuckDB.

    Shows how to:
    - Read Parquet, CSV, and JSON files
    - Query files without loading into memory first
    - Use glob patterns for multiple files
    """
    print("\n" + "=" * 60)
    print("Example 2: Reading Files Directly")
    print("=" * 60)

    if not DUCKDB_AVAILABLE:
        print("Skipping - DuckDB not installed")
        return

    with TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create test files
        # Parquet
        parquet_data = pa.table(
            {
                "product_id": [1, 2, 3, 4, 5],
                "product_name": ["Widget", "Gadget", "Gizmo", "Doohickey", "Thingamajig"],
                "price": [9.99, 19.99, 29.99, 39.99, 49.99],
                "in_stock": [True, True, False, True, False],
            }
        )
        pq.write_table(parquet_data, tmppath / "products.parquet")

        # CSV
        csv_content = """order_id,customer_id,product_id,quantity
1001,101,1,2
1002,102,2,1
1003,101,3,3
1004,103,1,1
"""
        (tmppath / "orders.csv").write_text(csv_content)

        # JSON
        json_content = """{"customer_id": 101, "name": "Alice", "tier": "gold"}
{"customer_id": 102, "name": "Bob", "tier": "silver"}
{"customer_id": 103, "name": "Charlie", "tier": "bronze"}
"""
        (tmppath / "customers.ndjson").write_text(json_content)

        # Create database and read files
        settings = DuckDBArrowSettings()
        db = ArrowDatabaseFactory.create(settings)

        try:
            # Read Parquet
            products = db.read_parquet(str(tmppath / "products.parquet"))
            print(f"\n✅ Parquet file: {products.num_rows} products")
            print(f"   Product names: {products.column('product_name').to_pylist()}")

            # Read CSV
            orders = db.read_csv(str(tmppath / "orders.csv"))
            print(f"\n✅ CSV file: {orders.num_rows} orders")

            # Read JSON (newline-delimited)
            customers = db.read_json(str(tmppath / "customers.ndjson"))
            print(f"\n✅ JSON file: {customers.num_rows} customers")
            print(f"   Customer names: {customers.column('name').to_pylist()}")

            # Query files directly with SQL (without loading first!)
            result = db.execute_arrow(
                f"""
                SELECT
                    c.name as customer_name,
                    p.product_name,
                    o.quantity,
                    p.price * o.quantity as total
                FROM read_csv_auto('{tmppath / "orders.csv"}') o
                JOIN read_parquet('{tmppath / "products.parquet"}') p
                    ON o.product_id = p.product_id
                JOIN read_json_auto('{tmppath / "customers.ndjson"}') c
                    ON o.customer_id = c.customer_id
                ORDER BY total DESC
            """
            )
            print(f"\n✅ Join across all files: {result.num_rows} rows")
            print(
                f"   Top order: {result.column('customer_name').to_pylist()[0]} "
                f"bought {result.column('product_name').to_pylist()[0]} "
                f"for ${result.column('total').to_pylist()[0]:.2f}"
            )

        finally:
            db.close()


# =============================================================================
# Example 3: In-Memory Data Processing
# =============================================================================


def example_in_memory_processing() -> None:
    """
    Process in-memory Arrow tables with SQL.

    Shows how to:
    - Register Arrow tables as virtual tables
    - Query and transform data with SQL
    - Join multiple Arrow tables
    """
    print("\n" + "=" * 60)
    print("Example 3: In-Memory Data Processing")
    print("=" * 60)

    if not DUCKDB_AVAILABLE:
        print("Skipping - DuckDB not installed")
        return

    settings = DuckDBArrowSettings()
    db = ArrowDatabaseFactory.create(settings)

    try:
        # Create Arrow tables (could come from another source)
        events = pa.table(
            {
                "event_id": range(1, 11),
                "user_id": [1, 2, 1, 3, 2, 1, 3, 2, 1, 3],
                "event_type": [
                    "view",
                    "click",
                    "purchase",
                    "view",
                    "view",
                    "click",
                    "purchase",
                    "purchase",
                    "view",
                    "view",
                ],
                "amount": [
                    None,
                    None,
                    99.99,
                    None,
                    None,
                    None,
                    49.99,
                    149.99,
                    None,
                    None,
                ],
            }
        )

        users = pa.table(
            {
                "user_id": [1, 2, 3],
                "username": ["alice", "bob", "charlie"],
                "signup_date": ["2025-01-01", "2025-06-15", "2025-12-01"],
            }
        )

        # Register tables
        db.register_arrow_table("events", events)
        db.register_arrow_table("users", users)
        print(f"\n✅ Registered tables: {db.get_table_names()}")

        # Aggregate events by user
        user_stats = db.execute_arrow(
            """
            SELECT
                u.username,
                COUNT(*) as total_events,
                COUNT(CASE WHEN e.event_type = 'purchase' THEN 1 END) as purchases,
                COALESCE(SUM(e.amount), 0) as total_spent
            FROM events e
            JOIN users u ON e.user_id = u.user_id
            GROUP BY u.username
            ORDER BY total_spent DESC
        """
        )
        print("\n✅ User statistics:")
        for i in range(user_stats.num_rows):
            print(
                f"   {user_stats.column('username')[i]}: "
                f"{user_stats.column('total_events')[i]} events, "
                f"{user_stats.column('purchases')[i]} purchases, "
                f"${user_stats.column('total_spent')[i]:.2f} spent"
            )

        # Event type breakdown
        event_breakdown = db.execute_arrow(
            """
            SELECT
                event_type,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
            FROM events
            GROUP BY event_type
            ORDER BY count DESC
        """
        )
        print("\n✅ Event breakdown:")
        for i in range(event_breakdown.num_rows):
            print(
                f"   {event_breakdown.column('event_type')[i]}: "
                f"{event_breakdown.column('count')[i]} "
                f"({event_breakdown.column('percentage')[i]}%)"
            )

    finally:
        db.close()


# =============================================================================
# Example 4: DataFrame Integration
# =============================================================================


def example_dataframe_integration() -> None:
    """
    Integration with pandas and polars.

    Shows how to:
    - Convert Arrow tables to pandas DataFrames
    - Convert Arrow tables to polars DataFrames
    - Use convenience methods for quick analysis
    """
    print("\n" + "=" * 60)
    print("Example 4: DataFrame Integration")
    print("=" * 60)

    if not DUCKDB_AVAILABLE:
        print("Skipping - DuckDB not installed")
        return

    settings = DuckDBArrowSettings()
    db = ArrowDatabaseFactory.create(settings)

    try:
        # Generate sample data
        sample_data = db.execute_arrow(
            """
            SELECT
                i as id,
                'user_' || i as name,
                CASE WHEN i % 3 = 0 THEN 'admin'
                     WHEN i % 3 = 1 THEN 'user'
                     ELSE 'guest' END as role,
                random() * 100 as score
            FROM generate_series(1, 1000) as t(i)
        """
        )
        print(f"\n✅ Generated {sample_data.num_rows} rows of sample data")
        print(f"   Memory: {sample_data.nbytes / 1024:.2f} KB")

        # Convert to pandas
        if PANDAS_AVAILABLE:
            df_pandas = db.to_pandas(
                """
                SELECT role, COUNT(*) as count, AVG(score) as avg_score
                FROM generate_series(1, 1000) as t(i),
                     LATERAL (SELECT
                         CASE WHEN i % 3 = 0 THEN 'admin'
                              WHEN i % 3 = 1 THEN 'user'
                              ELSE 'guest' END as role,
                         random() * 100 as score
                     ) stats
                GROUP BY role
            """
            )
            print("\n✅ Pandas DataFrame:")
            print(df_pandas.to_string(index=False))
        else:
            print("\n⚠️  Pandas not installed - skipping pandas example")

        # Convert to polars
        if POLARS_AVAILABLE:
            df_polars = db.to_polars(
                """
                SELECT
                    i as id,
                    random() * 100 as value
                FROM generate_series(1, 5) as t(i)
            """
            )
            print("\n✅ Polars DataFrame:")
            print(df_polars)
        else:
            print("\n⚠️  Polars not installed - skipping polars example")

    finally:
        db.close()


# =============================================================================
# Example 5: ETL Pipeline Pattern
# =============================================================================


def example_etl_pipeline() -> None:
    """
    ETL pipeline using Arrow database.

    Shows how to:
    - Extract data from multiple sources
    - Transform with SQL
    - Load to output files
    """
    print("\n" + "=" * 60)
    print("Example 5: ETL Pipeline Pattern")
    print("=" * 60)

    if not DUCKDB_AVAILABLE:
        print("Skipping - DuckDB not installed")
        return

    with TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create source data files
        # Sales data (could be from data warehouse)
        sales = pa.table(
            {
                "sale_id": range(1, 101),
                "product_id": [i % 10 + 1 for i in range(100)],
                "quantity": [i % 5 + 1 for i in range(100)],
                "sale_date": ["2026-01-01"] * 50 + ["2026-01-02"] * 50,
            }
        )
        pq.write_table(sales, tmppath / "sales.parquet")

        # Product catalog (could be from API)
        products = pa.table(
            {
                "product_id": range(1, 11),
                "product_name": [f"Product {i}" for i in range(1, 11)],
                "category": ["Electronics"] * 3 + ["Clothing"] * 4 + ["Home"] * 3,
                "unit_price": [10.0 * i for i in range(1, 11)],
            }
        )
        pq.write_table(products, tmppath / "products.parquet")

        # Create pipeline database
        settings = DuckDBArrowSettings()
        db = ArrowDatabaseFactory.create(settings)

        try:
            print("\n📥 EXTRACT: Loading source data...")
            sales_data = db.read_parquet(str(tmppath / "sales.parquet"))
            products_data = db.read_parquet(str(tmppath / "products.parquet"))
            print(f"   Sales: {sales_data.num_rows} rows")
            print(f"   Products: {products_data.num_rows} rows")

            # Register for transformation
            db.register_arrow_table("raw_sales", sales_data)
            db.register_arrow_table("raw_products", products_data)

            print("\n🔄 TRANSFORM: Aggregating data...")

            # Daily sales by category
            daily_category_sales = db.execute_arrow(
                """
                SELECT
                    s.sale_date,
                    p.category,
                    COUNT(*) as num_sales,
                    SUM(s.quantity) as total_quantity,
                    SUM(s.quantity * p.unit_price) as total_revenue
                FROM raw_sales s
                JOIN raw_products p ON s.product_id = p.product_id
                GROUP BY s.sale_date, p.category
                ORDER BY s.sale_date, total_revenue DESC
            """
            )
            print(f"   Daily category sales: {daily_category_sales.num_rows} rows")

            # Top products
            top_products = db.execute_arrow(
                """
                SELECT
                    p.product_name,
                    p.category,
                    SUM(s.quantity) as units_sold,
                    SUM(s.quantity * p.unit_price) as revenue,
                    RANK() OVER (ORDER BY SUM(s.quantity * p.unit_price) DESC) as rank
                FROM raw_sales s
                JOIN raw_products p ON s.product_id = p.product_id
                GROUP BY p.product_name, p.category
                ORDER BY revenue DESC
                LIMIT 5
            """
            )
            print(f"   Top products: {top_products.num_rows} rows")

            print("\n📤 LOAD: Writing output files...")

            # Write aggregated data to Parquet
            db.register_arrow_table("daily_sales", daily_category_sales)
            db.write_parquet(
                "SELECT * FROM daily_sales", str(tmppath / "output_daily_sales.parquet")
            )
            print(f"   ✅ Wrote {tmppath / 'output_daily_sales.parquet'}")

            db.register_arrow_table("top_products", top_products)
            db.write_parquet(
                "SELECT * FROM top_products", str(tmppath / "output_top_products.parquet")
            )
            print(f"   ✅ Wrote {tmppath / 'output_top_products.parquet'}")

            # Summary
            print("\n📊 SUMMARY:")
            print(f"   Top product: {top_products.column('product_name')[0]}")
            print(f"   Revenue: ${top_products.column('revenue')[0]:.2f}")

            total_rev = db.execute_arrow("SELECT SUM(total_revenue) as total FROM daily_sales")
            print(f"   Total revenue: ${total_rev.column('total')[0]:.2f}")

        finally:
            db.close()


# =============================================================================
# Example 6: Mock for Testing
# =============================================================================


def example_mock_testing() -> None:
    """
    Using MockArrowDatabase for unit testing.

    Shows how to:
    - Create mock database instances
    - Set predefined responses
    - Track method calls for assertions
    """
    print("\n" + "=" * 60)
    print("Example 6: Mock for Testing")
    print("=" * 60)

    # Create mock database
    mock = ArrowDatabaseFactory.create_mock()
    print("\n✅ Created mock database")

    # Track calls without pyarrow
    mock.execute_arrow("SELECT * FROM users WHERE id = 1")
    mock.execute("INSERT INTO logs VALUES ('test')")
    mock.validate_connection()

    print(f"\n✅ Method calls tracked: {len(mock.calls)}")
    for call in mock.calls:
        print(f"   {call}")

    # Reset for new test
    mock.reset()
    print(f"\n✅ After reset: {len(mock.calls)} calls")

    # Set predefined response (requires pyarrow)
    if DUCKDB_AVAILABLE:
        expected_result = pa.table({"id": [1, 2], "name": ["Alice", "Bob"]})
        mock.set_response("SELECT * FROM users", expected_result)

        result = mock.execute_arrow("SELECT * FROM users")
        print(f"\n✅ Predefined response returned: {result.num_rows} rows")

        # Register table and verify
        mock.register_arrow_table("test_table", expected_result)
        tables = mock.get_table_names()
        print(f"✅ Registered tables: {tables}")


# =============================================================================
# Example 7: Settings Configuration
# =============================================================================


def example_settings_configuration() -> None:
    """
    Different settings configurations for various databases.

    Shows how to:
    - Configure DuckDB with extensions
    - Configure Snowflake with secrets
    - Configure PostgreSQL with SSL
    """
    print("\n" + "=" * 60)
    print("Example 7: Settings Configuration")
    print("=" * 60)

    # DuckDB settings
    duckdb_settings = DuckDBArrowSettings(
        database=":memory:",  # or "/path/to/db.duckdb" for persistent
        read_only=False,
        extensions=["parquet", "json"],  # Extensions to auto-load
    )
    print("\n✅ DuckDB settings:")
    print(f"   Database: {duckdb_settings.database}")
    print(f"   Read-only: {duckdb_settings.read_only}")
    print(f"   Extensions: {duckdb_settings.extensions}")
    print(f"   Adapter type: {duckdb_settings.adapter_type}")

    # Snowflake settings
    snowflake_settings = SnowflakeArrowSettings(
        account="my_account",
        warehouse="COMPUTE_WH",
        database="ANALYTICS_DB",
        schema="PUBLIC",
        user="etl_user",
        password="secret",  # or use password_secret with SecretsManager
        role="ETL_ROLE",
        arrow_batch_size=100_000,
    )
    print("\n✅ Snowflake settings:")
    print(f"   Account: {snowflake_settings.account}")
    print(f"   Warehouse: {snowflake_settings.warehouse}")
    print(f"   Database: {snowflake_settings.database}")
    print(f"   Schema: {snowflake_settings.schema}")
    print(f"   Role: {snowflake_settings.role}")
    print(f"   Adapter type: {snowflake_settings.adapter_type}")

    # PostgreSQL settings
    postgres_settings = PostgresArrowSettings(
        host="localhost",
        port=5432,
        database="analytics",
        user="postgres",
        password="password",  # or use password_secret with SecretsManager
        schema="public",
        ssl_mode="require",
    )
    print("\n✅ PostgreSQL settings:")
    print(f"   Host: {postgres_settings.host}:{postgres_settings.port}")
    print(f"   Database: {postgres_settings.database}")
    print(f"   Schema: {postgres_settings.schema}")
    print(f"   SSL mode: {postgres_settings.ssl_mode}")
    print(f"   Adapter type: {postgres_settings.adapter_type}")


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("Arrow Database Examples")
    print("=" * 60)

    example_basic_duckdb()
    example_read_files()
    example_in_memory_processing()
    example_dataframe_integration()
    example_etl_pipeline()
    example_mock_testing()
    example_settings_configuration()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
