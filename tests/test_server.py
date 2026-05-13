"""
Unit tests for the server abstraction layer.

Tests the Server interface, FlaskServer, FastAPIServer, and ServerFactory
implementations to ensure they work correctly.
"""

from typing import Any, Callable, List, Optional

import pytest

from axiompy.servers import (
    Server,
    ServerError,
    ServerFactory,
    ServerSettings,
    ServerType,
)

# ============================================================================
# Mock Server for Testing
# ============================================================================


class MockServer(Server):
    """Mock server implementation for testing the abstract interface."""

    def __init__(self, settings: ServerSettings):
        super().__init__(settings)
        self.routes = []
        self.middlewares = []
        self.run_called = False

    def route(self, path: str, methods: Optional[List[str]] = None, **kwargs: Any) -> Callable:
        def decorator(handler: Callable) -> Callable:
            self.routes.append({"path": path, "methods": methods, "handler": handler})
            return handler

        return decorator

    def add_middleware(self, middleware: Callable, **kwargs: Any) -> None:
        self.middlewares.append(middleware)

    def run(self, host: Optional[str] = None, port: Optional[int] = None, **kwargs: Any) -> None:
        self.run_called = True

    def get_app(self) -> Any:
        return None


# ============================================================================
# ServerSettings Tests
# ============================================================================


def test_server_settings_defaults():
    """Test ServerSettings default values."""
    settings = ServerSettings()

    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.debug is False
    assert settings.reload is False
    assert settings.workers == 1
    assert settings.extra_params == {}


def test_server_settings_custom():
    """Test ServerSettings with custom values."""
    settings = ServerSettings(
        host="0.0.0.0",
        port=5000,
        debug=True,
        reload=True,
        workers=4,
        extra_params={"custom": "value"},
    )

    assert settings.host == "0.0.0.0"
    assert settings.port == 5000
    assert settings.debug is True
    assert settings.reload is True
    assert settings.workers == 4
    assert settings.extra_params == {"custom": "value"}


# ============================================================================
# ServerFactory Tests
# ============================================================================


def test_factory_create_flask():
    """Test creating a Flask server via factory."""
    pytest.importorskip("flask")

    settings = ServerSettings()
    server = ServerFactory.create(ServerType.FLASK, settings)

    assert server is not None
    assert hasattr(server, "route")
    assert hasattr(server, "add_middleware")
    assert hasattr(server, "run")
    assert hasattr(server, "get_app")


def test_factory_create_fastapi():
    """Test creating a FastAPI server via factory."""
    pytest.importorskip("fastapi")

    settings = ServerSettings()
    server = ServerFactory.create(ServerType.FASTAPI, settings)

    assert server is not None
    assert hasattr(server, "route")
    assert hasattr(server, "add_middleware")
    assert hasattr(server, "run")
    assert hasattr(server, "get_app")


def test_factory_unsupported_type():
    """Test that factory raises error for unsupported server type."""
    settings = ServerSettings()

    # Create a fake enum value
    class FakeType:
        value = "unsupported"

    with pytest.raises(ValueError, match="Unsupported server type"):
        ServerFactory.create(FakeType(), settings)


def test_factory_register_custom_server():
    """Test registering a custom server implementation."""
    # Create a custom server type
    from enum import Enum

    class CustomType(Enum):
        CUSTOM = "custom"

    # Register the mock server
    ServerFactory.register_server(CustomType.CUSTOM, MockServer)

    # Create using factory
    settings = ServerSettings()
    server = ServerFactory.create(CustomType.CUSTOM, settings)

    assert isinstance(server, MockServer)


def test_factory_register_invalid_class():
    """Test that registering a non-Server class raises TypeError."""
    from enum import Enum

    class CustomType(Enum):
        INVALID = "invalid"

    class NotAServer:
        pass

    with pytest.raises(TypeError, match="must inherit from Server"):
        ServerFactory.register_server(CustomType.INVALID, NotAServer)


# ============================================================================
# Flask Server Tests
# ============================================================================


@pytest.fixture
def flask_server():
    """Fixture providing a Flask server instance."""
    pytest.importorskip("flask")
    settings = ServerSettings(host="127.0.0.1", port=5000, debug=True)
    return ServerFactory.create(ServerType.FLASK, settings)


def test_flask_server_initialization(flask_server):
    """Test Flask server initializes correctly."""
    assert flask_server is not None
    assert flask_server.settings.host == "127.0.0.1"
    assert flask_server.settings.port == 5000
    assert flask_server.settings.debug is True

    app = flask_server.get_app()
    assert app is not None
    assert app.config["DEBUG"] is True


def test_flask_server_route_registration(flask_server):
    """Test registering routes with Flask server."""

    @flask_server.route("/test")
    def test_route():
        return {"message": "test"}

    @flask_server.route("/users/<int:user_id>", methods=["GET", "POST"])
    def user_route(user_id):
        return {"user_id": user_id}

    app = flask_server.get_app()
    assert app is not None

    # Check routes were registered
    rules = [rule.rule for rule in app.url_map.iter_rules()]
    assert "/test" in rules
    assert "/users/<int:user_id>" in rules


