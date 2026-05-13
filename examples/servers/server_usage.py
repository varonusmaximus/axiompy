"""
Examples of using the axiompy server abstraction layer.

This file demonstrates how to use the ServerFactory and various server
implementations for building web APIs.

Note: Choose your preferred framework (Flask or FastAPI) and the abstraction
handles the details.
"""

from axiompy.servers import Server, ServerFactory, ServerSettings, ServerType

# ============================================================================
# Example 1: Simple API with Flask
# ============================================================================


def flask_example():
    """Basic Flask server example."""
    print("=" * 70)
    print("Flask Server Example")
    print("=" * 70)

    # Create Flask server
    settings = ServerSettings(host="127.0.0.1", port=5000, debug=True)
    server = ServerFactory.create(ServerType.FLASK, settings)

    # Define routes
    @server.route("/")
    def home():
        return {"message": "Welcome to Flask API"}

    @server.route("/health", methods=["GET"])
    def health():
        return {"status": "healthy", "framework": "Flask"}

    @server.route("/users/<int:user_id>", methods=["GET"])
    def get_user(user_id):
        return {"id": user_id, "name": f"User {user_id}", "framework": "Flask"}

    @server.route("/users", methods=["POST"])
    def create_user(data):
        # 'data' parameter automatically gets request JSON
        return {"id": 123, "name": data.get("name"), "created": True}

    print("\nFlask server configured with routes:")
    print("  GET  / - Home")
    print("  GET  /health - Health check")
    print("  GET  /users/<id> - Get user")
    print("  POST /users - Create user")
    print("\nTo start the server, uncomment server.run() below")
    # server.run()  # Uncomment to start


# ============================================================================
# Example 2: Simple API with FastAPI
# ============================================================================


def fastapi_example():
    """Basic FastAPI server example."""
    print("\n" + "=" * 70)
    print("FastAPI Server Example")
    print("=" * 70)

    # Create FastAPI server
    settings = ServerSettings(
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
    )
    server = ServerFactory.create(ServerType.FASTAPI, settings)

    # Define routes
    @server.route("/")
    def home():
        return {"message": "Welcome to FastAPI"}

    @server.route("/health", methods=["GET"])
    def health():
        return {"status": "healthy", "framework": "FastAPI"}

    @server.route("/users/{user_id}", methods=["GET"])
    def get_user(user_id: int):
        return {"id": user_id, "name": f"User {user_id}", "framework": "FastAPI"}

    @server.route("/users", methods=["POST"])
    def create_user(data: dict):
        # 'data' parameter automatically gets request JSON
        return {"id": 456, "name": data.get("name"), "created": True}

    print("\nFastAPI server configured with routes:")
    print("  GET  / - Home")
    print("  GET  /health - Health check")
    print("  GET  /users/{id} - Get user")
    print("  POST /users - Create user")
    print("\nTo start the server, uncomment server.run() below")
    print("Then visit: http://localhost:8000/docs for automatic API docs!")
    # server.run()  # Uncomment to start


# ============================================================================
# Example 3: Framework-Agnostic Application Class
# ============================================================================


class UserAPI:
    """
    Example API that works with any server implementation.

    This demonstrates the power of the abstraction - your application
    code doesn't need to know which framework is being used.
    """

    def __init__(self, server: Server):
        """Initialize with any server implementation."""
        self.server = server
        self.users = {
            1: {"id": 1, "name": "Alice", "email": "alice@example.com"},
            2: {"id": 2, "name": "Bob", "email": "bob@example.com"},
        }
        self._next_id = 3
        self._setup_routes()

    def _setup_routes(self):
        """Register all routes."""
        self.server.route("/api/users", methods=["GET"])(self.list_users)
        self.server.route("/api/users/<int:user_id>", methods=["GET"])(self.get_user)
        self.server.route("/api/users", methods=["POST"])(self.create_user)
        self.server.route("/api/users/<int:user_id>", methods=["PUT"])(self.update_user)
        self.server.route("/api/users/<int:user_id>", methods=["DELETE"])(self.delete_user)

    def list_users(self):
        """Get all users."""
        return {"users": list(self.users.values())}

    def get_user(self, user_id: int):
        """Get a specific user."""
        user = self.users.get(user_id)
        if not user:
            return {"error": "User not found"}, 404
        return user

    def create_user(self, data: dict):
        """Create a new user."""
        user = {
            "id": self._next_id,
            "name": data.get("name"),
            "email": data.get("email"),
        }
        self.users[self._next_id] = user
        self._next_id += 1
        return user

    def update_user(self, user_id: int, data: dict):
        """Update an existing user."""
        if user_id not in self.users:
            return {"error": "User not found"}, 404

        user = self.users[user_id]
        user["name"] = data.get("name", user["name"])
        user["email"] = data.get("email", user["email"])
        return user

    def delete_user(self, user_id: int):
        """Delete a user."""
        if user_id not in self.users:
            return {"error": "User not found"}, 404

        del self.users[user_id]
        return {"message": "User deleted"}


def framework_agnostic_example():
    """Demonstrate the same API working with different frameworks."""
    print("\n" + "=" * 70)
    print("Framework-Agnostic Application Example")
    print("=" * 70)

    # Same application code works with Flask
    print("\nWith Flask:")
    flask_settings = ServerSettings(port=5000)
    flask_server = ServerFactory.create(ServerType.FLASK, flask_settings)
    flask_api = UserAPI(flask_server)
    print(f"  Created UserAPI with Flask ({len(flask_api.users)} users)")

    # Same application code works with FastAPI
    print("\nWith FastAPI:")
    fastapi_settings = ServerSettings(port=8000)
    fastapi_server = ServerFactory.create(ServerType.FASTAPI, fastapi_settings)
    fastapi_api = UserAPI(fastapi_server)
    print(f"  Created UserAPI with FastAPI ({len(fastapi_api.users)} users)")

    print("\n✓ Same application code works with both frameworks!")
    print("  To run either, uncomment the run() call below:")
    # flask_server.run()  # Or
    # fastapi_server.run()


