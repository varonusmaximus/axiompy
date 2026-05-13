"""Health check endpoints."""

import time
from datetime import datetime

from fastapi import APIRouter

from api.models import HealthCheckResponse
from axiompy.loggers import LoggerFactory

logger = LoggerFactory.create_logger(__name__)
router = APIRouter()

# Track application startup time
_start_time = time.time()


@router.get("/health", response_model=HealthCheckResponse, tags=["health"])
async def health_check():
    """
    Health check endpoint.

    Returns:
        HealthCheckResponse: Current health status
    """
    uptime = time.time() - _start_time

    logger.debug("Health check requested")

    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        message="Service is healthy",
        uptime_seconds=uptime,
    )
