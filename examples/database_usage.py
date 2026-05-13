"""
Examples of using the axiompy database abstraction layer.

This file demonstrates how to use the DatabaseFactory and various database
implementations for common CRUD operations and custom SQL queries.

Note: The database connects automatically when created and cleans up
resources automatically when the instance is destroyed.
"""

from axiompy.io.database import DatabaseError, DatabaseFactory, DatabaseSettings, DatabaseType


def sqlite_example():
    """Example using SQLite (no external dependencies required)."""
    print("=== SQLite Example ===")

    # Create settings for in-memory SQLite database
    settings = DatabaseSettings(database=":memory:")

    # Create database instance (connects automatically)
    db = DatabaseFactory.create(DatabaseType.SQLITE, settings)
    print("Connected to SQLite database")

    try:
        # Create a table using execute()
        db.execute(
            """
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER DEFAULT 0
            )
        """
        )
        print("Created products table")

        # Insert data using set() method
        product1_id = db.set("products", {"name": "Widget", "price": 19.99, "quantity": 100})
        product2_id = db.set("products", {"name": "Gadget", "price": 29.99, "quantity": 50})
        print(f"Inserted 2 products (IDs: {product1_id}, {product2_id})")

        # Batch insert using a loop
        more_products = [
            {"name": "Doohickey", "price": 9.99, "quantity": 200},
            {"name": "Thingamajig", "price": 39.99, "quantity": 25},
            {"name": "Whatchamacallit", "price": 14.99, "quantity": 75},
        ]
        for product in more_products:
            db.set("products", product)
        print(f"Inserted {len(more_products)} more products")

        # Query data using get_all()
        all_products = db.get_all("products")
        print(f"\nAll products ({len(all_products)} total):")
        for product in all_products:
            print(f"  - {product['name']}: ${product['price']} (qty: {product['quantity']})")

        # Query with custom SQL using execute()
        expensive_products = db.execute(
            "SELECT * FROM products WHERE price > ? ORDER BY price", (20.0,)
        )
        print(f"\nExpensive products (${'>'}20):")
        if isinstance(expensive_products, list):
            for product in expensive_products:
                print(f"  - {product['name']}: ${product['price']}")

        # Update data using update()
        updated = db.update("products", product1_id, {"quantity": 150})
        print(f"\nUpdated {updated} product(s)")

        # Get a single product using get()
        widget = db.get("products", product1_id)
        if widget:
            print(f"Widget now has quantity: {widget['quantity']}")

        # Delete data using delete()
        deleted = db.delete("products", product2_id)
        print(f"Deleted {deleted} product(s)")

        # Final count using execute()
        remaining = db.execute("SELECT COUNT(*) as count FROM products")
        if isinstance(remaining, list) and remaining:
            print(f"Remaining products: {remaining[0]['count']}")

    except DatabaseError as e:
        print(f"Database error: {e}")

    # Resources are cleaned up automatically when db goes out of scope
    print("Database will clean up automatically\n")


def postgresql_example():
    """
    Example using PostgreSQL.

    Requires: pip install psycopg2-binary
    Note: This is a demo - you'll need an actual PostgreSQL server running.
    """
    print("=== PostgreSQL Example ===")

    # Create settings for PostgreSQL
    settings = DatabaseSettings(
        host="localhost",
        port=5432,
        database="myapp",
        username="myuser",
        password="mypassword",
        connection_timeout=10,
    )

    try:
        # Create database instance (connects automatically)
        db = DatabaseFactory.create(DatabaseType.POSTGRES, settings)
        print("Connected to PostgreSQL database")

        # Create table with PostgreSQL-specific syntax
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        print("Created users table")

        # Insert using set() - PostgreSQL implementation uses RETURNING
        user_id = db.set("users", {"username": "johndoe", "email": "john@example.com"})
        print(f"Inserted user with ID: {user_id}")

        # Get user by ID
        user = db.get("users", user_id)
        if user:
            print(f"Retrieved user: {user['username']} ({user['email']})")

        # Update user
        affected = db.update("users", user_id, {"email": "john.doe@example.com"})
        print(f"Updated {affected} user(s)")

        # Query with named parameters using execute()
        users = db.execute(
            "SELECT * FROM users WHERE username = %(username)s", {"username": "johndoe"}
        )
        if isinstance(users, list):
            print(f"Found {len(users)} user(s)")

        # Get all users
        all_users = db.get_all("users")
        print(f"Total users: {len(all_users)}")

        print("PostgreSQL example complete")

    except DatabaseError as e:
        print(f"PostgreSQL example error (expected if not configured): {e}")


