# Metrics Service API Example

> A comprehensive, production-ready RESTful API for managing metric definitions using axiompy's FastAPI and Database abstractions.

## 🚀 Quick Start

```bash
# 1. Run the interactive demo (no server needed)
python examples/metrics/demo_metrics_api.py

# 2. Run unit tests
python examples/metrics/test_metrics_unit.py

# 3. Start the API server
python examples/metrics/metrics_server.py

# 4. In another terminal, run integration tests
python examples/metrics/test_metrics_api.py

# 5. Access API documentation
open http://localhost:8000/docs
```

## 📁 Files in This Example

| File | Purpose | Lines |
|------|---------|-------|
| `metrics_server.py` | Main application with API, Service, and Repository | 532 |
| `demo_metrics_api.py` | Interactive demo showcasing all features | 217 |
| `test_metrics_unit.py` | 27 unit tests for all layers | 620 |
| `test_metrics_api.py` | Integration tests for HTTP endpoints | 279 |
| `README.md` | Complete guide and API reference (this file) | 597 |
| `METRICS_API_SUMMARY.md` | Implementation details and lessons learned | 461 |
| `__init__.py` | Package exports for easy imports | 35 |

**Total: 2,741 lines of code and documentation**

## 🏗️ Architecture

This example demonstrates best practices for building a layered application:

```
┌─────────────────────────────────────────────┐
│           MetricsAPI (FastAPI)              │
│  - HTTP endpoints                           │
│  - Request/response handling                │
│  - Status codes                             │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│           MetricsService                    │
│  - Business logic                           │
│  - Validation                               │
│  - Orchestration                            │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│        MetricsRepository                    │
│  - CRUD operations                          │
│  - Query building                           │
│  - Schema management                        │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│      axiompy Database Abstraction            │
│  - SQLite / PostgreSQL / MySQL / DynamoDB   │
└─────────────────────────────────────────────┘
```

### Layer Responsibilities

- **API Layer**: HTTP protocol, request/response formatting, status codes
- **Service Layer**: Business rules, validation, error handling
- **Repository Layer**: Data access, query building, schema management
- **Database Layer**: Database connections, transaction management

## ✨ Features

- ✅ Full CRUD operations for metric definitions
- ✅ Tag-based filtering and searching
- ✅ Input validation with detailed error messages
- ✅ RESTful API with proper HTTP status codes
- ✅ Works with SQLite, PostgreSQL, MySQL, or DynamoDB
- ✅ Comprehensive test coverage (27 unit + 10 integration tests)
- ✅ Production-ready error handling
- ✅ Automatic API documentation (FastAPI/Swagger)
- ✅ Clean, layered architecture
- ✅ Dependency injection for easy testing

## 📊 Data Model

The service manages metric definitions with the following schema:

| Field           | Type     | Description                              |
|----------------|----------|------------------------------------------|
| id             | integer  | Primary key (auto-generated)             |
| name           | string   | Unique metric name                       |
| description    | string   | What the metric measures                 |
| source_system  | string   | Source system identifier                 |
| query_template | string   | SQL or query template                    |
| tags           | string   | Comma-separated tags for filtering       |
| created_at     | datetime | Creation timestamp                       |
| updated_at     | datetime | Last update timestamp                    |

## 🔧 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/metrics` | Create a metric |
| GET | `/api/v1/metrics` | List all metrics (with filtering) |
| GET | `/api/v1/metrics/{id}` | Get specific metric |
| PUT | `/api/v1/metrics/{id}` | Update a metric |
| DELETE | `/api/v1/metrics/{id}` | Delete a metric |

### Detailed Endpoint Documentation

