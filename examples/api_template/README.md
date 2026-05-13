# 🚀 AxiomPy Production API Template

A comprehensive, production-ready API template demonstrating all axiompy best practices:
- Railway-Oriented Programming (Result types)
- Input validation with fail-fast semantics
- Comprehensive error handling with recovery hints
- Observability with structured logging and execution timing
- Resilience with retry logic and graceful degradation
- Clean layered architecture with unit and integration tests

## Quick Start

1. **Copy [`USER_DOMAIN_EXAMPLE.md`](USER_DOMAIN_EXAMPLE.md)** as your domain specification (rename/customize fields as needed).
2. **Generate your API** using the AI prompt below (patterns follow `axiompy.servers` and this template layout).
3. **Run tests**: `pytest tests/`
4. **Start API**: `python -m api.main`

For architecture patterns, see [`axiompy/servers/README.md`](../../axiompy/servers/README.md) and the layered layout described in this README.

See the **How to Generate Your API** section below for details.

## 🤖 Generate APIs with AI

This template works perfectly with AI code generation! Use the AI prompt below with your domain specification to generate complete, production-ready APIs in minutes.

### Steps

1. **Copy your domain specification** - Start with [`USER_DOMAIN_EXAMPLE.md`](USER_DOMAIN_EXAMPLE.md)
   - Replace `{YOUR_DOMAIN_NAME}` with your service name
   - Fill in: Context, Resources, Endpoints, Business Rules, Validation, Error Scenarios
   - Set OUTPUT FOLDER to your desired location

2. **Generate your API** - Use the AI prompt below (see next section)

3. **Run and test**:
   ```bash
   pytest tests/
   python -m api.main
   ```

### Example

See [USER_DOMAIN_EXAMPLE.md](USER_DOMAIN_EXAMPLE.md) for a complete example domain specification.

### How to Generate Your API

Use an AI assistant with your customized domain markdown (based on [`USER_DOMAIN_EXAMPLE.md`](USER_DOMAIN_EXAMPLE.md)) and the sample prompt below.

**Sample prompt:**

```
Please execute {domain}.md using the patterns in this api_template (axiompy.servers, Result types, routes/services/domain) to generate my API in the OUTPUT FOLDER.
```

That's it! The example domain file contains the structure expected by this template. The AI will handle the rest.

### What You'll Get

- ✅ Complete Service class with all CRUD methods
- ✅ Result types for all operations (no exceptions)
- ✅ Pydantic models with validation
- ✅ Custom error classes with recovery hints
- ✅ FastAPI routes with error handling
- ✅ 80%+ test coverage (unit + integration)
- ✅ Production-quality code with docstrings
- ✅ In-memory storage (demo-ready)

### Next Steps

1. **Copy your domain** from [`USER_DOMAIN_EXAMPLE.md`](USER_DOMAIN_EXAMPLE.md)
2. **Use the AI prompt above** to generate your API
3. **Run tests**: `pytest tests/`
4. **Start server**: `python -m api.main`

## Architecture

### Layered Design (Bottom-Up)

