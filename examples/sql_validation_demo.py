"""Demo: SQL Validation Before Execution

This demonstrates the new SQL validation capabilities:
1. Syntax validation using sqlparse
2. Column validation against schema
3. Database dry-run validation using EXPLAIN
"""

import sqlite3

from axiompy.reasoning.validators import SQLValidator


def demo_syntax_validation():
    """Demo 1: Syntax validation catches malformed SQL"""
    print("=" * 70)
    print("DEMO 1: Syntax Validation")
    print("=" * 70)

    # Valid SQL
    valid_sql = "SELECT name, email FROM users WHERE id = 1"
    result = SQLValidator.validate_syntax(valid_sql)
    print(f"\n✓ Valid SQL: {valid_sql}")
    print(f"  Result: {result.valid}")

    # Invalid SQL - missing FROM clause
    invalid_sql1 = "SELECT name WHERE id = 1"
    result = SQLValidator.validate_syntax(invalid_sql1)
    print(f"\n✗ Invalid SQL: {invalid_sql1}")
    print(f"  Result: {result.valid}")
    print(f"  Errors: {result.errors}")

    # Invalid SQL - LIMIT without FROM
    invalid_sql2 = "SELECT * LIMIT 10"
    result = SQLValidator.validate_syntax(invalid_sql2)
    print(f"\n✗ Invalid SQL: {invalid_sql2}")
    print(f"  Result: {result.valid}")
    print(f"  Errors: {result.errors}")

    # Invalid SQL - unmatched parentheses
    invalid_sql3 = "SELECT COUNT(id FROM users"
    result = SQLValidator.validate_syntax(invalid_sql3)
    print(f"\n✗ Invalid SQL: {invalid_sql3}")
    print(f"  Result: {result.valid}")
    print(f"  Errors: {result.errors}")


def demo_column_validation():
    """Demo 2: Column validation against schema"""
    print("\n" + "=" * 70)
    print("DEMO 2: Column Validation")
    print("=" * 70)

    # Define schema
    schema_columns = {"id", "name", "email", "created_at", "age"}

    # Valid SQL with valid columns
    valid_sql = "SELECT name, email FROM users WHERE age > 18"
    result = SQLValidator.validate_columns(valid_sql, schema_columns)
    print(f"\n✓ Valid SQL: {valid_sql}")
    print(f"  Result: {result.valid}")

    # Invalid SQL with non-existent column
    invalid_sql = "SELECT name, invalid_column FROM users"
    result = SQLValidator.validate_columns(invalid_sql, schema_columns)
    print(f"\n✗ Invalid SQL: {invalid_sql}")
    print(f"  Result: {result.valid}")
    print(f"  Missing columns: {result.missing_columns}")
    print(f"  Warnings: {result.warnings}")


def demo_database_dryrun():
    """Demo 3: Database dry-run validation using EXPLAIN"""
    print("\n" + "=" * 70)
    print("DEMO 3: Database Dry-Run Validation")
    print("=" * 70)

    # Create in-memory database with sample schema
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            age INTEGER
        )
    """
    )
    conn.execute(
        """
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            total REAL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """
    )

    # Valid SQL
    valid_sql = "SELECT name, email FROM users WHERE age > 18"
    result = SQLValidator.validate_with_db_dryrun(valid_sql, conn)
    print(f"\n✓ Valid SQL: {valid_sql}")
    print(f"  Result: {result.valid}")

    # Invalid SQL - table doesn't exist
    invalid_sql1 = "SELECT * FROM nonexistent_table"
    result = SQLValidator.validate_with_db_dryrun(invalid_sql1, conn)
    print(f"\n✗ Invalid SQL: {invalid_sql1}")
    print(f"  Result: {result.valid}")
    print(f"  Errors: {result.errors}")

    # Invalid SQL - column doesn't exist
    invalid_sql2 = "SELECT name, invalid_column FROM users"
    result = SQLValidator.validate_with_db_dryrun(invalid_sql2, conn)
    print(f"\n✗ Invalid SQL: {invalid_sql2}")
    print(f"  Result: {result.valid}")
    print(f"  Errors: {result.errors}")

    # Invalid SQL - syntax error (LIMIT without FROM)
    invalid_sql3 = "SELECT * LIMIT 10"
    result = SQLValidator.validate_with_db_dryrun(invalid_sql3, conn)
    print(f"\n✗ Invalid SQL: {invalid_sql3}")
    print(f"  Result: {result.valid}")
    print(f"  Errors: {result.errors}")

    # Valid SQL with JOIN
    valid_join = """
        SELECT u.name, COUNT(o.order_id) as order_count
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        GROUP BY u.id, u.name
    """
    result = SQLValidator.validate_with_db_dryrun(valid_join, conn)
    print(f"\n✓ Valid SQL (with JOIN): {valid_join.strip()}")
    print(f"  Result: {result.valid}")

    conn.close()


if __name__ == "__main__":
    print("\n" + "🔍 SQL VALIDATION DEMO" + "\n")

    demo_syntax_validation()
    demo_column_validation()
    demo_database_dryrun()

    print("\n" + "=" * 70)
    print("✓ All demos completed!")
    print("=" * 70)
    print("\nKey Features:")
    print("  1. Syntax validation catches malformed SQL before execution")
    print("  2. Column validation prevents hallucinated column names")
    print("  3. Database dry-run catches runtime errors without data access")
    print("\nThis prevents wasted time on invalid queries from AI models!")
    print()
