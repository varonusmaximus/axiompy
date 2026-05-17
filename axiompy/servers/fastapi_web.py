"""
FastAPI integration for axiompy.web HttpResponseError.

Requires the ``[servers]`` extra (fastapi, uvicorn). FastAPI is imported lazily
inside each function so ``import axiompy.servers.fastapi_web`` does not require
FastAPI until a helper is called.
"""

from __future__ import annotations

from typing import Any

from axiompy.web import HttpResponseError


def raise_fastapi_http_exception(err: HttpResponseError) -> None:
    """
    Convert HttpResponseError to FastAPI HTTPException and re-raise.

    Args:
        err: Error raised by ResultErrorHandler.handle_error

    Raises:
        fastapi.HTTPException: With matching status_code and detail
    """
    from fastapi import HTTPException

    raise HTTPException(status_code=err.status_code, detail=err.detail)


def register_fastapi_http_response_handler(app: Any) -> None:
    """
    Register a FastAPI exception handler for HttpResponseError.

    Call once after creating the FastAPI app so routes can use
    ResultErrorHandler.handle_error without per-route try/except.

    Args:
        app: FastAPI application instance
    """
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.exception_handler(HttpResponseError)
    async def _http_response_error_handler(
        _request: Request, exc: HttpResponseError
    ) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
