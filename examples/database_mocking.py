# @!documentation

"""
Examples demonstrating how to mock the database abstraction for unit testing.

This file shows best practices for:
- Creating mock database implementations
- Writing testable services using dependency injection
- Unit testing services without real database connections
- Verifying database interactions in tests
"""

from typing import Any, Dict, List, Optional, Tuple, Union

from axiompy.io.database import Database, DatabaseSettings

# ============================================================================
# Mock Database Implementation
# ============================================================================


class MockDatabase(Database):
    """
    Mock database implementation for unit testing.

    This mock allows you to:
    - Set predetermined return values for operations
    - Track all database calls made during tests
    - Simulate database errors
    - Verify interactions without real database connections
    """

    def __init__(self, settings: Optional[DatabaseSettings] = None):
        """Initialize the mock database."""
        super().__init__(settings or DatabaseSettings())

        # Track all calls for verification
        self.get_calls: List[tuple] = []
        self.get_all_calls: List[str] = []
        self.set_calls: List[tuple] = []
        self.update_calls: List[tuple] = []
        self.delete_calls: List[tuple] = []
        self.execute_calls: List[tuple] = []

        # Store mock responses
        self._get_responses: List[Optional[Dict[str, Any]]] = []
        self._get_all_responses: List[List[Dict[str, Any]]] = []
        self._set_responses: List[Any] = []
        self._update_responses: List[int] = []
        self._delete_responses: List[int] = []
        self._execute_responses: List[Union[int, List[Dict[str, Any]]]] = []

        # Error simulation
        self._should_raise_error = False
        self._error_message = ""

    def _cleanup(self) -> None:
        """Clean up mock resources (no-op for mock)."""
        pass

    def get(self, table: str, key_value: Any, key_column: str = "id") -> Optional[Dict[str, Any]]:
        """Execute a mock get and return predetermined result."""
        from axiompy.io.database import DatabaseQueryError

        self.get_calls.append((table, key_value, key_column))

        if self._should_raise_error:
            raise DatabaseQueryError(self._error_message)

        if self._get_responses:
            return self._get_responses.pop(0)
        return None

    def get_all(self, table: str) -> List[Dict[str, Any]]:
        """Execute a mock get_all and return predetermined results."""
        from axiompy.io.database import DatabaseQueryError

        self.get_all_calls.append(table)

        if self._should_raise_error:
            raise DatabaseQueryError(self._error_message)

        if self._get_all_responses:
            return self._get_all_responses.pop(0)
        return []

    def set(self, table: str, data: Dict[str, Any]) -> Any:
        """Execute a mock set and return predetermined ID."""
        from axiompy.io.database import DatabaseQueryError

        self.set_calls.append((table, data))

        if self._should_raise_error:
            raise DatabaseQueryError(self._error_message)

        if self._set_responses:
            return self._set_responses.pop(0)
        return 1

    def update(
        self, table: str, key_value: Any, data: Dict[str, Any], key_column: str = "id"
    ) -> int:
        """Execute a mock update and return predetermined affected rows."""
        from axiompy.io.database import DatabaseQueryError

        self.update_calls.append((table, key_value, data, key_column))

        if self._should_raise_error:
            raise DatabaseQueryError(self._error_message)

        if self._update_responses:
            return self._update_responses.pop(0)
        return 1

    def delete(self, table: str, key_value: Any, key_column: str = "id") -> int:
        """Execute a mock delete and return predetermined affected rows."""
        from axiompy.io.database import DatabaseQueryError

        self.delete_calls.append((table, key_value, key_column))

        if self._should_raise_error:
            raise DatabaseQueryError(self._error_message)

        if self._delete_responses:
            return self._delete_responses.pop(0)
        return 1

    def execute(
        self, sql_string: str, params: Optional[Union[Tuple, Dict]] = None
    ) -> Union[int, List[Dict[str, Any]]]:
        """Execute a mock custom SQL command and return predetermined result."""
        from axiompy.io.database import DatabaseQueryError

        self.execute_calls.append((sql_string, params))

        if self._should_raise_error:
            raise DatabaseQueryError(self._error_message)

        if self._execute_responses:
            return self._execute_responses.pop(0)

        # Default: return empty list for SELECT, 0 for others
        if sql_string.strip().upper().startswith("SELECT"):
            return []
        return 0

    # Helper methods for test setup

    def add_get_response(self, response: Optional[Dict[str, Any]]) -> None:
        """Add a response that will be returned by the next get call."""
        self._get_responses.append(response)

    def add_get_all_response(self, response: List[Dict[str, Any]]) -> None:
        """Add a response that will be returned by the next get_all call."""
        self._get_all_responses.append(response)

    def add_set_response(self, inserted_id: Any) -> None:
        """Add a response that will be returned by the next set call."""
        self._set_responses.append(inserted_id)

    def add_update_response(self, affected_rows: int) -> None:
        """Add a response that will be returned by the next update call."""
        self._update_responses.append(affected_rows)

    def add_delete_response(self, affected_rows: int) -> None:
        """Add a response that will be returned by the next delete call."""
        self._delete_responses.append(affected_rows)

    def add_execute_response(self, response: Union[int, List[Dict[str, Any]]]) -> None:
        """Add a response that will be returned by the next execute call."""
        self._execute_responses.append(response)

    def set_error(self, error_message: str) -> None:
        """Configure the mock to raise an error on the next call."""
        self._should_raise_error = True
        self._error_message = error_message

    def reset(self) -> None:
        """Reset all mock state."""
        self.get_calls.clear()
        self.get_all_calls.clear()
        self.set_calls.clear()
        self.update_calls.clear()
        self.delete_calls.clear()
        self.execute_calls.clear()
        self._get_responses.clear()
        self._get_all_responses.clear()
        self._set_responses.clear()
        self._update_responses.clear()
        self._delete_responses.clear()
        self._execute_responses.clear()
        self._should_raise_error = False
        self._error_message = ""


