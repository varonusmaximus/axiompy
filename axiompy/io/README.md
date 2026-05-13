# AxiomPy I/O Utilities

Comprehensive I/O utilities for file, database, object storage, and HTTP operations with built-in error handling, logging, and sensible defaults.

## Overview

The `axiompy.io` package provides production-ready utilities for common I/O operations:

- **File I/O**: Read files with automatic error handling, caching, and format detection
- **Database**: Database abstraction layer with support for PostgreSQL, MySQL, DynamoDB, and SQLite
- **Object Storage**: Provider-agnostic interface for AWS S3, Google Cloud Storage, and Azure Blob Storage
- **HTTP**: HTTP client with flexible serializers/deserializers, retry logic, and error handling

> **💡 Tip:** The `axiompy.data` module builds on these I/O utilities for data engineering (Pandas, Spark, streaming). It is shipped in the **`axiompy-data`** distribution (`pip install axiompy-data`) in the **axiompy-data** repository—install alongside core `axiompy`. After install, see `axiompy/data/README.md` in that package’s source tree.

## Installation

Basic functionality requires no additional dependencies:
```bash
pip install axiompy
```

Optional dependencies:
```bash
# File I/O
pip install pyyaml        # For YAML file support

# Database
pip install psycopg2-binary         # For PostgreSQL
pip install mysql-connector-python  # For MySQL
pip install boto3                   # For DynamoDB

# Object Storage
pip install boto3                   # For AWS S3
pip install google-cloud-storage    # For Google Cloud Storage
pip install azure-storage-blob      # For Azure Blob Storage

# Or install all storage providers at once
pip install axiompy[storage]

# Future
pip install requests      # For HTTP operations
```

---

## Table of Contents

