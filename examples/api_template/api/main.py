# @!documentation

"""
Production-Ready API using AxiomPy Building Blocks

Demonstrates all axiompy best practices:
- Railway-Oriented Programming with Result types
- Input validation with fail-fast semantics
- Custom error hierarchy with recovery hints
- Structured logging with execution timing
- Resilience with retry logic
- Clean layered architecture with dependency injection
- Framework-agnostic via ServerFactory abstraction

Architecture (bottom-up):
1. Database Layer: axiompy DatabaseFactory (SQLITE, POSTGRES, MYSQL, DYNAMODB)
2. Repository Layer: ResourceRepository (data access)
3. Domain Layer: Resource entity + ResourceService (business logic)
4. HTTP Layer: ResourceHandlers (adapter) + ResourceModel (HTTP adapter)
5. Routes: Thin wrappers calling handlers
6. Server Layer: axiompy ServerFactory (FastAPI/Flask abstraction)

Dependency Injection Chain:
    Database → Repository → Service → Handlers → Routes → Server
"""

import logging
import os

from services.repository import ResourceRepository
from services.resource_service import ResourceService

from api.config.settings import get_settings
from api.routes import health
from api.routes.resources import ResourceRoutes, setup_routes
from api.routes.resources import router as resources_router
from axiompy.io.database import DatabaseFactory, DatabaseSettings, DatabaseType
from axiompy.loggers import LoggerFactory
from axiompy.servers import (
    ServerFactory,
    ServerSettings,
    ServerType,
    register_fastapi_http_response_handler,
)

# Initialize logger
logger = LoggerFactory.create_logger(__name__)
settings = get_settings()

# Configure logging level
logging.getLogger().setLevel(settings.log_level)

# Create server via ServerFactory abstraction (supports FastAPI, Flask, others)
server_settings = ServerSettings(
    host=settings.api_host,
    port=settings.api_port,
    debug=settings.debug,
    workers=settings.workers,
    extra_params={
        "title": "AxiomPy Template API",
        "description": "Production-ready API template using axiompy building blocks",
        "version": "1.0.0",
    },
)

# Create server instance via factory (framework-agnostic)
server = ServerFactory.create(ServerType.FASTAPI, server_settings)

# Get the underlying FastAPI app for router registration
# This gives us framework-agnostic code while still supporting FastAPI features
#
# NOTE: Module-level `app` is acceptable here because this is the application
# entry point (composition root), not a reusable library module. For reusable
# modules in axiompy/*, avoid module-level globals - use Factory pattern instead.
# See AGENTS.md "Global Variables" anti-pattern.
app = server.get_app()
register_fastapi_http_response_handler(app)

# Include health routes
app.include_router(health.router, prefix="/api/v1", tags=["health"])


@app.on_event("startup")
async def startup_event():
    """
    Initialize application on startup.

    Wires up the complete dependency injection chain:
    1. Create database via DatabaseFactory
    2. Create repository (depends on database)
    3. Create service (depends on repository)
    4. Create handlers (depends on service)
    5. Configure routes to use handlers
    """
    logger.info("Starting AxiomPy Template API")
    logger.info(f"API Host: {settings.api_host}")
    logger.info(f"API Port: {settings.api_port}")
    logger.info(f"Log Level: {settings.log_level}")

    try:
        # 1. Create database
        logger.info("Initializing database...")
        db_settings = DatabaseSettings(
            database=os.getenv("DB_NAME", "api.db"),
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            username=os.getenv("DB_USER", "user"),
            password=os.getenv("DB_PASSWORD", "password"),
        )

        # Use SQLite for demo (comment out and use POSTGRES for production)
        database = DatabaseFactory.create(DatabaseType.SQLITE, db_settings)
        logger.info("Database initialized: SQLite")

        # For production, use PostgreSQL:
        # database = DatabaseFactory.create(DatabaseType.POSTGRES, db_settings)
        # Or MySQL:
        # database = DatabaseFactory.create(DatabaseType.MYSQL, db_settings)

        # 2. Create repository (depends on database)
        logger.info("Initializing repository...")
        repository = ResourceRepository(database=database)

        # 3. Create service (depends on repository)
        logger.info("Initializing service...")
        service = ResourceService(repository=repository)

        # 4. Setup resource routes with service dependency
        logger.info("Setting up resource routes...")
        resource_routes = ResourceRoutes(service=service)
        setup_routes(resources_router, resource_routes)
        app.include_router(resources_router, prefix="/api/v1", tags=["resources"])

        logger.info("✅ Application startup complete - all layers initialized")

    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {str(e)}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down AxiomPy Template API")


@app.get("/", tags=["root"])
async def root():
    """Root endpoint returning API info."""
    return {
        "name": "AxiomPy Template API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
    }


if __name__ == "__main__":
    # Run via ServerFactory abstraction (framework-agnostic)
    # This works with FastAPI, Flask, or any registered server type
    server.run(
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.workers,
        reload=settings.debug,
    )
