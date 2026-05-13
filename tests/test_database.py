"""
Tests for the database abstraction layer.

These tests use SQLite as it's part of the Python standard library.
For MySQL, PostgreSQL, and DynamoDB tests, ensure the respective
drivers are installed and databases are available.
"""

import os
import tempfile

import pytest

from axiompy.io.database import (
    Database,
    DatabaseConnectionError,
    DatabaseError,
    DatabaseFactory,
    DatabaseQueryError,
    DatabaseSettings,
    DatabaseType,
)


class TestDatabaseSettings:
    """Test DatabaseSettings dataclass."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = DatabaseSettings()
        assert settings.connection_timeout == 30
        assert settings.pool_size == 5
        assert settings.extra_params == {}

    def test_custom_settings(self):
        """Test custom settings."""
        settings = DatabaseSettings(
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password="testpass",
            connection_timeout=60,
        )
        assert settings.host == "localhost"
        assert settings.port == 5432
        assert settings.database == "testdb"
        assert settings.username == "testuser"
        assert settings.password == "testpass"
        assert settings.connection_timeout == 60


class TestSQLiteDatabase:
    """Test SQLite database implementation."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary SQLite database."""
        # Create a temporary file
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)

    @pytest.fixture
    def db(self, temp_db):
        """Create a SQLite database instance with test table."""
        settings = DatabaseSettings(database=temp_db)
        database = DatabaseFactory.create(DatabaseType.SQLITE, settings)

        # Create a test table
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                age INTEGER
            )
        """
        )

        yield database

        # Explicitly clean up database resources before temp file deletion
        database._cleanup()

    def test_factory_create_sqlite(self):
        """Test creating SQLite database via factory."""
        settings = DatabaseSettings(database=":memory:")
        db = DatabaseFactory.create(DatabaseType.SQLITE, settings)
        assert isinstance(db, Database)

    def test_set_insert(self, db):
        """Test inserting data using set()."""
        user_id = db.set("users", {"name": "John Doe", "email": "john@example.com", "age": 30})
        assert user_id is not None
        assert user_id > 0

    def test_get_single(self, db):
        """Test getting a single record using get()."""
        # Insert test data
        user_id = db.set("users", {"name": "Jane Doe", "email": "jane@example.com", "age": 25})

        # Get the data
        result = db.get("users", user_id)

        assert result is not None
        assert result["name"] == "Jane Doe"
        assert result["email"] == "jane@example.com"
        assert result["age"] == 25

    def test_get_nonexistent(self, db):
        """Test getting a non-existent record returns None."""
        result = db.get("users", 999999)
        assert result is None

    def test_get_by_custom_column(self, db):
        """Test getting by a custom column."""
        db.set("users", {"name": "Bob", "email": "bob@example.com", "age": 35})

        # Get by email instead of id
        result = db.get("users", "bob@example.com", key_column="email")

        assert result is not None
        assert result["name"] == "Bob"
        assert result["age"] == 35

    def test_get_all(self, db):
        """Test getting all records."""
        # Insert multiple users
        db.set("users", {"name": "Alice", "email": "alice@example.com", "age": 28})
        db.set("users", {"name": "Bob", "email": "bob@example.com", "age": 32})
        db.set("users", {"name": "Charlie", "email": "charlie@example.com", "age": 35})

        # Get all
        all_users = db.get_all("users")
        assert len(all_users) == 3

        # Verify all names are present
        names = {user["name"] for user in all_users}
        assert names == {"Alice", "Bob", "Charlie"}

    def test_update(self, db):
        """Test updating data."""
        # Insert initial data
        user_id = db.set("users", {"name": "Update User", "email": "update@example.com", "age": 30})

        # Update the data
        affected = db.update("users", user_id, {"age": 31})
        assert affected == 1

        # Verify the update
        result = db.get("users", user_id)
        assert result["age"] == 31
        assert result["name"] == "Update User"  # Unchanged

    def test_update_multiple_fields(self, db):
        """Test updating multiple fields at once."""
        user_id = db.set("users", {"name": "Old Name", "email": "old@example.com", "age": 25})

        affected = db.update("users", user_id, {"name": "New Name", "age": 26})
        assert affected == 1

        result = db.get("users", user_id)
        assert result["name"] == "New Name"
        assert result["age"] == 26
        assert result["email"] == "old@example.com"  # Unchanged

    def test_update_by_custom_column(self, db):
        """Test updating by custom column."""
        db.set("users", {"name": "Test", "email": "test@example.com", "age": 20})

        affected = db.update("users", "test@example.com", {"age": 21}, key_column="email")
        assert affected == 1

        result = db.get("users", "test@example.com", key_column="email")
        assert result["age"] == 21

    def test_delete(self, db):
        """Test deleting data."""
        # Insert initial data
        user_id = db.set("users", {"name": "Delete User", "email": "delete@example.com", "age": 40})

        # Delete the data
        affected = db.delete("users", user_id)
        assert affected == 1

        # Verify the deletion
        result = db.get("users", user_id)
        assert result is None

    def test_delete_by_custom_column(self, db):
        """Test deleting by custom column."""
        db.set("users", {"name": "Delete Me", "email": "deleteme@example.com", "age": 30})

        affected = db.delete("users", "deleteme@example.com", key_column="email")
        assert affected == 1

        result = db.get("users", "deleteme@example.com", key_column="email")
        assert result is None

    def test_execute_select(self, db):
        """Test execute() with SELECT query."""
        # Insert test data
        for i in range(5):
            db.set("users", {"name": f"User {i}", "email": f"user{i}@example.com", "age": 20 + i})

        # Execute custom query (ages: 20, 21, 22, 23, 24 -> only 23, 24 are > 22)
        results = db.execute("SELECT * FROM users WHERE age > ?", (22,))

        assert isinstance(results, list)
        assert len(results) == 2
        assert all(user["age"] > 22 for user in results)

    def test_execute_create_table(self, db):
        """Test execute() with CREATE TABLE."""
        result = db.execute(
            """
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL
            )
        """
        )
        # Should return 0 for DDL
        assert result == 0

        # Verify table was created
        db.set("products", {"name": "Widget", "price": 19.99})
        products = db.get_all("products")
        assert len(products) == 1

    def test_execute_insert(self, db):
        """Test execute() with INSERT."""
        result = db.execute(
            "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
            ("Direct Insert", "direct@example.com", 45),
        )
        # Should return 1 (rows affected)
        assert result == 1

        # Verify insert
        all_users = db.get_all("users")
        assert len(all_users) == 1

    def test_execute_update(self, db):
        """Test execute() with UPDATE."""
        user_id = db.set("users", {"name": "Test", "email": "test@example.com", "age": 20})

        result = db.execute("UPDATE users SET age = ? WHERE id = ?", (25, user_id))
        assert result == 1

    def test_execute_delete(self, db):
        """Test execute() with DELETE."""
        db.set("users", {"name": "Test", "email": "test@example.com", "age": 20})

        result = db.execute("DELETE FROM users WHERE email = ?", ("test@example.com",))
        assert result == 1

    def test_empty_table(self, db):
        """Test get_all() on empty table."""
        results = db.get_all("users")
        assert results == []

    def test_aggregation_with_execute(self, db):
        """Test aggregation queries using execute()."""
        # Insert test data
        for i in range(3):
            db.set(
                "users", {"name": f"User {i}", "email": f"user{i}@example.com", "age": 30 + i * 5}
            )

        # Test COUNT
        count_result = db.execute("SELECT COUNT(*) as count FROM users")
        assert count_result[0]["count"] == 3

        # Test AVG
        avg_result = db.execute("SELECT AVG(age) as avg_age FROM users")
        assert avg_result[0]["avg_age"] == 35.0


class TestDatabaseFactory:
    """Test DatabaseFactory."""

    def test_create_sqlite(self):
        """Test creating SQLite database."""
        settings = DatabaseSettings(database=":memory:")
        db = DatabaseFactory.create(DatabaseType.SQLITE, settings)
        assert db is not None
        assert isinstance(db, Database)

    def test_unsupported_database_type(self):
        """Test creating unsupported database type."""
        settings = DatabaseSettings()
        # Create a fake enum value
        from enum import Enum

        class FakeType(Enum):
            FAKE = "fake"

        with pytest.raises(ValueError, match="Unsupported database type"):
            DatabaseFactory.create(FakeType.FAKE, settings)

    def test_register_custom_database(self):
        """Test registering a custom database implementation."""

        class CustomDatabase(Database):
            def __init__(self, settings):
                super().__init__(settings)
                self._connection = "mock_connection"

            def _cleanup(self):
                pass

            def get(self, table, key_value, key_column="id"):
                return None

            def get_all(self, table):
                return []

            def set(self, table, data):
                return 1

            def update(self, table, key_value, data, key_column="id"):
                return 0

            def delete(self, table, key_value, key_column="id"):
                return 0

            def execute(self, sql_string, params=None):
                return []

        # Save the original implementation

        original_impl = DatabaseFactory._database_map[DatabaseType.SQLITE]

        try:
            # Use existing enum for test
            custom_type = DatabaseType.SQLITE
            DatabaseFactory.register_database(custom_type, CustomDatabase)

            settings = DatabaseSettings()
            db = DatabaseFactory.create(custom_type, settings)
            assert isinstance(db, CustomDatabase)
        finally:
            # Restore the original implementation
            DatabaseFactory._database_map[DatabaseType.SQLITE] = original_impl


class TestDatabaseErrors:
    """Test database error handling."""

    def test_database_error_hierarchy(self):
        """Test error class hierarchy."""
        assert issubclass(DatabaseConnectionError, DatabaseError)
        assert issubclass(DatabaseQueryError, DatabaseError)

    def test_invalid_query(self):
        """Test error handling for invalid query."""
        settings = DatabaseSettings(database=":memory:")
        db = DatabaseFactory.create(DatabaseType.SQLITE, settings)

        with pytest.raises(DatabaseQueryError):
            db.execute("INVALID SQL QUERY")

        db._cleanup()

    def test_invalid_command(self):
        """Test error handling for invalid command."""
        settings = DatabaseSettings(database=":memory:")
        db = DatabaseFactory.create(DatabaseType.SQLITE, settings)

        with pytest.raises(DatabaseQueryError):
            db.set("nonexistent_table", {"col": "value"})

        db._cleanup()

    def test_connection_error(self):
        """Test connection error handling."""
        # Try to connect to a directory instead of a file (should fail)
        settings = DatabaseSettings(database="/nonexistent/path/to/database.db")

        with pytest.raises(DatabaseConnectionError):
            DatabaseFactory.create(DatabaseType.SQLITE, settings)

    def test_get_from_nonexistent_table(self):
        """Test error when getting from non-existent table."""
        settings = DatabaseSettings(database=":memory:")
        db = DatabaseFactory.create(DatabaseType.SQLITE, settings)

        with pytest.raises(DatabaseQueryError):
            db.get("nonexistent_table", 1)

        db._cleanup()


class TestDatabaseCleanup:
    """Test database resource cleanup."""

    def test_automatic_cleanup(self):
        """Test that _cleanup() properly closes connections and allows reconnection."""
        import tempfile

        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            settings = DatabaseSettings(database=db_path)

            # Create and use database
            db = DatabaseFactory.create(DatabaseType.SQLITE, settings)
            db.execute("CREATE TABLE test (id INTEGER, name TEXT)")
            db.set("test", {"id": 1, "name": "Test"})
            db._cleanup()

            # Verify file persists after cleanup
            assert os.path.exists(db_path), f"Database file should exist at {db_path}"

            # Verify we can reconnect and see the table
            db2 = DatabaseFactory.create(DatabaseType.SQLITE, settings)
            try:
                results = db2.execute("SELECT name FROM sqlite_master WHERE type='table'")
                assert len(results) == 1
                assert results[0]["name"] == "test"

                # Verify data persisted
                test_data = db2.get_all("test")
                assert len(test_data) == 1
                assert test_data[0]["name"] == "Test"
            finally:
                db2._cleanup()
        finally:
            # Clean up temp file
            if os.path.exists(db_path):
                os.remove(db_path)


class TestCRUDWorkflow:
    """Test complete CRUD workflow."""

    def test_full_crud_workflow(self):
        """Test a complete create-read-update-delete workflow."""
        settings = DatabaseSettings(database=":memory:")
        db = DatabaseFactory.create(DatabaseType.SQLITE, settings)

        # Setup table
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

        # CREATE - Insert multiple products
        widget_id = db.set("products", {"name": "Widget", "price": 19.99, "quantity": 100})
        gadget_id = db.set("products", {"name": "Gadget", "price": 29.99, "quantity": 50})
        db.set("products", {"name": "Doohickey", "price": 9.99, "quantity": 200})

        assert widget_id is not None
        assert gadget_id is not None

        # READ - Get single product
        widget = db.get("products", widget_id)
        assert widget["name"] == "Widget"
        assert widget["price"] == 19.99

        # READ - Get all products
        all_products = db.get_all("products")
        assert len(all_products) == 3

        # READ - Custom query with execute
        expensive = db.execute("SELECT * FROM products WHERE price > ?", (15.0,))
        assert len(expensive) == 2

        # UPDATE - Update widget quantity
        affected = db.update("products", widget_id, {"quantity": 150})
        assert affected == 1

        updated_widget = db.get("products", widget_id)
        assert updated_widget["quantity"] == 150

        # UPDATE - Bulk update with execute
        db.execute("UPDATE products SET price = price * 1.1 WHERE price < ?", (20.0,))

        # DELETE - Delete one product
        affected = db.delete("products", gadget_id)
        assert affected == 1

        # Verify deletion
        deleted_product = db.get("products", gadget_id)
        assert deleted_product is None

        # Verify remaining count
        remaining = db.get_all("products")
        assert len(remaining) == 2

        db._cleanup()


class TestMySQLDatabase:
    """Test MySQL database with mocked connector."""

    @pytest.fixture(autouse=True)
    def mock_mysql_module(self, mocker):
        """Mock MySQL connector module before any imports."""
        # Mock the mysql.connector module globally
        mock_mysql = mocker.MagicMock()
        mock_connector = mocker.MagicMock()
        mock_mysql.connector = mock_connector
        mocker.patch.dict("sys.modules", {"mysql": mock_mysql, "mysql.connector": mock_connector})
        return mock_connector

    @pytest.fixture
    def mock_mysql_connection(self, mock_mysql_module, mocker):
        """Mock MySQL connection and return mocked connection and cursor."""
        # Create mock connection and cursor
        mock_cursor = mocker.MagicMock()
        mock_connection = mocker.MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_mysql_module.connect.return_value = mock_connection

        return mock_connection, mock_cursor, mock_mysql_module

    def test_mysql_get(self, mock_mysql_connection):
        """Test MySQL get() method."""
        mock_connection, mock_cursor, mock_mysql = mock_mysql_connection
        mock_cursor.fetchone.return_value = {"id": 1, "name": "Alice", "email": "alice@example.com"}

        # Import after mocking
        from axiompy.io.database import MySQLDatabase

        settings = DatabaseSettings(
            host="localhost", database="test", username="user", password="pass"
        )
        db = MySQLDatabase(settings)

        result = db.get("users", 1)

        assert result is not None
        assert result["name"] == "Alice"
        mock_cursor.execute.assert_called_once()
        db._cleanup()

    def test_mysql_get_all(self, mock_mysql_connection):
        """Test MySQL get_all() method."""
        mock_connection, mock_cursor, mock_mysql = mock_mysql_connection
        mock_cursor.fetchall.return_value = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

        from axiompy.io.database import MySQLDatabase

        settings = DatabaseSettings(
            host="localhost", database="test", username="user", password="pass"
        )
        db = MySQLDatabase(settings)

        results = db.get_all("users")

        assert len(results) == 2
        assert results[0]["name"] == "Alice"
        db._cleanup()

    def test_mysql_set(self, mock_mysql_connection):
        """Test MySQL set() method."""
        mock_connection, mock_cursor, mock_mysql = mock_mysql_connection
        mock_cursor.lastrowid = 123

        from axiompy.io.database import MySQLDatabase

        settings = DatabaseSettings(
            host="localhost", database="test", username="user", password="pass"
        )
        db = MySQLDatabase(settings)

        user_id = db.set("users", {"name": "Charlie", "email": "charlie@example.com"})

        assert user_id == 123
        mock_cursor.execute.assert_called_once()
        db._cleanup()

    def test_mysql_update(self, mock_mysql_connection):
        """Test MySQL update() method."""
        mock_connection, mock_cursor, mock_mysql = mock_mysql_connection
        mock_cursor.rowcount = 1

        from axiompy.io.database import MySQLDatabase

        settings = DatabaseSettings(
            host="localhost", database="test", username="user", password="pass"
        )
        db = MySQLDatabase(settings)

        affected = db.update("users", 1, {"email": "newemail@example.com"})

        assert affected == 1
        mock_cursor.execute.assert_called_once()
        db._cleanup()

    def test_mysql_delete(self, mock_mysql_connection):
        """Test MySQL delete() method."""
        mock_connection, mock_cursor, mock_mysql = mock_mysql_connection
        mock_cursor.rowcount = 1

        from axiompy.io.database import MySQLDatabase

        settings = DatabaseSettings(
            host="localhost", database="test", username="user", password="pass"
        )
        db = MySQLDatabase(settings)

        affected = db.delete("users", 1)

        assert affected == 1
        mock_cursor.execute.assert_called_once()
        db._cleanup()

    def test_mysql_execute_select(self, mock_mysql_connection):
        """Test MySQL execute() with SELECT."""
        mock_connection, mock_cursor, mock_mysql = mock_mysql_connection
        mock_cursor.fetchall.return_value = [{"id": 1, "name": "Alice", "age": 30}]

        from axiompy.io.database import MySQLDatabase

        settings = DatabaseSettings(
            host="localhost", database="test", username="user", password="pass"
        )
        db = MySQLDatabase(settings)

        results = db.execute("SELECT * FROM users WHERE age > %s", (25,))

        assert isinstance(results, list)
        assert len(results) == 1
        db._cleanup()

    def test_mysql_execute_insert(self, mock_mysql_connection):
        """Test MySQL execute() with INSERT."""
        mock_connection, mock_cursor, mock_mysql = mock_mysql_connection
        mock_cursor.rowcount = 1

        from axiompy.io.database import MySQLDatabase

        settings = DatabaseSettings(
            host="localhost", database="test", username="user", password="pass"
        )
        db = MySQLDatabase(settings)

        result = db.execute("INSERT INTO users (name) VALUES (%s)", ("David",))

        assert result == 1
        db._cleanup()


class TestPostgreSQLDatabase:
    """Test PostgreSQL database with mocked psycopg2."""

    @pytest.fixture
    def mock_postgres_connection(self, mocker):
        """Mock psycopg2 and return mocked connection and cursor."""
        # Mock psycopg2 modules
        mock_psycopg2 = mocker.MagicMock()
        mock_extras = mocker.MagicMock()
        mock_psycopg2.extras = mock_extras

        mocker.patch.dict(
            "sys.modules", {"psycopg2": mock_psycopg2, "psycopg2.extras": mock_extras}
        )

        # Create mock connection and cursor
        mock_cursor = mocker.MagicMock()
        mock_connection = mocker.MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_psycopg2.connect.return_value = mock_connection

        return mock_connection, mock_cursor, mock_psycopg2

    def test_postgres_get(self, mock_postgres_connection):
        """Test PostgreSQL get() method."""
        mock_connection, mock_cursor, mock_psycopg2 = mock_postgres_connection

        # Mock RealDictRow
        mock_row = {"id": 1, "name": "Alice", "email": "alice@example.com"}
        mock_cursor.fetchone.return_value = mock_row

        from axiompy.io.database import PostgreSQLDatabase

        settings = DatabaseSettings(
            host="localhost", database="test", username="user", password="pass"
        )
        db = PostgreSQLDatabase(settings)

        result = db.get("users", 1)

        assert result is not None
        assert result["name"] == "Alice"
        db._cleanup()

    def test_postgres_get_all(self, mock_postgres_connection):
        """Test PostgreSQL get_all() method."""
        mock_connection, mock_cursor, mock_psycopg2 = mock_postgres_connection
        mock_cursor.fetchall.return_value = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

        from axiompy.io.database import PostgreSQLDatabase

        settings = DatabaseSettings(
            host="localhost", database="test", username="user", password="pass"
        )
        db = PostgreSQLDatabase(settings)

        results = db.get_all("users")

        assert len(results) == 2
        assert results[0]["name"] == "Alice"
        db._cleanup()

    def test_postgres_set(self, mock_postgres_connection):
        """Test PostgreSQL set() method."""
        mock_connection, mock_cursor, mock_psycopg2 = mock_postgres_connection
        mock_cursor.fetchone.return_value = {"id": 123}

        from axiompy.io.database import PostgreSQLDatabase

        settings = DatabaseSettings(
            host="localhost", database="test", username="user", password="pass"
        )
        db = PostgreSQLDatabase(settings)

        user_id = db.set("users", {"name": "Charlie", "email": "charlie@example.com"})

        assert user_id == 123
        db._cleanup()

    def test_postgres_update(self, mock_postgres_connection):
        """Test PostgreSQL update() method."""
        mock_connection, mock_cursor, mock_psycopg2 = mock_postgres_connection
        mock_cursor.rowcount = 1

        from axiompy.io.database import PostgreSQLDatabase

        settings = DatabaseSettings(
            host="localhost", database="test", username="user", password="pass"
        )
        db = PostgreSQLDatabase(settings)

        affected = db.update("users", 1, {"email": "newemail@example.com"})

        assert affected == 1
        db._cleanup()

    def test_postgres_delete(self, mock_postgres_connection):
        """Test PostgreSQL delete() method."""
        mock_connection, mock_cursor, mock_psycopg2 = mock_postgres_connection
        mock_cursor.rowcount = 1

        from axiompy.io.database import PostgreSQLDatabase

        settings = DatabaseSettings(
            host="localhost", database="test", username="user", password="pass"
        )
        db = PostgreSQLDatabase(settings)

        affected = db.delete("users", 1)

        assert affected == 1
        db._cleanup()

    def test_postgres_execute(self, mock_postgres_connection):
        """Test PostgreSQL execute() method."""
        mock_connection, mock_cursor, mock_psycopg2 = mock_postgres_connection
        mock_cursor.fetchall.return_value = [{"id": 1, "name": "Alice", "age": 30}]

        from axiompy.io.database import PostgreSQLDatabase

        settings = DatabaseSettings(
            host="localhost", database="test", username="user", password="pass"
        )
        db = PostgreSQLDatabase(settings)

        results = db.execute("SELECT * FROM users WHERE age > %s", (25,))

        assert isinstance(results, list)
        assert len(results) == 1
        db._cleanup()


class TestDynamoDBDatabase:
    """Test DynamoDB database with mocked boto3."""

    @pytest.fixture
    def mock_dynamodb_connection(self, mocker):
        """Mock boto3 and return mocked resource and client."""
        # Mock boto3
        mock_boto3 = mocker.MagicMock()
        mocker.patch.dict("sys.modules", {"boto3": mock_boto3})

        # Create mock resource and client
        mock_resource = mocker.MagicMock()
        mock_client = mocker.MagicMock()
        mock_boto3.resource.return_value = mock_resource
        mock_boto3.client.return_value = mock_client

        return mock_resource, mock_client, mock_boto3

    def test_dynamodb_get(self, mock_dynamodb_connection, mocker):
        """Test DynamoDB get() method."""
        mock_resource, mock_client, mock_boto3 = mock_dynamodb_connection

        # Mock table
        mock_table = mocker.MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"user_id": "123", "name": "Alice", "email": "alice@example.com"}
        }
        mock_resource.Table.return_value = mock_table

        from axiompy.io.database import DynamoDBDatabase

        settings = DatabaseSettings(region="us-east-1")
        db = DynamoDBDatabase(settings)

        result = db.get("Users", "123", key_column="user_id")

        assert result is not None
        assert result["name"] == "Alice"
        db._cleanup()

    def test_dynamodb_get_all(self, mock_dynamodb_connection, mocker):
        """Test DynamoDB get_all() method."""
        mock_resource, mock_client, mock_boto3 = mock_dynamodb_connection

        # Mock table
        mock_table = mocker.MagicMock()
        mock_table.scan.return_value = {
            "Items": [{"user_id": "1", "name": "Alice"}, {"user_id": "2", "name": "Bob"}]
        }
        mock_resource.Table.return_value = mock_table

        from axiompy.io.database import DynamoDBDatabase

        settings = DatabaseSettings(region="us-east-1")
        db = DynamoDBDatabase(settings)

        results = db.get_all("Users")

        assert len(results) == 2
        assert results[0]["name"] == "Alice"
        db._cleanup()

    def test_dynamodb_set(self, mock_dynamodb_connection, mocker):
        """Test DynamoDB set() method."""
        mock_resource, mock_client, mock_boto3 = mock_dynamodb_connection

        # Mock table
        mock_table = mocker.MagicMock()
        mock_resource.Table.return_value = mock_table

        from axiompy.io.database import DynamoDBDatabase

        settings = DatabaseSettings(region="us-east-1")
        db = DynamoDBDatabase(settings)

        # DynamoDB returns the 'id' field if present, otherwise None
        data = {"id": "123", "name": "Charlie", "email": "charlie@example.com"}
        returned_id = db.set("Users", data)

        assert returned_id == "123"
        mock_table.put_item.assert_called_once()
        db._cleanup()

    def test_dynamodb_update(self, mock_dynamodb_connection, mocker):
        """Test DynamoDB update() method."""
        mock_resource, mock_client, mock_boto3 = mock_dynamodb_connection

        # Mock table
        mock_table = mocker.MagicMock()
        mock_resource.Table.return_value = mock_table

        from axiompy.io.database import DynamoDBDatabase

        settings = DatabaseSettings(region="us-east-1")
        db = DynamoDBDatabase(settings)

        affected = db.update(
            "Users", "123", {"email": "newemail@example.com"}, key_column="user_id"
        )

        assert affected == 1
        mock_table.update_item.assert_called_once()
        db._cleanup()

    def test_dynamodb_delete(self, mock_dynamodb_connection, mocker):
        """Test DynamoDB delete() method."""
        mock_resource, mock_client, mock_boto3 = mock_dynamodb_connection

        # Mock table
        mock_table = mocker.MagicMock()
        mock_resource.Table.return_value = mock_table

        from axiompy.io.database import DynamoDBDatabase

        settings = DatabaseSettings(region="us-east-1")
        db = DynamoDBDatabase(settings)

        affected = db.delete("Users", "123", key_column="user_id")

        assert affected == 1
        mock_table.delete_item.assert_called_once()
        db._cleanup()

    def test_dynamodb_execute_query(self, mock_dynamodb_connection, mocker):
        """Test DynamoDB execute() with query."""
        mock_resource, mock_client, mock_boto3 = mock_dynamodb_connection

        # Mock table
        mock_table = mocker.MagicMock()
        mock_table.query.return_value = {"Items": [{"user_id": "123", "name": "Alice"}]}
        mock_resource.Table.return_value = mock_table

        from unittest.mock import MagicMock

        from axiompy.io.database import DynamoDBDatabase

        settings = DatabaseSettings(region="us-east-1")
        db = DynamoDBDatabase(settings)

        # Create a mock Key condition
        mock_key = MagicMock()
        results = db.execute("Users", {"KeyConditionExpression": mock_key})

        assert isinstance(results, list)
        assert len(results) == 1
        db._cleanup()

    def test_dynamodb_execute_scan(self, mock_dynamodb_connection, mocker):
        """Test DynamoDB execute() with scan."""
        mock_resource, mock_client, mock_boto3 = mock_dynamodb_connection

        # Mock table
        mock_table = mocker.MagicMock()
        mock_table.scan.return_value = {
            "Items": [{"user_id": "1", "name": "Alice"}, {"user_id": "2", "name": "Bob"}]
        }
        mock_resource.Table.return_value = mock_table

        from axiompy.io.database import DynamoDBDatabase

        settings = DatabaseSettings(region="us-east-1")
        db = DynamoDBDatabase(settings)

        results = db.execute("Users", {"_operation": "scan"})

        assert isinstance(results, list)
        assert len(results) == 2
        db._cleanup()