# ============================================================================
# Example Service - User Repository
# ============================================================================


class UserRepository:
    """
    Example repository class that depends on the Database interface.

    This service can work with any Database implementation - real or mock.
    By depending on the abstract Database interface rather than a concrete
    implementation, we enable easy testing and flexibility.
    """

    def __init__(self, database: Database):
        """
        Initialize the repository with a database connection.

        Args:
            database: Any Database implementation (real or mock)
        """
        self.db = database

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a user by ID.

        Args:
            user_id: User ID to look up

        Returns:
            User dictionary or None if not found
        """
        return self.db.get("users", user_id)

    def get_all_users(self) -> List[Dict[str, Any]]:
        """
        Get all users.

        Returns:
            List of user dictionaries
        """
        return self.db.get_all("users")

    def get_users_by_email_domain(self, domain: str) -> List[Dict[str, Any]]:
        """
        Get all users with email addresses in a specific domain.

        Args:
            domain: Email domain (e.g., "example.com")

        Returns:
            List of user dictionaries
        """
        results = self.db.execute(
            "SELECT id, name, email FROM users WHERE email LIKE ?", (f"%@{domain}",)
        )
        return results if isinstance(results, list) else []

    def create_user(self, name: str, email: str) -> Any:
        """
        Create a new user.

        Args:
            name: User's name
            email: User's email address

        Returns:
            ID of the created user
        """
        return self.db.set("users", {"name": name, "email": email})

    def update_user_email(self, user_id: int, new_email: str) -> bool:
        """
        Update a user's email address.

        Args:
            user_id: User ID to update
            new_email: New email address

        Returns:
            True if user was updated, False if not found
        """
        affected = self.db.update("users", user_id, {"email": new_email})
        return affected > 0

    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user by ID.

        Args:
            user_id: User ID to delete

        Returns:
            True if user was deleted, False if not found
        """
        affected = self.db.delete("users", user_id)
        return affected > 0

    def get_user_count(self) -> int:
        """
        Get total number of users.

        Returns:
            Total user count
        """
        results = self.db.execute("SELECT COUNT(*) as count FROM users")
        if isinstance(results, list) and results:
            return results[0]["count"]
        return 0


