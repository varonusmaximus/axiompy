"""
Database abstraction layer with support for multiple database backends.

Provides a consistent CRUD interface for interacting with different database systems through
an abstract base class and concrete implementations. Supports MySQL, PostgreSQL, DynamoDB,
and SQLite with automatic connection management and unified error handling.

Key Benefits:
    - Zero external dependencies for core functionality (SQLite uses stdlib)
    - Consistent CRUD API across all database types
    - Easy mocking for unit testing without real database connections
    - Dependency injection-friendly design
    - Automatic resource cleanup via destructors
    - Flexible execute() method for custom SQL

Quick Example:
    >>> from axiompy.io.database import DatabaseFactory, DatabaseType, DatabaseSettings
    >>>
    >>> settings = DatabaseSettings(host="localhost", port=5432, database="mydb",
    ...                             username="user", password="pass")
    >>> db = DatabaseFactory.create(DatabaseType.POSTGRES, settings)
    >>> user = db.get("users", 123)
    >>> all_users = db.get_all("users")
    >>> user_id = db.set("users", {"name": "Alice", "email": "alice@example.com"})
    >>> db.update("users", 123, {"name": "Alice Smith"})
    >>> db.delete("users", 123)

For comprehensive examples including testing patterns, see:
    - examples/database_usage.py - Production usage examples
    - examples/database_mocking.py - Unit testing with mocks
    - axiompy/io/README.md - Complete documentation
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from axiompy.decorators import Retry
from axiompy.loggers import LoggerFactory
from axiompy.validators import ensure_in_range, ensure_not_empty, ensure_not_none, ensure_positive

logger = LoggerFactory.create_logger(__name__)


class DatabaseType(Enum):
    """Supported database types."""

    MYSQL = "mysql"
    POSTGRES = "postgres"
    DYNAMODB = "dynamodb"
    SQLITE = "sqlite"


@dataclass
class DatabaseSettings:
    """
    Database connection configuration.

    Attributes:
        host: Database host address
        port: Database port number
        database: Database name (or file path for SQLite)
        username: Database username
        password: Database password
        region: AWS region (DynamoDB only)
        access_key_id: AWS access key ID (DynamoDB only)
        secret_access_key: AWS secret access key (DynamoDB only)
        connection_timeout: Connection timeout in seconds
        pool_size: Connection pool size (not used currently)
        extra_params: Additional database-specific parameters
    """

    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    region: Optional[str] = None
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    connection_timeout: int = 30
    pool_size: int = 5
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate settings after initialization."""
        if self.port is not None:
            ensure_in_range(self.port, 1, 65535, f"port {self.port} must be between 1 and 65535")

        ensure_positive(
            self.connection_timeout,
            f"connection_timeout {self.connection_timeout} must be positive",
        )
        ensure_positive(self.pool_size, f"pool_size {self.pool_size} must be positive")
        logger.debug("DatabaseSettings validated successfully")


class DatabaseError(Exception):
    """Base exception for database errors."""

    pass


class DatabaseConnectionError(DatabaseError):
    """Database connection failure."""

    pass


class DatabaseQueryError(DatabaseError):
    """Query or command execution failure."""

    pass


