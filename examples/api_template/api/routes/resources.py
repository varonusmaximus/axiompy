"""
Resource endpoints - HTTP adapter layer between FastAPI and domain layer.

Uses railway-oriented programming (Result[T, E]) via axiompy.web for elegant error handling.

RAILWAY-ORIENTED PROGRAMMING (ROP) PATTERN
===========================================

This module demonstrates ROP using axiompy.web helpers for:
- Input validation with Result[T, E] returns
- Error handling and conversion to HTTP responses
- Generic pagination utilities
- 5-step adapter pattern for HTTP routes

The key insight: instead of throwing exceptions or returning None, we wrap values in Result types.

Two tracks:
- Success track (Ok): Carries the successful value
- Failure track (Err): Carries the error message

The magic: .map() and .then() automatically short-circuit on errors!

Example: If validation fails with ResultValidator.validate_pagination(), the rest of the chain is skipped.
"""

from fastapi import APIRouter, Body, Query
from services.resource_service import ResourceService

from api.models import ResourceModel
from axiompy.decorators import CatchAndLog
from axiompy.loggers import LoggerFactory
from axiompy.result import Ok
from axiompy.web import (
    PaginationHelper,
    ResultConverter,
    ResultErrorHandler,
    ResultValidator,
)

logger = LoggerFactory.create_logger(__name__)
router = APIRouter()


