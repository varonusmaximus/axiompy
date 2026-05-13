"""
Unit tests for the Metrics Service components.

Demonstrates testing patterns for each layer of the application using mocks
and dependency injection, without requiring a real database or server.

Usage:
    python -m pytest examples/metrics/test_metrics_unit.py -v
    # or
    python examples/metrics/test_metrics_unit.py
    # or
    python -m examples.metrics.test_metrics_unit
"""

import sys
import unittest
from typing import Any, Dict, List, Optional, Tuple, Union

from axiompy.io.database import Database, DatabaseSettings
from axiompy.servers import Server, ServerSettings

# Import the components we're testing
from examples.metrics.metrics_server import MetricsAPI, MetricsRepository, MetricsService


class MockDatabase(Database):
    """Mock database for testing without real database connections."""

    def __init__(self, settings: DatabaseSettings):
        super().__init__(settings)
        self.data = {}
        self.next_id = 1
        self.execute_calls = []

    def _cleanup(self) -> None:
        pass

    def get(self, table: str, key_value: Any, key_column: str = "id") -> Optional[Dict[str, Any]]:
        """Get a record by key."""
        for item in self.data.get(table, {}).values():
            if item.get(key_column) == key_value:
                return item
        return None

    def get_all(self, table: str) -> List[Dict[str, Any]]:
        """Get all records from a table."""
        return list(self.data.get(table, {}).values())

    def set(self, table: str, data: Dict[str, Any]) -> Any:
        """Insert a new record."""
        if table not in self.data:
            self.data[table] = {}

        record_id = self.next_id
        self.next_id += 1

        record = {**data, "id": record_id}
        self.data[table][record_id] = record
        return record_id

    def update(
        self, table: str, key_value: Any, data: Dict[str, Any], key_column: str = "id"
    ) -> int:
        """Update an existing record."""
        record = self.get(table, key_value, key_column)
        if record:
            record.update(data)
            return 1
        return 0

    def delete(self, table: str, key_value: Any, key_column: str = "id") -> int:
        """Delete a record by key."""
        if table in self.data:
            for record_id, record in list(self.data[table].items()):
                if record.get(key_column) == key_value:
                    del self.data[table][record_id]
                    return 1
        return 0

    def execute(
        self, sql_string: str, params: Optional[Union[Tuple, Dict]] = None
    ) -> Union[int, List[Dict[str, Any]]]:
        """Execute arbitrary SQL command."""
        self.execute_calls.append((sql_string, params))

        # Handle SELECT queries
        if "SELECT" in sql_string.upper():
            if "WHERE name = ?" in sql_string and params:
                table = "metrics"
                for item in self.data.get(table, {}).values():
                    if item.get("name") == params[0]:
                        return [item]
                return []
            elif "WHERE tags LIKE ?" in sql_string and params:
                table = "metrics"
                tag = params[0].strip("%")
                results = []
                for item in self.data.get(table, {}).values():
                    if tag in item.get("tags", ""):
                        results.append(item)
                return results
            return []

        # For CREATE TABLE, just return success
        return 0


class MockServer(Server):
    """Mock server for testing API without running a real server."""

    def __init__(self, settings: ServerSettings):
        super().__init__(settings)
        self.routes = {}

    def route(self, path: str, methods: Optional[List[str]] = None, **kwargs):
        """Register a route handler."""
        if methods is None:
            methods = ["GET"]

        def decorator(handler):
            for method in methods:
                route_key = f"{method}:{path}"
                self.routes[route_key] = handler
            return handler

        return decorator

    def add_middleware(self, middleware, **kwargs) -> None:
        """Add middleware (no-op for mock)."""
        pass

    def run(self, host: Optional[str] = None, port: Optional[int] = None, **kwargs) -> None:
        """Start server (no-op for mock)."""
        pass

    def get_app(self):
        """Get the app (returns None for mock)."""
        return None

    def call_route(self, method: str, path: str, **kwargs):
        """Helper to call a route for testing."""
        route_key = f"{method}:{path}"
        if route_key in self.routes:
            handler = self.routes[route_key]
            return handler(**kwargs)
        raise ValueError(f"Route not found: {route_key}")