def test_flask_server_route_with_json_response(flask_server):
    """Test that Flask server auto-converts dict to JSON."""

    @flask_server.route("/json-test")
    def json_test():
        return {"status": "ok", "data": [1, 2, 3]}

    app = flask_server.get_app()
    client = app.test_client()

    response = client.get("/json-test")
    assert response.status_code == 200
    assert response.json == {"status": "ok", "data": [1, 2, 3]}


def test_flask_server_route_with_data_parameter(flask_server):
    """Test Flask server passes request data to handler."""

    @flask_server.route("/create", methods=["POST"])
    def create_handler(data):
        return {"received": data.get("name")}

    app = flask_server.get_app()
    client = app.test_client()

    response = client.post("/create", json={"name": "test"})
    assert response.status_code == 200
    assert response.json == {"received": "test"}


def test_flask_server_middleware(flask_server):
    """Test adding middleware to Flask server."""
    calls = []

    def before_middleware():
        calls.append("before")

    def after_middleware(response):
        calls.append("after")
        return response

    before_middleware.__name__ = "before_request_middleware"
    after_middleware.__name__ = "after_request_middleware"

    flask_server.add_middleware(before_middleware)
    flask_server.add_middleware(after_middleware)

    @flask_server.route("/test")
    def test_route():
        return {"status": "ok"}

    app = flask_server.get_app()
    client = app.test_client()

    response = client.get("/test")
    assert response.status_code == 200
    assert "before" in calls
    assert "after" in calls


def test_flask_server_extra_params(flask_server):
    """Test Flask server with extra configuration parameters."""
    settings = ServerSettings(
        extra_params={
            "JSON_SORT_KEYS": False,
            "MAX_CONTENT_LENGTH": 1024,
        }
    )
    server = ServerFactory.create(ServerType.FLASK, settings)
    app = server.get_app()

    assert app.config["JSON_SORT_KEYS"] is False
    assert app.config["MAX_CONTENT_LENGTH"] == 1024


def test_flask_server_missing_dependency():
    """Test Flask server raises error when Flask not installed."""
    import sys
    from unittest.mock import patch

    # Mock import to simulate Flask not being installed
    with patch.dict(sys.modules, {"flask": None}):
        settings = ServerSettings()
        with pytest.raises(ServerError, match="Flask not installed"):
            # Force reimport to trigger the error
            from axiompy.servers.server import FlaskServer

            FlaskServer(settings)


# ============================================================================
# FastAPI Server Tests
# ============================================================================


@pytest.fixture
def fastapi_server():
    """Fixture providing a FastAPI server instance."""
    pytest.importorskip("fastapi")
    settings = ServerSettings(
        host="0.0.0.0", port=8000, debug=True, extra_params={"title": "Test API"}
    )
    return ServerFactory.create(ServerType.FASTAPI, settings)


def test_fastapi_server_initialization(fastapi_server):
    """Test FastAPI server initializes correctly."""
    assert fastapi_server is not None
    assert fastapi_server.settings.host == "0.0.0.0"
    assert fastapi_server.settings.port == 8000

    app = fastapi_server.get_app()
    assert app is not None
    assert app.title == "Test API"


def test_fastapi_server_route_registration(fastapi_server):
    """Test registering routes with FastAPI server."""

    @fastapi_server.route("/test")
    def test_route():
        return {"message": "test"}

    @fastapi_server.route("/users/{user_id}", methods=["GET", "POST"])
    def user_route(user_id: int):
        return {"user_id": user_id}

    app = fastapi_server.get_app()
    assert app is not None

    # Check routes were registered
    routes = [route.path for route in app.routes]
    assert "/test" in routes
    assert "/users/{user_id}" in routes


def test_fastapi_server_route_with_json_response(fastapi_server):
    """Test that FastAPI server handles JSON responses."""
    from fastapi.testclient import TestClient

    @fastapi_server.route("/json-test")
    def json_test():
        return {"status": "ok", "data": [1, 2, 3]}

    app = fastapi_server.get_app()
    client = TestClient(app)

    response = client.get("/json-test")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "data": [1, 2, 3]}


def test_fastapi_server_route_with_data_parameter(fastapi_server):
    """Test FastAPI server passes request data to handler."""
    from fastapi.testclient import TestClient

    @fastapi_server.route("/create", methods=["POST"])
    def create_handler(data: dict):
        return {"received": data.get("name")}

    app = fastapi_server.get_app()
    client = TestClient(app)

    response = client.post("/create", json={"name": "test"})
    assert response.status_code == 200
    assert response.json()["received"] == "test"


def test_fastapi_server_multiple_methods(fastapi_server):
    """Test FastAPI server with multiple HTTP methods."""
    from fastapi.testclient import TestClient

    @fastapi_server.route("/resource", methods=["GET", "POST", "PUT", "DELETE"])
    def resource_handler():
        return {"message": "success"}

    app = fastapi_server.get_app()
    client = TestClient(app)

    assert client.get("/resource").status_code == 200
    assert client.post("/resource").status_code == 200
    assert client.put("/resource").status_code == 200
    assert client.delete("/resource").status_code == 200


