"""
Examples demonstrating how to test web applications using the server abstraction.

This file shows best practices for:
- Creating mock server implementations
- Writing testable applications using dependency injection
- Unit testing applications without real servers
- Testing with Flask and FastAPI test clients
"""

from typing import Any, Callable, Dict, List, Optional

from axiompy.servers import Server, ServerFactory, ServerSettings, ServerType

# ============================================================================
# Mock Server Implementation
# ============================================================================


class MockServer(Server):
    """
    Mock server implementation for unit testing.

    This mock allows you to:
    - Track all route registrations
    - Simulate route handlers without running a real server
    - Verify routes are registered correctly
    - Test application logic in isolation
    """

    def __init__(self, settings: Optional[ServerSettings] = None):
        """Initialize the mock server."""
        super().__init__(settings or ServerSettings())

        # Track all registered routes
        self.routes: List[Dict[str, Any]] = []
        self.middlewares: List[Callable] = []
        self.run_called = False
        self.run_kwargs: Dict[str, Any] = {}

    def route(
        self,
        path: str,
        methods: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Callable:
        """Mock route registration."""
        if methods is None:
            methods = ["GET"]

        def decorator(handler: Callable) -> Callable:
            self.routes.append(
                {
                    "path": path,
                    "methods": methods,
                    "handler": handler,
                    "kwargs": kwargs,
                }
            )
            return handler

        return decorator

    def add_middleware(self, middleware: Callable, **kwargs: Any) -> None:
        """Mock middleware registration."""
        self.middlewares.append(middleware)

    def run(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Mock server run - doesn't actually start a server."""
        self.run_called = True
        self.run_kwargs = {
            "host": host or self.settings.host,
            "port": port or self.settings.port,
            **kwargs,
        }

    def get_app(self) -> Any:
        """Return None for mock server."""
        return None

    def call_route(self, path: str, method: str = "GET", **kwargs: Any) -> Any:
        """
        Helper method to call a registered route handler.

        This allows testing route logic without a real server.
        """
        for route in self.routes:
            if route["path"] == path and method in route["methods"]:
                return route["handler"](**kwargs)
        raise ValueError(f"Route not found: {method} {path}")

    def verify_route_registered(self, path: str, methods: Optional[List[str]] = None) -> bool:
        """Verify that a route was registered."""
        for route in self.routes:
            if route["path"] == path:
                if methods is None or set(methods) == set(route["methods"]):
                    return True
        return False


# ============================================================================
# Example Application
# ============================================================================


class TaskAPI:
    """
    Example task management API that works with any server.

    This demonstrates how to build testable applications using
    dependency injection with the server abstraction.
    """

    def __init__(self, server: Server):
        """Initialize with any server implementation."""
        self.server = server
        self.tasks: Dict[int, Dict[str, Any]] = {}
        self.next_id = 1
        self._setup_routes()

    def _setup_routes(self):
        """Register all routes."""
        self.server.route("/tasks", methods=["GET"])(self.list_tasks)
        self.server.route("/tasks", methods=["POST"])(self.create_task)
        self.server.route("/tasks/<int:task_id>", methods=["GET"])(self.get_task)
        self.server.route("/tasks/<int:task_id>", methods=["PUT"])(self.update_task)
        self.server.route("/tasks/<int:task_id>", methods=["DELETE"])(self.delete_task)
        self.server.route("/tasks/<int:task_id>/complete", methods=["POST"])(self.complete_task)

    def list_tasks(self):
        """Get all tasks."""
        return {"tasks": list(self.tasks.values())}

    def get_task(self, task_id: int):
        """Get a specific task."""
        task = self.tasks.get(task_id)
        if not task:
            return {"error": "Task not found"}, 404
        return task

    def create_task(self, data: dict):
        """Create a new task."""
        if not data.get("title"):
            return {"error": "Title is required"}, 400

        task = {
            "id": self.next_id,
            "title": data["title"],
            "description": data.get("description", ""),
            "completed": False,
        }
        self.tasks[self.next_id] = task
        self.next_id += 1
        return task

    def update_task(self, task_id: int, data: dict):
        """Update an existing task."""
        if task_id not in self.tasks:
            return {"error": "Task not found"}, 404

        task = self.tasks[task_id]
        task["title"] = data.get("title", task["title"])
        task["description"] = data.get("description", task["description"])
        return task

    def delete_task(self, task_id: int):
        """Delete a task."""
        if task_id not in self.tasks:
            return {"error": "Task not found"}, 404

        del self.tasks[task_id]
        return {"message": "Task deleted"}

    def complete_task(self, task_id: int):
        """Mark a task as completed."""
        if task_id not in self.tasks:
            return {"error": "Task not found"}, 404

        self.tasks[task_id]["completed"] = True
        return self.tasks[task_id]


# ============================================================================
# Unit Tests with Mock Server
# ============================================================================


def test_task_api_routes_registered():
    """Test that all routes are registered correctly."""
    # Arrange
    mock_server = MockServer()
    api = TaskAPI(mock_server)

    # Assert
    assert len(mock_server.routes) == 6
    assert mock_server.verify_route_registered("/tasks", ["GET"])
    assert mock_server.verify_route_registered("/tasks", ["POST"])
    assert mock_server.verify_route_registered("/tasks/<int:task_id>", ["GET"])
    assert mock_server.verify_route_registered("/tasks/<int:task_id>", ["PUT"])
    assert mock_server.verify_route_registered("/tasks/<int:task_id>", ["DELETE"])
    assert mock_server.verify_route_registered("/tasks/<int:task_id>/complete", ["POST"])
    print("✓ test_task_api_routes_registered passed")


def test_create_task_success():
    """Test creating a task successfully."""
    # Arrange
    mock_server = MockServer()
    api = TaskAPI(mock_server)

    # Act
    result = mock_server.call_route(
        "/tasks", "POST", data={"title": "Test Task", "description": "Test Description"}
    )

    # Assert
    assert result["id"] == 1
    assert result["title"] == "Test Task"
    assert result["description"] == "Test Description"
    assert result["completed"] is False
    assert 1 in api.tasks
    print("✓ test_create_task_success passed")


def test_create_task_missing_title():
    """Test that creating a task without a title fails."""
    # Arrange
    mock_server = MockServer()
    api = TaskAPI(mock_server)

    # Act
    result, status_code = mock_server.call_route("/tasks", "POST", data={})

    # Assert
    assert status_code == 400
    assert "error" in result
    assert len(api.tasks) == 0
    print("✓ test_create_task_missing_title passed")


def test_list_tasks():
    """Test listing all tasks."""
    # Arrange
    mock_server = MockServer()
    api = TaskAPI(mock_server)

    # Create some tasks
    api.create_task({"title": "Task 1"})
    api.create_task({"title": "Task 2"})

    # Act
    result = mock_server.call_route("/tasks", "GET")

    # Assert
    assert len(result["tasks"]) == 2
    assert result["tasks"][0]["title"] == "Task 1"
    assert result["tasks"][1]["title"] == "Task 2"
    print("✓ test_list_tasks passed")


def test_get_task_found():
    """Test getting an existing task."""
    # Arrange
    mock_server = MockServer()
    api = TaskAPI(mock_server)
    api.create_task({"title": "Test Task"})

    # Act
    result = mock_server.call_route("/tasks/<int:task_id>", "GET", task_id=1)

    # Assert
    assert result["id"] == 1
    assert result["title"] == "Test Task"
    print("✓ test_get_task_found passed")


def test_get_task_not_found():
    """Test getting a non-existent task."""
    # Arrange
    mock_server = MockServer()
    api = TaskAPI(mock_server)

    # Act
    result, status_code = mock_server.call_route("/tasks/<int:task_id>", "GET", task_id=999)

    # Assert
    assert status_code == 404
    assert "error" in result
    print("✓ test_get_task_not_found passed")


def test_update_task():
    """Test updating a task."""
    # Arrange
    mock_server = MockServer()
    api = TaskAPI(mock_server)
    api.create_task({"title": "Original Title"})

    # Act
    result = mock_server.call_route(
        "/tasks/<int:task_id>", "PUT", task_id=1, data={"title": "Updated Title"}
    )

    # Assert
    assert result["id"] == 1
    assert result["title"] == "Updated Title"
    assert api.tasks[1]["title"] == "Updated Title"
    print("✓ test_update_task passed")


def test_delete_task():
    """Test deleting a task."""
    # Arrange
    mock_server = MockServer()
    api = TaskAPI(mock_server)
    api.create_task({"title": "Task to Delete"})

    # Act
    result = mock_server.call_route("/tasks/<int:task_id>", "DELETE", task_id=1)

    # Assert
    assert "message" in result
    assert 1 not in api.tasks
    print("✓ test_delete_task passed")


def test_complete_task():
    """Test marking a task as completed."""
    # Arrange
    mock_server = MockServer()
    api = TaskAPI(mock_server)
    api.create_task({"title": "Task to Complete"})

    # Act
    result = mock_server.call_route("/tasks/<int:task_id>/complete", "POST", task_id=1)

    # Assert
    assert result["completed"] is True
    assert api.tasks[1]["completed"] is True
    print("✓ test_complete_task passed")


# ============================================================================
# Integration Tests with Flask Test Client
# ============================================================================


def test_flask_integration():
    """Test the API with Flask test client."""
    print("\n" + "=" * 70)
    print("Flask Integration Tests")
    print("=" * 70)

    # Create Flask server
    settings = ServerSettings()
    server = ServerFactory.create(ServerType.FLASK, settings)
    api = TaskAPI(server)

    # Get test client
    app = server.get_app()
    client = app.test_client()

    # Test create task
    response = client.post("/tasks", json={"title": "Flask Test Task"})
    assert response.status_code == 200
    assert response.json["title"] == "Flask Test Task"
    print("✓ Flask POST /tasks works")

    # Test list tasks
    response = client.get("/tasks")
    assert response.status_code == 200
    assert len(response.json["tasks"]) == 1
    print("✓ Flask GET /tasks works")

    # Test get specific task
    response = client.get("/tasks/1")
    assert response.status_code == 200
    assert response.json["id"] == 1
    print("✓ Flask GET /tasks/1 works")

    # Test update task
    response = client.put("/tasks/1", json={"title": "Updated Flask Task"})
    assert response.status_code == 200
    assert response.json["title"] == "Updated Flask Task"
    print("✓ Flask PUT /tasks/1 works")

    # Test complete task
    response = client.post("/tasks/1/complete")
    assert response.status_code == 200
    assert response.json["completed"] is True
    print("✓ Flask POST /tasks/1/complete works")

    # Test delete task
    response = client.delete("/tasks/1")
    assert response.status_code == 200
    print("✓ Flask DELETE /tasks/1 works")

    print("\n✓ All Flask integration tests passed!")


# ============================================================================
# Integration Tests with FastAPI Test Client
# ============================================================================


def test_fastapi_integration():
    """Test the API with FastAPI test client."""
    print("\n" + "=" * 70)
    print("FastAPI Integration Tests")
    print("=" * 70)

    try:
        from fastapi.testclient import TestClient
    except ImportError:
        print("FastAPI not installed, skipping integration tests")
        return

    # Create FastAPI server
    settings = ServerSettings()
    server = ServerFactory.create(ServerType.FASTAPI, settings)
    api = TaskAPI(server)

    # Get test client
    app = server.get_app()
    client = TestClient(app)

    # Test create task
    response = client.post("/tasks", json={"title": "FastAPI Test Task"})
    assert response.status_code == 200
    assert response.json()["title"] == "FastAPI Test Task"
    print("✓ FastAPI POST /tasks works")

    # Test list tasks
    response = client.get("/tasks")
    assert response.status_code == 200
    assert len(response.json()["tasks"]) == 1
    print("✓ FastAPI GET /tasks works")

    # Test get specific task
    response = client.get("/tasks/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1
    print("✓ FastAPI GET /tasks/1 works")

    # Test update task
    response = client.put("/tasks/1", json={"title": "Updated FastAPI Task"})
    assert response.status_code == 200
    assert response.json()["title"] == "Updated FastAPI Task"
    print("✓ FastAPI PUT /tasks/1 works")

    # Test complete task
    response = client.post("/tasks/1/complete")
    assert response.status_code == 200
    assert response.json()["completed"] is True
    print("✓ FastAPI POST /tasks/1/complete works")

    # Test delete task
    response = client.delete("/tasks/1")
    assert response.status_code == 200
    print("✓ FastAPI DELETE /tasks/1 works")

    print("\n✓ All FastAPI integration tests passed!")


# ============================================================================
# Main - Run all tests
# ============================================================================


def run_all_tests():
    """Run all unit tests."""
    print("=" * 70)
    print("Running Unit Tests with Mock Server")
    print("=" * 70)
    print()

    tests = [
        test_task_api_routes_registered,
        test_create_task_success,
        test_create_task_missing_title,
        test_list_tasks,
        test_get_task_found,
        test_get_task_not_found,
        test_update_task,
        test_delete_task,
        test_complete_task,
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
        print("\n✓ All unit tests passed!")

    # Run integration tests
    try:
        test_flask_integration()
    except Exception as e:
        print(f"\nFlask integration tests error: {e}")

    try:
        test_fastapi_integration()
    except Exception as e:
        print(f"\nFastAPI integration tests error: {e}")

    print("\n" + "=" * 70)
    print("Key Benefits Demonstrated:")
    print("=" * 70)
    print("  • No real server required for unit tests")
    print("  • Fast test execution")
    print("  • Easy to verify route registration")
    print("  • Test business logic in isolation")
    print("  • Framework test clients work seamlessly")
    print("  • Same application works with both Flask and FastAPI")


if __name__ == "__main__":
    run_all_tests()
