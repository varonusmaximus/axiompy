# @!documentation

"""
Metrics Service API Example Package

A comprehensive example of building a RESTful API for managing metric definitions
using axiompy's FastAPI and database abstractions.

Main Components:
    - MetricsRepository: Data access layer
    - MetricsService: Business logic layer
    - MetricsAPI: FastAPI server layer

Usage:
    # Run the server
    python -m examples.metrics.metrics_server

    # Run the demo
    python -m examples.metrics.demo_metrics_api

    # Run tests
    python -m examples.metrics.test_metrics_unit
    python -m examples.metrics.test_metrics_api

For more information, see README.md in this directory.
"""

from examples.metrics.metrics_server import (
    MetricsAPI,
    MetricsRepository,
    MetricsService,
    create_app,
)

__all__ = ["MetricsRepository", "MetricsService", "MetricsAPI", "create_app"]
