# @!documentation

"""Shared fixtures for integration tests."""

import asyncio

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with startup event called."""
    from api.main import app

    # Create client
    client = TestClient(app)

    # Manually trigger startup event for testing
    # (TestClient doesn't automatically call async startup events)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        app.router.lifespan_context(None).__aenter__()
        if hasattr(app.router, "lifespan_context")
        else None
    )

    # Alternative: Call the startup event directly
    for handler in app.router.on_startup:
        loop.run_until_complete(handler()) if asyncio.iscoroutinefunction(handler) else handler()

    return client