```
┌─────────────────────────────────────────────────────────────────┐
│                      HTTP Layer (api/)                          │
│  ┌──────────────────────────┐  ┌───────────────────────────┐   │
│  │  Routes (routes/)        │  │  Models (models.py)       │   │
│  │  • ResourceRoutes class  │  │  • ResourceModel          │   │
│  │  • async methods with    │  │  • from_domain()          │   │
│  │    Result[T,E] pipeline  │  │  • to_domain()            │   │
│  │  • setup_routes() wiring │  │  • Pydantic validation    │   │
│  │  • @CatchAndLog + ROP    │  │                           │   │
│  └──────────────────────────┘  └───────────────────────────┘   │
│  All handlers are in routes/ using railway-oriented programming │
│  with Result chains (.map(), .then())                           │
└─────────────────────────────────────────────────────────────────┘
              ↑ Returns validated Response dict
              │ Receives Resource domain entity
┌─────────────────────────────────────────────────────────────────┐
│                  Domain Layer (services/)                       │
│  ┌──────────────────────────┐  ┌───────────────────────────┐   │
│  │  Domain (domain.py)      │  │  Service (resource_      │   │
│  │  • Resource dataclass    │  │  service.py)             │   │
│  │  • Business logic        │  │  • Orchestrates logic    │   │
│  │  • from_dict()           │  │  • Validates with        │   │
│  │  • to_dict()             │  │    axiompy validators     │   │
│  │  • Conversions           │  │  • Works with domain     │   │
│  │                          │  │    entities              │   │
│  └──────────────────────────┘  └───────────────────────────┘   │
│  • Standalone, no inheritance                                  │
│  • Business rules & validation                                 │
│  • Uses @LogAndRethrow for error logging                       │
└─────────────────────────────────────────────────────────────────┘
              ↑ Works with dicts (Resource.to_dict())
              │ Receives dicts from repository
┌─────────────────────────────────────────────────────────────────┐
│                 Repository Layer (services/)                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ResourceRepository (repository.py)                      │  │
│  │  • Pure data access layer (CRUD)                         │  │
│  │  • create(data: dict) → int                              │  │
│  │  • get_by_id(id: int) → Optional[dict]                   │  │
│  │  • get_all() → List[dict]                                │  │
│  │  • update(id: int, data: dict) → int                     │  │
│  │  • delete(id: int) → int                                 │  │
│  │  • Uses axiompy validators for input validation           │  │
│  │  • Timestamps managed here (created_at, updated_at)      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
              ↑ Uses axiompy Database abstraction
              │
┌─────────────────────────────────────────────────────────────────┐
│              Database Layer (axiompy)                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  DatabaseFactory.create(DatabaseType.*, settings)        │  │
│  │  Supports: SQLite, PostgreSQL, MySQL, DynamoDB           │  │
│  │  • get(table, key) → Optional[dict]                      │  │
│  │  • get_all(table) → List[dict]                           │  │
│  │  • set(table, data) → int (returns ID)                   │  │
│  │  • update(table, key, data) → int (rows affected)        │  │
│  │  • delete(table, key) → int (rows affected)              │  │
│  │  • execute(sql, params) → List[dict]                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
api_template/
├── api/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app initialization + DI wiring
│   ├── models.py               # Pydantic models + domain adapters
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py          # Health check endpoints
│   │   └── resources.py       # ResourceRoutes class + setup_routes()
│   └── middleware/
│       ├── __init__.py
│       └── error_handling.py  # ErrorHandler utility
├── services/
│   ├── __init__.py
│   ├── domain.py              # Resource domain entity (@dataclass)
│   ├── resource_service.py    # ResourceService (business logic, standalone)
│   └── repository.py          # ResourceRepository (CRUD via axiompy Database)
├── tests/
│   ├── __init__.py
│   ├── unit/                  # Unit tests (mock repository)
│   │   ├── test_validators.py
│   │   └── test_resource_service.py
│   └── integration/           # Integration tests (full stack)
│       ├── test_health_endpoints.py
│       ├── test_resource_endpoints.py
│       └── conftest.py
└── requirements.txt           # Dependencies
```

## Key Features

### 1. Railway-Oriented Boundaries
All service methods return `Result[T, E]` types for composable, exception-free error handling:

```python
result = service.get_resource(id)
  .map(lambda r: transform(r))
  .then(validate)
  .unwrap_or(default_value)
```

### 2. Input Validation
Declarative validators at API boundaries with clear error messages:

```python
from axiompy.validators import ensure_not_empty, ensure_positive

ensure_not_empty(resource_id, "resource_id cannot be empty")
ensure_positive(limit, "limit must be positive", allow_none=True)
```

### 3. Comprehensive Error Handling
Custom error hierarchy with recovery hints:

```python
from api.errors import ResourceNotFound, ValidationFailed

raise ResourceNotFound(
    resource_id=resource_id,
    recovery_hint="Check that the resource ID is valid and exists"
)
```

### 4. Observability
Structured logging with execution timing at DEBUG level only:

```python
from axiompy.loggers import LoggerFactory

logger = LoggerFactory.create_logger(__name__)
logger.debug(f"Fetching resource: {resource_id}")
```

### 5. Resilience
Built-in retry logic for transient failures:

```python
from axiompy.decorators import Retry

@Retry(logger, max_attempts=3, delay=1.0, backoff=2.0)
def call_external_service():
    return requests.get("https://api.example.com/data")
```