- [File I/O Utilities](#file-io-utilities)
- [Database Abstraction Layer](#database-abstraction-layer)
- [Object Storage](#object-storage)
- [HTTP I/O](#http-io)
- [JSON-RPC Client](#json-rpc-client)

---

## File I/O Utilities

Comprehensive file reading utilities with automatic error handling and format support.

### Quick Start

```python
from axiompy.io import read_text, read_json, read_csv

# Read a text file
content = read_text('config.txt')

# Read JSON with fallback
config = read_json('config.json', default={}, raise_on_error=False)

# Process CSV
users = read_csv('users.csv')
for user in users:
    print(user['name'], user['age'])
```

### Available Functions

| Function | Purpose | Key Features |
|----------|---------|--------------|
| `read_text` | Text files | Encoding support, defaults |
| `read_json` | JSON data | Auto-parsing, error handling |
| `read_lines` | Large files | Memory-efficient generator |
| `read_csv` | Tabular data | Dict output, custom delimiters |
| `read_yaml` | YAML config | Safe loading |
| `read_binary` | Binary files | Chunked reading option |
| `safe_read` | Optional files | Never fails, always returns |
| `read_multiple` | Batch ops | Multiple files at once |
| `read_with_path_expansion` | User paths | ~/ and $VAR expansion |
| `CachedReader` | Hot files | In-memory caching, TTL |

### 1. `read_text()` - Text File Reading

Read text files with encoding support and error handling.

```python
from axiompy.io import read_text

# Basic usage
content = read_text('config.txt')

# With default (never raises)
content = read_text('optional.txt', default='')

# Different encoding
content = read_text('file.txt', encoding='latin-1')
```

**Parameters:**
- `filepath`: Path to file (str or Path)
- `encoding`: Text encoding (default: 'utf-8')
- `errors`: Encoding error handling ('strict', 'ignore', 'replace')
- `default`: Value to return on error (None raises exception)
- `logger`: Custom logger instance

**Use when:** Reading configuration files, logs, plain text

---

### 2. `read_json()` - JSON Parsing

Parse JSON files with automatic error handling.

```python
from axiompy.io import read_json

# Basic usage
data = read_json('config.json')

# Safe reading with default
data = read_json('config.json', default={}, raise_on_error=False)

# Custom encoding
data = read_json('data.json', encoding='utf-8')
```

**Parameters:**
- `filepath`: Path to JSON file
- `encoding`: Text encoding (default: 'utf-8')
- `default`: Value to return on error
- `raise_on_error`: Whether to raise exceptions (default: True)
- `logger`: Custom logger instance

**Use when:** Reading JSON configuration, API responses, data files

---

### 3. `read_lines()` - Memory-Efficient Line Reading

Process files line by line without loading entire file into memory.

```python
from axiompy.io import read_lines

# Process large files
for line in read_lines('large_log.txt'):
    process(line)

# Skip empty lines
for line in read_lines('file.txt', skip_empty=True):
    print(line)

# Keep whitespace
for line in read_lines('file.txt', strip=False):
    print(repr(line))
```

**Parameters:**
- `filepath`: Path to file
- `encoding`: Text encoding (default: 'utf-8')
- `strip`: Whether to strip whitespace (default: True)
- `skip_empty`: Whether to skip empty lines (default: False)
- `logger`: Custom logger instance

**Returns:** Generator yielding lines

**Use when:** Processing large log files, avoiding memory issues

---

### 4. `read_csv()` - CSV Data Reading

Read CSV files into list of dictionaries.

```python
from axiompy.io import read_csv

# With headers
users = read_csv('users.csv')
# [{'name': 'John', 'age': '30'}, ...]

# Without headers
data = read_csv('data.csv', has_header=False)
# [{'column_0': 'value', 'column_1': 'value'}, ...]

# TSV files
data = read_csv('data.tsv', delimiter='\t')
```

**Parameters:**
- `filepath`: Path to CSV file
- `delimiter`: Field delimiter (default: ',')
- `has_header`: Whether first row contains headers (default: True)
- `encoding`: Text encoding (default: 'utf-8')
- `logger`: Custom logger instance

**Returns:** List of dictionaries (one per row)

**Use when:** Reading tabular data, spreadsheets exported as CSV

---

### 5. `read_yaml()` - YAML Parsing

Parse YAML configuration files safely.

```python
from axiompy.io import read_yaml

# Basic usage (requires PyYAML)
config = read_yaml('config.yaml')

# Safe reading with default
config = read_yaml('config.yaml', default={}, raise_on_error=False)
```

**Parameters:**
- `filepath`: Path to YAML file
- `encoding`: Text encoding (default: 'utf-8')
- `default`: Value to return on error
- `raise_on_error`: Whether to raise exceptions (default: True)
- `logger`: Custom logger instance

**Requires:** `pip install pyyaml`

**Use when:** Reading YAML configuration files

---

### 6. `read_binary()` - Binary File Reading

Read binary files with optional chunked reading.

```python
from axiompy.io import read_binary

# Read entire file
data = read_binary('image.png')

# Read in chunks (memory efficient)
for chunk in read_binary('large_file.bin', chunk_size=8192):
    process(chunk)
```

**Parameters:**
- `filepath`: Path to binary file
- `chunk_size`: If set, returns generator yielding chunks of this size
- `logger`: Custom logger instance

**Returns:** bytes (full file) or Generator[bytes] (if chunk_size provided)

**Use when:** Reading images, videos, any binary data

---

### 7. `safe_read()` - Never-Fail Reading

Defensive file reading that always succeeds.

```python
from axiompy.io import safe_read
import json

# Simple text with default
content = safe_read('config.txt', default='# default')

# With JSON parser
data = safe_read('data.json', parser=json.loads, default={})

# With custom parser
count = safe_read('count.txt', parser=int, default=0)

# Complex parsing
def parse_config(text):
    return dict(line.split('=') for line in text.strip().split('\n'))

config = safe_read('app.conf', parser=parse_config, default={})
```

**Parameters:**
- `filepath`: Path to file
- `default`: Value to return on any error (default: None)
- `parser`: Optional function to parse file contents
- `encoding`: Text encoding (default: 'utf-8')
- `logger`: Custom logger instance

**Returns:** Parsed content or default value (never raises exceptions)

**Use when:** Optional configuration files, defensive programming

---

### 8. `read_multiple()` - Batch File Reading

Read multiple files in a single operation.

```python
from axiompy.io import read_multiple, read_json

# Read multiple text files
files = read_multiple(['a.txt', 'b.txt', 'c.txt'])
# {'a.txt': 'content a', 'b.txt': 'content b', ...}

# Read multiple JSON files
configs = read_multiple(
    ['dev.json', 'staging.json', 'prod.json'],
    reader_func=read_json,
    fail_fast=False
)

# Pass additional arguments to reader function
files = read_multiple(
    ['file1.txt', 'file2.txt'],
    reader_func=read_text,
    encoding='latin-1',
    default=''
)
```

**Parameters:**
- `filepaths`: List of file paths to read
- `reader_func`: Function to use for reading (default: read_text)
- `fail_fast`: If True, stop on first error (default: False)
- `logger`: Custom logger instance
- `**reader_kwargs`: Additional arguments passed to reader_func

**Returns:** Dict mapping filepath (as string) to contents

**Use when:** Loading multiple config files, batch processing

---

### 9. `read_with_path_expansion()` - Path Expansion

Read files with automatic path expansion.

```python
from axiompy.io import read_with_path_expansion

# Home directory expansion
content = read_with_path_expansion('~/.bashrc')

# Environment variables
content = read_with_path_expansion('$HOME/config.txt')
content = read_with_path_expansion('${CONFIG_DIR}/app.conf')

# Disable expansions if needed
content = read_with_path_expansion(
    path,
    allow_env_vars=False,
    allow_home=False
)
```

**Parameters:**
- `filepath`: Path string that may contain ~ or environment variables
- `allow_env_vars`: Whether to expand $VAR and ${VAR} (default: True)
- `allow_home`: Whether to expand ~ to home directory (default: True)
- `encoding`: Text encoding (default: 'utf-8')
- `logger`: Custom logger instance

**Use when:** User-facing config paths, cross-platform scripts

---

### 10. `CachedReader` - Cached File Reading

File reader with in-memory caching for performance.

```python
from axiompy.io import CachedReader
import json

# Create cached reader with 5-minute TTL
reader = CachedReader(ttl=300)

# First read from disk
config = reader.read('config.json', parser=json.loads)

# Subsequent reads from cache (fast!)
config = reader.read('config.json', parser=json.loads)
config = reader.read('config.json', parser=json.loads)

# Clear specific file from cache
reader.clear_cache('config.json')

# Clear all cache
reader.clear_cache()

# Get cache statistics
stats = reader.get_cache_stats()
print(f"Cached files: {stats['num_entries']}")
```

**Methods:**

- `read(filepath, parser=None, encoding='utf-8', ttl=None)` - Read with caching
- `clear_cache(filepath=None)` - Clear cache (specific file or all)
- `get_cache_stats()` - Get cache statistics

**Constructor Parameters:**
- `ttl`: Time-to-live for cache entries in seconds (None = no expiry)
- `logger`: Custom logger instance

**Use when:** Frequently accessed config files, performance optimization

---

### File I/O Common Patterns

#### Pattern 1: Configuration Loading with Fallbacks

```python
from axiompy.io import safe_read
import json

# Load with multiple fallbacks
config = safe_read('config.json', parser=json.loads, default={
    'debug': False,
    'port': 8000,
    'database': 'sqlite:///app.db'
})
```

#### Pattern 2: Multi-Environment Configuration

```python
from axiompy.io import read_multiple, read_json
import os

env = os.getenv('APP_ENV', 'dev')

# Read base config + environment-specific overrides
configs = read_multiple(
    ['config.base.json', f'config.{env}.json', 'config.local.json'],
    reader_func=read_json,
    fail_fast=False  # Continue if optional files missing
)

# Merge configs (later ones override earlier)
final_config = {}
for config_path in sorted(configs.keys()):
    final_config.update(configs[config_path])
```

#### Pattern 3: Large File Processing

```python
from axiompy.io import read_lines

# Memory-efficient log analysis
stats = {'total': 0, 'errors': 0, 'warnings': 0}

for line in read_lines('app.log', skip_empty=True):
    stats['total'] += 1
    if 'ERROR' in line:
        stats['errors'] += 1
    elif 'WARNING' in line:
        stats['warnings'] += 1

print(f"Processed {stats['total']} lines")
```

#### Pattern 4: Binary File Streaming

```python
from axiompy.io import read_binary
import hashlib

# Stream large binary file
hasher = hashlib.sha256()
for chunk in read_binary('large_file.bin', chunk_size=8192):
    hasher.update(chunk)

digest = hasher.hexdigest()
```

#### Pattern 5: Graceful Degradation

```python
from axiompy.io import safe_read
import json

# Try multiple config locations
for path in ['~/.myapp/config.json', '/etc/myapp/config.json', 'config.json']:
    config = safe_read(path, parser=json.loads)
    if config:
        print(f"Loaded config from: {path}")
        break
else:
    print("No config found, using defaults")
    config = {'debug': True}
```

### File I/O Error Handling

All file utilities support three error handling strategies:

#### 1. Raise Exceptions (Default)
```python
content = read_text('file.txt')  # Raises FileNotFoundError if missing
```

#### 2. Return Default Value
```python
content = read_text('file.txt', default='')  # Returns '' if error
```

#### 3. Safe Mode (Never Fails)
```python
content = safe_read('file.txt', default='')  # Always succeeds
```

#### Custom Logging

All utilities accept an optional `logger` parameter:

```python
import logging
from axiompy.io import read_json

logger = logging.getLogger('myapp')
config = read_json('config.json', logger=logger)
```

### File I/O Performance Tips

1. **Use `read_lines()`** for large files instead of `read_text()` to avoid loading entire file into memory
2. **Use `CachedReader`** for frequently accessed files to avoid repeated disk I/O
3. **Use `chunk_size`** with `read_binary()` when processing large binary files
4. **Use `fail_fast=False`** with `read_multiple()` when some files are optional
5. **Use generators** for streaming operations to minimize memory usage

---

### Result-Based File Operations (Railway-Oriented Programming)

For functional error handling without exceptions, use the `try_*` functions that return `Result` types:

```python
from axiompy.io.file import try_read_text, try_read_json, try_parse_json

# Read text file with Result type
result = try_read_text('config.txt')
if result.is_ok():
    config = result.unwrap()
else:
    error = result.get_error()
    print(f"Error: {error}")

# Chainable JSON reading with error recovery
result = (try_read_json('data.json')
    .map(lambda data: data['users'])  # Transform on success
    .unwrap_or([]))  # Return empty list on error

# Complex error handling with transformations
result = (try_parse_json(json_string)
    .map_error(lambda e: f"Parse failed: {e}")  # Enhance error message
    .or_else(lambda e: try_read_json('default.json')))  # Fallback to file
```

#### Available Result Functions

| Function | Returns | Purpose |
|----------|---------|---------|
| `try_read_text(filepath, encoding, errors, logger)` | `Result[str, str]` | Read text with Result |
| `try_read_json(filepath, encoding, logger)` | `Result[Dict, str]` | Read & parse JSON with Result |
| `try_parse_json(content, filepath, logger)` | `Result[Dict, str]` | Parse JSON string with Result |

#### Result Method Examples

```python
# Composition: Chain operations
result = try_read_json('app.json').map(lambda x: x['version'])

# Error recovery: Provide alternative
result = try_read_json('primary.json').unwrap_or({'default': True})

# Error handling: Process errors
result = try_read_text('file.txt').map_error(lambda e: f"Failed: {e}")

# Conditional logic
if try_read_json('config.json').is_ok():
    print("Config loaded successfully")
else:
    print("Config not found, using defaults")
```

#### Complete Example: Multi-Step File Processing

```python
from axiompy.io.file import try_read_text, try_parse_json

# Read -> Parse -> Transform -> Use
user_data = (try_read_text('users.json')
    .then(lambda content: try_parse_json(content))  # Parse JSON
    .map(lambda data: data['users'])  # Extract users
    .map(lambda users: [u for u in users if u['active']])  # Filter active
    .map(lambda users: sorted(users, key=lambda u: u['name']))  # Sort
    .unwrap_or([]))  # Get result or empty list

print(f"Processing {len(user_data)} active users")
```

---

## Database Abstraction Layer

The database module provides a **consistent, CRUD-based interface** for interacting with multiple database backends without requiring ORMs or heavy external dependencies.

### Supported Databases

- **PostgreSQL** - Full-featured relational database
- **MySQL** - Popular relational database  
- **DynamoDB** - AWS NoSQL database
- **SQLite** - Lightweight database (built-in, no external dependencies)

### Key Features

✅ **Minimal Dependencies**: Uses only standard library where possible  
✅ **No ORM Overhead**: Direct SQL/query execution for maximum control and performance  
✅ **Intuitive CRUD API**: Simple methods for common operations (get, set, update, delete)  
✅ **Flexible Execute Method**: Full SQL control when you need it  
✅ **Automatic Connection Management**: Connects on instantiation, cleans up on destruction  
✅ **Consistent Interface**: Same API across all database types  
✅ **Easy Mocking**: Simple to create mock implementations for unit testing  
✅ **Type Hints**: Full typing support for better IDE integration  

### Database Quick Start

```python
from axiompy.io.database import DatabaseFactory, DatabaseType, DatabaseSettings

# Create database settings
settings = DatabaseSettings(
    host="localhost",
    port=5432,
    database="myapp",
    username="user",
    password="password"
)

# Create database instance (connects automatically)
db = DatabaseFactory.create(DatabaseType.POSTGRES, settings)

# CRUD operations - simple and intuitive
user_id = db.set("users", {"name": "Alice", "email": "alice@example.com", "age": 30})
user = db.get("users", user_id)
db.update("users", user_id, {"age": 31})
all_users = db.get_all("users")
db.delete("users", user_id)

# Custom SQL when needed - full flexibility
adults = db.execute("SELECT * FROM users WHERE age >= ?", (18,))

# Resources are cleaned up automatically when db goes out of scope
```

### Database Architecture

The database abstraction follows these design principles:

1. **Abstract Base Class**: `Database` defines the interface
2. **Concrete Implementations**: Each database type has its own implementation
3. **Factory Pattern**: `DatabaseFactory` creates instances
4. **Dependency Injection**: Services depend on the interface, not implementations

```
┌─────────────────────┐
│  Database (ABC)     │  ← Abstract interface
└─────────────────────┘
          ▲
          │ implements
          │
    ┌─────┴──────┬──────────┬──────────────┐
    │            │          │              │
┌───┴────┐  ┌───┴─────┐  ┌─┴────────┐  ┌──┴──────────┐
│ MySQL  │  │Postgres │  │ DynamoDB │  │   SQLite    │
│Database│  │Database │  │ Database │  │  Database   │
└────────┘  └─────────┘  └──────────┘  └─────────────┘
```

### Database Settings

Configure database connections using the `DatabaseSettings` dataclass:

```python
from axiompy.io.database import DatabaseSettings

# SQL Databases (PostgreSQL, MySQL, SQLite)
settings = DatabaseSettings(
    host="localhost",           # Database host
    port=5432,                  # Database port (3306 for MySQL)
    database="myapp",           # Database name (or file path for SQLite)
    username="user",            # Database username
    password="password",        # Database password
    connection_timeout=30,      # Connection timeout in seconds
    extra_params={}             # Database-specific parameters
)

# DynamoDB
dynamo_settings = DatabaseSettings(
    region="us-east-1",         # AWS region
    access_key_id="...",        # AWS access key (optional, uses credential chain)
    secret_access_key="...",    # AWS secret key (optional)
)

# SQLite (in-memory)
sqlite_settings = DatabaseSettings(
    database=":memory:"         # Special value for in-memory database
)
```

### Database Usage Examples

#### PostgreSQL

```python
from axiompy.io.database import DatabaseFactory, DatabaseType, DatabaseSettings

settings = DatabaseSettings(
    host="localhost",
    port=5432,
    database="myapp",
    username="postgres",
    password="password"
)

db = DatabaseFactory.create(DatabaseType.POSTGRES, settings)

# CRUD operations
user_id = db.set("users", {"name": "Alice", "email": "alice@example.com", "age": 30})
user = db.get("users", user_id)
db.update("users", user_id, {"email": "alice.new@example.com"})

# Custom query with PostgreSQL-specific features
results = db.execute("""
    INSERT INTO users (name, email) 
    VALUES (%s, %s) 
    RETURNING id, name, email
""", ("Bob", "bob@example.com"))

print(f"Created user: {results[0]}")
```

#### MySQL

```python
settings = DatabaseSettings(
    host="localhost",
    port=3306,
    database="myapp",
    username="root",
    password="password",
    extra_params={
        "charset": "utf8mb4",
        "use_unicode": True
    }
)

db = DatabaseFactory.create(DatabaseType.MYSQL, settings)

# CRUD operations
order_id = db.set("orders", {
    "customer_name": "John Smith",
    "total": 199.99,
    "status": "pending"
})
order = db.get("orders", order_id)
db.update("orders", order_id, {"status": "completed"})

# Complex queries using execute
summary = db.execute("""
    SELECT status, COUNT(*) as count, SUM(total) as revenue
    FROM orders
    GROUP BY status
""")
```

#### SQLite

```python
# Perfect for testing and development
settings = DatabaseSettings(database=":memory:")
db = DatabaseFactory.create(DatabaseType.SQLITE, settings)

# Create table using execute
db.execute("""
    CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL
    )
""")

# CRUD operations
product_id = db.set("products", {"name": "Widget", "price": 19.99})
product = db.get("products", product_id)
all_products = db.get_all("products")
db.update("products", product_id, {"price": 24.99})
db.delete("products", product_id)
```

#### DynamoDB

```python
settings = DatabaseSettings(region="us-east-1")
db = DatabaseFactory.create(DatabaseType.DYNAMODB, settings)

# CRUD operations (DynamoDB requires you to provide the key)
db.set("Users", {
    "user_id": "123",
    "username": "john",
    "email": "john@example.com"
})

user = db.get("Users", "123", key_column="user_id")
db.update("Users", "123", {"email": "john.new@example.com"}, key_column="user_id")
all_users = db.get_all("Users")  # Warning: scans entire table
db.delete("Users", "123", key_column="user_id")

# Custom query with execute
from boto3.dynamodb.conditions import Key

results = db.execute(
    "Users",  # Table name
    {
        "KeyConditionExpression": Key("user_id").eq("123")
    }
)
```

### Testing with Database Mocks

The consistent `Database` interface makes it trivial to create mock implementations for unit testing without requiring actual database connections.

#### Creating a Mock Database

```python
from axiompy.io.database import Database, DatabaseSettings
from typing import Any, Dict, List, Optional, Union, Tuple

class MockDatabase(Database):
    """Mock database for testing."""
    
    def __init__(self):
        super().__init__(DatabaseSettings())
        self._data = {}  # Simple in-memory storage
        self._next_id = 1
    
    def _cleanup(self):
        pass
    
    def get(self, table: str, key_value: Any, key_column: str = "id") -> Optional[Dict[str, Any]]:
        table_data = self._data.get(table, {})
        for record in table_data.values():
            if record.get(key_column) == key_value:
                return record
        return None
    
    def get_all(self, table: str) -> List[Dict[str, Any]]:
        return list(self._data.get(table, {}).values())
    
    def set(self, table: str, data: Dict[str, Any]) -> Any:
        if table not in self._data:
            self._data[table] = {}
        record_id = self._next_id
        self._next_id += 1
        record = {"id": record_id, **data}
        self._data[table][record_id] = record
        return record_id
    
    def update(self, table: str, key_value: Any, data: Dict[str, Any], key_column: str = "id") -> int:
        record = self.get(table, key_value, key_column)
        if record:
            record.update(data)
            return 1
        return 0
    
    def delete(self, table: str, key_value: Any, key_column: str = "id") -> int:
        table_data = self._data.get(table, {})
        for record_id, record in list(table_data.items()):
            if record.get(key_column) == key_value:
                del table_data[record_id]
                return 1
        return 0
    
    def execute(self, sql_string: str, params: Optional[Union[Tuple, Dict]] = None) -> Union[int, List[Dict[str, Any]]]:
        # Simple mock - just return empty for now
        if sql_string.strip().upper().startswith("SELECT"):
            return []
        return 0
```

#### Writing Testable Services

Services should depend on the `Database` interface, not concrete implementations:

```python
class UserService:
    """Service that works with ANY Database implementation."""
    
    def __init__(self, database: Database):
        self.db = database  # Depends on interface
    
    def get_user(self, user_id: int):
        return self.db.get("users", user_id)
    
    def create_user(self, name: str, email: str):
        return self.db.set("users", {"name": name, "email": email})
    
    def update_user_email(self, user_id: int, new_email: str):
        return self.db.update("users", user_id, {"email": new_email})
    
    def delete_user(self, user_id: int):
        return self.db.delete("users", user_id)
    
    def find_adults(self):
        return self.db.execute("SELECT * FROM users WHERE age >= ?", (18,))
```

#### Unit Testing with Mocks

```python
def test_create_and_get_user():
    """Test user creation and retrieval with mock database."""
    # Arrange
    mock_db = MockDatabase()
    service = UserService(mock_db)
    
    # Act
    user_id = service.create_user("Alice", "alice@example.com")
    user = service.get_user(user_id)
    
    # Assert
    assert user is not None
    assert user['name'] == 'Alice'
    assert user['email'] == 'alice@example.com'


def test_get_user_not_found():
    """Test user not found scenario."""
    # Arrange
    mock_db = MockDatabase()
    service = UserService(mock_db)
    
    # Act
    user = service.get_user(999)
    
    # Assert
    assert user is None


def test_update_user():
    """Test user update."""
    # Arrange
    mock_db = MockDatabase()
    service = UserService(mock_db)
    user_id = service.create_user("Bob", "bob@example.com")
    
    # Act
    affected = service.update_user_email(user_id, "bob.new@example.com")
    updated_user = service.get_user(user_id)
    
    # Assert
    assert affected == 1
    assert updated_user['email'] == "bob.new@example.com"


def test_delete_user():
    """Test user deletion."""
    # Arrange
    mock_db = MockDatabase()
    service = UserService(mock_db)
    user_id = service.create_user("Charlie", "charlie@example.com")
    
    # Act
    affected = service.delete_user(user_id)
    user = service.get_user(user_id)
    
    # Assert
    assert affected == 1
    assert user is None
```

### Benefits of Database Testing with Mocks

✅ **Fast**: No I/O overhead, tests run in milliseconds  
✅ **Reliable**: No network issues or external dependencies  
✅ **Simple**: No database setup or teardown required  
✅ **Isolated**: Each test is completely independent  
✅ **Verifiable**: Assert on exact database interactions  
✅ **Flexible**: Easy to simulate error conditions and edge cases  

### Database Best Practices

#### 1. Use Dependency Injection

Pass the database as a constructor parameter:

```python
# ✅ Good - testable
class MyService:
    def __init__(self, database: Database):
        self.db = database

# ❌ Bad - hard to test
class MyService:
    def __init__(self):
        self.db = DatabaseFactory.create(...)  # Hard-coded dependency
```

#### 2. Separate Unit and Integration Tests

- **Unit tests**: Use mocks, test business logic
- **Integration tests**: Use real databases (SQLite works great), test end-to-end

```python
# tests/unit/test_user_service.py
def test_with_mock():
    mock_db = MockDatabase()
    service = UserService(mock_db)
    # Fast unit test

# tests/integration/test_user_service.py
def test_with_real_db():
    db = DatabaseFactory.create(DatabaseType.SQLITE, 
                                DatabaseSettings(database=":memory:"))
    service = UserService(db)
    # Slower but comprehensive
```

#### 3. Keep SQL in Repositories

Separate data access from business logic:

```python
# ✅ Good - repository pattern
class UserRepository:
    def __init__(self, database: Database):
        self.db = database
    
    def get_by_id(self, user_id: int):
        return self.db.execute_query(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        )

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.repo = user_repo  # Business logic separate from data access
    
    def get_active_user(self, user_id: int):
        user = self.repo.get_by_id(user_id)
        return user if user and user['active'] else None
```

### Database Error Handling

All database implementations raise consistent exceptions:

```python
from axiompy.io.database import (
    DatabaseError,              # Base exception
    DatabaseConnectionError,    # Connection failures
    DatabaseQueryError          # Query/command execution failures
)

try:
    db = DatabaseFactory.create(DatabaseType.POSTGRES, settings)
    results = db.execute_query("SELECT * FROM users")
except DatabaseConnectionError as e:
    print(f"Failed to connect: {e}")
except DatabaseQueryError as e:
    print(f"Query failed: {e}")
except DatabaseError as e:
    print(f"Database error: {e}")
```

### Database Examples

See the `examples/` directory for complete examples:

- **`database_usage.py`** - Production usage examples for all database types
- **`database_mocking.py`** - Comprehensive testing examples with mocks
- **`TESTING_GUIDE.md`** - Detailed guide on testing with the abstraction

### Database Integration with Data Module

The `axiompy.data` module integrates seamlessly with the Database abstraction for:

- **Lineage Tracking**: Store transformation metadata in any database
- **Pipeline Checkpoints**: Persist pipeline state for resumable workflows
- **DataFrame I/O**: Read/write DataFrames directly to/from databases

```python
from axiompy.io import DatabaseFactory, DatabaseType, DatabaseSettings
from axiompy.data import DataFrameAdapterFactory, LineageTrackerFactory

# Setup database
db_settings = DatabaseSettings(host="localhost", database="myapp", 
                                username="user", password="pass")
db = DatabaseFactory.create(DatabaseType.POSTGRES, db_settings)

# Read DataFrame from database
adapter = DataFrameAdapterFactory.create_auto(df)
df = adapter.read_table(db, "users", columns=["id", "name", "email"])

# Track lineage to database
tracker = LineageTrackerFactory.create_auto(df, storage=db)
tracker.track_transformation(
    job_name="etl_pipeline",
    input_sources=["raw_users"],
    output_targets=["clean_users"],
    transformation="Clean and validate user data"
)

# Write DataFrame back to database
adapter.write_table(df, db, "processed_users", mode="append")
```

See `axiompy/data/README.md` in the **axiompy-data** package for more integration examples.

### Database API Reference

#### DatabaseFactory

```python
DatabaseFactory.create(db_type: DatabaseType, settings: DatabaseSettings) -> Database
```

Creates a database instance of the specified type.

#### Database Interface

```python
class Database(ABC):
    def get(self, table: str, key_value: Any, key_column: str = "id") -> Optional[Dict[str, Any]]
        """Get a single record by key."""
    
    def get_all(self, table: str) -> List[Dict[str, Any]]
        """Get all records from a table."""
    
    def set(self, table: str, data: Dict[str, Any]) -> Any
        """Insert a new record and return its ID/key."""
    
    def update(self, table: str, key_value: Any, data: Dict[str, Any], key_column: str = "id") -> int
        """Update an existing record and return affected rows."""
    
    def delete(self, table: str, key_value: Any, key_column: str = "id") -> int
        """Delete a record by key and return affected rows."""
    
    def execute(self, sql_string: str, params: Optional[Union[Tuple, Dict]] = None) -> Union[int, List[Dict[str, Any]]]
        """Execute arbitrary SQL. Returns list for SELECT, int for INSERT/UPDATE/DELETE."""
```

**Method Details:**

- **`get(table, key_value, key_column="id")`**: Fetch a single record by key
  - Returns: Dictionary or None if not found
  - Example: `user = db.get("users", 123)`

- **`get_all(table)`**: Fetch all records from a table
  - Returns: List of dictionaries
  - Example: `all_users = db.get_all("users")`

- **`set(table, data)`**: Insert a new record
  - Returns: The inserted record's ID (database-specific type)
  - Example: `user_id = db.set("users", {"name": "Alice", "email": "alice@example.com"})`

- **`update(table, key_value, data, key_column="id")`**: Update an existing record
  - Returns: Number of affected rows
  - Example: `affected = db.update("users", 123, {"email": "new@example.com"})`

- **`delete(table, key_value, key_column="id")`**: Delete a record
  - Returns: Number of affected rows
  - Example: `affected = db.delete("users", 123)`

- **`execute(sql_string, params=None)`**: Execute custom SQL
  - Returns: List of dicts for SELECT, int for other commands
  - Example: `adults = db.execute("SELECT * FROM users WHERE age >= ?", (18,))`

#### DatabaseSettings

```python
@dataclass
class DatabaseSettings:
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    region: Optional[str] = None              # DynamoDB only
    access_key_id: Optional[str] = None       # DynamoDB only
    secret_access_key: Optional[str] = None   # DynamoDB only
    connection_timeout: int = 30
    pool_size: int = 5
    extra_params: Dict[str, Any] = field(default_factory=dict)
```

---

## Object Storage

Provider-agnostic object storage abstraction with support for AWS S3, Google Cloud Storage, and Azure Blob Storage.

### Overview

The object storage module provides a unified interface for working with cloud object storage services. Write your code once and switch between providers with a single line change.

**Key Features:**
- ✅ **Provider Agnostic**: Same API for S3, GCS, and Azure
- ✅ **Easy Testing**: Mock implementations for unit tests
- ✅ **Dependency Injection**: Services depend on interface, not implementations
- ✅ **Type Safe**: Full type hints throughout
- ✅ **Production Ready**: Error handling, logging, resource cleanup

### Quick Start

```python
from axiompy.io import ObjectStorageFactory, StorageType, StorageSettings

# Configure storage (example for AWS S3)
settings = StorageSettings(
    bucket="my-bucket",
    region="us-east-1",
    access_key_id="YOUR_KEY",
    secret_access_key="YOUR_SECRET"
)

# Create storage instance
storage = ObjectStorageFactory.create(StorageType.S3, settings)

# Upload a file
storage.put_object("data/report.pdf", b"PDF content")

# Download a file
content = storage.get_object("data/report.pdf")

# List objects
files = storage.list_objects(prefix="data/")
for file in files:
    print(f"{file.key}: {file.size} bytes")

# Generate temporary share link (valid 1 hour)
url = storage.generate_presigned_url("data/report.pdf", expiration=3600)

# Delete a file
storage.delete_object("data/report.pdf")
```

### Supported Providers

| Provider | StorageType | Required Package |
|----------|-------------|------------------|
| AWS S3 | `StorageType.S3` | `boto3` |
| Google Cloud Storage | `StorageType.GCS` | `google-cloud-storage` |
| Azure Blob Storage | `StorageType.AZURE` | `azure-storage-blob` |

### Configuration Examples

#### AWS S3

```python
settings = StorageSettings(
    bucket="my-s3-bucket",
    region="us-east-1",
    access_key_id="AKIA...",
    secret_access_key="...",
    endpoint_url="http://localhost:9000"  # Optional: for MinIO, etc.
)
storage = ObjectStorageFactory.create(StorageType.S3, settings)
```

#### Google Cloud Storage

```python
settings = StorageSettings(
    bucket="my-gcs-bucket",
    project_id="my-project-123",
    credentials_path="/path/to/service-account.json"
)
storage = ObjectStorageFactory.create(StorageType.GCS, settings)
```

#### Azure Blob Storage

```python
# Option 1: Connection string
settings = StorageSettings(
    bucket="my-container",
    connection_string="DefaultEndpointsProtocol=https;..."
)

# Option 2: Account + Key
settings = StorageSettings(
    bucket="my-container",
    account_name="mystorageaccount",
    account_key="YOUR_KEY"
)

storage = ObjectStorageFactory.create(StorageType.AZURE, settings)
```

### Available Operations

| Method | Description |
|--------|-------------|
| `put_object()` | Upload object (bytes or file-like) |
| `get_object()` | Download object as bytes |
| `delete_object()` | Delete an object |
| `object_exists()` | Check if object exists |
| `list_objects()` | List objects with prefix filter |
| `get_object_metadata()` | Get size, modified time, etc. |
| `copy_object()` | Copy within or between buckets |
| `generate_presigned_url()` | Create temporary access URL |
| `put_file()` | Upload from disk |
| `get_file()` | Download to disk |
| `delete_objects()` | Batch delete (optimized for S3) |

### Advanced Usage

#### Upload with Metadata

```python
storage.put_object(
    "data/report.json",
    json_data,
    content_type="application/json",
    metadata={"author": "user123", "version": "2.0"}
)
```

#### Copy Operations

```python
# Copy within same bucket
storage.copy_object("backup/old.txt", "archive/old.txt")

# Copy from another bucket
storage.copy_object(
    "data.json",
    "archive/data.json",
    source_bucket="other-bucket"
)
```

#### Batch Delete

```python
keys = ["temp/file1.txt", "temp/file2.txt", "temp/file3.txt"]
results = storage.delete_objects(keys)

for key, success in results.items():
    print(f"{key}: {'✓' if success else '✗'}")
```

### Dependency Injection Pattern

```python
class DocumentService:
    """Service using storage via dependency injection."""
    
    def __init__(self, storage: ObjectStorage):
        self.storage = storage  # Depends on interface!
    
    def save_document(self, doc_id: str, content: bytes):
        self.storage.put_object(f"docs/{doc_id}.pdf", content)
    
    def get_document(self, doc_id: str) -> bytes:
        return self.storage.get_object(f"docs/{doc_id}.pdf")

# Production: use real storage
storage = ObjectStorageFactory.create(StorageType.S3, settings)
service = DocumentService(storage)

# Testing: use mock storage (no cloud needed!)
mock_storage = MockObjectStorage(StorageSettings(bucket="test"))
service = DocumentService(mock_storage)
```

### Error Handling

```python
from axiompy.io import ObjectNotFoundError, ObjectStorageError

try:
    content = storage.get_object("important.txt")
except ObjectNotFoundError:
    # Object doesn't exist
    content = b"default content"
except ObjectStorageError as e:
    # Other storage error
    logger.error(f"Storage error: {e}")
    raise
```

For comprehensive examples, see `examples/object_storage_examples.py`.

### Object Storage Integration with Data Module

The `axiompy.data` module integrates with ObjectStorage for:

- **Data Partitioning**: Write time/hash/range-partitioned data to S3/GCS/Azure
- **Format Conversion**: Read/write Parquet, CSV, JSON to cloud storage
- **Batch Processing**: Process large datasets stored in object storage

```python
from axiompy.io import ObjectStorageFactory, StorageType, StorageSettings
from axiompy.data import DataPartitionerFactory, PartitionStrategy

# Setup object storage
storage_settings = StorageSettings(bucket="my-data-lake", region="us-east-1")
storage = ObjectStorageFactory.create(StorageType.S3, storage_settings)

# Partition data to cloud storage
partitioner = DataPartitionerFactory.create_auto(
    df,
    partition_key="event_date",
    strategy=PartitionStrategy.TIME_DAILY
)

paths = partitioner.write_partitioned(
    df,
    base_path="s3://my-data-lake/events/",
    storage=storage,
    format="parquet"
)
# Creates: s3://my-data-lake/events/year=2024/month=10/day=30/data.parquet

# Read partitioned data back
subset = partitioner.read_partition(
    "s3://my-data-lake/events/year=2024/month=10/day=30",
    storage=storage
)
```

See `axiompy/data/README.md` in the **axiompy-data** package for more integration examples.

---

## HTTP I/O

HTTP client with flexible serializers/deserializers, automatic retry logic, and comprehensive error handling.

### Key Features

✅ **Flexible Serialization**: Pass custom serializers/deserializers for any format (JSON, XML, YAML, etc.)  
✅ **Automatic Retries**: Built-in exponential backoff with configurable retry policies  
✅ **Error Handling**: Consistent exception handling with detailed error messages  
✅ **Session Management**: Connection pooling and session reuse  
✅ **Timeout Handling**: Configurable timeouts for all operations  
✅ **Authentication**: Support for Basic, Digest, and custom authentication  
✅ **Type Safe**: Full type hints with generics for return values  
✅ **Logging**: Built-in debug logging for all requests  
✅ **Async batch (optional)**: Concurrent requests with `httpx`, per-slot fluent headers, `HTTPExchangeStatus` outcomes (`axiompy[http-async]`)

### Quick Start

```python
from axiompy.io import HTTPClientFactory, DeserializerFactory, SerializerFactory

# Create HTTP client
client = HTTPClientFactory.create()

# Simple GET with JSON deserialization
deserializer = DeserializerFactory.create_json()
data = client.get("https://api.example.com/users", deserializer=deserializer)
print(data)  # Parsed JSON dict

# POST with serialization
serializer = SerializerFactory.create_json()
response = client.post(
    "https://api.example.com/users",
    json={"name": "Alice", "email": "alice@example.com"},
    serializer=serializer,
    deserializer=deserializer
)
print(response)  # Parsed JSON response

# With retry logic
from axiompy.io import RetryConfig

retry_config = RetryConfig(max_attempts=3, base_delay=1.0)
data = client.get_with_retry(
    "https://api.example.com/data",
    retry_config=retry_config,
    deserializer=deserializer
)
```

### Async batch client (`httpx`)

For asyncio code paths, use **`HTTPClientFactory.create(transport=HTTPTransport.ASYNC, settings=...)`** (default transport is **`HTTPTransport.SYNC`**, sync **`HTTPClient`**). Install **`httpx`** via optional extra:

```bash
pip install 'axiompy[http-async]'
```

Batch calls share a **single per-request timeout** for the whole batch (from **`new_batch(timeout_secs=...)`** or the client’s **`HTTPClientSettings.timeout_secs`**). **`dispatch_and_join()`** runs all committed slots concurrently with **`asyncio.gather`** and returns when every slot has a terminal outcome (no exception to the caller for timeouts, transport errors, or non-success HTTP status codes—those appear as **`HTTPExchangeResult`** rows).

**Public API**: Use **`HTTPExchangeStatus`** (`complete`, `failed`, `timeout`, …) and **`HTTPExchangeResult`** (`status`, `results` for parsed body when complete, `http_status_code`, `error_message`). Parsed bodies are plain Python values (dict/list/str); **`httpx`** types are not exposed on **`axiompy.io`** exports.

**Factories**: **`AsyncHTTPClientFactory.create(settings)`** or **`HTTPClientFactory.create(..., transport=HTTPTransport.ASYNC, settings=...)`**. **`MockAsyncHTTPClient`** / **`AsyncHTTPClientFactory.create_mock()`** preset batch results for unit tests without network.

Use **`http.HTTPMethod`** (Python 3.11+) or the same enum from **`axiompy.io.http_async`** on Python 3.10.

```python
import asyncio
from http import HTTPMethod

from axiompy.io import (
    HTTPClientFactory,
    HTTPClientSettings,
    HTTPExchangeStatus,
    HTTPTransport,
)

async def main() -> None:
    client = HTTPClientFactory.create(
        transport=HTTPTransport.ASYNC,
        settings=HTTPClientSettings(timeout_secs=30),
    )
    batch = (
        client.new_batch()
        .add(HTTPMethod.GET, "https://api.example.com/resource")
        .header("X-Request-Id", "abc")
        .commit()
        .add(HTTPMethod.POST, "https://api.example.com/events")
        .json({"event": "open"})
        .header("Idempotency-Key", "ik-1")
        .commit()
    )
    responses = await batch.dispatch_and_join()
    r1, r2 = responses.unwrap()
    if r1.status == HTTPExchangeStatus.COMPLETE:
        print(r1.results)
    if r2.status == HTTPExchangeStatus.TIMEOUT:
        print(r2.error_message)

asyncio.run(main())
```

Shorthand: **`add_get(url, headers=..., params=...)`** and **`add_post(url, json=..., headers=...)`** append a single slot without the **`add(...).commit()`** sub-builder.

#### Testing (`tests/test_http_async.py`)

- **Unit / mock-transport tests** exercise batch fluency, parsing helpers, **`MockAsyncHTTPClient`**, and error paths without real I/O.
- **Integration tests** start a loopback **uvicorn** server whose routes are registered only through **`axiompy.servers.ServerFactory`** and **`@server.route`** (tuple **`(body, status_code)`** for errors). They require **`fastapi`**, **`uvicorn`**, and **`httpx`** (e.g. dev / **`test-all`** install). Set **`AXIOMPY_SKIP_ASYNC_HTTP_LOCAL_SERVER=1`** to skip that class in constrained environments.

### HTTP Client Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `get(url, headers, params, deserializer)` | GET request | Response or deserialized object |
| `post(url, data, json, headers, serializer, deserializer)` | POST request | Response or deserialized object |
| `put(url, data, json, headers, serializer, deserializer)` | PUT request | Response or deserialized object |
| `patch(url, data, json, headers, serializer, deserializer)` | PATCH request | Response or deserialized object |
| `delete(url, headers, deserializer)` | DELETE request | Response or deserialized object |
| `get_with_retry(url, retry_config, deserializer, **kwargs)` | GET with retry | Response or deserialized object |
| `post_with_retry(url, data, json, retry_config, serializer, deserializer, **kwargs)` | POST with retry | Response or deserialized object |
| `put_with_retry(url, data, json, retry_config, serializer, deserializer, **kwargs)` | PUT with retry | Response or deserialized object |
| `patch_with_retry(url, data, json, retry_config, serializer, deserializer, **kwargs)` | PATCH with retry | Response or deserialized object |
| `delete_with_retry(url, retry_config, deserializer, **kwargs)` | DELETE with retry | Response or deserialized object |

### Serializers and Deserializers

| Factory Method | Returns | Purpose |
|---|---|---|
| `SerializerFactory.create_json(**kwargs)` | JSONSerializer | Serialize Python objects to JSON |
| `DeserializerFactory.create_json(**kwargs)` | JSONDeserializer | Parse JSON responses |
| `DeserializerFactory.create_xml()` | XMLDeserializer | Parse XML responses |
| `DeserializerFactory.create_yaml()` | YAMLDeserializer | Parse YAML responses |
| `SerializerFactory.create(format, **kwargs)` | Serializer | Create serializer for any format |
| `DeserializerFactory.create(format, **kwargs)` | Deserializer | Create deserializer for any format |

### Configuration

```python
from axiompy.io import HTTPClientFactory, RetryConfig

# Create client with custom settings
client = (HTTPClientFactory
    .create()
    .with_timeout(60)
    .with_headers({"User-Agent": "MyApp/1.0"})
    .with_basic_auth("user", "password")
)

# Configure retry behavior
retry_config = RetryConfig(
    max_attempts=5,
    base_delay=0.5,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True
)

# Use in requests
data = client.get_with_retry(
    "https://api.example.com/data",
    retry_config=retry_config,
    deserializer=DeserializerFactory.create_json()
)
```

### Error Handling

```python
from axiompy.io import HTTPClientFactory, HTTPRequestError, HTTPAuthError

client = HTTPClientFactory.create()

try:
    data = client.get("https://api.example.com/users")
except HTTPAuthError as e:
    print(f"Authentication failed: {e}")
except HTTPRequestError as e:
    print(f"Request failed: {e}")
```

### Custom Serializers/Deserializers

```python
from axiompy.io.serialization import Serializer, Deserializer, SerializationFormat
from axiompy.io import SerializerFactory, DeserializerFactory
import protobuf

# Create custom protobuf serializer
class ProtobufSerializer(Serializer):
    def serialize(self, data):
        return data.SerializeToString()

class ProtobufDeserializer(Deserializer):
    def __init__(self, message_class):
        self.message_class = message_class
    
    def deserialize(self, response):
        msg = self.message_class()
        msg.ParseFromString(response.content)
        return msg

# Register custom formats
SerializerFactory.register(SerializationFormat.PROTOBUF, ProtobufSerializer)
DeserializerFactory.register(SerializationFormat.PROTOBUF, ProtobufDeserializer)

# Use custom serializer
custom_deserializer = ProtobufDeserializer(MyMessage)
data = client.get("https://api.example.com/data", deserializer=custom_deserializer)
```

### Testing with HTTP Client

```python
from unittest.mock import Mock, patch
from axiompy.io import HTTPClientFactory, DeserializerFactory

# Test with mocked responses
@patch('axiompy.io.http.requests.Session.get')
def test_get_with_deserializer(mock_get):
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = {"users": [{"id": 1, "name": "Alice"}]}
    mock_get.return_value = mock_response
    
    client = HTTPClientFactory.create()
    deserializer = DeserializerFactory.create_json()
    
    # Act
    result = client.get("https://api.example.com/users", deserializer=deserializer)
    
    # Assert
    assert result == {"users": [{"id": 1, "name": "Alice"}]}
    mock_get.assert_called_once()
```

---

## JSON-RPC Client

JSON-RPC 2.0 client with HTTP transport, retry logic, and comprehensive error handling. Built on top of the HTTPClient for maximum reliability.

### Key Features

✅ **JSON-RPC 2.0 Compliant**: Full protocol support including batch requests and notifications  
✅ **Built on HTTPClient**: Leverages existing retry logic, authentication, and session management  
✅ **Typed Exceptions**: Structured error handling with `JSONRPCMethodError`, `JSONRPCConnectionError`, etc.  
✅ **Input Validation**: Uses axiompy validators (`ensure_url`, `ensure_not_empty`, `ensure_in_range`) for robust input checking  
✅ **Performance Logging**: `@LogExecutionTime` decorator on all public methods for debugging  
✅ **Batch Requests**: Execute multiple method calls in a single HTTP request  
✅ **Notifications**: Fire-and-forget method calls with no response expected  
✅ **Mock Client**: Built-in `MockJSONRPCClient` for easy unit testing  
✅ **Fluent API**: Chainable configuration matching HTTPClient patterns  
✅ **Factory Pattern**: Consistent client creation via `JSONRPCClientFactory`  

### Quick Start

```python
from axiompy.io import JSONRPCClientFactory, RetryConfig

# Create client
client = JSONRPCClientFactory.create(
    url="http://localhost:8000/jsonrpc",
    timeout_secs=30
)

# Simple method call
result = client.call("add", {"a": 1, "b": 2})
print(result)  # 3

# With authentication (fluent API)
client = (
    JSONRPCClientFactory.create("http://localhost:8000/jsonrpc")
    .bearer_token("my_token")
    .add_header("X-Custom", "value")
)

# Call with retry logic
retry_config = RetryConfig().with_max_attempts(5)
result = client.call_with_retry("unreliable_method", {"param": "value"}, retry_config)
```

### Input Validation

The JSON-RPC client uses axiompy validators for robust input checking:

| Validation | Validator Used | Error |
|------------|----------------|-------|
| **URL format** | `ensure_url` | Invalid URL raises `ValueError` |
| **Timeout range** | `ensure_in_range(1, 3600)` | Out of range raises `ValueError` |
| **Method name** | `ensure_not_empty` | Empty/whitespace method raises `ValueError` |

```python
from axiompy.io import JSONRPCClientFactory

# Invalid URL format raises ValueError
try:
    client = JSONRPCClientFactory.create(url="not-a-valid-url")
except ValueError as e:
    print(f"URL validation failed: {e}")

# Timeout out of range raises ValueError
try:
    client = JSONRPCClientFactory.create(url="http://localhost", timeout_secs=5000)
except ValueError as e:
    print(f"Timeout validation failed: {e}")

# Empty method name raises ValueError
client = JSONRPCClientFactory.create(url="http://localhost:8000/jsonrpc")
try:
    client.call("", {"a": 1})  # Empty method name
except ValueError as e:
    print(f"Method validation failed: {e}")
```

### Performance Logging

All public methods use `@LogExecutionTime` decorator for performance monitoring (logs at DEBUG level):

```python
import logging
from axiompy.io import JSONRPCClientFactory

# Enable DEBUG logging to see timing
logging.basicConfig(level=logging.DEBUG)

client = JSONRPCClientFactory.create("http://localhost:8000/jsonrpc")
result = client.call("add", {"a": 1, "b": 2})
# Logs: JSON-RPC 'call' completed in 0.0234s
```

### Method Calls

#### Single Method Call

```python
from axiompy.io import JSONRPCClientFactory

client = JSONRPCClientFactory.create("http://localhost:8000/jsonrpc")

# With named parameters (dict)
result = client.call("add", {"a": 1, "b": 2})

# With positional parameters (list)
result = client.call("add", [1, 2])

# Without parameters
result = client.call("ping")
```

#### Notifications (Fire-and-Forget)

Notifications are method calls that don't expect a response:

```python
# Send notification - returns immediately, no response
client.notify("log", {"level": "info", "message": "User logged in"})

# Useful for logging, metrics, or fire-and-forget operations
client.notify("track_event", {"event": "page_view", "page": "/home"})
```

### Batch Requests

Execute multiple requests in a single HTTP call for efficiency:

```python
from axiompy.io import JSONRPCClientFactory

client = JSONRPCClientFactory.create("http://localhost:8000/jsonrpc")

# Build batch requests
requests = [
    client.request("add", {"a": 1, "b": 2}),
    client.request("multiply", {"x": 3, "y": 4}),
    client.notification_request("log", {"msg": "batch"}),  # No response
    client.request("divide", {"a": 10, "b": 2}),
]

# Execute batch
results = client.batch(requests)

# Process results: List of (request_id, result, error) tuples
for req_id, result, error in results:
    if error:
        print(f"Error for {req_id}: {error['message']}")
    else:
        print(f"Result for {req_id}: {result}")
```

### Retry Logic

Built-in retry support using the same `RetryConfig` as HTTPClient:

```python
from axiompy.io import JSONRPCClientFactory, RetryConfig

client = JSONRPCClientFactory.create("http://localhost:8000/jsonrpc")

# Configure retry behavior
retry_config = (
    RetryConfig()
    .with_max_attempts(5)
    .with_initial_backoff_ms(500)
    .with_max_backoff_ms(10000)
    .with_backoff_multiplier(2.0)
)

# Single call with retry
result = client.call_with_retry("flaky_method", {"data": "test"}, retry_config)

# Batch with retry
requests = [
    client.request("method1", {}),
    client.request("method2", {}),
]
results = client.batch_with_retry(requests, retry_config)
```

### Authentication

Fluent API for authentication (delegates to HTTPClient):

```python
from axiompy.io import JSONRPCClientFactory

# Bearer token
client = (
    JSONRPCClientFactory.create("http://localhost:8000/jsonrpc")
    .bearer_token("my_oauth_token")
)

# Basic auth
client = (
    JSONRPCClientFactory.create("http://localhost:8000/jsonrpc")
    .basic_auth("username", "password")
)

# Custom header auth (API key, etc.)
client = (
    JSONRPCClientFactory.create("http://localhost:8000/jsonrpc")
    .custom_auth("X-API-Key", "secret_key")
)

# Multiple headers
client = (
    JSONRPCClientFactory.create("http://localhost:8000/jsonrpc")
    .bearer_token("token")
    .add_header("X-Request-ID", "req-123")
    .add_header("X-Client-Version", "1.0")
)
```

### Error Handling

Structured error handling with typed exceptions:

```python
from axiompy.io import (
    JSONRPCClientFactory,
    JSONRPCMethodError,
    JSONRPCConnectionError,
    JSONRPCProtocolError,
    JSONRPCErrorCode,
)

client = JSONRPCClientFactory.create("http://localhost:8000/jsonrpc")

try:
    result = client.call("some_method", {"param": "value"})
except JSONRPCMethodError as e:
    # Server returned an error response
    print(f"Method error: {e.message}")
    print(f"Error code: {e.code}")  # JSON-RPC error code
    print(f"Error data: {e.data}")  # Optional additional data
    
    # Check specific error codes
    if e.code == JSONRPCErrorCode.METHOD_NOT_FOUND.value:
        print("Method does not exist")
    elif e.code == JSONRPCErrorCode.INVALID_PARAMS.value:
        print("Invalid parameters")
        
except JSONRPCConnectionError as e:
    # Connection to server failed
    print(f"Connection error: {e}")
    
except JSONRPCProtocolError as e:
    # Invalid response format from server
    print(f"Protocol error: {e}")
```

#### JSON-RPC Error Codes

Standard JSON-RPC 2.0 error codes are available via `JSONRPCErrorCode`:

| Code | Name | Description |
|------|------|-------------|
| -32700 | PARSE_ERROR | Invalid JSON |
| -32600 | INVALID_REQUEST | Not a valid Request object |
| -32601 | METHOD_NOT_FOUND | Method does not exist |
| -32602 | INVALID_PARAMS | Invalid method parameters |
| -32603 | INTERNAL_ERROR | Internal JSON-RPC error |
| -32000 | SERVER_ERROR | Generic server error |

### Testing with MockJSONRPCClient

Built-in mock client for unit testing:

```python
from axiompy.io import JSONRPCClientFactory, MockJSONRPCClient, JSONRPCMethodError

# Create mock client
mock = JSONRPCClientFactory.create_mock()

# Set predefined responses
mock.set_response("add", 42)
mock.set_response("multiply", 12)

# Set predefined errors
mock.set_error("fail", -32000, "Intentional error", {"reason": "test"})

# Use in tests
result = mock.call("add", {"a": 1, "b": 2})
assert result == 42

# Verify calls were made
assert len(mock.calls) == 1
assert mock.calls[0] == ("add", {"a": 1, "b": 2})

# Test notifications
mock.notify("log", {"msg": "test"})
assert len(mock.notifications) == 1

# Reset state
mock.reset()
assert mock.calls == []
```

#### Dependency Injection Pattern

```python
# Service that uses JSON-RPC client
class PaymentService:
    def __init__(self, rpc_client):
        self.client = rpc_client  # Depends on interface
    
    def process_payment(self, amount: float) -> dict:
        return self.client.call("process_payment", {"amount": amount})
    
    def get_status(self, payment_id: str) -> dict:
        return self.client.call("get_status", {"id": payment_id})

# Production: use real client
client = JSONRPCClientFactory.create("http://payment-api/jsonrpc")
service = PaymentService(client)

# Testing: use mock client
mock = JSONRPCClientFactory.create_mock({
    "process_payment": {"status": "success", "id": "pay-123"},
    "get_status": {"status": "completed"},
})
service = PaymentService(mock)
```

### Configuration

#### JSONRPCClientSettings

```python
from axiompy.io.jsonrpc import JSONRPCClientSettings, JSONRPCClientFactory

# Full configuration
settings = JSONRPCClientSettings(
    url="http://localhost:8000/jsonrpc",
    timeout_secs=60,
    verify_ssl=True,
    id_generator=lambda: str(uuid.uuid4()),  # Custom ID generator
    extra_params={"custom": "value"},
)

client = JSONRPCClientFactory.create_from_settings(settings)
```

### API Reference

#### JSONRPCClientFactory

```python
JSONRPCClientFactory.create(
    url: str,
    timeout_secs: int = 30,
    verify_ssl: bool = True,
    id_generator: Optional[Callable] = None
) -> JSONRPCClient

JSONRPCClientFactory.create_from_settings(settings: JSONRPCClientSettings) -> JSONRPCClient

JSONRPCClientFactory.create_mock(responses: Optional[Dict[str, Any]] = None) -> MockJSONRPCClient
```

#### JSONRPCClient Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `call(method, params)` | Single method call | Result value |
| `notify(method, params)` | Fire-and-forget notification | None |
| `batch(requests)` | Execute batch requests | List of (id, result, error) |
| `call_with_retry(method, params, retry_config)` | Call with retry | Result value |
| `batch_with_retry(requests, retry_config)` | Batch with retry | List of (id, result, error) |
| `request(method, params)` | Create request builder | JSONRPCRequestBuilder |
| `notification_request(method, params)` | Create notification builder | JSONRPCRequestBuilder |
| `add_header(key, value)` | Add default header | Self (fluent) |
| `bearer_token(token)` | Set bearer auth | Self (fluent) |
| `basic_auth(user, pass)` | Set basic auth | Self (fluent) |
| `custom_auth(header, value)` | Set custom auth | Self (fluent) |

### Complete Example: MCP Client

```python
from axiompy.io import JSONRPCClientFactory, RetryConfig

# Create client for MCP server
client = (
    JSONRPCClientFactory.create("http://localhost:8000/jsonrpc")
    .bearer_token("mcp_token")
)

# Initialize connection
init_result = client.call("initialize", {
    "protocolVersion": "2024-11-05",
    "clientInfo": {"name": "my-client", "version": "1.0"}
})
print(f"Server: {init_result['serverInfo']['name']}")

# Send initialized notification
client.notify("initialized", {})

# List available tools
tools_result = client.call("tools/list", {})
for tool in tools_result["tools"]:
    print(f"Tool: {tool['name']} - {tool['description']}")

# Call a tool
result = client.call_with_retry(
    "tools/call",
    {"name": "add", "arguments": {"a": 1, "b": 2}},
    RetryConfig().with_max_attempts(3)
)
print(f"Result: {result['content'][0]['text']}")
```

---

## Testing

Comprehensive test suite included:

```bash
# Run all I/O tests
pytest tests/test_file_io.py tests/test_database.py -v

# Run specific test modules
pytest tests/test_file_io.py -v
pytest tests/test_database.py -v

# Run with coverage
pytest tests/ --cov=axiompy.io
```

**Test Coverage:**
- File I/O: 32 tests covering all file operations
- Database: Comprehensive tests for all database types and mocking patterns

---

## API Reference

For detailed API documentation, see docstrings in:
- `axiompy/io/file.py` - File I/O utilities
- `axiompy/io/database.py` - Database abstraction layer
- `axiompy/io/object.py` - Object storage abstraction (S3, GCS, Azure)
- `axiompy/io/http.py` - HTTP client utilities

---

## Contributing

When adding new I/O utilities:

1. Follow the established patterns (error handling, logging, defaults)
2. Add comprehensive docstrings with examples
3. Write tests in `tests/test_<module>.py`
4. Update this README with new utilities
5. Add usage examples to `examples/`

### Adding a New Database Type

To add support for a new database:

1. Create a class that inherits from `Database`
2. Implement all abstract methods: `get`, `get_all`, `set`, `update`, `delete`, `execute`
3. Implement `_cleanup` for resource cleanup
4. Register with `DatabaseFactory.register_database()`

```python
class MyDatabase(Database):
    def __init__(self, settings: DatabaseSettings):
        super().__init__(settings)
        # Connect to database here
    
    def _cleanup(self):
        # Clean up resources here
    
    def get(self, table: str, key_value: Any, key_column: str = "id") -> Optional[Dict[str, Any]]:
        # Implementation - fetch single record
    
    def get_all(self, table: str) -> List[Dict[str, Any]]:
        # Implementation - fetch all records
    
    def set(self, table: str, data: Dict[str, Any]) -> Any:
        # Implementation - insert record
    
    def update(self, table: str, key_value: Any, data: Dict[str, Any], key_column: str = "id") -> int:
        # Implementation - update record
    
    def delete(self, table: str, key_value: Any, key_column: str = "id") -> int:
        # Implementation - delete record
    
    def execute(self, sql_string: str, params: Optional[Union[Tuple, Dict]] = None) -> Union[int, List[Dict[str, Any]]]:
        # Implementation - execute custom SQL

# Register the new database type
DatabaseFactory.register_database(DatabaseType.MY_DB, MyDatabase)
```

---

## License

Part of the AxiomPy library. See main repository for license information.

---

**Last Updated:** 2025-12-03