class TestMetricsRepository(unittest.TestCase):
    """Test the MetricsRepository layer."""

    def setUp(self):
        """Set up test fixtures."""
        self.db = MockDatabase(DatabaseSettings())
        self.repo = MetricsRepository(self.db)

    def test_create_metric(self):
        """Test creating a metric."""
        metric_data = {
            "name": "test_metric",
            "description": "Test description",
            "source_system": "test_db",
            "query_template": "SELECT * FROM test",
            "tags": "test,unit",
        }

        metric_id = self.repo.create(metric_data)
        self.assertIsNotNone(metric_id)
        self.assertEqual(metric_id, 1)

        # Verify it was stored
        stored = self.repo.get_by_id(metric_id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored["name"], "test_metric")
        self.assertIn("created_at", stored)
        self.assertIn("updated_at", stored)

    def test_get_by_id(self):
        """Test getting a metric by ID."""
        # Create a metric
        metric_data = {
            "name": "test_metric",
            "description": "Test description",
            "source_system": "test_db",
            "query_template": "SELECT * FROM test",
            "tags": "test",
        }
        metric_id = self.repo.create(metric_data)

        # Get it back
        metric = self.repo.get_by_id(metric_id)
        self.assertIsNotNone(metric)
        self.assertEqual(metric["name"], "test_metric")

    def test_get_by_name(self):
        """Test getting a metric by name."""
        metric_data = {
            "name": "unique_metric",
            "description": "Test description",
            "source_system": "test_db",
            "query_template": "SELECT * FROM test",
            "tags": "test",
        }
        self.repo.create(metric_data)

        # Get by name
        metric = self.repo.get_by_name("unique_metric")
        self.assertIsNotNone(metric)
        self.assertEqual(metric["name"], "unique_metric")

        # Non-existent name
        metric = self.repo.get_by_name("nonexistent")
        self.assertIsNone(metric)

    def test_get_all(self):
        """Test getting all metrics."""
        # Create multiple metrics
        for i in range(3):
            self.repo.create(
                {
                    "name": f"metric_{i}",
                    "description": f"Description {i}",
                    "source_system": "test_db",
                    "query_template": "SELECT * FROM test",
                    "tags": "test",
                }
            )

        # Get all
        metrics = self.repo.get_all()
        self.assertEqual(len(metrics), 3)

    def test_get_all_with_tag_filter(self):
        """Test filtering metrics by tag."""
        # Create metrics with different tags
        self.repo.create(
            {
                "name": "financial_metric",
                "description": "Financial",
                "source_system": "test_db",
                "query_template": "SELECT * FROM test",
                "tags": "financial,daily",
            }
        )
        self.repo.create(
            {
                "name": "user_metric",
                "description": "Users",
                "source_system": "test_db",
                "query_template": "SELECT * FROM test",
                "tags": "users,daily",
            }
        )

        # Filter by tag
        financial_metrics = self.repo.get_all(tag_filter="financial")
        self.assertEqual(len(financial_metrics), 1)
        self.assertEqual(financial_metrics[0]["name"], "financial_metric")

    def test_update(self):
        """Test updating a metric."""
        # Create a metric
        metric_id = self.repo.create(
            {
                "name": "test_metric",
                "description": "Original description",
                "source_system": "test_db",
                "query_template": "SELECT * FROM test",
                "tags": "test",
            }
        )

        # Update it
        affected = self.repo.update(metric_id, {"description": "Updated description"})
        self.assertEqual(affected, 1)

        # Verify update
        metric = self.repo.get_by_id(metric_id)
        self.assertEqual(metric["description"], "Updated description")
        self.assertIn("updated_at", metric)

    def test_delete(self):
        """Test deleting a metric."""
        # Create a metric
        metric_id = self.repo.create(
            {
                "name": "test_metric",
                "description": "Test",
                "source_system": "test_db",
                "query_template": "SELECT * FROM test",
                "tags": "test",
            }
        )

        # Delete it
        affected = self.repo.delete(metric_id)
        self.assertEqual(affected, 1)

        # Verify deletion
        metric = self.repo.get_by_id(metric_id)
        self.assertIsNone(metric)

    def test_exists(self):
        """Test checking if a metric exists."""
        # Create a metric
        metric_id = self.repo.create(
            {
                "name": "test_metric",
                "description": "Test",
                "source_system": "test_db",
                "query_template": "SELECT * FROM test",
                "tags": "test",
            }
        )

        self.assertTrue(self.repo.exists(metric_id))
        self.assertFalse(self.repo.exists(999))


