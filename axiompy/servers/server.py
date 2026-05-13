"""
Web server abstraction layer with support for Flask and FastAPI.

Provides a consistent interface for creating web servers with different frameworks
through an abstract base class and concrete implementations. Supports Flask and FastAPI
with automatic dependency management and unified error handling.

Key Benefits:
    - Minimal external dependencies (frameworks are optional)
    - Consistent API across server types
    - Easy mocking for unit testing
    - Dependency injection-friendly design
    - Framework-agnostic application code

Quick Example:
    >>> from axiompy.servers import ServerFactory, ServerType, ServerSettings
    >>>
    >>> settings = ServerSettings(host="0.0.0.0", port=8000)
    >>> server = ServerFactory.create(ServerType.FASTAPI, settings)
    >>>
    >>> @server.route("/hello", methods=["GET"])
    >>> def hello():
    ...     return {"message": "Hello, World!"}
    >>>
    >>> server.run()

For comprehensive examples, see:
    - examples/servers/server_usage.py - Production usage examples
    - examples/servers/server_testing.py - Unit testing patterns
"""

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from axiompy.loggers import LoggerFactory
from axiompy.validators import ensure_in_range

logger = LoggerFactory.create_logger(__name__)


class ServerType(Enum):
    """Supported web server frameworks."""

    FLASK = "flask"
    FASTAPI = "fastapi"


@dataclass
class ServerSettings:
    """
    Web server configuration.

    Attributes:
        host: Server host address (default: "127.0.0.1")
        port: Server port number (default: 8000)
        debug: Enable debug mode (default: False)
        reload: Enable auto-reload on code changes (default: False)
        workers: Number of worker processes (default: 1)
        extra_params: Additional framework-specific parameters
    """

    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    workers: int = 1
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate settings after initialization."""
        # Note: host can be empty string (allowed for testing/edge cases)
        # Port 0 is valid for automatic port selection, so allow 0-65535
        ensure_in_range(self.port, 0, 65535, f"port {self.port} must be between 0 and 65535")
        # Note: workers validation is left to the framework, edge cases allowed for testing

        # Warning if reload is True with multiple workers (not compatible)
        if self.reload and self.workers > 1:
            logger.warning(
                "reload=True with workers>1 is not supported; reload mode overrides workers to 1"
            )

        logger.debug("ServerSettings validated successfully")


class ServerError(Exception):
    """Base exception for server errors."""

    pass


# Type alias for route handlers
RouteHandler = Callable[..., Any]


class Server(ABC):
    """
    Abstract base class for web servers.

    All server implementations provide a consistent interface for defining routes,
    middleware, and running the server.

    Design Advantages:
        - Dependency Injection: Services depend on interface, not implementations
        - Easy Testing: Create simple mocks without real servers
        - Swappable: Switch frameworks without changing application code
        - Consistent: Same error types across all implementations

    Example Usage:
        >>> class MyAPI:
        ...     def __init__(self, server: Server):
        ...         self.server = server
        ...         self._setup_routes()
        ...
        ...     def _setup_routes(self):
        ...         self.server.route("/users", methods=["GET"])(self.get_users)
        ...         self.server.route("/users", methods=["POST"])(self.create_user)
        ...
        ...     def get_users(self):
        ...         return [{"id": 1, "name": "Alice"}]
        ...
        ...     def create_user(self, data: dict):
        ...         return {"id": 2, "name": data["name"]}

        # Works with any Server implementation (Flask, FastAPI, mock, etc.)
    """

    def __init__(self, settings: ServerSettings):
        """
        Initialize server instance.

        Args:
            settings: Server configuration
        """
        self.settings = settings
        self._app = None

    @abstractmethod
    def route(
        self,
        path: str,
        methods: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Callable[[RouteHandler], RouteHandler]:
        """
        Decorator to register a route handler.

        Args:
            path: URL path for the route (e.g., "/users", "/api/items/{item_id}")
            methods: HTTP methods (e.g., ["GET", "POST"]). Default: ["GET"]
            **kwargs: Additional framework-specific route options

        Returns:
            Decorator function that registers the handler

        Example:
            >>> @server.route("/hello", methods=["GET"])
            >>> def hello():
            ...     return {"message": "Hello"}
        """
        pass

    @abstractmethod
    def add_middleware(self, middleware: Callable, **kwargs: Any) -> None:
        """
        Add middleware to the server.

        Args:
            middleware: Middleware function or class
            **kwargs: Additional framework-specific middleware options
        """
        pass

    @abstractmethod
    def run(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """
        Start the server.

        Args:
            host: Override host from settings
            port: Override port from settings
            **kwargs: Additional framework-specific run options
        """
        pass

    @abstractmethod
    def get_app(self) -> Any:
        """
        Get the underlying framework application object.

        Returns:
            Flask app, FastAPI app, etc.

        This is useful for:
        - Advanced framework-specific configuration
        - Testing with framework test clients
        - Integration with framework-specific tools
        """
        pass


class FlaskServer(Server):
    """Flask web server implementation."""

    def __init__(self, settings: ServerSettings):
        super().__init__(settings)

        try:
            from flask import Flask, jsonify, request

            self._flask = Flask
            self._request = request
            self._jsonify = jsonify
        except ImportError:
            raise ServerError("Flask not installed. Install with: pip install flask")

        self._app = self._flask(__name__)
        self._app.config["DEBUG"] = settings.debug

        # Apply extra parameters
        for key, value in settings.extra_params.items():
            self._app.config[key] = value

        logger.info("Flask server initialized")

    def route(
        self,
        path: str,
        methods: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Callable[[RouteHandler], RouteHandler]:
        """Register a Flask route."""
        if methods is None:
            methods = ["GET"]

        def decorator(handler: RouteHandler) -> RouteHandler:
            # Wrap the handler to automatically jsonify dict/list returns
            def wrapped_handler(*args: Any, **handler_kwargs: Any) -> Any:
                # Check if handler expects request data
                sig = inspect.signature(handler)
                params = sig.parameters

                # If handler has a 'data' parameter, pass request data
                if "data" in params:
                    if self._request.is_json:
                        handler_kwargs["data"] = self._request.get_json()
                    elif self._request.form:
                        handler_kwargs["data"] = self._request.form.to_dict()
                    elif self._request.args:
                        handler_kwargs["data"] = self._request.args.to_dict()

                result = handler(*args, **handler_kwargs)

                # Auto-jsonify dict and list responses
                # Handle tuples like (data, status_code) or (data, status_code, headers)
                if isinstance(result, tuple):
                    if len(result) >= 1 and isinstance(result[0], dict | list):
                        # Jsonify the data part and return the tuple
                        return (self._jsonify(result[0]),) + result[1:]
                    return result
                elif isinstance(result, dict | list):
                    return self._jsonify(result)
                return result

            # Preserve original function name for Flask endpoint
            wrapped_handler.__name__ = handler.__name__
            wrapped_handler.__doc__ = handler.__doc__

            # Register with Flask
            self._app.route(path, methods=methods, **kwargs)(wrapped_handler)
            logger.debug(f"Registered Flask route: {methods} {path}")
            return handler

        return decorator

    def add_middleware(self, middleware: Callable, **kwargs: Any) -> None:
        """Add Flask middleware (before_request, after_request, etc.)."""
        # Flask middleware is typically added as decorators
        # Support common patterns
        if hasattr(middleware, "__name__"):
            if "before" in middleware.__name__.lower():
                self._app.before_request(middleware)
            elif "after" in middleware.__name__.lower():
                self._app.after_request(middleware)
            else:
                # Default to before_request
                self._app.before_request(middleware)
        else:
            self._app.before_request(middleware)

        logger.debug("Added Flask middleware")

    def run(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Start the Flask server."""
        host = host or self.settings.host
        port = port or self.settings.port

        logger.info(f"Starting Flask server on {host}:{port}")
        self._app.run(
            host=host,
            port=port,
            debug=self.settings.debug,
            **kwargs,
        )

    def get_app(self) -> Any:
        """Get the Flask application instance."""
        return self._app