class ResourceRoutes:
    """
    Class-based routes for resource endpoints.

    Receives ResourceService via dependency injection.
    Uses axiompy.web helpers for railway-oriented validation pipelines.

    All complex validation logic is delegated to axiompy.web, keeping routes
    focused on orchestration rather than implementation details.
    """

    def __init__(self, service: ResourceService):
        """Initialize routes with service dependency."""
        self.service = service
        logger.info("ResourceRoutes initialized")

    # ============================================================================
    # Route Handlers (Railway-Oriented with Result Composition)
    # ============================================================================

    @CatchAndLog(
        logger=logger,
        reraise=False,
        exceptions=(Exception,),
        default_return=({"error": "Internal server error"}, 500),
    )
    async def create_resource(self, data: dict):
        """
        POST /api/v1/resources - Create a new resource.

        Railway-oriented pipeline:
        Parse HTTP → Domain → Service → HTTP → Response

        Uses ResultValidator.parse_model() from axiompy.web to handle validation.
        """
        # Railway-oriented validation pipeline
        result = (
            ResultValidator.parse_model(data, ResourceModel)
            .map(lambda model: model.to_domain())
            .then(lambda resource: Ok(self.service.create_resource(resource)))
            .map(lambda created: ResourceModel.from_domain(created))
            .map(
                lambda response_model: {
                    "resource": response_model.model_dump(mode="json"),
                    "message": "Resource created",
                }
            )
        )

        # Handle result: Unwrap success or raise HTTP error
        if result.is_ok():
            logger.info("Created resource successfully")
            return result.unwrap()
        else:
            logger.error(f"Failed to create resource: {result.get_error()}")
            ResultErrorHandler.handle_error(result, default_status=400)

    @CatchAndLog(
        logger=logger,
        reraise=False,
        exceptions=(Exception,),
        default_return=({"error": "Internal server error"}, 500),
    )
    async def get_resource(self, resource_id: int):
        """
        GET /api/v1/resources/{resource_id} - Get a specific resource.

        Shows how to handle "not found" in the Result pipeline:
        - Validate ID using ResultValidator.validate_id()
        - Call service (returns Resource or None)
        - Convert None to Err using ResultConverter.or_not_found()
        - If found, transform through domain → HTTP and return
        - If not found, error track handles it via ResultErrorHandler
        """
        # Railway-oriented validation pipeline
        result = (
            ResultValidator.validate_id(resource_id)
            .then(
                lambda rid: ResultConverter.or_not_found(
                    self.service.get_resource(rid), "Resource", rid
                )
            )
            .map(lambda resource: ResourceModel.from_domain(resource))
            .map(lambda response_model: {"resource": response_model.model_dump(mode="json")})
        )

        # Handle result: Unwrap success or raise HTTP error
        if result.is_ok():
            logger.info(f"Retrieved resource: {resource_id}")
            return result.unwrap()
        else:
            ResultErrorHandler.handle_error(result)

    @CatchAndLog(
        logger=logger,
        reraise=False,
        exceptions=(Exception,),
        default_return=({"error": "Internal server error"}, 500),
    )
    async def list_resources(self, page: int = 1, per_page: int = 10):
        """
        GET /api/v1/resources - List all resources with pagination.

        Pipeline:
        1. Validate pagination params using ResultValidator.validate_pagination()
        2. Get all resources from service
        3. Paginate and format response using PaginationHelper.paginate_models()

        Note: .map(lambda _: ...) ignores the validation result and moves on.
        The underscore _ means "I don't need this value, just continue if success".
        """
        # Railway-oriented validation pipeline
        result = (
            ResultValidator.validate_pagination(page, per_page)
            .map(lambda _: self.service.list_resources())
            .map(lambda all_resources: self._paginate_resources(all_resources, page, per_page))
        )

        # Handle result: Unwrap success or raise HTTP error
        if result.is_ok():
            logger.info(f"Listed resources: page={page}, per_page={per_page}")
            return result.unwrap()
        else:
            logger.error(f"Failed to list resources: {result.get_error()}")
            ResultErrorHandler.handle_error(result, default_status=400)

    def _paginate_resources(self, all_resources, page: int, per_page: int) -> dict:
        """
        Paginate resources and format response.

        This is a pure transformation function (not Result-returning).
        It's called via .map() in the pipeline to transform data.
        If _paginate_resources raises an exception, @CatchAndLog catches it and returns a 500.

        Delegates to PaginationHelper.paginate_models() from axiompy.web.
        """
        # Convert domain entities to HTTP models
        resource_models = [ResourceModel.from_domain(r) for r in all_resources]

        # Use PaginationHelper from axiompy.web
        paginated = PaginationHelper.paginate_models(resource_models, page, per_page)

        return {"resources": paginated["items"], "pagination": paginated["pagination"]}

    @CatchAndLog(
        logger=logger,
        reraise=False,
        exceptions=(Exception,),
        default_return=({"error": "Internal server error"}, 500),
    )
    async def update_resource(self, resource_id: int, data: dict):
        """
        PUT /api/v1/resources/{resource_id} - Update a resource.

        More complex pipeline with nested .then() calls:
        - Validate resource ID first
        - Then parse and prepare request body
        - Then call service with prepared resource
        - Finally transform response

        Key: Each .then() can return a new Result chain, allowing us to compose
        multiple validation steps without nesting try/except blocks.
        """
        # Railway-oriented validation pipeline
        result = (
            ResultValidator.validate_id(resource_id)
            .then(
                lambda rid: ResultValidator.parse_model(data, ResourceModel)
                .map(lambda model: model.to_domain())
                .map(lambda resource: self._set_id(resource, rid))
            )
            .then(
                lambda resource: ResultConverter.or_not_found(
                    self.service.update_resource(resource_id, resource), "Resource", resource_id
                )
            )
            .map(lambda updated: ResourceModel.from_domain(updated))
            .map(
                lambda response_model: {
                    "resource": response_model.model_dump(mode="json"),
                    "message": "Resource updated",
                }
            )
        )

        # Handle result: Unwrap success or raise HTTP error
        if result.is_ok():
            logger.info(f"Updated resource: {resource_id}")
            return result.unwrap()
        else:
            ResultErrorHandler.handle_error(result)

    def _set_id(self, resource, resource_id: int):
        """Set resource ID for update operation."""
        resource.id = resource_id
        return resource

    @CatchAndLog(
        logger=logger,
        reraise=False,
        exceptions=(Exception,),
        default_return=({"error": "Internal server error"}, 500),
    )
    async def delete_resource(self, resource_id: int):
        """
        DELETE /api/v1/resources/{resource_id} - Delete a resource.

        Simple pipeline:
        - Validate ID using ResultValidator.validate_id()
        - Delete via service (returns True/False)
        - Convert result to Err if service returned None/False using ResultConverter.or_not_found()
        - Return None for 204 No Content response
        """
        # Railway-oriented validation pipeline
        result = (
            ResultValidator.validate_id(resource_id)
            .then(
                lambda rid: ResultConverter.or_not_found(
                    self.service.delete_resource(rid), "Resource", rid
                )
            )
            .map(lambda _: None)  # 204 No Content
        )

        # Handle result: Unwrap success or raise HTTP error
        if result.is_ok():
            logger.info(f"Deleted resource: {resource_id}")
            return result.unwrap()
        else:
            ResultErrorHandler.handle_error(result)


def setup_routes(router: APIRouter, routes: ResourceRoutes) -> None:
    """
    Setup resource routes on the router.

    Called from api/main.py to wire routes with service dependency.

    Args:
        router: FastAPI APIRouter to register routes on
        routes: ResourceRoutes instance with injected service
    """

    @router.post("/resources", status_code=201)
    async def create(data: dict = Body(...)):
        """POST /api/v1/resources"""
        return await routes.create_resource(data)

    @router.get("/resources/{resource_id}")
    async def get(resource_id: int):
        """GET /api/v1/resources/{resource_id}"""
        return await routes.get_resource(resource_id)

    @router.get("/resources")
    async def list_all(page: int = Query(1, ge=1), per_page: int = Query(10, ge=1, le=100)):
        """GET /api/v1/resources"""
        return await routes.list_resources(page, per_page)

    @router.put("/resources/{resource_id}")
    async def update(resource_id: int, data: dict = Body(...)):
        """PUT /api/v1/resources/{resource_id}"""
        return await routes.update_resource(resource_id, data)

    @router.delete("/resources/{resource_id}", status_code=204)
    async def delete(resource_id: int):
        """DELETE /api/v1/resources/{resource_id}"""
        return await routes.delete_resource(resource_id)
