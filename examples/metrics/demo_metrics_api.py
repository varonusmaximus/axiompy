# @!documentation

"""
Quick demonstration of the Metrics Service API.

This demo shows how to use the Metrics API programmatically without needing
to run a separate server. Perfect for quick testing and exploration.

Usage:
    python examples/metrics/demo_metrics_api.py
    # or
    python -m examples.metrics.demo_metrics_api
"""

from metrics_server import MetricsRepository, MetricsService

from axiompy.io.database import DatabaseFactory, DatabaseSettings, DatabaseType


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_metric(metric: dict):
    """Pretty print a metric."""
    print(f"\n  📊 Metric ID: {metric['id']}")
    print(f"     Name: {metric['name']}")
    print(f"     Description: {metric['description']}")
    print(f"     Source System: {metric['source_system']}")
    print(f"     Query: {metric['query_template']}")
    print(f"     Tags: {metric.get('tags', 'N/A')}")
    print(f"     Created: {metric['created_at']}")
    print(f"     Updated: {metric['updated_at']}")


def main():
    """Run the demonstration."""
    print("\n" + "🚀 " * 30)
    print("    Metrics Service API Demo")
    print("🚀 " * 30)

    # Create in-memory SQLite database
    print_section("1. Setting Up Database")
    db_settings = DatabaseSettings(database=":memory:")  # In-memory database
    database = DatabaseFactory.create(DatabaseType.SQLITE, db_settings)
    print("  ✓ Created in-memory SQLite database")

    # Create service components
    repository = MetricsRepository(database)
    service = MetricsService(repository)
    print("  ✓ Initialized MetricsRepository and MetricsService")

    # Create metrics
    print_section("2. Creating Metrics")

    metrics_to_create = [
        {
            "name": "daily_revenue",
            "description": "Total daily revenue from all sales channels",
            "source_system": "sales_database",
            "query_template": "SELECT DATE(created_at) as date, SUM(amount) as revenue FROM sales WHERE DATE(created_at) = ?",
            "tags": "financial,daily,revenue",
        },
        {
            "name": "active_users",
            "description": "Count of daily active users",
            "source_system": "user_database",
            "query_template": "SELECT COUNT(DISTINCT user_id) FROM activity WHERE DATE(timestamp) = ?",
            "tags": "users,daily,engagement",
        },
        {
            "name": "conversion_rate",
            "description": "Daily conversion rate percentage",
            "source_system": "analytics_database",
            "query_template": "SELECT (COUNT(conversions) * 100.0 / COUNT(visits)) as rate FROM events WHERE DATE(created_at) = ?",
            "tags": "financial,conversion,daily",
        },
        {
            "name": "avg_order_value",
            "description": "Average order value for completed orders",
            "source_system": "sales_database",
            "query_template": "SELECT AVG(order_total) as avg_value FROM orders WHERE status = 'completed' AND DATE(created_at) = ?",
            "tags": "financial,sales",
        },
        {
            "name": "customer_satisfaction",
            "description": "Average customer satisfaction score",
            "source_system": "feedback_database",
            "query_template": "SELECT AVG(rating) as satisfaction FROM reviews WHERE DATE(created_at) = ?",
            "tags": "customer,quality",
        },
    ]

    created_metrics = []
    for metric_data in metrics_to_create:
        metric = service.create_metric(metric_data)
        created_metrics.append(metric)
        print(f"  ✓ Created: {metric['name']} (ID: {metric['id']})")

    print(f"\n  Total metrics created: {len(created_metrics)}")

    # List all metrics
    print_section("3. Listing All Metrics")
    all_metrics = service.list_metrics()
    print(f"  Found {len(all_metrics)} metrics:\n")
    for metric in all_metrics:
        print(f"    • {metric['name']} - {metric['description']}")

    # Filter by tag
    print_section("4. Filtering Metrics by Tag")
    financial_metrics = service.list_metrics(tag="financial")
    print(f"  Found {len(financial_metrics)} metrics with tag 'financial':\n")
    for metric in financial_metrics:
        print(f"    • {metric['name']} (tags: {metric['tags']})")

    # Get specific metric
    print_section("5. Getting Specific Metric")
    metric_id = created_metrics[0]["id"]
    metric = service.get_metric(metric_id)
    print(f"  Retrieved metric {metric_id}:")
    print_metric(metric)

    # Update a metric
    print_section("6. Updating a Metric")
    metric_id = created_metrics[0]["id"]
    print(f"  Original description: {created_metrics[0]['description']}")

    updated_metric = service.update_metric(
        metric_id,
        {
            "description": "📈 Updated: Total daily revenue from all sales channels including online and retail",
            "tags": "financial,daily,revenue,updated",
        },
    )
    print(f"  Updated description: {updated_metric['description']}")
    print(f"  Updated tags: {updated_metric['tags']}")

    # Demonstrate validation
    print_section("7. Validation Examples")

    # Try to create metric with missing fields
    print("\n  Attempting to create metric with missing required fields...")
    try:
        service.create_metric({"name": "incomplete_metric"})
    except ValueError as e:
        print(f"  ✓ Validation caught error: {e}")

    # Try to create duplicate metric
    print("\n  Attempting to create metric with duplicate name...")
    try:
        service.create_metric(
            {
                "name": "daily_revenue",  # Duplicate!
                "description": "Test",
                "source_system": "test",
                "query_template": "SELECT * FROM test",
            }
        )
    except ValueError as e:
        print(f"  ✓ Validation caught error: {e}")

    # Try to create metric with invalid name
    print("\n  Attempting to create metric with invalid name characters...")
    try:
        service.create_metric(
            {
                "name": "invalid metric!",  # Invalid characters!
                "description": "Test",
                "source_system": "test",
                "query_template": "SELECT * FROM test",
            }
        )
    except ValueError as e:
        print(f"  ✓ Validation caught error: {e}")

    # Delete a metric
    print_section("8. Deleting a Metric")
    metric_to_delete = created_metrics[-1]
    print(f"  Deleting metric: {metric_to_delete['name']} (ID: {metric_to_delete['id']})")
    deleted = service.delete_metric(metric_to_delete["id"])
    print(f"  ✓ Metric deleted: {deleted}")

    # Verify deletion
    remaining_metrics = service.list_metrics()
    print(f"  Remaining metrics: {len(remaining_metrics)}")

    # Final summary
    print_section("9. Final Summary")
    all_metrics = service.list_metrics()

    print(f"\n  📊 Total Metrics: {len(all_metrics)}")
    print("  🏷️  Available Tags:")

    # Collect all unique tags
    all_tags = set()
    for metric in all_metrics:
        tags = metric.get("tags", "").split(",")
        all_tags.update(tag.strip() for tag in tags if tag.strip())

    for tag in sorted(all_tags):
        tag_count = len(service.list_metrics(tag=tag))
        print(f"      • {tag}: {tag_count} metrics")

    print("\n  📈 Metrics by Source System:")
    source_systems = {}
    for metric in all_metrics:
        source = metric["source_system"]
        source_systems[source] = source_systems.get(source, 0) + 1

    for source, count in sorted(source_systems.items()):
        print(f"      • {source}: {count} metrics")

    print("\n" + "=" * 70)
    print("  ✅ Demo Complete!")
    print("=" * 70)
    print("\n  Next Steps:")
    print("    • Run 'python examples/metrics/metrics_server.py' to start the API server")
    print("    • Run 'python examples/metrics/test_metrics_api.py' for integration tests")
    print("    • Run 'python examples/metrics/test_metrics_unit.py' for unit tests")
    print("    • Visit http://localhost:8000/docs for API documentation")
    print("\n")


if __name__ == "__main__":
    main()