#### Health Check
```http
GET /health
```

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "service": "metrics-api"
}
```

#### Create Metric
```http
POST /api/v1/metrics
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "daily_revenue",
  "description": "Total daily revenue from all sales",
  "source_system": "sales_database",
  "query_template": "SELECT SUM(amount) FROM sales WHERE DATE(created_at) = ?",
  "tags": "financial,daily"
}
```

**Response:** `201 Created`
```json
{
  "metric": {
    "id": 1,
    "name": "daily_revenue",
    "description": "Total daily revenue from all sales",
    "source_system": "sales_database",
    "query_template": "SELECT SUM(amount) FROM sales WHERE DATE(created_at) = ?",
    "tags": "financial,daily",
    "created_at": "2025-10-31T12:00:00",
    "updated_at": "2025-10-31T12:00:00"
  },
  "message": "Metric created successfully"
}
```

**Validation Errors:** `400 Bad Request`
```json
{
  "error": "Missing required field: description"
}
```

#### Get Metric by ID
```http
GET /api/v1/metrics/{metric_id}
```

**Response:** `200 OK`
```json
{
  "metric": {
    "id": 1,
    "name": "daily_revenue",
    "description": "Total daily revenue from all sales",
    ...
  }
}
```

**Not Found:** `404 Not Found`
```json
{
  "error": "Metric 1 not found"
}
```

#### List All Metrics
```http
GET /api/v1/metrics?tag=financial
```

**Query Parameters:**
- `tag` (optional): Filter by tag (e.g., `?tag=financial`)

**Response:** `200 OK`
```json
{
  "metrics": [
    {
      "id": 1,
      "name": "daily_revenue",
      ...
    },
    {
      "id": 2,
      "name": "active_users",
      ...
    }
  ],
  "count": 2
}
```

#### Update Metric
```http
PUT /api/v1/metrics/{metric_id}
Content-Type: application/json
```

**Request Body:** (partial update supported)
```json
{
  "description": "Updated description",
  "tags": "financial,daily,updated"
}
```

**Response:** `200 OK`
```json
{
  "metric": {
    "id": 1,
    "name": "daily_revenue",
    "description": "Updated description",
    ...
  },
  "message": "Metric updated successfully"
}
```

#### Delete Metric
```http
DELETE /api/v1/metrics/{metric_id}
```

**Response:** `200 OK`
```json
{
  "message": "Metric 1 deleted successfully"
}
```

## 💡 Usage Examples

### Prerequisites

```bash
# Install dependencies
pip install fastapi uvicorn requests

# Optional: For PostgreSQL/MySQL
pip install psycopg2-binary      # PostgreSQL
pip install mysql-connector-python  # MySQL
```

### Using curl

```bash
# Create a metric
curl -X POST http://localhost:8000/api/v1/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily_revenue",
    "description": "Daily revenue from all channels",
    "source_system": "sales_db",
    "query_template": "SELECT SUM(amount) FROM sales WHERE DATE(created_at) = ?",
    "tags": "financial,daily"
  }'

# List all metrics
curl http://localhost:8000/api/v1/metrics

# Filter by tag
curl "http://localhost:8000/api/v1/metrics?tag=financial"

# Get specific metric
curl http://localhost:8000/api/v1/metrics/1

# Update metric
curl -X PUT http://localhost:8000/api/v1/metrics/1 \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated description"}'

# Delete metric
curl -X DELETE http://localhost:8000/api/v1/metrics/1
```

### Using Python

```python
import requests

BASE_URL = "http://localhost:8000"

# Create a metric
metric_data = {
    "name": "daily_revenue",
    "description": "Daily revenue calculation",
    "source_system": "sales_db",
    "query_template": "SELECT SUM(amount) FROM sales WHERE DATE(created_at) = ?",
    "tags": "financial,daily"
}
response = requests.post(f"{BASE_URL}/api/v1/metrics", json=metric_data)
metric = response.json()["metric"]
print(f"Created metric: {metric['id']}")

# Get metric
response = requests.get(f"{BASE_URL}/api/v1/metrics/{metric['id']}")
print(response.json())

# List all metrics
response = requests.get(f"{BASE_URL}/api/v1/metrics")
print(f"Total metrics: {response.json()['count']}")

# Filter by tag
response = requests.get(f"{BASE_URL}/api/v1/metrics?tag=financial")
print(f"Financial metrics: {response.json()['count']}")

# Update metric
update_data = {"description": "Updated description"}
response = requests.put(f"{BASE_URL}/api/v1/metrics/{metric['id']}", json=update_data)
print(response.json())

# Delete metric
response = requests.delete(f"{BASE_URL}/api/v1/metrics/{metric['id']}")
print(response.json())
```

## 🔄 Switching Database Backends

The example uses SQLite by default, but you can easily switch to other databases:

### PostgreSQL

```python
from axiompy.io.database import DatabaseFactory, DatabaseType, DatabaseSettings

db_settings = DatabaseSettings(
    host="localhost",
    port=5432,
    database="metrics_db",
    username="postgres",
    password="your_password"
)
database = DatabaseFactory.create(DatabaseType.POSTGRES, db_settings)
```

### MySQL

```python
db_settings = DatabaseSettings(
    host="localhost",
    port=3306,
    database="metrics_db",
    username="root",
    password="your_password"
)
database = DatabaseFactory.create(DatabaseType.MYSQL, db_settings)
```

### DynamoDB

```python
db_settings = DatabaseSettings(
    region="us-east-1",
    access_key_id="your_access_key",
    secret_access_key="your_secret_key"
)
database = DatabaseFactory.create(DatabaseType.DYNAMODB, db_settings)
```

## 🎯 Design Patterns

### 1. Layered Architecture
Each layer has a specific responsibility and can be tested independently.

### 2. Dependency Injection
Components depend on abstractions, making them easy to mock and test:

```python
# Production: inject real database
database = DatabaseFactory.create(DatabaseType.SQLITE, settings)
repository = MetricsRepository(database)
service = MetricsService(repository)