## Layered Architecture Explained

This template implements **Domain-Driven Design** with clear separation of concerns. Each layer has a specific responsibility:

### HTTP Layer (routes + models)

**Responsibility**: HTTP protocol concerns only. Routes use **railway-oriented programming** (Result types) for elegant error handling.

```python
# api/routes/resources.py - Class-based routes with railway-oriented error handling
class ResourceRoutes:
    def __init__(self, service: ResourceService):
        self.service = service
    
    @CatchAndLog(logger, reraise=False, default_return=({"error": "Internal"}, 500))
    async def create_resource(self, data: dict):
        """
        POST /api/v1/resources - 5-step adapter with Result pipeline
        
        Uses .map() and .then() to chain transformations.
        If any step fails, short-circuits to error handling.
        """
        # Railway-oriented validation pipeline
        result = (
            self._parse_resource_model(data)           # Parse HTTP → Pydantic
            .map(lambda model: model.to_domain())      # Convert → Domain
            .then(lambda resource: Ok(self.service.create_resource(resource)))  # Service call
            .map(lambda created: ResourceModel.from_domain(created))  # Domain → HTTP
            .map(lambda response_model: {
                "resource": response_model.model_dump(mode="json"),
                "message": "Resource created"
            })
        )
        
        # Handle result: success or error
        if result.is_ok():
            return result.unwrap()
        else:
            self._handle_result_error(result)

def setup_routes(router: APIRouter, routes: ResourceRoutes) -> None:
    """Wire class methods to @router decorators"""
    @router.post("/resources", status_code=201)
    async def create(data: dict = Body(...)):
        return await routes.create_resource(data)

# api/models.py - Pydantic adapters with domain conversion
class ResourceModel(BaseModel):
    """HTTP representation with domain adapters"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    
    @classmethod
    def from_domain(cls, resource: "Resource") -> "ResourceModel":
        """Convert domain entity to HTTP representation"""
        return cls(
            id=resource.id,
            name=resource.name,
            description=resource.description
        )
    
    def to_domain(self) -> "Resource":
        """Convert HTTP representation to domain entity"""
        return Resource(
            id=self.id,
            name=self.name,
            description=self.description
        )
```

**Key Points**:
- ✅ Class-based routes with dependency injection (service passed to constructor)
- ✅ Railway-oriented programming with Result[T, E] for error handling
- ✅ setup_routes() factory function wires methods to @router decorators
- ✅ 5-step adapter pattern: Parse → Domain → Service → HTTP → Response
- ✅ Uses .map() and .then() to chain transformations (auto short-circuits on error)
- ✅ @CatchAndLog catches uncaught exceptions and returns 500 errors
- ✅ Pydantic models only for HTTP validation and serialization
- ✅ Adapters (from_domain/to_domain) at layer boundaries

### Domain Layer (domain + service)

**Responsibility**: Business logic and domain entities

```python
# services/domain.py
@dataclass
class Resource:
    """Domain entity - the business concept"""
    name: str
    description: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Resource":
        """Convert dict (from repository) to domain entity"""
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            description=data.get("description"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
    
    def to_dict(self) -> dict:
        """Convert domain entity to dict (for repository)"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

# services/resource_service.py
class ResourceService:
    """Business logic for resources - standalone service (no inheritance)"""
    
    def __init__(self, repository: ResourceRepository):
        self.repository = repository
    
    @LogAndRethrow(logger)
    def create_resource(self, resource: Resource) -> Resource:
        """Create resource with business validation"""
        # Validate business rules
        ensure_not_empty(resource.name, "Resource name cannot be empty")
        ensure_length(resource.name, min_length=1, max_length=255)
        
        # Persist via repository
        resource_dict = resource.to_dict()
        resource_id = self.repository.create(resource_dict)
        
        # Return domain entity with generated ID and timestamps
        created_dict = self.repository.get_by_id(resource_id)
        return Resource.from_dict(created_dict)
```

**Key Points**:
- ✅ Standalone service (no inheritance from BaseService)
- ✅ Business logic with axiompy validators for rule enforcement
- ✅ Uses @LogAndRethrow for automatic error logging
- ✅ Orchestrates repository operations (CRUD via repository)
- ✅ Conversions (from_dict/to_dict) at layer boundaries
- ✅ No knowledge of HTTP or database details

