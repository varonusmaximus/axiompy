"""E-commerce data service with customer and order analysis."""

from axiompy.reasoning import (
    BaseDatasetService,
    DatasetMetadata,
    ExampleMetadata,
    ScopeMetadata,
    TableSchemaMetadata,
)


class EcommerceService(BaseDatasetService):
    """E-commerce data service with customer and order analysis."""

    dataset_name = "ecommerce"
    description = "E-commerce customer and order data (1M records)"

    def __init__(self, database):
        """Initialize with database connection."""
        self.db = database

    def query(self, sql: str, limit: int = None) -> list[dict]:
        """Execute SQL query."""
        if limit:
            # Only add LIMIT if one doesn't already exist in the SQL
            if "LIMIT" not in sql.upper():
                sql = f"{sql.rstrip(';')} LIMIT {limit}"
        return self.db.execute(sql)

    def get_capabilities(self) -> list[str]:
        """Get dataset capabilities."""
        return [
            "customer_analysis",
            "sales_trends",
            "product_performance",
            "geographic_insights",
            "customer_segmentation",
            "revenue_analysis",
        ]

    def get_metadata(self) -> DatasetMetadata:
        """Get dataset metadata for AI reasoning."""
        return DatasetMetadata(
            dataset="ecommerce",
            description="E-commerce customer and order data with 1 million records. IMPORTANT: Return ONLY valid SQL, no explanations or text.",
            scope=ScopeMetadata(
                geographic="Global (8 countries)",
                temporal="12 months rolling",
                domain="E-commerce & Retail",
                important="All amounts in USD. Statuses: Pending, Confirmed, Shipped, Delivered, Returned, Cancelled",
            ),
            schema={
                "customers": TableSchemaMetadata(
                    columns={
                        "customer_id": "INTEGER PRIMARY KEY",
                        "name": "TEXT",
                        "email": "TEXT",
                        "country": "TEXT",
                        "signup_date": "DATE",
                        "customer_tier": "TEXT (Bronze, Silver, Gold, Platinum)",
                        "lifetime_value": "REAL (USD)",
                    },
                    description="Customer master data with segmentation",
                    row_count=100000,
                ),
                "products": TableSchemaMetadata(
                    columns={
                        "product_id": "INTEGER PRIMARY KEY",
                        "name": "TEXT",
                        "category": "TEXT",
                        "price": "REAL (USD)",
                        "stock": "INTEGER",
                    },
                    description="Product catalog",
                    row_count=500,
                    indexes=["category", "price"],
                ),
                "orders": TableSchemaMetadata(
                    columns={
                        "order_id": "INTEGER PRIMARY KEY",
                        "customer_id": "INTEGER",
                        "product_id": "INTEGER",
                        "order_date": "DATE",
                        "quantity": "INTEGER",
                        "total_amount": "REAL (USD)",
                        "status": "TEXT",
                    },
                    description="Order history and transactions",
                    row_count=1000000,
                    indexes=["customer_id", "order_date", "product_id"],
                ),
            },
            capabilities=[
                "customer_analysis",
                "sales_trends",
                "product_performance",
                "geographic_insights",
                "customer_segmentation",
                "revenue_analysis",
            ],
            keywords={
                "customer_tiers": ["bronze", "silver", "gold", "platinum"],
                "categories": [
                    "electronics",
                    "clothing",
                    "home",
                    "sports",
                    "books",
                    "toys",
                    "food",
                ],
                "statuses": [
                    "pending",
                    "confirmed",
                    "shipped",
                    "delivered",
                    "returned",
                    "cancelled",
                ],
                "countries": [
                    "usa",
                    "uk",
                    "canada",
                    "australia",
                    "germany",
                    "france",
                    "japan",
                    "india",
                ],
            },
            constraints=[
                "Order amounts include quantity × price with 10-20% variance (discounts/taxes)",
                "Customer signup dates span up to 2 years in the past",
                "Order dates span 365 days from present",
                "Lifetime value is calculated based on total spending",
            ],
            common_mistakes={
                "wrong_date_format": "Use DATE format for order_date (YYYY-MM-DD)",
                "currency_confusion": "All amounts are in USD",
                "status_case": "Use exact case: Pending, Confirmed, Shipped, Delivered, Returned, Cancelled",
                "missing_join": "Always JOIN orders with customers/products, don't use orders alone for total calculations",
                "aggregate_without_groupby": "If using SUM/COUNT/AVG, MUST use GROUP BY unless aggregating entire table",
                "important_sql_tips": "Always use GROUP BY with aggregates. Use JOINs to combine tables. Filter with WHERE before GROUP BY.",
                "sql_structure": "ONLY return valid SQL. Do not include explanations or markdown. Return ONLY the SQL statement without any text before or after.",
                "no_explanations": "Return raw SQL query only, no markdown code blocks, no 'Here is the SQL:', no explanations",
                "column_qualification": "ALWAYS use table name or alias when selecting columns (e.g., products.category NOT just category). Use aliases: o=orders, p=products, c=customers",
                "join_requirement": "When you JOIN tables, you MUST qualify column names with table alias or name in SELECT clause",
            },
            examples=[
                ExampleMetadata(
                    question="What are the top 5 products by revenue?",
                    sql="SELECT p.name, SUM(o.total_amount) AS revenue FROM orders o JOIN products p ON o.product_id = p.product_id GROUP BY p.product_id, p.name ORDER BY revenue DESC LIMIT 5",
                    expected_results="Returns product names with revenue totals. Uses p alias for products, o for orders. All columns qualified.",
                ),
                ExampleMetadata(
                    question="Show me the top 5 categories by revenue",
                    sql="SELECT p.category, SUM(o.total_amount) AS revenue FROM orders o JOIN products p ON o.product_id = p.product_id GROUP BY p.category ORDER BY revenue DESC LIMIT 5",
                    expected_results="Returns categories with revenue. IMPORTANT: Use p.category (NOT c.category). p=products, o=orders.",
                ),
                ExampleMetadata(
                    question="Who are the top 10 customers by spending?",
                    sql="SELECT c.name, c.email, SUM(o.total_amount) AS total_spent FROM orders o JOIN customers c ON o.customer_id = c.customer_id GROUP BY c.customer_id, c.name, c.email ORDER BY total_spent DESC LIMIT 10",
                    expected_results="Returns customer names/emails with spending totals. Uses c alias for customers, o for orders.",
                ),
            ],
        )
