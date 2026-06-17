# @!testing

"""Tests for FastAPI bridge helpers in axiompy.servers.fastapi_web."""

import pytest

from axiompy.result import Err
from axiompy.servers.fastapi_web import (
    raise_fastapi_http_exception,
    register_fastapi_http_response_handler,
)
from axiompy.web import HttpResponseError, ResultErrorHandler


class TestFastapiWebBridge:
    """FastAPI integration for HttpResponseError (requires fastapi extra)."""

    def test_raise_fastapi_http_exception(self):
        pytest.importorskip("fastapi")
        from fastapi import HTTPException

        err = HttpResponseError(
            status_code=404,
            detail={"error": "missing", "error_code": "NOT_FOUND"},
        )

        with pytest.raises(HTTPException) as exc_info:
            raise_fastapi_http_exception(err)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == err.detail

    def test_register_fastapi_http_response_handler(self):
        fastapi = pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient

        app = fastapi.FastAPI()
        register_fastapi_http_response_handler(app)

        @app.get("/fail")
        def fail() -> None:
            ResultErrorHandler.handle_error(Err("Resource 1 not found"))

        client = TestClient(app)
        response = client.get("/fail")

        assert response.status_code == 404
        assert response.json()["error_code"] == "NOT_FOUND"