def mysql_example():
    """
    Example using MySQL.

    Requires: pip install mysql-connector-python
    Note: This is a demo - you'll need an actual MySQL server running.
    """
    print("\n=== MySQL Example ===")

    # Create settings for MySQL
    settings = DatabaseSettings(
        host="localhost",
        port=3306,
        database="myapp",
        username="root",
        password="rootpassword",
        extra_params={"charset": "utf8mb4", "use_unicode": True},
    )

    try:
        # Create database instance (connects automatically)
        db = DatabaseFactory.create(DatabaseType.MYSQL, settings)
        print("Connected to MySQL database")

        # Create table
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                customer_name VARCHAR(100) NOT NULL,
                total DECIMAL(10, 2) NOT NULL,
                status ENUM('pending', 'completed', 'cancelled') DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        print("Created orders table")

        # Insert multiple orders using set()
        order1_id = db.set(
            "orders", {"customer_name": "Alice Johnson", "total": 199.99, "status": "completed"}
        )
        order2_id = db.set(
            "orders", {"customer_name": "Bob Smith", "total": 299.99, "status": "pending"}
        )
        print(f"Inserted orders with IDs: {order1_id}, {order2_id}")

        # Query with aggregation using execute()
        summary = db.execute(
            """
            SELECT status, COUNT(*) as count, SUM(total) as total
            FROM orders
            GROUP BY status
        """
        )
        if isinstance(summary, list):
            print("Order summary:")
            for row in summary:
                print(f"  {row['status']}: {row['count']} orders, ${row['total']}")

        # Get order by custom column
        alice_orders = db.execute(
            "SELECT * FROM orders WHERE customer_name = %s", ("Alice Johnson",)
        )
        if isinstance(alice_orders, list):
            print(f"Alice has {len(alice_orders)} order(s)")

        print("MySQL example complete")

    except DatabaseError as e:
        print(f"MySQL example error (expected if not configured): {e}")


def dynamodb_example():
    """
    Example using DynamoDB.

    Requires: pip install boto3
    Note: This is a demo - you'll need AWS credentials and DynamoDB access.
    """
    print("\n=== DynamoDB Example ===")

    # Create settings for DynamoDB
    settings = DatabaseSettings(
        region="us-east-1",
        # Optionally provide credentials (or use AWS credential chain)
        # access_key_id="your-access-key",
        # secret_access_key="your-secret-key"
    )

    try:
        # Create database instance (connects automatically)
        db = DatabaseFactory.create(DatabaseType.DYNAMODB, settings)
        print("Connected to DynamoDB")

        # Note: DynamoDB has a different interface than SQL databases
        # Table name is used instead of SQL table names

        # Put an item using set()
        user_id = db.set(
            "Users", {"id": "user_456", "username": "janedoe", "email": "jane@example.com"}
        )
        print(f"Put item with key: {user_id}")

        # Get item by key using get()
        user = db.get("Users", "user_456", key_column="id")
        if user:
            print(f"Retrieved user: {user['username']}")

        # Update item using update()
        db.update("Users", "user_456", {"email": "jane.doe@example.com"}, key_column="id")
        print("Updated user email")

        # Query with KeyConditionExpression using execute()
        from boto3.dynamodb.conditions import Key

        results = db.execute(
            "Users",
            {
                "KeyConditionExpression": Key("id").eq("user_456"),
            },
        )
        if isinstance(results, list):
            print(f"Query returned {len(results)} items")

        # Scan table (get_all)
        all_users = db.get_all("Users")
        print(f"Total users in table: {len(all_users)}")

        # Delete item
        deleted = db.delete("Users", "user_456", key_column="id")
        print(f"Deleted {deleted} item(s)")

        print("DynamoDB example complete")

    except DatabaseError as e:
        print(f"DynamoDB example error (expected if not configured): {e}")
    except ImportError as e:
        print(f"DynamoDB requires boto3: {e}")