class Database(ABC):
    """
    Abstract base class for database connections.

    All database implementations provide a consistent CRUD interface with convenience
    methods for common operations and an execute() method for custom SQL.

    Connections are established automatically on instantiation and cleaned up via __del__.

    Design Advantages:
        - Dependency Injection: Services depend on interface, not implementations
        - Easy Testing: Create simple mocks without real database connections
        - Swappable: Switch databases without changing business logic
        - Consistent: Same error types across all implementations

    Example Usage:
        >>> class UserRepository:
        ...     def __init__(self, database: Database):
        ...         self.db = database
        ...
        ...     def find_user(self, user_id: int):
        ...         return self.db.get("users", user_id)
        ...
        ...     def create_user(self, name: str, email: str):
        ...         return self.db.set("users", {"name": name, "email": email})

        # Works with any Database implementation (MySQL, PostgreSQL, SQLite, mock, etc.)
    """

    def __init__(self, settings: DatabaseSettings):
        """
        Initialize database instance.

        Subclasses should establish connection in __init__ and raise
        DatabaseConnectionError if connection fails.

        Args:
            settings: Database configuration

        Raises:
            DatabaseConnectionError: If connection fails
        """
        self.settings = settings
        self._connection = None

    def __del__(self):
        """Ensure resources are cleaned up when instance is destroyed."""
        self._cleanup()

    @abstractmethod
    def _cleanup(self) -> None:  # pragma: no cover
        """
        Clean up database resources.

        Subclasses should override to close connections and cursors.
        Should not raise exceptions.
        """
        pass

    @abstractmethod
    def get(
        self, table: str, key_value: Any, key_column: str = "id"
    ) -> Optional[Dict[str, Any]]:  # pragma: no cover
        """
        Get a single record by key.

        Args:
            table: Table name
            key_value: Value of the key to search for
            key_column: Column name to search by (default: "id")

        Returns:
            Dictionary representing the row, or None if not found

        Raises:
            DatabaseQueryError: If query execution fails
        """
        pass

    @abstractmethod
    def get_all(self, table: str) -> List[Dict[str, Any]]:  # pragma: no cover
        """
        Get all records from a table.

        Args:
            table: Table name

        Returns:
            List of dictionaries representing rows

        Raises:
            DatabaseQueryError: If query execution fails
        """
        pass

    @abstractmethod
    def set(self, table: str, data: Dict[str, Any]) -> Any:  # pragma: no cover
        """
        Insert a new record.

        Args:
            table: Table name
            data: Dictionary of column-value pairs

        Returns:
            The ID/key of the inserted record (database-specific type)

        Raises:
            DatabaseQueryError: If insert fails
        """
        pass

    @abstractmethod
    def update(
        self, table: str, key_value: Any, data: Dict[str, Any], key_column: str = "id"
    ) -> int:  # pragma: no cover
        """
        Update an existing record.

        Args:
            table: Table name
            key_value: Value of the key to update
            data: Dictionary of column-value pairs to update
            key_column: Column name to match by (default: "id")

        Returns:
            Number of affected rows

        Raises:
            DatabaseQueryError: If update fails
        """
        pass

    @abstractmethod
    def delete(self, table: str, key_value: Any, key_column: str = "id") -> int:  # pragma: no cover
        """
        Delete a record by key.

        Args:
            table: Table name
            key_value: Value of the key to delete
            key_column: Column name to match by (default: "id")

        Returns:
            Number of affected rows

        Raises:
            DatabaseQueryError: If delete fails
        """
        pass

    @abstractmethod
    def execute(
        self, sql_string: str, params: Optional[Union[Tuple, Dict]] = None
    ) -> Union[int, List[Dict[str, Any]]]:  # pragma: no cover
        """
        Execute arbitrary SQL command or query.

        This is the escape hatch for custom SQL that doesn't fit the CRUD methods.
        The implementation varies by database type.

        Args:
            sql_string: SQL command or query string
            params: Query parameters (tuple for positional, dict for named)

        Returns:
            For SELECT queries: List of dictionaries representing rows
            For INSERT/UPDATE/DELETE: Number of affected rows
            For other commands: 0

        Raises:
            DatabaseQueryError: If execution fails
        """
        pass


