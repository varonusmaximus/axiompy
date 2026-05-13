"""
Metrics Service API using axiompy FastAPI and Database tools.

This example demonstrates a complete RESTful API for managing metric definitions
with proper layering: API -> Service -> Repository -> Database.

Architecture:
    - MetricsAPI: FastAPI server with route handlers
    - MetricsService: Business logic and validation
    - MetricsRepository: Database access layer

The service manages metric metadata including:
    - metric_id: Unique identifier
    - name: Metric name
    - description: What the metric measures
    - source_system: Where the data comes from
    - query_template: SQL or query template to execute
    - tags: Comma-separated tags for filtering
    - created_at/updated_at: Timestamps

Example Usage:
    python examples/metrics/metrics_server.py
    # or
    python -m examples.metrics.metrics_server

    Then in another terminal:
    # Create a metric
    curl -X POST http://localhost:8000/api/v1/metrics \\
        -H "Content-Type: application/json" \\
        -d '{"name": "daily_revenue", "description": "Daily revenue calculation", 
             "source_system": "sales_db", "query_template": "SELECT SUM(amount) FROM sales",
             "tags": "financial,daily"}'

    # Get all metrics
    curl http://localhost:8000/api/v1/metrics

    # Get specific metric
    curl http://localhost:8000/api/v1/metrics/1

    # Update metric
    curl -X PUT http://localhost:8000/api/v1/metrics/1 \\
        -H "Content-Type: application/json" \\
        -d '{"description": "Updated description"}'

    # Filter by tag
    curl "http://localhost:8000/api/v1/metrics?tag=financial"
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from axiompy.decorators import CatchAndLog
from axiompy.io.database import (
    Database,
    DatabaseFactory,
    DatabaseQueryError,
    DatabaseSettings,
    DatabaseType,
)
from axiompy.loggers import LoggerFactory
from axiompy.servers import ServerFactory, ServerSettings, ServerType
from axiompy.validators import (
    ValidationError,
    ensure_dict_has_keys,
    ensure_length,
    ensure_not_empty,
    ensure_not_none,
    ensure_positive,
    ensure_regex_match,
    ensure_type,
)

logger = LoggerFactory.create_logger(__name__)


class MetricsRepository:
    """
    Data access layer for metrics.

    Handles all database operations for metric definitions using the axiompy Database abstraction.
    This layer is database-agnostic and can work with MySQL, PostgreSQL, SQLite, or DynamoDB.
    """

    def __init__(self, database: Database):
        """
        Initialize repository with database connection.

        Args:
            database: Database instance from axiompy
        """
        ensure_not_none(database, "Database instance cannot be None")
        ensure_type(database, Database, "Database must be a Database instance")

        self.db = database
        self._ensure_schema()

    @CatchAndLog(
        logger=logger,
        reraise=False,
        exceptions=(DatabaseQueryError,),
        log_level=30,  # logging.WARNING
    )
    def _ensure_schema(self) -> None:
        """Create metrics table if it doesn't exist."""
        # Try to create the table (SQLite syntax, works for most SQL DBs)
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                source_system TEXT,
                query_template TEXT,
                tags TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """
        self.db.execute(create_table_sql)
        logger.info("Metrics table schema verified")

    def create(self, metric_data: Dict[str, Any]) -> int:
        """
        Create a new metric.

        Args:
            metric_data: Dictionary with metric fields

        Returns:
            ID of the created metric

        Raises:
            DatabaseQueryError: If creation fails
            ValidationError: If metric_data is invalid
        """
        ensure_not_none(metric_data, "Metric data cannot be None")
        ensure_type(metric_data, dict, "Metric data must be a dictionary")

        now = datetime.utcnow().isoformat()
        data = {**metric_data, "created_at": now, "updated_at": now}
        metric_id = self.db.set("metrics", data)
        logger.info(f"Created metric: {metric_id}")
        return metric_id

    def get_by_id(self, metric_id: int) -> Optional[Dict[str, Any]]:
        """
        Get metric by ID.

        Args:
            metric_id: Metric identifier

        Returns:
            Metric data or None if not found

        Raises:
            ValidationError: If metric_id is invalid
        """
        ensure_not_none(metric_id, "Metric ID cannot be None")
        ensure_type(metric_id, int, "Metric ID must be an integer")
        ensure_positive(metric_id, f"Metric ID must be positive, got {metric_id}")

        return self.db.get("metrics", metric_id)

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get metric by name.

        Args:
            name: Metric name

        Returns:
            Metric data or None if not found

        Raises:
            ValidationError: If name is invalid
        """
        ensure_not_none(name, "Metric name cannot be None")
        ensure_type(name, str, "Metric name must be a string")
        ensure_not_empty(name, "Metric name cannot be empty")

        # Use execute for custom query
        results = self.db.execute("SELECT * FROM metrics WHERE name = ?", (name,))
        return results[0] if results else None

    def get_all(self, tag_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all metrics, optionally filtered by tag.

        Args:
            tag_filter: Optional tag to filter by

        Returns:
            List of metric dictionaries

        Raises:
            ValidationError: If tag_filter is invalid
        """
        if tag_filter:
            ensure_type(tag_filter, str, "Tag filter must be a string")
            ensure_not_empty(tag_filter, "Tag filter cannot be empty")

            # Filter by tag using LIKE for comma-separated tags
            results = self.db.execute(
                "SELECT * FROM metrics WHERE tags LIKE ?", (f"%{tag_filter}%",)
            )
            return results
        else:
            return self.db.get_all("metrics")

    def update(self, metric_id: int, metric_data: Dict[str, Any]) -> int:
        """
        Update an existing metric.

        Args:
            metric_id: Metric identifier
            metric_data: Fields to update

        Returns:
            Number of rows affected

        Raises:
            DatabaseQueryError: If update fails
            ValidationError: If parameters are invalid
        """
        ensure_not_none(metric_id, "Metric ID cannot be None")
        ensure_type(metric_id, int, "Metric ID must be an integer")
        ensure_positive(metric_id, f"Metric ID must be positive, got {metric_id}")
        ensure_not_none(metric_data, "Metric data cannot be None")
        ensure_type(metric_data, dict, "Metric data must be a dictionary")
        ensure_not_empty(metric_data, "Metric data cannot be empty")

        data = {**metric_data, "updated_at": datetime.utcnow().isoformat()}
        affected = self.db.update("metrics", metric_id, data)
        logger.info(f"Updated metric {metric_id}: {affected} rows")
        return affected

    def delete(self, metric_id: int) -> int:
        """
        Delete a metric by ID.

        Args:
            metric_id: Metric identifier

        Returns:
            Number of rows affected

        Raises:
            ValidationError: If metric_id is invalid
        """
        ensure_not_none(metric_id, "Metric ID cannot be None")
        ensure_type(metric_id, int, "Metric ID must be an integer")
        ensure_positive(metric_id, f"Metric ID must be positive, got {metric_id}")

        affected = self.db.delete("metrics", metric_id)
        logger.info(f"Deleted metric {metric_id}: {affected} rows")
        return affected

    def exists(self, metric_id: int) -> bool:
        """Check if a metric exists."""
        return self.get_by_id(metric_id) is not None


class MetricsService:
    """
    Business logic layer for metrics management.

    Handles validation, business rules, and orchestrates repository operations.
    Provides a clean interface for the API layer.
    """

    def __init__(self, repository: MetricsRepository):
        """
        Initialize service with repository.

        Args:
            repository: MetricsRepository instance
        """
        ensure_not_none(repository, "Repository cannot be None")
        ensure_type(
            repository, MetricsRepository, "Repository must be a MetricsRepository instance"
        )

        self.repo = repository

    def create_metric(self, metric_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new metric with validation.

        Args:
            metric_data: Metric definition

        Returns:
            Created metric with ID

        Raises:
            ValueError: If validation fails
            ValidationError: If data validation fails
        """
        # Type and basic validation
        ensure_not_none(metric_data, "Metric data cannot be None")
        ensure_type(metric_data, dict, "Metric data must be a dictionary")

        # Validate required fields
        required_fields = ["name", "description", "source_system", "query_template"]
        try:
            ensure_dict_has_keys(metric_data, required_fields)
        except ValidationError:
            # Check which specific field is missing for better error message
            for field in required_fields:
                if field not in metric_data:
                    raise ValueError(f"Missing required field: {field}")

        # Validate field contents
        for field in required_fields:
            ensure_not_empty(metric_data[field], f"Field '{field}' cannot be empty")

        # Validate name format (alphanumeric, underscores, hyphens)
        name = metric_data["name"]
        try:
            ensure_type(name, str, "Metric name must be a string")
            ensure_length(
                name, min_length=1, max_length=255, message="Metric name must be 1-255 characters"
            )
            ensure_regex_match(
                name,
                r"^[a-zA-Z0-9_-]+$",
                "Metric name must contain only alphanumeric characters, underscores, and hyphens",
            )

            # Validate description length
            ensure_length(
                metric_data["description"],
                max_length=1000,
                message="Description must not exceed 1000 characters",
            )

            # Validate source_system length
            ensure_length(
                metric_data["source_system"],
                max_length=255,
                message="Source system must not exceed 255 characters",
            )

            # Validate query_template length
            ensure_length(
                metric_data["query_template"],
                max_length=10000,
                message="Query template must not exceed 10000 characters",
            )
        except ValidationError as e:
            raise ValueError(str(e))

        # Check for duplicate name
        existing = self.repo.get_by_name(name)
        if existing:
            raise ValueError(f"Metric with name '{name}' already exists")

        # Create the metric
        metric_id = self.repo.create(metric_data)

        # Return the created metric
        created_metric = self.repo.get_by_id(metric_id)
        return created_metric

    def get_metric(self, metric_id: int) -> Optional[Dict[str, Any]]:
        """
        Get metric by ID.

        Args:
            metric_id: Metric identifier

        Returns:
            Metric data or None if not found

        Raises:
            ValidationError: If metric_id is invalid
        """
        ensure_not_none(metric_id, "Metric ID cannot be None")
        ensure_type(metric_id, int, "Metric ID must be an integer")

        return self.repo.get_by_id(metric_id)

    def list_metrics(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all metrics with optional tag filtering.

        Args:
            tag: Optional tag to filter by

        Returns:
            List of metrics

        Raises:
            ValidationError: If tag is invalid
        """
        if tag is not None:
            ensure_type(tag, str, "Tag must be a string")

        return self.repo.get_all(tag_filter=tag)

    def update_metric(self, metric_id: int, metric_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing metric.

        Args:
            metric_id: Metric identifier
            metric_data: Fields to update

        Returns:
            Updated metric data

        Raises:
            ValueError: If metric doesn't exist or validation fails
            ValidationError: If parameters are invalid
        """
        # Validate parameters
        ensure_not_none(metric_id, "Metric ID cannot be None")
        ensure_type(metric_id, int, "Metric ID must be an integer")
        ensure_not_none(metric_data, "Metric data cannot be None")
        ensure_type(metric_data, dict, "Metric data must be a dictionary")
        ensure_not_empty(metric_data, "Metric data cannot be empty")

        # Check if metric exists
        if not self.repo.exists(metric_id):
            raise ValueError(f"Metric {metric_id} not found")

        # Validate name if being updated
        try:
            if "name" in metric_data:
                name = metric_data["name"]
                ensure_type(name, str, "Metric name must be a string")
                ensure_not_empty(name, "Metric name cannot be empty")
                ensure_length(
                    name,
                    min_length=1,
                    max_length=255,
                    message="Metric name must be 1-255 characters",
                )
                ensure_regex_match(
                    name,
                    r"^[a-zA-Z0-9_-]+$",
                    "Metric name must contain only alphanumeric characters, underscores, and hyphens",
                )

                # Check for duplicate name (excluding current metric)
                existing = self.repo.get_by_name(name)
                if existing and existing["id"] != metric_id:
                    raise ValueError(f"Metric with name '{name}' already exists")

            # Validate other fields if present
            if "description" in metric_data:
                ensure_length(
                    metric_data["description"],
                    max_length=1000,
                    message="Description must not exceed 1000 characters",
                )

            if "source_system" in metric_data:
                ensure_length(
                    metric_data["source_system"],
                    max_length=255,
                    message="Source system must not exceed 255 characters",
                )

            if "query_template" in metric_data:
                ensure_length(
                    metric_data["query_template"],
                    max_length=10000,
                    message="Query template must not exceed 10000 characters",
                )
        except ValidationError as e:
            # Convert ValidationError to ValueError for consistency
            if "already exists" in str(e):
                raise  # Re-raise the original ValueError about duplicate names
            raise ValueError(str(e))

        # Update the metric
        self.repo.update(metric_id, metric_data)

        # Return updated metric
        updated_metric = self.repo.get_by_id(metric_id)
        return updated_metric

    def delete_metric(self, metric_id: int) -> bool:
        """
        Delete a metric.

        Args:
            metric_id: Metric identifier

        Returns:
            True if deleted, False if not found

        Raises:
            ValidationError: If metric_id is invalid
        """
        ensure_not_none(metric_id, "Metric ID cannot be None")
        ensure_type(metric_id, int, "Metric ID must be an integer")

        affected = self.repo.delete(metric_id)
        return affected > 0


class MetricsAPI:
    """
    FastAPI server for metrics management.

    Provides RESTful endpoints for metric CRUD operations using axiompy's FastAPI abstraction.
    Follows REST best practices with proper HTTP methods and status codes.
    """

    def __init__(self, service: MetricsService, server: Any):
        """
        Initialize API with service and server.

        Args:
            service: MetricsService instance
            server: axiompy Server instance
        """
        ensure_not_none(service, "Service cannot be None")
        ensure_type(service, MetricsService, "Service must be a MetricsService instance")
        ensure_not_none(server, "Server cannot be None")

        self.service = service
        self.server = server
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Register all API routes."""
        # Health check
        self.server.route("/health", methods=["GET"])(self.health_check)

        # Metrics endpoints
        self.server.route("/api/v1/metrics", methods=["POST"])(self.create_metric)
        self.server.route("/api/v1/metrics", methods=["GET"])(self.list_metrics)
        self.server.route("/api/v1/metrics/{metric_id}", methods=["GET"])(self.get_metric)
        self.server.route("/api/v1/metrics/{metric_id}", methods=["PUT"])(self.update_metric)
        self.server.route("/api/v1/metrics/{metric_id}", methods=["DELETE"])(self.delete_metric)

        logger.info("API routes registered")

    def health_check(self) -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy", "service": "metrics-api"}

    @CatchAndLog(
        logger=logger,
        reraise=False,
        exceptions=(Exception,),
        default_return=({"error": "Internal server error"}, 500),
    )
    def create_metric(self, data: Dict[str, Any]) -> tuple:
        """
        POST /api/v1/metrics
        Create a new metric.
        """
        try:
            metric = self.service.create_metric(data)
            return ({"metric": metric, "message": "Metric created successfully"}, 201)
        except (ValueError, ValidationError) as e:
            return ({"error": str(e)}, 400)

    @CatchAndLog(
        logger=logger,
        reraise=False,
        exceptions=(Exception,),
        default_return=({"error": "Internal server error"}, 500),
    )
    def get_metric(self, metric_id: int) -> tuple:
        """
        GET /api/v1/metrics/{metric_id}
        Get metric by ID.
        """
        metric = self.service.get_metric(metric_id)
        if metric:
            return ({"metric": metric}, 200)
        else:
            return ({"error": f"Metric {metric_id} not found"}, 404)

    @CatchAndLog(
        logger=logger,
        reraise=False,
        exceptions=(Exception,),
        default_return=({"error": "Internal server error"}, 500),
    )
    def list_metrics(self, tag: Optional[str] = None) -> tuple:
        """
        GET /api/v1/metrics
        List all metrics with optional tag filtering.

        Query Parameters:
            tag: Optional tag to filter by
        """
        metrics = self.service.list_metrics(tag=tag)
        return ({"metrics": metrics, "count": len(metrics)}, 200)

    @CatchAndLog(
        logger=logger,
        reraise=False,
        exceptions=(Exception,),
        default_return=({"error": "Internal server error"}, 500),
    )
    def update_metric(self, metric_id: int, data: Dict[str, Any]) -> tuple:
        """
        PUT /api/v1/metrics/{metric_id}
        Update an existing metric.
        """
        try:
            metric = self.service.update_metric(metric_id, data)
            return ({"metric": metric, "message": "Metric updated successfully"}, 200)
        except (ValueError, ValidationError) as e:
            return ({"error": str(e)}, 404 if "not found" in str(e) else 400)

    @CatchAndLog(
        logger=logger,
        reraise=False,
        exceptions=(Exception,),
        default_return=({"error": "Internal server error"}, 500),
    )
    def delete_metric(self, metric_id: int) -> tuple:
        """
        DELETE /api/v1/metrics/{metric_id}
        Delete a metric.
        """
        deleted = self.service.delete_metric(metric_id)
        if deleted:
            return ({"message": f"Metric {metric_id} deleted successfully"}, 200)
        else:
            return ({"error": f"Metric {metric_id} not found"}, 404)

    def run(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        """Start the API server."""
        logger.info(f"Starting Metrics API on {host}:{port}")
        self.server.run(host=host, port=port)


def create_app(database: Database) -> MetricsAPI:
    """
    Factory function to create the complete metrics API application.

    Args:
        database: Configured database instance

    Returns:
        Configured MetricsAPI instance
    """
    # Create repository
    repository = MetricsRepository(database)

    # Create service
    service = MetricsService(repository)

    # Create server
    server_settings = ServerSettings(
        host="0.0.0.0",
        port=8000,
        debug=True,
        extra_params={
            "title": "Metrics Service API",
            "description": "RESTful API for managing metric definitions",
            "version": "1.0.0",
        },
    )
    server = ServerFactory.create(ServerType.FASTAPI, server_settings)

    # Create API
    api = MetricsAPI(service, server)

    return api


def main():
    """Main entry point for the metrics service."""
    # Configure SQLite database (easy for demonstration)
    # In production, switch to PostgreSQL, MySQL, etc.
    db_settings = DatabaseSettings(database="metrics.db")  # SQLite file

    # Create database connection
    database = DatabaseFactory.create(DatabaseType.SQLITE, db_settings)

    # Create and run the application
    app = create_app(database)

    print("\n" + "=" * 70)
    print("🚀 Metrics Service API is starting...")
    print("=" * 70)
    print("\n📖 API Documentation available at: http://localhost:8000/docs")
    print("\n🔧 Example Commands:")
    print("\n  Create a metric:")
    print("  curl -X POST http://localhost:8000/api/v1/metrics \\")
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"name": "daily_revenue", "description": "Daily revenue", ')
    print(
        '         "source_system": "sales_db", "query_template": "SELECT SUM(amount) FROM sales",'
    )
    print('         "tags": "financial,daily"}\'')
    print("\n  List all metrics:")
    print("  curl http://localhost:8000/api/v1/metrics")
    print("\n  Get specific metric:")
    print("  curl http://localhost:8000/api/v1/metrics/1")
    print("\n  Filter by tag:")
    print('  curl "http://localhost:8000/api/v1/metrics?tag=financial"')
    print("\n" + "=" * 70 + "\n")

    try:
        app.run()
    except KeyboardInterrupt:
        print("\n\n👋 Metrics Service API shutting down...")


if __name__ == "__main__":
    main()
