"""Generate synthetic e-commerce data with customers and shopping history.

Creates a SQLite database with ~1 million records demonstrating realistic
customer and shopping patterns.

Usage:
    python examples/generate_ecommerce_data.py

Output:
    examples/ecommerce.db (SQLite database, ~100MB)
"""

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


def generate_ecommerce_database(
    db_path: str = "examples/ecommerce.db", num_records: int = 1_000_000
):
    """Generate synthetic e-commerce database with customers and orders."""

    db_path = Path(db_path)
    db_path.parent.mkdir(exist_ok=True)

    # Remove existing database
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Generating e-commerce database with {num_records:,} records...")
    print(f"Output: {db_path}")

    # Create tables
    print("\n1. Creating schema...")
    cursor.execute(
        """
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            country TEXT,
            signup_date DATE,
            customer_tier TEXT,
            lifetime_value REAL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            price REAL,
            stock INTEGER
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            order_date DATE,
            quantity INTEGER,
            total_amount REAL,
            status TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY(product_id) REFERENCES products(product_id)
        )
    """
    )

    cursor.execute("CREATE INDEX idx_orders_customer ON orders(customer_id)")
    cursor.execute("CREATE INDEX idx_orders_date ON orders(order_date)")
    cursor.execute("CREATE INDEX idx_orders_product ON orders(product_id)")

    # Generate products
    print("2. Generating products...")
    categories = ["Electronics", "Clothing", "Home & Garden", "Sports", "Books", "Toys", "Food"]
    products = []
    for i in range(1, 501):  # 500 products
        category = random.choice(categories)
        price = round(random.uniform(10, 500), 2)
        products.append((i, f"Product_{i}", category, price, random.randint(10, 1000)))

    cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?)", products)
    print(f"   ✓ Created {len(products)} products")

    # Generate customers
    print("3. Generating customers...")
    countries = ["USA", "UK", "Canada", "Australia", "Germany", "France", "Japan", "India"]
    tiers = ["Bronze", "Silver", "Gold", "Platinum"]
    customers = []

    num_customers = num_records // 10  # ~100K customers (10 orders per customer on avg)
    for i in range(1, num_customers + 1):
        signup_date = datetime.now() - timedelta(days=random.randint(1, 730))
        lifetime_value = round(random.uniform(100, 10000), 2)
        customers.append(
            (
                i,
                f"Customer_{i}",
                f"customer_{i}@example.com",
                random.choice(countries),
                signup_date.date(),
                random.choice(tiers),
                lifetime_value,
            )
        )

    cursor.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?)", customers)
    print(f"   ✓ Created {len(customers):,} customers")

    # Generate orders
    print("4. Generating orders (this may take a minute)...")
    orders = []
    statuses = ["Pending", "Confirmed", "Shipped", "Delivered", "Returned", "Cancelled"]

    base_date = datetime.now() - timedelta(days=365)
    batch_size = 10000

    for order_id in range(1, num_records + 1):
        customer_id = random.randint(1, num_customers)
        product_id = random.randint(1, 500)
        order_date = base_date + timedelta(days=random.randint(0, 365))
        quantity = random.randint(1, 5)

        # Get product price
        product = products[product_id - 1]
        price = product[3]
        total_amount = round(
            quantity * price * random.uniform(0.8, 1.2), 2
        )  # With discount variance

        status = random.choice(statuses)

        orders.append(
            (order_id, customer_id, product_id, order_date.date(), quantity, total_amount, status)
        )

        # Batch insert
        if len(orders) >= batch_size:
            cursor.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)", orders)
            conn.commit()
            print(f"   ✓ Inserted {order_id:,} orders...")
            orders = []

    # Final batch
    if orders:
        cursor.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)", orders)
        conn.commit()

    print(f"   ✓ Created {num_records:,} orders")

    # Verify data
    print("\n5. Verifying data...")
    cursor.execute("SELECT COUNT(*) FROM customers")
    customer_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders")
    order_count = cursor.fetchone()[0]

    print(f"   ✓ Customers: {customer_count:,}")
    print(f"   ✓ Products: {product_count:,}")
    print(f"   ✓ Orders: {order_count:,}")

    # Get some stats
    cursor.execute("SELECT AVG(total_amount), MAX(total_amount), MIN(total_amount) FROM orders")
    avg_amount, max_amount, min_amount = cursor.fetchone()
    cursor.execute("SELECT SUM(total_amount) FROM orders")
    total_revenue = cursor.fetchone()[0]

    print("\n6. Database Statistics:")
    print(f"   ✓ Total Revenue: ${total_revenue:,.2f}")
    print(f"   ✓ Average Order: ${avg_amount:,.2f}")
    print(f"   ✓ Order Range: ${min_amount:,.2f} - ${max_amount:,.2f}")

    conn.close()
    db_size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"\n✓ Database created: {db_path} ({db_size_mb:.1f} MB)")
    print("\nNext: Run 'python examples/ecommerce_demo.py' to use with AxiomPy reasoning")


if __name__ == "__main__":
    generate_ecommerce_database()