# ============================================================================
# Example Service - Order Service
# ============================================================================


class OrderService:
    """
    Example service that combines business logic with database operations.

    This demonstrates a more complex service with business rules.
    """

    def __init__(self, database: Database):
        """Initialize the service with a database connection."""
        self.db = database

    def create_order(self, customer_id: int, items: List[Dict[str, Any]]) -> Optional[int]:
        """
        Create a new order with validation.

        Args:
            customer_id: ID of the customer placing the order
            items: List of items (each with 'product_id', 'quantity', 'price')

        Returns:
            Order ID if created successfully, None otherwise
        """
        # Business logic: validate minimum order
        if not items:
            return None

        total = sum(item["price"] * item["quantity"] for item in items)

        # Business logic: minimum order amount
        if total < 10.0:
            return None

        # Create order
        order_id = self.db.set("orders", {"customer_id": customer_id, "total": total})
        return order_id

    def get_customer_orders(self, customer_id: int) -> List[Dict[str, Any]]:
        """
        Get all orders for a specific customer.

        Args:
            customer_id: Customer ID

        Returns:
            List of order dictionaries
        """
        results = self.db.execute(
            "SELECT id, customer_id, total, created_at FROM orders WHERE customer_id = ?",
            (customer_id,),
        )
        return results if isinstance(results, list) else []

    def calculate_customer_lifetime_value(self, customer_id: int) -> float:
        """
        Calculate total amount spent by a customer.

        Args:
            customer_id: Customer ID

        Returns:
            Total amount spent
        """
        results = self.db.execute(
            "SELECT SUM(total) as lifetime_value FROM orders WHERE customer_id = ?", (customer_id,)
        )

        if isinstance(results, list) and results and results[0]["lifetime_value"] is not None:
            return float(results[0]["lifetime_value"])
        return 0.0


# ============================================================================
# Unit Tests Examples
# ============================================================================


def test_get_user_by_id_found():
    """Test retrieving an existing user."""
    # Arrange
    mock_db = MockDatabase()
    mock_db.add_get_response(
        {"id": 1, "name": "John Doe", "email": "john@example.com", "created_at": "2024-01-01"}
    )
    repo = UserRepository(mock_db)

    # Act
    user = repo.get_user_by_id(1)

    # Assert
    assert user is not None
    assert user["id"] == 1
    assert user["name"] == "John Doe"
    assert user["email"] == "john@example.com"

    # Verify database interaction
    assert len(mock_db.get_calls) == 1
    assert mock_db.get_calls[0] == ("users", 1, "id")
    print("✓ test_get_user_by_id_found passed")


def test_get_user_by_id_not_found():
    """Test retrieving a non-existent user."""
    # Arrange
    mock_db = MockDatabase()
    mock_db.add_get_response(None)  # User not found
    repo = UserRepository(mock_db)

    # Act
    user = repo.get_user_by_id(999)

    # Assert
    assert user is None
    assert len(mock_db.get_calls) == 1
    print("✓ test_get_user_by_id_not_found passed")


def test_get_all_users():
    """Test retrieving all users."""
    # Arrange
    mock_db = MockDatabase()
    mock_db.add_get_all_response(
        [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
        ]
    )
    repo = UserRepository(mock_db)

    # Act
    users = repo.get_all_users()

    # Assert
    assert len(users) == 2
    assert users[0]["name"] == "Alice"
    assert users[1]["name"] == "Bob"
    assert mock_db.get_all_calls[0] == "users"
    print("✓ test_get_all_users passed")