class TestMetricsService(unittest.TestCase):
    """Test the MetricsService layer."""

    def setUp(self):
        """Set up test fixtures."""
        self.db = MockDatabase(DatabaseSettings())
        self.repo = MetricsRepository(self.db)
        self.service = MetricsService(self.repo)

    def test_create_metric_success(self):
        """Test successful metric creation."""
        metric_data = {
            "name": "test_metric",
            "description": "Test description",
            "source_system": "test_db",
            "query_template": "SELECT * FROM test",
        }

        metric = self.service.create_metric(metric_data)
        self.assertIsNotNone(metric)
        self.assertEqual(metric["name"], "test_metric")

    def test_create_metric_missing_required_field(self):
        """Test validation of required fields."""
        metric_data = {
            "name": "test_metric",
            # Missing required fields
        }

        with self.assertRaises(ValueError) as context:
            self.service.create_metric(metric_data)

        self.assertIn("Missing required field", str(context.exception))

    def test_create_metric_invalid_name(self):
        """Test validation of metric name format."""
        metric_data = {
            "name": "invalid metric!",  # Contains invalid characters
            "description": "Test",
            "source_system": "test_db",
            "query_template": "SELECT * FROM test",
        }

        with self.assertRaises(ValueError) as context:
            self.service.create_metric(metric_data)

        self.assertIn("alphanumeric", str(context.exception))

    def test_create_metric_duplicate_name(self):
        """Test validation of duplicate metric names."""
        metric_data = {
            "name": "duplicate_metric",
            "description": "Test",
            "source_system": "test_db",
            "query_template": "SELECT * FROM test",
        }

        # Create first metric
        self.service.create_metric(metric_data)

        # Try to create duplicate
        with self.assertRaises(ValueError) as context:
            self.service.create_metric(metric_data)

        self.assertIn("already exists", str(context.exception))

    def test_get_metric(self):
        """Test getting a metric."""
        # Create a metric
        created = self.service.create_metric(
            {
                "name": "test_metric",
                "description": "Test",
                "source_system": "test_db",
                "query_template": "SELECT * FROM test",
            }
        )

        # Get it
        metric = self.service.get_metric(created["id"])
        self.assertIsNotNone(metric)
        self.assertEqual(metric["id"], created["id"])

    def test_list_metrics(self):
        """Test listing metrics."""
        # Create multiple metrics
        for i in range(3):
            self.service.create_metric(
                {
                    "name": f"metric_{i}",
                    "description": f"Description {i}",
                    "source_system": "test_db",
                    "query_template": "SELECT * FROM test",
                }
            )

        # List all
        metrics = self.service.list_metrics()
        self.assertEqual(len(metrics), 3)

    def test_list_metrics_with_tag_filter(self):
        """Test filtering metrics by tag."""
        # Create metrics with different tags
        self.service.create_metric(
            {
                "name": "financial_metric",
                "description": "Financial",
                "source_system": "test_db",
                "query_template": "SELECT * FROM test",
                "tags": "financial",
            }
        )
        self.service.create_metric(
            {
                "name": "user_metric",
                "description": "Users",
                "source_system": "test_db",
                "query_template": "SELECT * FROM test",
                "tags": "users",
            }
        )

        # Filter by tag
        financial = self.service.list_metrics(tag="financial")
        self.assertEqual(len(financial), 1)

    def test_update_metric_success(self):
        """Test successful metric update."""
        # Create a metric
        created = self.service.create_metric(
            {
                "name": "test_metric",
                "description": "Original",
                "source_system": "test_db",
                "query_template": "SELECT * FROM test",
            }
        )

        # Update it
        updated = self.service.update_metric(created["id"], {"description": "Updated"})
        self.assertEqual(updated["description"], "Updated")

    def test_update_metric_not_found(self):
        """Test updating a non-existent metric."""
        with self.assertRaises(ValueError) as context:
            self.service.update_metric(999, {"description": "Updated"})

        self.assertIn("not found", str(context.exception))

    def test_update_metric_duplicate_name(self):
        """Test updating metric with duplicate name."""
        # Create two metrics
        self.service.create_metric(
            {
                "name": "metric_1",
                "description": "First",
                "source_system": "test_db",
                "query_template": "SELECT * FROM test",
            }
        )
        metric2 = self.service.create_metric(
            {
                "name": "metric_2",
                "description": "Second",
                "source_system": "test_db",
                "query_template": "SELECT * FROM test",
            }
        )

        # Try to rename metric_2 to metric_1
        with self.assertRaises(ValueError) as context:
            self.service.update_metric(metric2["id"], {"name": "metric_1"})

        self.assertIn("already exists", str(context.exception))

    def test_delete_metric(self):
        """Test deleting a metric."""
        # Create a metric
        created = self.service.create_metric(
            {
                "name": "test_metric",
                "description": "Test",
                "source_system": "test_db",
                "query_template": "SELECT * FROM test",
            }
        )

        # Delete it
        deleted = self.service.delete_metric(created["id"])
        self.assertTrue(deleted)

        # Verify deletion
        metric = self.service.get_metric(created["id"])
        self.assertIsNone(metric)