### Repository Layer (repository)

**Responsibility**: Pure data access (CRUD operations)

```python
# services/repository.py
class ResourceRepository:
    """Data access layer for resources"""
    
    def __init__(self, database: Database):
        ensure_not_none(database, "Database cannot be None")
        self.db = database
        self._ensure_schema()
    
    def create(self, data: dict) -> int:
        """Create resource. Returns ID"""
        ensure_not_none(data, "Data cannot be None")
        ensure_type(data, dict, "Data must be a dict")
        
        now = datetime.utcnow().isoformat()
        data_with_timestamps = {
            **data,
            "created_at": now,
            "updated_at": now
        }
        data_with_timestamps.pop("id", None)
        
        return self.db.set("resources", data_with_timestamps)
    
    def get_by_id(self, resource_id: int) -> Optional[dict]:
        """Get resource by ID. Returns dict or None"""
        ensure_not_none(resource_id, "Resource ID cannot be None")
        ensure_type(resource_id, int, "Resource ID must be int")
        
        return self.db.get("resources", resource_id)
    
    def get_all(self) -> List[dict]:
        """Get all resources. Returns list of dicts"""
        return self.db.get_all("resources")
    
    def update(self, resource_id: int, data: dict) -> int:
        """Update resource. Returns rows affected"""
        ensure_not_none(resource_id, "Resource ID cannot be None")
        ensure_type(resource_id, int, "Resource ID must be int")
        ensure_not_none(data, "Data cannot be None")
        
        data_with_timestamp = {
            **data,
            "updated_at": datetime.utcnow().isoformat()
        }
        data_with_timestamp.pop("id", None)
        data_with_timestamp.pop("created_at", None)
        
        return self.db.update("resources", resource_id, data_with_timestamp)
    
    def delete(self, resource_id: int) -> int:
        """Delete resource. Returns rows affected"""
        ensure_not_none(resource_id, "Resource ID cannot be None")
        ensure_type(resource_id, int, "Resource ID must be int")
        
        return self.db.delete("resources", resource_id)
```

**Key Points**:
- ✅ Pure data access (works with dicts only)
- ✅ Input validation with axiompy validators
- ✅ No business logic or domain knowledge
- ✅ Timestamp management
- ✅ Easy to test by mocking Database

### Database Layer (axiompy)

**Responsibility**: Database connectivity

```python
# In api/main.py or config
from axiompy.io.database import DatabaseFactory, DatabaseType, DatabaseSettings

db_settings = DatabaseSettings(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 5432)),
    database=os.getenv("DB_NAME", "api.db"),
    username=os.getenv("DB_USER", "user"),
    password=os.getenv("DB_PASSWORD", "password")
)

# Switch databases by changing DatabaseType
database = DatabaseFactory.create(DatabaseType.POSTGRES, db_settings)
# Or: DatabaseType.MYSQL, DatabaseType.SQLITE, DatabaseType.DYNAMODB
```

**Key Points**:
- ✅ Database-agnostic interface (CRUD operations)
- ✅ Multiple backend support
- ✅ Connection pooling and error handling
- ✅ Pure infrastructure layer

### Dependency Injection Chain

```python
# In api/main.py or a dependency injection module
from axiompy.io.database import DatabaseFactory, DatabaseType, DatabaseSettings

# 1. Create database
db_settings = DatabaseSettings(database="api.db")
database = DatabaseFactory.create(DatabaseType.SQLITE, db_settings)

# 2. Create repository (depends on database)
repository = ResourceRepository(database=database)

# 3. Create service (depends on repository)
service = ResourceService(repository=repository)

# 4. Create handlers (depends on service)
handlers = ResourceHandlers(service=service)

# 5. Use in FastAPI routes
@router.post("/api/v1/resources")
async def create_resource(request: dict, handlers: ResourceHandlers = Depends(get_handlers)):
    return handlers.create_resource(request)
```

This ensures:
- ✅ Easy to test: mock any layer
- ✅ Easy to swap: change implementations without affecting other layers
- ✅ Single responsibility: each layer has one job
- ✅ Loose coupling: layers depend on abstractions, not implementations

## Testing Strategy