class MySQLDatabase(Database):
    """MySQL database implementation using mysql-connector-python."""

    def __init__(self, settings: DatabaseSettings):
        super().__init__(settings)
        self._cursor = None

        try:
            import mysql.connector

            self._mysql = mysql.connector
        except ImportError:
            raise DatabaseError(
                "MySQL connector not installed. Install with: pip install mysql-connector-python"
            )

        try:
            config = {
                "host": self.settings.host,
                "port": self.settings.port or 3306,
                "database": self.settings.database,
                "user": self.settings.username,
                "password": self.settings.password,
                "connection_timeout": self.settings.connection_timeout,
                "autocommit": True,
                **self.settings.extra_params,
            }

            self._connection = self._mysql.connect(**config)
            self._cursor = self._connection.cursor(dictionary=True)
            logger.info(f"Connected to MySQL database: {self.settings.database}")

        except Exception as e:
            raise DatabaseConnectionError(f"Failed to connect to MySQL: {str(e)}")

    def _cleanup(self) -> None:  # pragma: no cover
        try:
            if self._cursor:
                self._cursor.close()
            if self._connection:
                self._connection.close()
            logger.debug("MySQL connection closed")
        except Exception:
            pass

    def get(self, table: str, key_value: Any, key_column: str = "id") -> Optional[Dict[str, Any]]:
        ensure_not_empty(table, "table name cannot be empty")
        ensure_not_empty(key_column, "key_column name cannot be empty")
        ensure_not_none(key_value, "key_value cannot be None")

        try:
            query = f"SELECT * FROM {table} WHERE {key_column} = %s"
            self._cursor.execute(query, (key_value,))
            result = self._cursor.fetchone()
            logger.debug(f"Get from {table} where {key_column}={key_value}: {result is not None}")
            return result
        except Exception as e:
            raise DatabaseQueryError(f"Get failed: {str(e)}")

    def get_all(self, table: str) -> List[Dict[str, Any]]:
        ensure_not_empty(table, "table name cannot be empty")

        try:
            query = f"SELECT * FROM {table}"
            self._cursor.execute(query)
            results = self._cursor.fetchall()
            logger.debug(f"Get all from {table}: {len(results)} rows")
            return results
        except Exception as e:
            raise DatabaseQueryError(f"Get all failed: {str(e)}")

    def set(self, table: str, data: Dict[str, Any]) -> Any:
        ensure_not_empty(table, "table name cannot be empty")
        ensure_not_none(data, "data cannot be None")

        try:
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            self._cursor.execute(query, tuple(data.values()))
            inserted_id = self._cursor.lastrowid
            logger.debug(f"Inserted into {table}: id={inserted_id}")
            return inserted_id
        except Exception as e:
            raise DatabaseQueryError(f"Insert failed: {str(e)}")

    def update(
        self, table: str, key_value: Any, data: Dict[str, Any], key_column: str = "id"
    ) -> int:
        ensure_not_empty(table, "table name cannot be empty")
        ensure_not_empty(key_column, "key_column name cannot be empty")
        ensure_not_none(key_value, "key_value cannot be None")
        ensure_not_none(data, "data cannot be None")

        try:
            set_clause = ", ".join([f"{col} = %s" for col in data])
            query = f"UPDATE {table} SET {set_clause} WHERE {key_column} = %s"
            params = tuple(data.values()) + (key_value,)
            self._cursor.execute(query, params)
            affected = self._cursor.rowcount
            logger.debug(f"Updated {table} where {key_column}={key_value}: {affected} rows")
            return affected
        except Exception as e:
            raise DatabaseQueryError(f"Update failed: {str(e)}")

    def delete(self, table: str, key_value: Any, key_column: str = "id") -> int:
        ensure_not_empty(table, "table name cannot be empty")
        ensure_not_empty(key_column, "key_column name cannot be empty")
        ensure_not_none(key_value, "key_value cannot be None")

        try:
            query = f"DELETE FROM {table} WHERE {key_column} = %s"
            self._cursor.execute(query, (key_value,))
            affected = self._cursor.rowcount
            logger.debug(f"Deleted from {table} where {key_column}={key_value}: {affected} rows")
            return affected
        except Exception as e:
            raise DatabaseQueryError(f"Delete failed: {str(e)}")

    def execute(
        self, sql_string: str, params: Optional[Union[Tuple, Dict]] = None
    ) -> Union[int, List[Dict[str, Any]]]:
        ensure_not_empty(sql_string, "sql_string cannot be empty")

        try:
            self._cursor.execute(sql_string, params or ())

            # Check if this is a SELECT query
            if sql_string.strip().upper().startswith("SELECT"):
                results = self._cursor.fetchall()
                logger.debug(f"Execute query: {len(results)} rows")
                return results
            else:
                affected = self._cursor.rowcount
                logger.debug(f"Execute command: {affected} rows affected")
                return affected if affected >= 0 else 0
        except Exception as e:
            raise DatabaseQueryError(f"Execute failed: {str(e)}")