class FastAPIServer(Server):
    """FastAPI web server implementation."""

    def __init__(self, settings: ServerSettings):
        super().__init__(settings)

        try:
            from fastapi import FastAPI, Request
            from fastapi.responses import JSONResponse

            self._fastapi = FastAPI
            self._request_cls = Request
            self._json_response = JSONResponse
        except ImportError:
            raise ServerError("FastAPI not installed. Install with: pip install fastapi uvicorn")

        # Create FastAPI app
        extra_params = dict(settings.extra_params)
        if "title" not in extra_params:
            extra_params["title"] = "AxiomPy API"
        if "debug" not in extra_params:
            extra_params["debug"] = settings.debug

        self._app = self._fastapi(**extra_params)
        logger.info("FastAPI server initialized")

    def route(
        self,
        path: str,
        methods: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Callable[[RouteHandler], RouteHandler]:
        """Register a FastAPI route."""
        if methods is None:
            methods = ["GET"]

        def decorator(handler: RouteHandler) -> RouteHandler:
            # Register route for each HTTP method
            for method in methods:
                method_lower = method.lower()

                # Get the appropriate decorator (get, post, put, delete, etc.)
                if hasattr(self._app, method_lower):
                    route_decorator = getattr(self._app, method_lower)

                    # Check if handler expects request data
                    sig = inspect.signature(handler)
                    params = sig.parameters

                    if "data" in params:
                        # Create a wrapper that accepts Request or body dict
                        async def wrapped_handler(
                            request: self._request_cls = None,
                            data: dict = None,
                        ) -> Any:
                            # If data not provided but request is, extract from request
                            if data is None and request is not None:
                                try:
                                    data = await request.json()
                                except Exception:
                                    data = {}

                            result = handler(data=data)

                            # Handle tuple returns like (data, status_code)
                            if isinstance(result, tuple) and len(result) >= 2:
                                return self._json_response(content=result[0], status_code=result[1])
                            return result

                        route_decorator(path, **kwargs)(wrapped_handler)
                    else:
                        # No data parameter, use handler as-is
                        if inspect.iscoroutinefunction(handler):
                            route_decorator(path, **kwargs)(handler)
                        else:
                            # Wrap sync function for async context
                            # Extract path parameters from the handler signature
                            handler_sig = inspect.signature(handler)
                            handler_params = list(handler_sig.parameters.keys())

                            # Create a wrapper with the same signature as the handler
                            # This allows FastAPI to correctly extract path/query parameters
                            def make_wrapper(handler_func, param_names):
                                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                                    result = handler_func(*args, **kwargs)
                                    # Handle tuple returns like (data, status_code)
                                    if isinstance(result, tuple) and len(result) >= 2:
                                        return self._json_response(
                                            content=result[0], status_code=result[1]
                                        )
                                    return result

                                # Copy the signature from the original handler
                                async_wrapper.__signature__ = handler_sig
                                async_wrapper.__name__ = handler_func.__name__
                                return async_wrapper

                            wrapper = make_wrapper(handler, handler_params)
                            route_decorator(path, **kwargs)(wrapper)

                    logger.debug(f"Registered FastAPI route: {method} {path}")

            return handler

        return decorator

    def add_middleware(self, middleware: Callable, **kwargs: Any) -> None:
        """Add FastAPI middleware."""
        self._app.middleware("http")(middleware)
        logger.debug("Added FastAPI middleware")

    def run(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Start the FastAPI server using uvicorn."""
        try:
            import uvicorn
        except ImportError:
            raise ServerError("Uvicorn not installed. Install with: pip install uvicorn")

        host = host or self.settings.host
        port = port or self.settings.port

        logger.info(f"Starting FastAPI server on {host}:{port}")

        uvicorn_kwargs = {
            "host": host,
            "port": port,
            "reload": self.settings.reload,
            "workers": self.settings.workers if not self.settings.reload else 1,
            **kwargs,
        }

        uvicorn.run(self._app, **uvicorn_kwargs)

    def get_app(self) -> Any:
        """Get the FastAPI application instance."""
        return self._app


class ServerFactory:
    """
    Factory for creating server instances.

    Main entry point for creating web servers. The factory automatically creates
    the appropriate server implementation based on the specified type.

    Usage:
        >>> settings = ServerSettings(host="0.0.0.0", port=8000)
        >>> server = ServerFactory.create(ServerType.FASTAPI, settings)
        >>>
        >>> @server.route("/api/health")
        >>> def health():
        ...     return {"status": "healthy"}
        >>>
        >>> server.run()

    Testing:
        For unit tests, create mock implementations directly:

        >>> class MockServer(Server):
        ...     def route(self, path, methods=None, **kwargs):
        ...         def decorator(handler): return handler
        ...         return decorator
        ...     def add_middleware(self, middleware, **kwargs): pass
        ...     def run(self, host=None, port=None, **kwargs): pass
        ...     def get_app(self): return None
        >>>
        >>> mock = MockServer(ServerSettings())
        >>> api = MyAPI(mock)  # Inject mock directly
    """

    _server_map = {
        ServerType.FLASK: FlaskServer,
        ServerType.FASTAPI: FastAPIServer,
    }

    @classmethod
    def create(cls, server_type: ServerType, settings: ServerSettings) -> Server:
        """
        Create a server instance.

        Args:
            server_type: Type of server to create
            settings: Configuration for the server

        Returns:
            Server instance

        Raises:
            ValueError: If server type is not supported
            ServerError: If instance creation fails
        """
        if server_type not in cls._server_map:
            raise ValueError(
                f"Unsupported server type: {server_type}. Supported: {list(cls._server_map.keys())}"
            )

        server_class = cls._server_map[server_type]
        try:
            return server_class(settings)
        except ServerError:
            # Let server-specific errors pass through unchanged
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise ServerError(f"Failed to create {server_type.value} server: {str(e)}")

    @classmethod
    def register_server(cls, server_type: ServerType, server_class: type) -> None:
        """
        Register a custom server implementation.

        Allows extending the factory with new server types.

        Args:
            server_type: Server type enum value
            server_class: Class implementing Server interface

        Raises:
            TypeError: If server_class doesn't inherit from Server
        """
        if not issubclass(server_class, Server):
            raise TypeError("server_class must inherit from Server")

        cls._server_map[server_type] = server_class
        logger.info(f"Registered custom server: {server_type.value}")