### Unit Tests (Tests service logic in isolation)
```python
def test_get_resource_success():
    service = ResourceService()
    result = service.get_resource(1)
    assert result.is_ok()
    assert result.unwrap().id == 1

def test_get_resource_not_found():
    service = ResourceService()
    result = service.get_resource(999)
    assert result.is_err()
    assert "not found" in result.get_error()
```

### Integration Tests (Tests API endpoints end-to-end)
```python
def test_get_resource_endpoint(client):
    response = client.get("/api/v1/resources/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

def test_get_resource_validation(client):
    response = client.get("/api/v1/resources/invalid")
    assert response.status_code == 400
    assert "validation" in response.json()["error"]
```

## Environment Setup

Create `.env` file:
```env
LOG_LEVEL=DEBUG
API_HOST=0.0.0.0
API_PORT=8000
WORKERS=4
```

## Running the API

```bash
# Development
python -m api.main

# With specific workers
gunicorn -w 4 api.main:app

# Production
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Customization Guide

### Use AI to Generate New Endpoints

The easiest way to add new endpoints is to use the AI prompt (see "Generate APIs with AI" section). Simply:

1. Update the **Domain Specification** with your new resource
2. Change **OUTPUT FOLDER** to your project path
3. Run the prompt through Claude/GPT-4
4. Merge the generated files into your project

### Manual Implementation

If you prefer to implement manually, follow these patterns from the template:

**1. Create a Service Class** (extends `BaseService`)
- Implement CRUD methods returning `Result[T, E]` types
- Add validation in service methods using axiompy validators
- Use structured logging via `LoggerFactory`

**2. Define Models** in `api/models.py`
- Pydantic `RequestModel` and `ResponseModel` classes
- Proper field validation and documentation

**3. Define Error Classes** in `api/errors.py`
- Extend `AxiomPyAPIError` with domain-specific errors
- Include recovery hints for each error type

**4. Implement Routes** in `api/routes/{domain}.py`
- Use FastAPI `Depends()` for dependency injection
- Handle service `Result` types and convert to HTTP responses
- Validate inputs at route boundaries

**5. Write Tests**
- Unit tests in `tests/unit/test_{domain}_service.py`
- Integration tests in `tests/integration/test_{domain}_endpoints.py`
- Target 80%+ coverage

## Best Practices

✅ **Use Result types** for all service methods (no exceptions)  
✅ **Validate at boundaries** (API routes + service entry points)  
✅ **Log at DEBUG level** only (performance in production)  
✅ **Add retry decorators** for external API calls  
✅ **Test unit logic first**, then integration  
✅ **Document service intent** in docstrings  
✅ **Use consistent error messages** with recovery hints  
✅ **Never catch generic exceptions** - be specific  

## Advanced Customization

### Add Authentication

```python
from fastapi.security import HTTPBearer, HTTPAuthenticationCredentials
from fastapi import Depends

security = HTTPBearer()

@router.get("/api/v1/users/{user_id}")
async def get_user(user_id: str, credentials: HTTPAuthenticationCredentials = Depends(security)):
    """Get user by ID (requires authentication)."""
    token = credentials.credentials
    # Verify token...
    return service.get_user(user_id)
```

### Add Rate Limiting

```python
from axiompy.decorators import RateLimited

@RateLimited(calls=100, period=3600)
@router.get("/api/v1/users")
async def list_users():
    """List users (rate-limited to 100 calls/hour)."""
    return service.list_users()
```

### Add Database with Repository Pattern

```python
from axiompy.io.database import DatabaseFactory, DatabaseType, DatabaseSettings, Database, DatabaseError
from axiompy.result import Result, Ok, Err

# Configure database
db_settings = DatabaseSettings(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 5432)),
    database=os.getenv("DB_NAME", "myapp"),
    username=os.getenv("DB_USER", "user"),
    password=os.getenv("DB_PASSWORD", "password")
)