class PostgreSQLDatabase(Database):
    """PostgreSQL database implementation using psycopg2."""

    def __init__(self, settings: DatabaseSettings):
        super().__init__(settings)
        self._cursor = None

        try:
            import psycopg2
            import psycopg2.extras

            self._psycopg2 = psycopg2
            self._extras = psycopg2.extras
        except ImportError:
            raise DatabaseError(
                "PostgreSQL connector not installed. Install with: pip install psycopg2-binary"
            )

        try:
            connection_params = {
                "host": self.settings.host,
                "port": self.settings.port or 5432,
                "database": self.settings.database,
                "user": self.settings.username,
                "password": self.settings.password,
                "connect_timeout": self.settings.connection_timeout,
                **self.settings.extra_params,
            }

            self._connection = self._psycopg2.connect(**connection_params)
            self._connection.autocommit = True
            self._cursor = self._connection.cursor(cursor_factory=self._extras.RealDictCursor)
            logger.info(f"Connected to PostgreSQL database: {self.settings.database}")

        except Exception as e:
            raise DatabaseConnectionError(f"Failed to connect to PostgreSQL: {str(e)}")

    def _cleanup(self) -> None:
        try:
            if self._cursor:
                self._cursor.close()
            if self._connection:
                self._connection.close()
            logger.debug("PostgreSQL connection closed")
        except Exception:
            pass

    def get(self, table: str, key_value: Any, key_column: str = "id") -> Optional[Dict[str, Any]]:
        try:
            query = f"SELECT * FROM {table} WHERE {key_column} = %s"
            self._cursor.execute(query, (key_value,))
            result = self._cursor.fetchone()
            logger.debug(f"Get from {table} where {key_column}={key_value}: {result is not None}")
            return dict(result) if result else None
        except Exception as e:
            raise DatabaseQueryError(f"Get failed: {str(e)}")

    def get_all(self, table: str) -> List[Dict[str, Any]]:
        try:
            query = f"SELECT * FROM {table}"
            self._cursor.execute(query)
            results = [dict(row) for row in self._cursor.fetchall()]
            logger.debug(f"Get all from {table}: {len(results)} rows")
            return results
        except Exception as e:
            raise DatabaseQueryError(f"Get all failed: {str(e)}")

    def set(self, table: str, data: Dict[str, Any]) -> Any:
        try:
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING id"
            self._cursor.execute(query, tuple(data.values()))
            result = self._cursor.fetchone()
            inserted_id = result["id"] if result else None
            logger.debug(f"Inserted into {table}: id={inserted_id}")
            return inserted_id
        except Exception as e:
            raise DatabaseQueryError(f"Insert failed: {str(e)}")

    def update(
        self, table: str, key_value: Any, data: Dict[str, Any], key_column: str = "id"
    ) -> int:
        try:
            set_clause = ", ".join([f"{col} = %s" for col in data])
            query = f"UPDATE {table} SET {set_clause} WHERE {key_column} = %s"
            params = tuple(data.values()) + (key_value,)
            self._cursor.execute(query, params)
            affected = self._cursor.rowcount
            logger.debug(f"Updated {table} where {key_column}={key_value}: {affected} rows")
            return affected
        except Exception as e:
            raise DatabaseQueryError(f"Update failed: {str(e)}")

    def delete(self, table: str, key_value: Any, key_column: str = "id") -> int:
        try:
            query = f"DELETE FROM {table} WHERE {key_column} = %s"
            self._cursor.execute(query, (key_value,))
            affected = self._cursor.rowcount
            logger.debug(f"Deleted from {table} where {key_column}={key_value}: {affected} rows")
            return affected
        except Exception as e:
            raise DatabaseQueryError(f"Delete failed: {str(e)}")

    @Retry(logger, max_attempts=3, delay=0.5, backoff=2.0, exceptions=(DatabaseQueryError,))
    def execute(
        self, sql_string: str, params: Optional[Union[Tuple, Dict]] = None
    ) -> Union[int, List[Dict[str, Any]]]:
        ensure_not_empty(sql_string, "sql_string cannot be empty")

        try:
            # Normalize whitespace: replace newlines and multiple spaces with single space
            # This fixes issues with LLM-generated SQL that includes newlines
            normalized_sql = " ".join(sql_string.split())
            self._cursor.execute(normalized_sql, params or ())

            # Check if this is a SELECT query
            if sql_string.strip().upper().startswith("SELECT"):
                results = [dict(row) for row in self._cursor.fetchall()]
                logger.debug(f"Execute query: {len(results)} rows")
                return results
            else:
                affected = self._cursor.rowcount
                logger.debug(f"Execute command: {affected} rows affected")
                return affected if affected >= 0 else 0
        except Exception as e:
            raise DatabaseQueryError(f"Execute failed: {str(e)}")