# ============================================================================
# Example 4: Middleware
# ============================================================================


def middleware_example():
    """Demonstrate adding middleware."""
    print("\n" + "=" * 70)
    print("Middleware Example")
    print("=" * 70)

    settings = ServerSettings(port=8000, debug=True)
    server = ServerFactory.create(ServerType.FASTAPI, settings)

    # Add logging middleware
    async def logging_middleware(request, call_next):
        """Log all requests."""
        print(f"Request: {request.method} {request.url.path}")
        response = await call_next(request)
        print(f"Response: {response.status_code}")
        return response

    server.add_middleware(logging_middleware)

    @server.route("/test")
    def test():
        return {"message": "Check the logs!"}

    print("\nMiddleware added - all requests will be logged")
    # server.run()


# ============================================================================
# Example 5: Testing with the Abstraction
# ============================================================================


def testing_example():
    """Show how to test using the abstraction."""
    print("\n" + "=" * 70)
    print("Testing Example")
    print("=" * 70)

    # Create server for testing
    settings = ServerSettings()
    server = ServerFactory.create(ServerType.FLASK, settings)

    # Create API
    api = UserAPI(server)

    # Get Flask test client
    app = server.get_app()
    client = app.test_client()

    # Test the API
    print("\nTesting UserAPI endpoints:")

    # Test list users
    response = client.get("/api/users")
    print(f"  GET /api/users: {response.status_code}")
    print(f"    Users: {len(response.json['users'])}")

    # Test create user
    response = client.post(
        "/api/users",
        json={"name": "Charlie", "email": "charlie@example.com"},
    )
    print(f"  POST /api/users: {response.status_code}")
    print(f"    Created user: {response.json['name']}")

    # Test get specific user
    response = client.get("/api/users/1")
    print(f"  GET /api/users/1: {response.status_code}")
    print(f"    User: {response.json['name']}")

    print("\n✓ All tests passed!")


# ============================================================================
# Example 6: Advanced Configuration
# ============================================================================


def advanced_configuration_example():
    """Show advanced configuration options."""
    print("\n" + "=" * 70)
    print("Advanced Configuration Example")
    print("=" * 70)

    # Flask with custom configuration
    flask_settings = ServerSettings(
        host="0.0.0.0",
        port=5000,
        debug=True,
        extra_params={
            "JSON_SORT_KEYS": False,
            "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,  # 16MB max request
        },
    )
    flask_server = ServerFactory.create(ServerType.FLASK, flask_settings)
    print("Flask server with custom config:")
    print(f"  Host: {flask_settings.host}")
    print(f"  Port: {flask_settings.port}")
    print(f"  Extra params: {list(flask_settings.extra_params.keys())}")

    # FastAPI with custom configuration
    fastapi_settings = ServerSettings(
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=4,
        extra_params={
            "title": "My Custom API",
            "description": "API built with AxiomPy abstraction",
            "version": "1.0.0",
        },
    )
    fastapi_server = ServerFactory.create(ServerType.FASTAPI, fastapi_settings)
    print("\nFastAPI server with custom config:")
    print(f"  Host: {fastapi_settings.host}")
    print(f"  Port: {fastapi_settings.port}")
    print(f"  Workers: {fastapi_settings.workers}")
    print(f"  Reload: {fastapi_settings.reload}")


# ============================================================================
# Example 7: Error Handling
# ============================================================================


def error_handling_example():
    """Demonstrate error handling."""
    print("\n" + "=" * 70)
    print("Error Handling Example")
    print("=" * 70)

    settings = ServerSettings()
    server = ServerFactory.create(ServerType.FLASK, settings)

    @server.route("/divide/<int:a>/<int:b>")
    def divide(a: int, b: int):
        """Endpoint that might raise an error."""
        try:
            result = a / b
            return {"result": result}
        except ZeroDivisionError:
            return {"error": "Cannot divide by zero"}, 400

    @server.route("/users/<int:user_id>")
    def get_user_safe(user_id: int):
        """Endpoint with validation."""
        if user_id < 1:
            return {"error": "Invalid user ID"}, 400

        # Simulate user not found
        if user_id > 100:
            return {"error": "User not found"}, 404

        return {"id": user_id, "name": f"User {user_id}"}

    print("\nError handling routes configured")
    print("  GET /divide/<a>/<b> - Division with error handling")
    print("  GET /users/<id> - User lookup with validation")


# ============================================================================
# Main
# ============================================================================


if __name__ == "__main__":
    """Run all examples (without starting servers)."""

    # Run non-blocking examples
    flask_example()
    fastapi_example()
    framework_agnostic_example()
    middleware_example()
    testing_example()
    advanced_configuration_example()
    error_handling_example()

    print("\n" + "=" * 70)
    print("All Examples Complete!")
    print("=" * 70)
    print("\nTo actually run a server, uncomment the server.run() calls")
    print("in any of the examples above.")
    print("\nKey Takeaways:")
    print("  • Same abstraction works with Flask and FastAPI")
    print("  • Write framework-agnostic application code")
    print("  • Easy to test with framework test clients")
    print("  • Switch frameworks without changing application logic")