# Repository: Handles data access
class UserRepository:
    def __init__(self, database: Database = None):
        """
        Initialize repository with database.
        
        Args:
            database: Database instance. If None, creates from factory.
                     Pass a mock for testing.
        """
        if database is None:
            database = DatabaseFactory.create(DatabaseType.POSTGRES, db_settings)
        self.db = database
    
    def get_user(self, user_id: str) -> Result[dict, str]:
        try:
            user = self.db.get("users", user_id)
            if not user:
                return Err(f"User {user_id} not found")
            return Ok(user)
        except DatabaseError as e:
            return Err(f"Database error: {str(e)}")
    
    def create_user(self, user_data: dict) -> Result[str, str]:
        try:
            user_id = self.db.set("users", user_data)
            return Ok(user_id)
        except DatabaseError as e:
            return Err(f"Database error: {str(e)}")
    
    def update_user(self, user_id: str, user_data: dict) -> Result[bool, str]:
        try:
            self.db.update("users", user_id, user_data)
            return Ok(True)
        except DatabaseError as e:
            return Err(f"Database error: {str(e)}")
    
    def delete_user(self, user_id: str) -> Result[bool, str]:
        try:
            self.db.delete("users", user_id)
            return Ok(True)
        except DatabaseError as e:
            return Err(f"Database error: {str(e)}")

# Service: Handles business logic
class UserService(BaseService):
    def __init__(self, repository: UserRepository = None):
        """
        Initialize service with repository.
        
        Args:
            repository: UserRepository instance. If None, creates with default database.
                       Pass a mock for testing.
        """
        super().__init__()
        self.repository = repository or UserRepository()
    
    def get_user(self, user_id: str) -> Result[dict, str]:
        # Business logic can validate and transform
        return self.repository.get_user(user_id)
    
    def create_user(self, user_data: dict) -> Result[str, str]:
        # Business logic: validate, enrich, etc.
        ensure_not_empty(user_data.get("email"), "Email is required")
        return self.repository.create_user(user_data)
```

**Testing Pattern (Mocking):**

```python
# In tests/
class MockUserRepository:
    def get_user(self, user_id: str) -> Result[dict, str]:
        if user_id == "1":
            return Ok({"id": "1", "email": "test@example.com"})
        return Err(f"User {user_id} not found")

# Unit test
def test_get_user():
    mock_repo = MockUserRepository()
    service = UserService(repository=mock_repo)
    
    result = service.get_user("1")
    assert result.is_ok()
    assert result.unwrap()["email"] == "test@example.com"
```

**Benefits:**
- ✅ **Separation of Concerns**: Repository handles data access, Service handles business logic
- ✅ **Testability**: Easy to mock Repository for unit tests without database
- ✅ **Dependency Injection**: Both classes accept their dependencies
- ✅ **Flexibility**: Can swap database implementations without changing Service

### Add Business Validators

Create `services/validators.py`:

```python
from axiompy.validators import ensure_not_empty, ensure_positive
from axiompy.result import Result, Ok, Err

def validate_email(email: str) -> Result[str, str]:
    """Validate email format."""
    try:
        ensure_not_empty(email, "Email cannot be empty")
        if "@" not in email:
            return Err("Invalid email format")
        return Ok(email)
    except Exception as e:
        return Err(str(e))

def validate_user_role(role: str) -> Result[str, str]:
    """Validate user role."""
    valid_roles = ["user", "admin", "moderator"]
    if role not in valid_roles:
        return Err(f"Invalid role. Must be one of: {valid_roles}")
    return Ok(role)
```

## Running Tests

```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# With coverage report
pytest tests/ --cov=api --cov=services --cov-report=html
```

## Troubleshooting

**Import errors?**  
Make sure `api/` and `services/` directories are Python packages (have `__init__.py`)

**Tests not running?**  
Install pytest: `pip install pytest pytest-cov`

**FastAPI not found?**  
Install dependencies: `pip install -r requirements.txt`

**Port already in use?**  
Change API_PORT in `.env` or use different port: `python -m api.main --port 9000`

## Example Implementation

See `examples/api_template/` for a complete working example:
- `api/` - Complete API implementation
- `services/` - Service layer with Result types
- `tests/` - Comprehensive unit and integration tests
- `config/` - Configuration files

## Dependencies

```
fastapi==0.104.0
uvicorn==0.24.0
pydantic==2.5.0
axiompy @ git+https://github.com/varonusmaximus/axiompy.git
```

## Support

- See root `axiompy` README for core module documentation
- Check `tests/` for usage examples
- Review `services/` for service pattern implementation

## License

Same as axiompy (MIT)

---

**Last Updated:** 2025-12-03