def test_create_user():
    """Test creating a new user."""
    # Arrange
    mock_db = MockDatabase()
    mock_db.add_set_response(123)  # Return new user ID
    repo = UserRepository(mock_db)

    # Act
    user_id = repo.create_user("Jane Smith", "jane@example.com")

    # Assert
    assert user_id == 123
    assert len(mock_db.set_calls) == 1
    table, data = mock_db.set_calls[0]
    assert table == "users"
    assert data["name"] == "Jane Smith"
    assert data["email"] == "jane@example.com"
    print("✓ test_create_user passed")


def test_update_user_email_success():
    """Test successfully updating a user's email."""
    # Arrange
    mock_db = MockDatabase()
    mock_db.add_update_response(1)  # 1 row affected
    repo = UserRepository(mock_db)

    # Act
    success = repo.update_user_email(1, "newemail@example.com")

    # Assert
    assert success is True
    assert len(mock_db.update_calls) == 1
    table, key_value, data, key_column = mock_db.update_calls[0]
    assert table == "users"
    assert key_value == 1
    assert data["email"] == "newemail@example.com"
    print("✓ test_update_user_email_success passed")


def test_update_user_email_not_found():
    """Test updating email for non-existent user."""
    # Arrange
    mock_db = MockDatabase()
    mock_db.add_update_response(0)  # 0 rows affected
    repo = UserRepository(mock_db)

    # Act
    success = repo.update_user_email(999, "newemail@example.com")

    # Assert
    assert success is False
    print("✓ test_update_user_email_not_found passed")


def test_delete_user_success():
    """Test successfully deleting a user."""
    # Arrange
    mock_db = MockDatabase()
    mock_db.add_delete_response(1)  # 1 row affected
    repo = UserRepository(mock_db)

    # Act
    success = repo.delete_user(1)

    # Assert
    assert success is True
    assert len(mock_db.delete_calls) == 1
    assert mock_db.delete_calls[0] == ("users", 1, "id")
    print("✓ test_delete_user_success passed")


def test_get_users_by_email_domain():
    """Test retrieving users by email domain using execute()."""
    # Arrange
    mock_db = MockDatabase()
    mock_db.add_execute_response(
        [
            {"id": 1, "name": "User 1", "email": "user1@company.com"},
            {"id": 2, "name": "User 2", "email": "user2@company.com"},
            {"id": 3, "name": "User 3", "email": "user3@company.com"},
        ]
    )
    repo = UserRepository(mock_db)

    # Act
    users = repo.get_users_by_email_domain("company.com")

    # Assert
    assert len(users) == 3
    assert all("@company.com" in user["email"] for user in users)
    assert len(mock_db.execute_calls) == 1
    sql, params = mock_db.execute_calls[0]
    assert "email LIKE" in sql
    assert params == ("%@company.com",)
    print("✓ test_get_users_by_email_domain passed")


def test_create_order_with_valid_items():
    """Test creating an order with valid items."""
    # Arrange
    mock_db = MockDatabase()
    mock_db.add_set_response(456)  # Return new order ID
    service = OrderService(mock_db)

    items = [
        {"product_id": 1, "quantity": 2, "price": 10.0},
        {"product_id": 2, "quantity": 1, "price": 5.0},
    ]

    # Act
    order_id = service.create_order(customer_id=1, items=items)

    # Assert
    assert order_id == 456
    assert len(mock_db.set_calls) == 1
    table, data = mock_db.set_calls[0]
    assert table == "orders"
    assert data["customer_id"] == 1
    assert data["total"] == 25.0
    print("✓ test_create_order_with_valid_items passed")


def test_create_order_below_minimum():
    """Test that orders below minimum amount are rejected."""
    # Arrange
    mock_db = MockDatabase()
    service = OrderService(mock_db)

    items = [
        {"product_id": 1, "quantity": 1, "price": 5.0},  # Total = $5 (below $10 minimum)
    ]

    # Act
    order_id = service.create_order(customer_id=1, items=items)

    # Assert
    assert order_id is None
    assert len(mock_db.set_calls) == 0  # No database call should be made
    print("✓ test_create_order_below_minimum passed")