class DynamoDBDatabase(Database):
    """
    DynamoDB database implementation using boto3.

    Note: DynamoDB is NoSQL with different semantics than SQL databases.
    The interface is adapted to fit the abstract Database contract.
    The 'table' parameter maps to DynamoDB table names.
    """

    def __init__(self, settings: DatabaseSettings):
        super().__init__(settings)
        self._dynamodb = None
        self._resource = None

        try:
            import boto3

            self._boto3 = boto3
        except ImportError:
            raise DatabaseError("AWS SDK not installed. Install with: pip install boto3")

        try:
            session_params = {
                "region_name": self.settings.region or "us-east-1",
            }

            if self.settings.access_key_id and self.settings.secret_access_key:
                session_params["aws_access_key_id"] = self.settings.access_key_id
                session_params["aws_secret_access_key"] = self.settings.secret_access_key

            self._resource = self._boto3.resource("dynamodb", **session_params)
            self._dynamodb = self._boto3.client("dynamodb", **session_params)
            logger.info(f"Connected to DynamoDB in region: {session_params['region_name']}")

        except Exception as e:
            raise DatabaseConnectionError(f"Failed to connect to DynamoDB: {str(e)}")

    def _cleanup(self) -> None:
        self._resource = None
        self._dynamodb = None
        logger.debug("DynamoDB session closed")

    def get(self, table: str, key_value: Any, key_column: str = "id") -> Optional[Dict[str, Any]]:
        """
        Get item from DynamoDB by key.

        Args:
            table: DynamoDB table name
            key_value: Value of the primary key
            key_column: Name of the primary key attribute
        """
        try:
            table_resource = self._resource.Table(table)
            response = table_resource.get_item(Key={key_column: key_value})
            item = response.get("Item")
            logger.debug(f"Get from {table} where {key_column}={key_value}: {item is not None}")
            return item
        except Exception as e:
            raise DatabaseQueryError(f"DynamoDB get failed: {str(e)}")

    def get_all(self, table: str) -> List[Dict[str, Any]]:
        """
        Scan all items from DynamoDB table.

        Warning: Scans can be expensive for large tables.
        """
        try:
            table_resource = self._resource.Table(table)
            response = table_resource.scan()
            items = response.get("Items", [])

            # Handle pagination if needed
            while "LastEvaluatedKey" in response:
                response = table_resource.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                items.extend(response.get("Items", []))

            logger.debug(f"Get all from {table}: {len(items)} items")
            return items
        except Exception as e:
            raise DatabaseQueryError(f"DynamoDB scan failed: {str(e)}")

    def set(self, table: str, data: Dict[str, Any]) -> Any:
        """
        Put item into DynamoDB.

        Returns the primary key value if 'id' is in data, otherwise returns None.
        """
        try:
            table_resource = self._resource.Table(table)
            table_resource.put_item(Item=data)
            # DynamoDB doesn't auto-generate IDs, return the provided key if present
            inserted_key = data.get("id")
            logger.debug(f"Put item into {table}: key={inserted_key}")
            return inserted_key
        except Exception as e:
            raise DatabaseQueryError(f"DynamoDB put failed: {str(e)}")

    def update(
        self, table: str, key_value: Any, data: Dict[str, Any], key_column: str = "id"
    ) -> int:
        """
        Update item in DynamoDB.

        Builds an UpdateExpression from the data dictionary.
        """
        try:
            table_resource = self._resource.Table(table)

            # Build update expression
            update_expr = "SET " + ", ".join([f"#{k} = :{k}" for k in data])
            expr_attr_names = {f"#{k}": k for k in data}
            expr_attr_values = {f":{k}": v for k, v in data.items()}

            table_resource.update_item(
                Key={key_column: key_value},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_values,
            )
            logger.debug(f"Updated {table} where {key_column}={key_value}")
            return 1  # DynamoDB doesn't return affected count
        except Exception as e:
            raise DatabaseQueryError(f"DynamoDB update failed: {str(e)}")

    def delete(self, table: str, key_value: Any, key_column: str = "id") -> int:
        """Delete item from DynamoDB by key."""
        try:
            table_resource = self._resource.Table(table)
            table_resource.delete_item(Key={key_column: key_value})
            logger.debug(f"Deleted from {table} where {key_column}={key_value}")
            return 1  # DynamoDB doesn't return affected count
        except Exception as e:
            raise DatabaseQueryError(f"DynamoDB delete failed: {str(e)}")

    def execute(
        self, sql_string: str, params: Optional[Union[Tuple, Dict]] = None
    ) -> Union[int, List[Dict[str, Any]]]:
        """
        Execute custom DynamoDB operation.

        For DynamoDB, sql_string should be the table name, and params should be
        a dict with the operation parameters (KeyConditionExpression for queries, etc.).

        This is a flexible method that allows for custom queries and operations.
        """
        try:
            if not params or not isinstance(params, dict):
                raise DatabaseQueryError("DynamoDB execute requires params dict")

            table_name = sql_string
            table = self._resource.Table(table_name)

            # Determine operation type based on params
            if "KeyConditionExpression" in params:
                response = table.query(**params)
                items = response.get("Items", [])
                logger.debug(f"DynamoDB query on {table_name}: {len(items)} items")
                return items
            elif "FilterExpression" in params or params.get("_operation") == "scan":
                # Remove our internal marker if present
                params_copy = {k: v for k, v in params.items() if k != "_operation"}
                response = table.scan(**params_copy)
                items = response.get("Items", [])
                logger.debug(f"DynamoDB scan on {table_name}: {len(items)} items")
                return items
            else:
                # Assume it's a scan if nothing else is specified
                response = table.scan(**params)
                items = response.get("Items", [])
                logger.debug(f"DynamoDB scan on {table_name}: {len(items)} items")
                return items

        except Exception as e:
            raise DatabaseQueryError(f"DynamoDB execute failed: {str(e)}")


