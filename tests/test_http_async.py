"""Tests for async HTTP batch client (axiompy.io.http_async)."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import threading
import time
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import AsyncClient as RealHttpxAsyncClient

from axiompy.io.http import HTTPClientFactory, HTTPClientSettings, HTTPTransport
from axiompy.servers import ServerFactory, ServerSettings, ServerType
from axiompy.io.http_async import (
    AsyncHTTPClient,
    AsyncHTTPClientFactory,
    HTTPBatchResponses,
    HTTPExchangeResult,
    HTTPExchangeStatus,
    HTTPMethod,
    MockAsyncHTTPClient,
    _parse_response_body,
    _response_to_result,
)


def _make_transport_json(data: dict) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=json.dumps(data).encode(),
        )

    return httpx.MockTransport(handler)


class TestHTTPMethodShim:
    """HTTPMethod is stdlib on 3.11+ or shim on 3.10."""

    def test_method_values(self) -> None:
        assert HTTPMethod.GET.value == "GET"
        assert HTTPMethod.POST.value == "POST"


class TestHTTPExchangeResult:
    def test_unwrap_order(self) -> None:
        r1 = HTTPExchangeResult(status=HTTPExchangeStatus.COMPLETE, results={"a": 1})
        r2 = HTTPExchangeResult(status=HTTPExchangeStatus.TIMEOUT, error_message="t")
        batch = HTTPBatchResponses((r1, r2))
        assert batch.unwrap() == (r1, r2)


class TestAsyncHTTPClientFactory:
    def test_create_returns_async_client(self) -> None:
        settings = HTTPClientSettings(timeout_secs=5)
        client = AsyncHTTPClientFactory.create(settings)
        assert isinstance(client, AsyncHTTPClient)
        assert client.settings.timeout_secs == 5

    def test_http_client_factory_async_transport(self) -> None:
        client = HTTPClientFactory.create(
            transport=HTTPTransport.ASYNC,
            settings=HTTPClientSettings(timeout_secs=10),
        )
        assert isinstance(client, AsyncHTTPClient)

    def test_http_client_factory_sync_default(self) -> None:
        client = HTTPClientFactory.create(timeout_secs=15)
        from axiompy.io.http import HTTPClient

        assert isinstance(client, HTTPClient)


class TestHTTPCallBatchFluent:
    """Integration-style tests with MockTransport."""

    def test_single_get_complete(self) -> None:
        transport = _make_transport_json({"hello": "world"})

        async def run() -> HTTPBatchResponses:
            client = AsyncHTTPClient(HTTPClientSettings(timeout_secs=30))
            with patch("axiompy.io.http_async.httpx.AsyncClient") as mock_cls:

                def _client_factory(*args: object, **kwargs: object) -> httpx.AsyncClient:
                    merged = {**kwargs, "transport": transport}
                    return RealHttpxAsyncClient(*args, **merged)

                mock_cls.side_effect = _client_factory
                batch = (
                    client.new_batch()
                    .add(HTTPMethod.GET, "https://example.test/api")
                    .header("X-Test", "1")
                    .commit()
                )
                return await batch.dispatch_and_join()

        responses = asyncio.run(run())
        (r1,) = responses.unwrap()
        assert r1.status == HTTPExchangeStatus.COMPLETE
        assert r1.results == {"hello": "world"}
        assert r1.http_status_code == 200

    def test_two_slots_order_and_merge_headers(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"content-type": "application/json"},
                content=json.dumps({"path": str(request.url.path)}).encode(),
            )

        transport = httpx.MockTransport(handler)

        async def run() -> HTTPBatchResponses:
            client = AsyncHTTPClient(HTTPClientSettings(timeout_secs=30)).add_header(
                "X-Global", "g"
            )
            with patch("axiompy.io.http_async.httpx.AsyncClient") as mock_cls:

                def _client_factory(*args: object, **kwargs: object) -> httpx.AsyncClient:
                    merged = {**kwargs, "transport": transport}
                    return RealHttpxAsyncClient(*args, **merged)

                mock_cls.side_effect = _client_factory
                batch = (
                    client.new_batch()
                    .add(HTTPMethod.GET, "https://example.test/a")
                    .header("X-Slot", "a")
                    .commit()
                    .add(HTTPMethod.GET, "https://example.test/b")
                    .header("X-Slot", "b")
                    .commit()
                )
                return await batch.dispatch_and_join()

        r1, r2 = asyncio.run(run()).unwrap()
        assert r1.results["path"] == "/a"
        assert r2.results["path"] == "/b"

    def test_timeout_maps_to_status(self) -> None:
        """Slot outcome TIMEOUT (as produced when httpx raises TimeoutException)."""

        async def run() -> HTTPBatchResponses:
            client = AsyncHTTPClient(HTTPClientSettings(timeout_secs=30))
            batch = (
                client.new_batch(timeout_secs=30)
                .add(HTTPMethod.GET, "https://example.test/slow")
                .commit()
            )
            with patch.object(
                batch,
                "_execute_one",
                new=AsyncMock(
                    return_value=HTTPExchangeResult(
                        status=HTTPExchangeStatus.TIMEOUT,
                        error_message="Request timed out",
                    )
                ),
            ):
                return await batch.dispatch_and_join()

        (r1,) = asyncio.run(run()).unwrap()
        assert r1.status == HTTPExchangeStatus.TIMEOUT

    def test_http_error_status_failed(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="unavailable")

        transport = httpx.MockTransport(handler)

        async def run() -> HTTPBatchResponses:
            client = AsyncHTTPClient(HTTPClientSettings(timeout_secs=5))
            with patch("axiompy.io.http_async.httpx.AsyncClient") as mock_cls:

                def _client_factory(*args: object, **kwargs: object) -> httpx.AsyncClient:
                    merged = {**kwargs, "transport": transport}
                    return RealHttpxAsyncClient(*args, **merged)

                mock_cls.side_effect = _client_factory
                batch = client.new_batch().add(HTTPMethod.GET, "https://x.test").commit()
                return await batch.dispatch_and_join()

        (r1,) = asyncio.run(run()).unwrap()
        assert r1.status == HTTPExchangeStatus.FAILED
        assert r1.http_status_code == 503

    def test_empty_batch_raises(self) -> None:
        async def run() -> None:
            client = AsyncHTTPClient(HTTPClientSettings(timeout_secs=5))
            batch = client.new_batch()
            await batch.dispatch_and_join()

        with pytest.raises(ValueError, match="no committed"):
            asyncio.run(run())

    def test_add_get_shorthand(self) -> None:
        transport = _make_transport_json({"k": "v"})

        async def run() -> HTTPBatchResponses:
            client = AsyncHTTPClient(HTTPClientSettings(timeout_secs=5))
            with patch("axiompy.io.http_async.httpx.AsyncClient") as mock_cls:

                def _client_factory(*args: object, **kwargs: object) -> httpx.AsyncClient:
                    merged = {**kwargs, "transport": transport}
                    return RealHttpxAsyncClient(*args, **merged)

                mock_cls.side_effect = _client_factory
                batch = client.new_batch().add_get(
                    "https://example.test/x",
                    headers={"H": "v"},
                )
                return await batch.dispatch_and_join()

        (r1,) = asyncio.run(run()).unwrap()
        assert r1.status == HTTPExchangeStatus.COMPLETE

    def test_str_method_accepted(self) -> None:
        transport = _make_transport_json({"ok": True})

        async def run() -> HTTPBatchResponses:
            client = AsyncHTTPClient(HTTPClientSettings(timeout_secs=5))
            with patch("axiompy.io.http_async.httpx.AsyncClient") as mock_cls:

                def _client_factory(*args: object, **kwargs: object) -> httpx.AsyncClient:
                    merged = {**kwargs, "transport": transport}
                    return RealHttpxAsyncClient(*args, **merged)

                mock_cls.side_effect = _client_factory
                batch = client.new_batch().add("get", "https://example.test/").commit()
                return await batch.dispatch_and_join()

        (r1,) = asyncio.run(run()).unwrap()
        assert r1.status == HTTPExchangeStatus.COMPLETE


class TestParseHelpers:
    def test_parse_json_content_type(self) -> None:
        req = httpx.Request("GET", "https://x.test")
        resp = httpx.Response(
            200,
            request=req,
            headers={"content-type": "application/json"},
            content=b'{"a":1}',
        )
        assert _parse_response_body(resp) == {"a": 1}

    def test_parse_json_malformed_falls_back_to_text(self) -> None:
        req = httpx.Request("GET", "https://x.test")
        resp = httpx.Response(
            200,
            request=req,
            headers={"content-type": "application/json"},
            content=b"not-json",
        )
        assert _parse_response_body(resp) == "not-json"

    def test_parse_json_object_without_json_content_type(self) -> None:
        req = httpx.Request("GET", "https://x.test")
        resp = httpx.Response(
            200,
            request=req,
            headers={"content-type": "text/plain"},
            content=b'{"x": 2}',
        )
        assert _parse_response_body(resp) == {"x": 2}

    def test_response_failed_branch(self) -> None:
        req = httpx.Request("GET", "https://x.test")
        resp = httpx.Response(400, request=req, text="bad")
        out = _response_to_result(resp)
        assert out.status == HTTPExchangeStatus.FAILED
        assert out.http_status_code == 400


class TestAsyncHTTPClientAuthFluent:
    def test_basic_digest_custom_chain(self) -> None:
        c = (
            AsyncHTTPClient(HTTPClientSettings(timeout_secs=5))
            .basic_auth("u", "p")
            .digest_auth("u2", "p2")
            .custom_auth("X-Key", "v")
        )
        assert c._auth is not None
        assert c._headers.get("X-Key") == "v"


class TestExecuteOneHttpxExceptions:
    """Exercise _execute_one mapping of httpx exceptions (real code path)."""

    def test_execute_one_timeout_exception(self) -> None:
        class _Inner:
            async def request(self, **kwargs: object) -> httpx.Response:
                raise httpx.TimeoutException("timed out")

        class _Ctx:
            async def __aenter__(self) -> _Inner:
                return _Inner()

            async def __aexit__(self, *args: object) -> None:
                return None

        async def run() -> HTTPExchangeResult:
            ac = AsyncHTTPClient(HTTPClientSettings(timeout_secs=5))
            b = ac.new_batch().add(HTTPMethod.GET, "https://x.test").commit()
            with patch(
                "axiompy.io.http_async.httpx.AsyncClient", side_effect=lambda *a, **k: _Ctx()
            ):
                results = await b.dispatch_and_join()
            return results.unwrap()[0]

        r = asyncio.run(run())
        assert r.status == HTTPExchangeStatus.TIMEOUT

    def test_execute_one_request_error(self) -> None:
        class _Inner:
            async def request(self, **kwargs: object) -> httpx.Response:
                raise httpx.RequestError("boom")

        class _Ctx:
            async def __aenter__(self) -> _Inner:
                return _Inner()

            async def __aexit__(self, *args: object) -> None:
                return None

        async def run() -> HTTPExchangeResult:
            ac = AsyncHTTPClient(HTTPClientSettings(timeout_secs=5))
            b = ac.new_batch().add(HTTPMethod.GET, "https://x.test").commit()
            with patch(
                "axiompy.io.http_async.httpx.AsyncClient", side_effect=lambda *a, **k: _Ctx()
            ):
                results = await b.dispatch_and_join()
            return results.unwrap()[0]

        r = asyncio.run(run())
        assert r.status == HTTPExchangeStatus.FAILED
        assert "boom" in (r.error_message or "")


class TestAddPostShorthand:
    def test_add_post_json(self) -> None:
        transport = _make_transport_json({"created": True})

        async def run() -> HTTPBatchResponses:
            client = AsyncHTTPClient(HTTPClientSettings(timeout_secs=5))
            with patch("axiompy.io.http_async.httpx.AsyncClient") as mock_cls:

                def _client_factory(*args: object, **kwargs: object) -> httpx.AsyncClient:
                    merged = {**kwargs, "transport": transport}
                    return RealHttpxAsyncClient(*args, **merged)

                mock_cls.side_effect = _client_factory
                batch = client.new_batch().add_post(
                    "https://example.test/p",
                    json={"a": 1},
                    headers={"H": "v"},
                )
                return await batch.dispatch_and_join()

        (r1,) = asyncio.run(run()).unwrap()
        assert r1.status == HTTPExchangeStatus.COMPLETE
        assert r1.results == {"created": True}


class TestMockAsyncHTTPClient:
    def test_dispatch_without_preset_raises(self) -> None:
        async def run() -> None:
            mock = MockAsyncHTTPClient()
            batch = mock.new_batch().add(HTTPMethod.GET, "x").commit()
            await batch.dispatch_and_join()

        with pytest.raises(RuntimeError, match="preset_batch_results"):
            asyncio.run(run())

    def test_preset_batch(self) -> None:
        async def run() -> None:
            mock = MockAsyncHTTPClient().preset_batch_results(
                HTTPExchangeResult(HTTPExchangeStatus.COMPLETE, results=1),
                HTTPExchangeResult(HTTPExchangeStatus.TIMEOUT, error_message="x"),
            )
            batch = (
                mock.new_batch()
                .add(HTTPMethod.GET, "http://u1")
                .commit()
                .add(HTTPMethod.GET, "http://u2")
                .commit()
            )
            r1, r2 = (await batch.dispatch_and_join()).unwrap()
            assert r1.results == 1
            assert r2.status == HTTPExchangeStatus.TIMEOUT

        asyncio.run(run())

    def test_mock_preset_mismatch_raises(self) -> None:
        async def run() -> None:
            mock = MockAsyncHTTPClient().preset_batch_results(
                HTTPExchangeResult(HTTPExchangeStatus.COMPLETE, results=1),
            )
            batch = (
                mock.new_batch().add(HTTPMethod.GET, "a").commit().add(HTTPMethod.GET, "b").commit()
            )
            await batch.dispatch_and_join()

        with pytest.raises(ValueError, match="Preset has"):
            asyncio.run(run())


def _pick_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _local_batch_server_tests_enabled() -> bool:
    return os.environ.get("AXIOMPY_SKIP_ASYNC_HTTP_LOCAL_SERVER", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    )


@pytest.fixture(scope="module")
def local_batch_http_base_url() -> Generator[str, None, None]:
    """
    Loopback HTTP server: routes registered only through :mod:`axiompy.servers` (``Server.route``,
    ``(body, status_code)`` tuples for non-2xx). Uvicorn runs the framework app; no FastAPI imports
    in this test module.
    """
    pytest.importorskip("fastapi")
    pytest.importorskip("uvicorn")
    import uvicorn

    port = _pick_loopback_port()
    settings = ServerSettings(host="127.0.0.1", port=port)
    server = ServerFactory.create(ServerType.FASTAPI, settings)

    @server.route("/posts/{post_id}", methods=["GET"])
    def get_post(post_id: int):
        if post_id == 0:
            return {"message": "Not found"}, 404
        return {
            "userId": 1,
            "id": post_id,
            "title": f"post-{post_id}",
            "body": "integration",
        }

    @server.route("/slow", methods=["GET"])
    async def slow() -> dict[str, bool]:
        await asyncio.sleep(15)
        return {"done": True}

    app = server.get_app()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="critical",
    )
    uvicorn_server = uvicorn.Server(config)
    thread = threading.Thread(target=uvicorn_server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.05)
    else:
        uvicorn_server.should_exit = True
        thread.join(timeout=5.0)
        pytest.fail("uvicorn failed to bind or accept connections")

    base = f"http://127.0.0.1:{port}"
    try:
        yield base
    finally:
        uvicorn_server.should_exit = True
        thread.join(timeout=10.0)


@pytest.mark.skipif(
    not _local_batch_server_tests_enabled(),
    reason="AXIOMPY_SKIP_ASYNC_HTTP_LOCAL_SERVER is set",
)
class TestAsyncHTTPClientLocalServerIntegration:
    """
    End-to-end batch calls against a local server (:mod:`axiompy.servers` + uvicorn).

    Requires ``fastapi`` and ``uvicorn`` (server backend). Set ``AXIOMPY_SKIP_ASYNC_HTTP_LOCAL_SERVER=1`` to skip.
    """

    def test_get_post(self, local_batch_http_base_url: str) -> None:
        async def run() -> HTTPBatchResponses:
            client = AsyncHTTPClient(HTTPClientSettings(timeout_secs=30))
            batch = client.new_batch().add_get(f"{local_batch_http_base_url}/posts/1")
            return await batch.dispatch_and_join()

        (r1,) = asyncio.run(run()).unwrap()
        assert r1.status == HTTPExchangeStatus.COMPLETE
        assert r1.http_status_code == 200
        assert isinstance(r1.results, dict)
        assert r1.results.get("id") == 1
        assert "title" in r1.results

    def test_parallel_two_posts(self, local_batch_http_base_url: str) -> None:
        async def run() -> HTTPBatchResponses:
            client = AsyncHTTPClient(HTTPClientSettings(timeout_secs=30))
            base = local_batch_http_base_url
            batch = client.new_batch().add_get(f"{base}/posts/1").add_get(f"{base}/posts/2")
            return await batch.dispatch_and_join()

        r1, r2 = asyncio.run(run()).unwrap()
        assert r1.status == HTTPExchangeStatus.COMPLETE
        assert r2.status == HTTPExchangeStatus.COMPLETE
        assert r1.results.get("id") == 1
        assert r2.results.get("id") == 2

    def test_not_found_returns_failed_status(self, local_batch_http_base_url: str) -> None:
        async def run() -> HTTPBatchResponses:
            client = AsyncHTTPClient(HTTPClientSettings(timeout_secs=30))
            batch = client.new_batch().add_get(f"{local_batch_http_base_url}/posts/0")
            return await batch.dispatch_and_join()

        (r1,) = asyncio.run(run()).unwrap()
        assert r1.status == HTTPExchangeStatus.FAILED
        assert r1.http_status_code == 404

    def test_delayed_response_times_out(self, local_batch_http_base_url: str) -> None:
        async def run() -> HTTPBatchResponses:
            client = AsyncHTTPClient(HTTPClientSettings(timeout_secs=30))
            batch = client.new_batch(timeout_secs=2).add_get(f"{local_batch_http_base_url}/slow")
            return await batch.dispatch_and_join()

        (r1,) = asyncio.run(run()).unwrap()
        assert r1.status == HTTPExchangeStatus.TIMEOUT
        assert r1.error_message == "Request timed out"