def crud_operations_example():
    """Example demonstrating all CRUD operations."""
    print("\n=== CRUD Operations Example ===")

    settings = DatabaseSettings(database=":memory:")
    db = DatabaseFactory.create(DatabaseType.SQLITE, settings)

    # Create table
    db.execute(
        """
        CREATE TABLE books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            rating REAL
        )
    """
    )
    print("Created books table")

    # CREATE - Insert new records
    print("\n1. CREATE (Insert)")
    book1_id = db.set(
        "books", {"title": "1984", "author": "George Orwell", "year": 1949, "rating": 4.5}
    )
    book2_id = db.set(
        "books",
        {"title": "Brave New World", "author": "Aldous Huxley", "year": 1932, "rating": 4.2},
    )
    book3_id = db.set(
        "books", {"title": "Fahrenheit 451", "author": "Ray Bradbury", "year": 1953, "rating": 4.3}
    )
    print(f"  Inserted 3 books with IDs: {book1_id}, {book2_id}, {book3_id}")

    # READ - Get single record
    print("\n2. READ (Get Single)")
    book = db.get("books", book1_id)
    if book:
        print(f"  Retrieved: {book['title']} by {book['author']}")

    # READ - Get all records
    print("\n3. READ (Get All)")
    all_books = db.get_all("books")
    print(f"  Total books: {len(all_books)}")
    for book in all_books:
        print(f"    - {book['title']} ({book['year']}) - Rating: {book['rating']}")

    # UPDATE - Modify existing record
    print("\n4. UPDATE")
    updated = db.update("books", book1_id, {"rating": 4.7, "year": 1949})
    print(f"  Updated {updated} book(s)")
    book = db.get("books", book1_id)
    if book:
        print(f"  New rating: {book['rating']}")

    # DELETE - Remove record
    print("\n5. DELETE")
    deleted = db.delete("books", book2_id)
    print(f"  Deleted {deleted} book(s)")
    remaining = db.get_all("books")
    print(f"  Remaining books: {len(remaining)}")

    # Custom queries with execute()
    print("\n6. CUSTOM QUERIES")
    high_rated = db.execute("SELECT * FROM books WHERE rating >= ? ORDER BY rating DESC", (4.3,))
    if isinstance(high_rated, list):
        print(f"  High-rated books ({len(high_rated)}):")
        for book in high_rated:
            print(f"    - {book['title']}: {book['rating']} stars")

    print("\nCRUD operations example complete")


def error_handling_example():
    """Example demonstrating error handling."""
    print("\n=== Error Handling Example ===")

    settings = DatabaseSettings(database=":memory:")
    db = DatabaseFactory.create(DatabaseType.SQLITE, settings)

    # Try invalid SQL with execute()
    try:
        db.execute("INVALID SQL SYNTAX")
    except DatabaseError as e:
        print(f"Caught expected error (invalid SQL): {type(e).__name__}")

    # Handle constraint violations
    db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT UNIQUE)")
    db.set("test", {"id": 1, "value": "first"})

    try:
        # This will fail due to UNIQUE constraint
        db.set("test", {"id": 2, "value": "first"})
    except DatabaseError as e:
        print(f"Caught expected error (constraint violation): {type(e).__name__}")

    # Verify first insert succeeded
    results = db.get_all("test")
    print(f"Rows in test table: {len(results)}")

    # Handle get() on non-existent record (returns None, doesn't raise)
    result = db.get("test", 999)
    print(f"Get non-existent record: {result}")

    print("Error handling example complete")


def connection_reuse_example():
    """Example showing how to use a database instance for multiple operations."""
    print("\n=== Connection Reuse Example ===")

    settings = DatabaseSettings(database=":memory:")
    db = DatabaseFactory.create(DatabaseType.SQLITE, settings)

    # Create table
    db.execute(
        """
        CREATE TABLE counters (
            name TEXT PRIMARY KEY,
            value INTEGER DEFAULT 0
        )
    """
    )
    print("Created counters table")

    # Multiple operations on same connection
    for i in range(5):
        db.set("counters", {"name": f"counter_{i}", "value": i * 10})
    print("Inserted 5 counters")

    # Query and update in loop
    counters = db.get_all("counters")
    for counter in counters:
        new_value = counter["value"] + 1
        db.update("counters", counter["name"], {"value": new_value}, key_column="name")
    print("Updated all counters")

    # Verify
    updated_counters = db.get_all("counters")
    print("Final counter values:")
    for counter in sorted(updated_counters, key=lambda x: x["name"]):
        print(f"  {counter['name']}: {counter['value']}")

    print("Connection reuse example complete")