class SQLiteDatabase(Database):
    """SQLite database implementation using Python's built-in sqlite3."""

    def __init__(self, settings: DatabaseSettings):
        super().__init__(settings)
        self._cursor = None

        import sqlite3

        self._sqlite3 = sqlite3

        try:
            db_path = self.settings.database or ":memory:"
            self._connection = self._sqlite3.connect(
                db_path,
                timeout=self.settings.connection_timeout,
                isolation_level=None,  # Auto-commit mode
                **self.settings.extra_params,
            )
            self._connection.row_factory = self._sqlite3.Row
            self._cursor = self._connection.cursor()
            logger.info(f"Connected to SQLite database: {db_path}")

        except Exception as e:
            raise DatabaseConnectionError(f"Failed to connect to SQLite: {str(e)}")

    def _cleanup(self) -> None:
        try:
            if self._cursor:
                self._cursor.close()
            if self._connection:
                self._connection.close()
            logger.debug("SQLite connection closed")
        except Exception:
            pass

    def get(self, table: str, key_value: Any, key_column: str = "id") -> Optional[Dict[str, Any]]:
        try:
            query = f"SELECT * FROM {table} WHERE {key_column} = ?"
            self._cursor.execute(query, (key_value,))
            result = self._cursor.fetchone()
            logger.debug(f"Get from {table} where {key_column}={key_value}: {result is not None}")
            return dict(result) if result else None
        except Exception as e:
            raise DatabaseQueryError(f"Get failed: {str(e)}")

    def get_all(self, table: str) -> List[Dict[str, Any]]:
        try:
            query = f"SELECT * FROM {table}"
            self._cursor.execute(query)
            results = [dict(row) for row in self._cursor.fetchall()]
            logger.debug(f"Get all from {table}: {len(results)} rows")
            return results
        except Exception as e:
            raise DatabaseQueryError(f"Get all failed: {str(e)}")

    def set(self, table: str, data: Dict[str, Any]) -> Any:
        try:
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            self._cursor.execute(query, tuple(data.values()))
            inserted_id = self._cursor.lastrowid
            logger.debug(f"Inserted into {table}: id={inserted_id}")
            return inserted_id
        except Exception as e:
            raise DatabaseQueryError(f"Insert failed: {str(e)}")

    def update(
        self, table: str, key_value: Any, data: Dict[str, Any], key_column: str = "id"
    ) -> int:
        try:
            set_clause = ", ".join([f"{col} = ?" for col in data])
            query = f"UPDATE {table} SET {set_clause} WHERE {key_column} = ?"
            params = tuple(data.values()) + (key_value,)
            self._cursor.execute(query, params)
            affected = self._cursor.rowcount
            logger.debug(f"Updated {table} where {key_column}={key_value}: {affected} rows")
            return affected
        except Exception as e:
            raise DatabaseQueryError(f"Update failed: {str(e)}")

    def delete(self, table: str, key_value: Any, key_column: str = "id") -> int:
        try:
            query = f"DELETE FROM {table} WHERE {key_column} = ?"
            self._cursor.execute(query, (key_value,))
            affected = self._cursor.rowcount
            logger.debug(f"Deleted from {table} where {key_column}={key_value}: {affected} rows")
            return affected
        except Exception as e:
            raise DatabaseQueryError(f"Delete failed: {str(e)}")

    @Retry(logger, max_attempts=3, delay=0.5, backoff=2.0, exceptions=(DatabaseQueryError,))
    def execute(
        self, sql_string: str, params: Optional[Union[Tuple, Dict]] = None
    ) -> Union[int, List[Dict[str, Any]]]:
        ensure_not_empty(sql_string, "sql_string cannot be empty")

        try:
            # Normalize whitespace: replace newlines and multiple spaces with single space
            # This fixes issues with LLM-generated SQL that includes newlines
            normalized_sql = " ".join(sql_string.split())
            self._cursor.execute(normalized_sql, params or ())

            # Check if this is a SELECT query
            if sql_string.strip().upper().startswith("SELECT"):
                results = [dict(row) for row in self._cursor.fetchall()]
                logger.debug(f"Execute query: {len(results)} rows")
                return results
            else:
                affected = self._cursor.rowcount
                # SQLite returns -1 for DDL statements (CREATE, DROP, ALTER)
                # Normalize to 0 for consistency
                if affected < 0:
                    affected = 0
                logger.debug(f"Execute command: {affected} rows affected")
                return affected
        except Exception as e:
            raise DatabaseQueryError(f"Execute failed: {str(e)}")