class TestMetricsAPI(unittest.TestCase):
    """Test the MetricsAPI layer."""

    def setUp(self):
        """Set up test fixtures."""
        self.db = MockDatabase(DatabaseSettings())
        self.repo = MetricsRepository(self.db)
        self.service = MetricsService(self.repo)
        self.server = MockServer(ServerSettings())
        self.api = MetricsAPI(self.service, self.server)

    def test_health_check(self):
        """Test health check endpoint."""
        result = self.api.health_check()
        self.assertEqual(result["status"], "healthy")

    def test_create_metric_success(self):
        """Test successful metric creation via API."""
        data = {
            "name": "test_metric",
            "description": "Test",
            "source_system": "test_db",
            "query_template": "SELECT * FROM test",
        }

        response, status_code = self.api.create_metric(data)
        self.assertEqual(status_code, 201)
        self.assertIn("metric", response)
        self.assertEqual(response["metric"]["name"], "test_metric")

    def test_create_metric_validation_error(self):
        """Test metric creation with validation error."""
        data = {"name": "incomplete"}  # Missing required fields

        response, status_code = self.api.create_metric(data)
        self.assertEqual(status_code, 400)
        self.assertIn("error", response)

    def test_get_metric_success(self):
        """Test getting a metric via API."""
        # Create a metric first
        data = {
            "name": "test_metric",
            "description": "Test",
            "source_system": "test_db",
            "query_template": "SELECT * FROM test",
        }
        create_response, _ = self.api.create_metric(data)
        metric_id = create_response["metric"]["id"]

        # Get it
        response, status_code = self.api.get_metric(metric_id)
        self.assertEqual(status_code, 200)
        self.assertIn("metric", response)

    def test_get_metric_not_found(self):
        """Test getting a non-existent metric."""
        response, status_code = self.api.get_metric(999)
        self.assertEqual(status_code, 404)
        self.assertIn("error", response)

    def test_list_metrics(self):
        """Test listing metrics via API."""
        # Create some metrics
        for i in range(3):
            self.api.create_metric(
                {
                    "name": f"metric_{i}",
                    "description": f"Test {i}",
                    "source_system": "test_db",
                    "query_template": "SELECT * FROM test",
                }
            )

        response, status_code = self.api.list_metrics()
        self.assertEqual(status_code, 200)
        self.assertEqual(response["count"], 3)

    def test_update_metric_success(self):
        """Test updating a metric via API."""
        # Create a metric
        create_response, _ = self.api.create_metric(
            {
                "name": "test_metric",
                "description": "Original",
                "source_system": "test_db",
                "query_template": "SELECT * FROM test",
            }
        )
        metric_id = create_response["metric"]["id"]

        # Update it
        response, status_code = self.api.update_metric(metric_id, {"description": "Updated"})
        self.assertEqual(status_code, 200)
        self.assertEqual(response["metric"]["description"], "Updated")

    def test_delete_metric_success(self):
        """Test deleting a metric via API."""
        # Create a metric
        create_response, _ = self.api.create_metric(
            {
                "name": "test_metric",
                "description": "Test",
                "source_system": "test_db",
                "query_template": "SELECT * FROM test",
            }
        )
        metric_id = create_response["metric"]["id"]

        # Delete it
        response, status_code = self.api.delete_metric(metric_id)
        self.assertEqual(status_code, 200)
        self.assertIn("deleted successfully", response["message"])


def run_tests():
    """Run all unit tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestMetricsRepository))
    suite.addTests(loader.loadTestsFromTestCase(TestMetricsService))
    suite.addTests(loader.loadTestsFromTestCase(TestMetricsAPI))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