# Testing: inject mock database
class MockDatabase(Database):
    def get(self, table, key_value, key_column="id"):
        return {"id": 1, "name": "test_metric"}
    # ... implement other methods

mock_db = MockDatabase(DatabaseSettings())
test_repository = MetricsRepository(mock_db)
test_service = MetricsService(test_repository)
```

### 3. Factory Pattern
Clean creation of servers and databases with consistent interfaces:

```python
# Server creation
server = ServerFactory.create(ServerType.FASTAPI, settings)

# Database creation
database = DatabaseFactory.create(DatabaseType.POSTGRES, settings)
```

### 4. Repository Pattern
Data access logic is isolated, making it easy to switch databases.

### 5. Service Layer
Business logic is separated from HTTP and database concerns.

### Error Handling

Errors are handled at appropriate layers:

```python
# Validation errors (400 Bad Request)
if not metric_data.get("name"):
    raise ValueError("Missing required field: name")

# Not found errors (404 Not Found)
if not metric:
    return {"error": "Metric not found"}, 404

# Database errors (500 Internal Server Error)
except DatabaseQueryError as e:
    logger.error(f"Database error: {e}")
    return {"error": "Internal server error"}, 500
```

## 🧪 Testing

```bash
# Run all unit tests (fast, no dependencies)
python examples/metrics/test_metrics_unit.py

# Output:
# Ran 27 tests in 0.008s
# OK ✅

# Run integration tests (requires server)
# Terminal 1:
python examples/metrics/metrics_server.py

# Terminal 2:
python examples/metrics/test_metrics_api.py

# Output:
# ✅ ALL TESTS PASSED!
```

### Unit Testing Example

```python
import unittest
from axiompy.io.database import Database, DatabaseSettings

class MockDatabase(Database):
    def __init__(self, settings):
        super().__init__(settings)
        self.data = {}

    def get(self, table, key_value, key_column="id"):
        return self.data.get(key_value)

    # ... implement other methods

class TestMetricsService(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabase(DatabaseSettings())
        self.repo = MetricsRepository(self.db)
        self.service = MetricsService(self.repo)

    def test_create_metric(self):
        metric_data = {
            "name": "test_metric",
            "description": "Test",
            "source_system": "test_db",
            "query_template": "SELECT * FROM test"
        }
        result = self.service.create_metric(metric_data)
        self.assertIsNotNone(result)
```

### Test Results

```
✅ Unit Tests: 27/27 passed in 0.008s
✅ Integration Tests: 10/10 passed
✅ Linter Errors: 0
✅ Demo: Runs successfully
```

## 🚧 Extension Ideas

The example can be extended with:

### Add Authentication
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.route("/api/v1/metrics", methods=["POST"])
def create_metric(data: dict, credentials=Depends(security)):
    # Validate token
    # ... create metric
```

### Add Pagination
```python
def list_metrics(self, page: int = 1, page_size: int = 20, tag: Optional[str] = None):
    offset = (page - 1) * page_size
    query = f"SELECT * FROM metrics LIMIT {page_size} OFFSET {offset}"
    # ...
```

### Add Metric Collections (Future Feature)
```python
@app.route("/api/v1/metrics/{vanity_name}", methods=["POST"])
def create_metric_collection(vanity_name: str, data: dict):
    # Store a collection of related metrics
    # Parse and validate the collection format
    pass
```

### Add Metric Execution
```python
def execute_metric(self, metric_id: int, params: dict) -> Any:
    """Execute the metric's query template with parameters."""
    metric = self.get_metric(metric_id)
    query = metric["query_template"]
    # Execute query against source_system
    # Return results
```

### Other Extensions
- Advanced filtering (multiple tags, full-text search)
- Audit logging (track who changed what and when)
- Caching for better performance
- Rate limiting to prevent abuse
- Webhook notifications for metric changes

## 🎓 What You'll Learn

By studying this example, you'll learn:

- ✅ How to structure a multi-layered Python application
- ✅ How to use axiompy's FastAPI and database abstractions
- ✅ RESTful API design with proper HTTP methods and status codes
- ✅ Dependency injection and inversion of control
- ✅ Comprehensive testing strategies (unit + integration)
- ✅ Error handling and validation patterns
- ✅ Working with multiple database backends
- ✅ Design patterns: Repository, Service Layer, Factory
- ✅ Production-ready API best practices

## 📚 Additional Documentation

- **[METRICS_API_SUMMARY.md](METRICS_API_SUMMARY.md)** - Implementation details, design decisions, and lessons learned
- [axiompy Server Documentation](../../axiompy/servers/README.md)
- [axiompy Database Documentation](../../axiompy/io/README.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 🤝 Contributing

This example follows axiompy best practices. Feel free to extend it and submit improvements!

## 📄 License

Part of the axiompy project.

---

**Ready to start?** Run `python examples/metrics/demo_metrics_api.py` to see it in action! 🚀

---

**Last Updated:** 2025-12-03