class DatabaseFactory:
    """
    Factory for creating database instances.

    Main entry point for database connections. The factory automatically creates
    the appropriate database implementation based on the specified type.

    Usage:
        >>> settings = DatabaseSettings(host="localhost", database="mydb",
        ...                             username="user", password="pass")
        >>> db = DatabaseFactory.create(DatabaseType.POSTGRES, settings)
        >>> user = db.get("users", 123)

    Testing:
        For unit tests, create mock implementations directly instead of using
        the factory:

        >>> class MockDB(Database):
        ...     def get(self, table, key_value, key_column="id"): return None
        ...     def get_all(self, table): return []
        ...     def set(self, table, data): return 1
        ...     def update(self, table, key_value, data, key_column="id"): return 1
        ...     def delete(self, table, key_value, key_column="id"): return 1
        ...     def execute(self, sql_string, params=None): return []
        ...     def _cleanup(self): pass
        >>>
        >>> mock = MockDB(DatabaseSettings())
        >>> service = UserService(mock)  # Inject mock directly
    """

    _database_map = {
        DatabaseType.MYSQL: MySQLDatabase,
        DatabaseType.POSTGRES: PostgreSQLDatabase,
        DatabaseType.DYNAMODB: DynamoDBDatabase,
        DatabaseType.SQLITE: SQLiteDatabase,
    }

    @classmethod
    def create(cls, db_type: DatabaseType, settings: DatabaseSettings) -> Database:
        """
        Create a database instance.

        Args:
            db_type: Type of database to create
            settings: Configuration for the database

        Returns:
            Database instance

        Raises:
            ValueError: If database type is not supported
            DatabaseError: If instance creation fails
        """
        if db_type not in cls._database_map:
            raise ValueError(
                f"Unsupported database type: {db_type}. Supported: {list(cls._database_map.keys())}"
            )

        database_class = cls._database_map[db_type]
        try:
            return database_class(settings)
        except (DatabaseConnectionError, DatabaseQueryError):
            # Let database-specific errors pass through unchanged
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise DatabaseError(f"Failed to create {db_type.value} database: {str(e)}")

    @classmethod
    def register_database(cls, db_type: DatabaseType, database_class: type) -> None:
        """
        Register a custom database implementation.

        Allows extending the factory with new database types.

        Args:
            db_type: Database type enum value
            database_class: Class implementing Database interface

        Raises:
            TypeError: If database_class doesn't inherit from Database
        """
        if not issubclass(database_class, Database):
            raise TypeError("database_class must inherit from Database")

        cls._database_map[db_type] = database_class
        logger.info(f"Registered custom database: {db_type.value}")