def test_create_order_with_empty_items():
    """Test that orders with no items are rejected."""
    # Arrange
    mock_db = MockDatabase()
    service = OrderService(mock_db)

    # Act
    order_id = service.create_order(customer_id=1, items=[])

    # Assert
    assert order_id is None
    assert len(mock_db.set_calls) == 0
    print("✓ test_create_order_with_empty_items passed")


def test_calculate_customer_lifetime_value():
    """Test calculating customer's lifetime value."""
    # Arrange
    mock_db = MockDatabase()
    mock_db.add_execute_response([{"lifetime_value": 1250.50}])
    service = OrderService(mock_db)

    # Act
    ltv = service.calculate_customer_lifetime_value(1)

    # Assert
    assert ltv == 1250.50
    assert len(mock_db.execute_calls) == 1
    sql, params = mock_db.execute_calls[0]
    assert "SUM(total)" in sql
    assert params == (1,)
    print("✓ test_calculate_customer_lifetime_value passed")


def test_calculate_customer_lifetime_value_no_orders():
    """Test lifetime value for customer with no orders."""
    # Arrange
    mock_db = MockDatabase()
    mock_db.add_execute_response([{"lifetime_value": None}])  # NULL from SUM with no rows
    service = OrderService(mock_db)

    # Act
    ltv = service.calculate_customer_lifetime_value(999)

    # Assert
    assert ltv == 0.0
    print("✓ test_calculate_customer_lifetime_value_no_orders passed")


def test_database_error_handling():
    """Test that services properly handle database errors."""
    from axiompy.io.database import DatabaseQueryError

    # Arrange
    mock_db = MockDatabase()
    mock_db.set_error("Connection lost")
    repo = UserRepository(mock_db)

    # Act & Assert
    try:
        repo.get_user_by_id(1)
        assert False, "Should have raised DatabaseQueryError"
    except DatabaseQueryError as e:
        assert "Connection lost" in str(e)
        print("✓ test_database_error_handling passed")


def test_get_user_count():
    """Test getting total user count."""
    # Arrange
    mock_db = MockDatabase()
    mock_db.add_execute_response([{"count": 42}])
    repo = UserRepository(mock_db)

    # Act
    count = repo.get_user_count()

    # Assert
    assert count == 42
    assert len(mock_db.execute_calls) == 1
    print("✓ test_get_user_count passed")


# ============================================================================
# Main - Run all tests
# ============================================================================


def run_all_tests():
    """Run all unit tests."""
    print("=" * 70)
    print("Running Unit Tests with Mock Database")
    print("=" * 70)
    print()

    tests = [
        test_get_user_by_id_found,
        test_get_user_by_id_not_found,
        test_get_all_users,
        test_create_user,
        test_update_user_email_success,
        test_update_user_email_not_found,
        test_delete_user_success,
        test_get_users_by_email_domain,
        test_create_order_with_valid_items,
        test_create_order_below_minimum,
        test_create_order_with_empty_items,
        test_calculate_customer_lifetime_value,
        test_calculate_customer_lifetime_value_no_orders,
        test_database_error_handling,
        test_get_user_count,
    ]

    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1

    print()
    print("=" * 70)
    print(f"Tests run: {len(tests)}")
    print(f"Passed: {len(tests) - failed}")
    print(f"Failed: {failed}")
    print("=" * 70)

    if failed == 0:
        print("\n✓ All tests passed! The mock database enables fast, reliable testing.")
        print("\nKey Benefits Demonstrated:")
        print("  • No real database required for unit tests")
        print("  • Fast test execution (no I/O)")
        print("  • Easy to simulate edge cases")
        print("  • Verify exact database interactions")
        print("  • Services decoupled from database implementation")


if __name__ == "__main__":
    run_all_tests()