def file_database_example():
    """Example using SQLite with a file database."""
    print("\n=== File Database Example ===")

    import os
    import tempfile

    # Create a temporary file for the database
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        # Create database with file path
        settings = DatabaseSettings(database=db_path)
        db = DatabaseFactory.create(DatabaseType.SQLITE, settings)
        print(f"Created database at: {db_path}")

        # Create and populate table
        db.execute(
            """
            CREATE TABLE settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """
        )

        db.set("settings", {"key": "app_name", "value": "AxiomPy Demo"})
        db.set("settings", {"key": "version", "value": "1.0.0"})
        print("Populated database")

        # Important: Explicitly delete db to ensure cleanup before reopening
        del db

        # Reopen the same database file
        db2 = DatabaseFactory.create(DatabaseType.SQLITE, DatabaseSettings(database=db_path))
        results = db2.get_all("settings")
        print("Data persisted to file:")
        for row in sorted(results, key=lambda x: x["key"]):
            print(f"  {row['key']}: {row['value']}")

        print("File database example complete")

    finally:
        # Cleanup temporary file
        if os.path.exists(db_path):
            os.remove(db_path)
            print("Cleaned up temporary database file")


def advanced_queries_example():
    """Example with more advanced SQL queries using execute()."""
    print("\n=== Advanced Queries Example ===")

    settings = DatabaseSettings(database=":memory:")
    db = DatabaseFactory.create(DatabaseType.SQLITE, settings)

    # Create tables
    db.execute(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE
        )
    """
    )

    db.execute(
        """
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            total REAL,
            order_date TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """
    )
    print("Created customers and orders tables")

    # Insert test data
    c1 = db.set("customers", {"name": "Alice", "email": "alice@example.com"})
    c2 = db.set("customers", {"name": "Bob", "email": "bob@example.com"})
    c3 = db.set("customers", {"name": "Charlie", "email": "charlie@example.com"})

    db.set("orders", {"customer_id": c1, "total": 150.00, "order_date": "2024-01-15"})
    db.set("orders", {"customer_id": c1, "total": 200.00, "order_date": "2024-02-20"})
    db.set("orders", {"customer_id": c2, "total": 75.00, "order_date": "2024-01-18"})
    db.set("orders", {"customer_id": c3, "total": 300.00, "order_date": "2024-03-10"})
    print("Inserted test data")

    # JOIN query
    print("\nJOIN query - Orders with customer names:")
    orders_with_customers = db.execute(
        """
        SELECT o.id, c.name as customer_name, o.total, o.order_date
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        ORDER BY o.order_date
    """
    )
    if isinstance(orders_with_customers, list):
        for order in orders_with_customers:
            print(f"  Order #{order['id']}: {order['customer_name']} - ${order['total']}")

    # Aggregation query
    print("\nAggregation - Customer lifetime value:")
    customer_ltv = db.execute(
        """
        SELECT c.name, COUNT(o.id) as order_count, SUM(o.total) as lifetime_value
        FROM customers c
        LEFT JOIN orders o ON c.id = o.customer_id
        GROUP BY c.id, c.name
        ORDER BY lifetime_value DESC
    """
    )
    if isinstance(customer_ltv, list):
        for customer in customer_ltv:
            ltv = customer["lifetime_value"] or 0
            print(
                f"  {customer['name']}: {customer['order_count']} orders, ${ltv:.2f} lifetime value"
            )

    # Subquery
    print("\nSubquery - Customers with above-average orders:")
    above_avg = db.execute(
        """
        SELECT c.name, o.total
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        WHERE o.total > (SELECT AVG(total) FROM orders)
        ORDER BY o.total DESC
    """
    )
    if isinstance(above_avg, list):
        for row in above_avg:
            print(f"  {row['name']}: ${row['total']}")

    print("\nAdvanced queries example complete")


if __name__ == "__main__":
    """Run all examples."""

    # SQLite examples (always work - no external dependencies)
    sqlite_example()
    crud_operations_example()
    error_handling_example()
    connection_reuse_example()
    file_database_example()
    advanced_queries_example()

    # These examples require external dependencies and running servers
    # Uncomment to try them if you have the infrastructure set up

    # postgresql_example()
    # mysql_example()
    # dynamodb_example()

    print("\n=== All Examples Complete ===")