def test_fastapi_server_middleware(fastapi_server):
    """Test adding middleware to FastAPI server."""
    from fastapi.testclient import TestClient

    calls = []

    async def test_middleware(request, call_next):
        calls.append("middleware")
        response = await call_next(request)
        return response

    fastapi_server.add_middleware(test_middleware)

    @fastapi_server.route("/test")
    def test_route():
        return {"status": "ok"}

    app = fastapi_server.get_app()
    client = TestClient(app)

    response = client.get("/test")
    assert response.status_code == 200
    assert "middleware" in calls


def test_fastapi_server_extra_params(fastapi_server):
    """Test FastAPI server with extra configuration parameters."""
    settings = ServerSettings(
        extra_params={
            "title": "Custom API",
            "description": "Test Description",
            "version": "2.0.0",
        }
    )
    server = ServerFactory.create(ServerType.FASTAPI, settings)
    app = server.get_app()

    assert app.title == "Custom API"
    assert app.description == "Test Description"
    assert app.version == "2.0.0"


def test_fastapi_server_missing_dependency():
    """Test FastAPI server raises error when FastAPI not installed."""
    import sys
    from unittest.mock import patch

    # Mock import to simulate FastAPI not being installed
    with patch.dict(sys.modules, {"fastapi": None}):
        settings = ServerSettings()
        with pytest.raises(ServerError, match="FastAPI not installed"):
            from axiompy.servers.server import FastAPIServer

            FastAPIServer(settings)


# ============================================================================
# Integration Tests
# ============================================================================


def test_framework_agnostic_application():
    """Test that the same application works with both Flask and FastAPI."""
    flask = pytest.importorskip("flask")
    fastapi = pytest.importorskip("fastapi")

    # Define a simple application
    class SimpleAPI:
        def __init__(self, server: Server):
            self.server = server
            self._setup_routes()

        def _setup_routes(self):
            self.server.route("/health", methods=["GET"])(self.health)
            self.server.route("/echo", methods=["POST"])(self.echo)

        def health(self):
            return {"status": "healthy"}

        def echo(self, data: dict):
            return {"echo": data}

    # Test with Flask
    flask_settings = ServerSettings()
    flask_server = ServerFactory.create(ServerType.FLASK, flask_settings)
    flask_api = SimpleAPI(flask_server)

    flask_app = flask_server.get_app()
    flask_client = flask_app.test_client()

    response = flask_client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "healthy"

    # Test with FastAPI
    from fastapi.testclient import TestClient

    fastapi_settings = ServerSettings()
    fastapi_server = ServerFactory.create(ServerType.FASTAPI, fastapi_settings)
    fastapi_api = SimpleAPI(fastapi_server)

    fastapi_app = fastapi_server.get_app()
    fastapi_client = TestClient(fastapi_app)

    response = fastapi_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_error_handling_consistency():
    """Test that error handling works consistently across frameworks."""
    flask = pytest.importorskip("flask")
    fastapi = pytest.importorskip("fastapi")

    def setup_server(server: Server):
        @server.route("/error")
        def error_handler():
            return {"error": "Something went wrong"}, 500

        @server.route("/not-found")
        def not_found():
            return {"error": "Not found"}, 404

        return server

    # Test Flask
    flask_server = setup_server(ServerFactory.create(ServerType.FLASK, ServerSettings()))
    flask_app = flask_server.get_app()
    flask_client = flask_app.test_client()

    response = flask_client.get("/error")
    assert response.status_code == 500
    assert "error" in response.json

    response = flask_client.get("/not-found")
    assert response.status_code == 404

    # Test FastAPI
    from fastapi.testclient import TestClient

    fastapi_server = setup_server(ServerFactory.create(ServerType.FASTAPI, ServerSettings()))
    fastapi_app = fastapi_server.get_app()
    fastapi_client = TestClient(fastapi_app)

    response = fastapi_client.get("/error")
    assert response.status_code == 500
    assert "error" in response.json()

    response = fastapi_client.get("/not-found")
    assert response.status_code == 404


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_server_settings_validation():
    """Test ServerSettings with edge case values."""
    # Test with port 0 (should use any available port)
    settings = ServerSettings(port=0)
    assert settings.port == 0

    # Test with empty host
    settings = ServerSettings(host="")
    assert settings.host == ""

    # Test with negative workers (should still accept it, validation up to framework)
    settings = ServerSettings(workers=-1)
    assert settings.workers == -1


def test_mock_server_interface():
    """Test that MockServer implements the full Server interface."""
    settings = ServerSettings()
    server = MockServer(settings)

    # Test route decorator
    @server.route("/test", methods=["GET", "POST"])
    def test_handler():
        return {"test": "ok"}

    assert len(server.routes) == 1
    assert server.routes[0]["path"] == "/test"
    assert server.routes[0]["methods"] == ["GET", "POST"]

    # Test middleware
    def test_middleware():
        pass

    server.add_middleware(test_middleware)
    assert len(server.middlewares) == 1

    # Test run
    assert server.run_called is False
    server.run()
    assert server.run_called is True

    # Test get_app
    assert server.get_app() is None
