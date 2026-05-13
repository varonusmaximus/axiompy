"""
Async HTTP client with batched concurrent requests and transport-agnostic outcomes.

Uses ``httpx`` behind the API. Install: ``pip install 'axiompy[http-async]'``.

On Python 3.11+, use :class:`http.HTTPMethod` for batch verbs. On 3.10, this module
re-exports a compatible :data:`HTTPMethod` enum with the same member names.

Quick example:
    >>> from http import HTTPMethod  # or: from axiompy.io.http_async import HTTPMethod
    >>> from axiompy.io.http import HTTPClientFactory, HTTPClientSettings, HTTPTransport
    >>> async def run():
    ...     client = HTTPClientFactory.create(
    ...         transport=HTTPTransport.ASYNC,
    ...         settings=HTTPClientSettings(timeout_secs=30),
    ...     )
    ...     batch = (
    ...         client.new_batch()
    ...         .add(HTTPMethod.GET, "https://example.com")
    ...         .header("X-Trace", "1")
    ...         .commit()
    ...     )
    ...     return await batch.dispatch_and_join()
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union, runtime_checkable

from axiompy.io.http import HTTPClientSettings
from axiompy.loggers import LoggerFactory
from axiompy.validators import ensure_in_range, ensure_not_empty

logger = LoggerFactory.create_logger(__name__)

if sys.version_info >= (3, 11):
    from http import HTTPMethod
else:

    class HTTPMethod(str, Enum):
        """Subset of HTTP verbs for batch API (Python 3.10 shim for ``http.HTTPMethod``)."""

        GET = "GET"
        HEAD = "HEAD"
        POST = "POST"
        PUT = "PUT"
        PATCH = "PATCH"
        DELETE = "DELETE"
        OPTIONS = "OPTIONS"


try:
    import httpx
except ImportError as e:  # pragma: no cover
    httpx = None  # type: ignore[assignment]
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None


def _require_httpx() -> None:
    if httpx is None:
        raise ImportError(
            "Async HTTP batch client requires httpx. Install with: pip install 'axiompy[http-async]'"
        ) from _IMPORT_ERROR


def _method_to_str(method: Union[HTTPMethod, str]) -> str:
    """Normalize verb to uppercase string for httpx."""
    if isinstance(method, str):
        return method.upper().strip()
    return str(method)


class HTTPExchangeStatus(str, Enum):
    """Terminal status of a single exchange in a batch."""

    COMPLETE = "complete"
    TIMEOUT = "timeout"
    FAILED = "failed"


@dataclass(frozen=True)
class HTTPExchangeResult:
    """
    Outcome for one HTTP call in a batch.

    Attributes:
        status: Whether the exchange completed, timed out, or failed.
        results: Response body when useful (parsed JSON, text, etc.).
        http_status_code: HTTP status when a response was received.
        error_message: Short message for FAILED or TIMEOUT when applicable.
    """

    status: HTTPExchangeStatus
    results: Any = None
    http_status_code: Optional[int] = None
    error_message: Optional[str] = None


@dataclass(frozen=True)
class HTTPBatchResponses:
    """Ordered results from :meth:`HTTPCallBatch.dispatch_and_join`."""

    _items: Tuple[HTTPExchangeResult, ...]

    def unwrap(self) -> Tuple[HTTPExchangeResult, ...]:
        """
        Return results in the same order as committed slots on the batch.

        Returns:
            One :class:`HTTPExchangeResult` per scheduled call.
        """
        return self._items


@dataclass
class _BatchCallSpec:
    """Internal description of one request in a batch."""

    method: str
    url: str
    headers: Dict[str, str]
    params: Optional[Dict[str, Any]] = None
    json_body: Any = None
    content: Optional[Union[str, bytes]] = None


def _parse_response_body(response: httpx.Response) -> Any:
    ct = (response.headers.get("content-type") or "").lower()
    if "application/json" in ct:
        try:
            return response.json()
        except (json.JSONDecodeError, ValueError):
            return response.text
    text = response.text
    if text.strip().startswith(("{", "[")):
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return text
    return text


def _response_to_result(response: httpx.Response) -> HTTPExchangeResult:
    if response.is_success:
        return HTTPExchangeResult(
            status=HTTPExchangeStatus.COMPLETE,
            results=_parse_response_body(response),
            http_status_code=response.status_code,
        )
    try:
        err_text = response.text[:500]
    except Exception:
        err_text = "Unable to read response body"
    return HTTPExchangeResult(
        status=HTTPExchangeStatus.FAILED,
        results=err_text,
        http_status_code=response.status_code,
        error_message=err_text[:200],
    )


@runtime_checkable
class AsyncHTTPClientProtocol(Protocol):
    """Structural type for async HTTP clients that support batched calls."""

    settings: HTTPClientSettings

    def new_batch(self, timeout_secs: Optional[int] = None) -> HTTPCallBatch: ...


class AsyncHTTPClient:
    """
    Async HTTP client using httpx for asyncio and concurrent batch requests.

    Configure auth and headers with the same fluent style as sync
    :class:`~axiompy.io.http.HTTPClient`.
    """

    def __init__(self, settings: HTTPClientSettings) -> None:
        _require_httpx()
        ensure_in_range(settings.timeout_secs, 1, 3600, "timeout_secs must be 1-3600")
        self.settings = settings
        self._headers: Dict[str, str] = {}
        self._auth: Optional[Any] = None
        logger.debug("AsyncHTTPClient initialized timeout_secs=%s", settings.timeout_secs)

    def add_header(self, key: str, value: str) -> AsyncHTTPClient:
        self._headers[key] = value
        logger.debug("AsyncHTTPClient added header %s", key)
        return self

    def bearer_token(self, token: str) -> AsyncHTTPClient:
        self.add_header("Authorization", f"Bearer {token}")
        return self

    def basic_auth(self, username: str, password: str) -> AsyncHTTPClient:
        _require_httpx()
        self._auth = httpx.BasicAuth(username, password)
        return self

    def digest_auth(self, username: str, password: str) -> AsyncHTTPClient:
        _require_httpx()
        self._auth = httpx.DigestAuth(username, password)
        return self

    def custom_auth(self, auth_header: str, auth_value: str) -> AsyncHTTPClient:
        self.add_header(auth_header, auth_value)
        return self

    def new_batch(self, timeout_secs: Optional[int] = None) -> HTTPCallBatch:
        effective = timeout_secs if timeout_secs is not None else self.settings.timeout_secs
        ensure_in_range(effective, 1, 3600, "batch timeout_secs must be 1-3600")
        return HTTPCallBatch(self, effective)

    def _client_kwargs(self) -> Dict[str, Any]:
        _require_httpx()
        return {
            "verify": self.settings.verify_ssl,
            "follow_redirects": self.settings.allow_redirects,
            "headers": dict(self._headers),
            "auth": self._auth,
        }


class HTTPBatchSlotBuilder:
    """
    Fluent builder for one slot in a batch; obtain via :meth:`HTTPCallBatch.add`.
    """

    def __init__(self, batch: HTTPCallBatch, method: Union[HTTPMethod, str], url: str) -> None:
        self._batch = batch
        self._method = _method_to_str(method)
        ensure_not_empty(url, "url must not be empty")
        self._url = url
        self._slot_headers: Dict[str, str] = {}
        self._params: Optional[Dict[str, Any]] = None
        self._json_body: Any = None
        self._content: Optional[Union[str, bytes]] = None

    def header(self, key: str, value: str) -> HTTPBatchSlotBuilder:
        self._slot_headers[key] = value
        return self

    def headers(self, mapping: Dict[str, str]) -> HTTPBatchSlotBuilder:
        self._slot_headers.update(mapping)
        return self

    def params(self, mapping: Dict[str, Any]) -> HTTPBatchSlotBuilder:
        self._params = dict(mapping)
        return self

    def json(self, body: Any) -> HTTPBatchSlotBuilder:
        self._json_body = body
        return self

    def content(self, body: Union[str, bytes]) -> HTTPBatchSlotBuilder:
        self._content = body
        return self

    def commit(self) -> HTTPCallBatch:
        merged = dict(self._batch._client._headers)
        merged.update(self._slot_headers)
        spec = _BatchCallSpec(
            method=self._method,
            url=self._url,
            headers=merged,
            params=self._params,
            json_body=self._json_body,
            content=self._content,
        )
        self._batch._specs.append(spec)
        return self._batch


class HTTPCallBatch:
    """
    Builder for concurrent HTTP calls sharing a per-call timeout.

    Use :meth:`add` with :class:`HTTPMethod`, then :meth:`HTTPBatchSlotBuilder.commit`,
    then ``await`` :meth:`dispatch_and_join`.
    """

    def __init__(self, client: AsyncHTTPClient, timeout_secs: int) -> None:
        self._client = client
        self._timeout_secs = timeout_secs
        self._specs: List[_BatchCallSpec] = []

    def add(self, method: Union[HTTPMethod, str], url: str) -> HTTPBatchSlotBuilder:
        """
        Start a fluent slot for one HTTP request.

        Args:
            method: ``http.HTTPMethod`` member (3.11+) or :data:`HTTPMethod` from this
                module on 3.10; or an uppercase verb string.
            url: Request URL.

        Returns:
            Slot builder; call :meth:`HTTPBatchSlotBuilder.commit` to append to the batch.
        """
        return HTTPBatchSlotBuilder(self, method, url)

    def add_get(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> HTTPCallBatch:
        """Shorthand: ``add(GET, url).headers(...).params(...).commit()``."""
        b = self.add(HTTPMethod.GET, url)
        if headers:
            b.headers(headers)
        if params:
            b.params(params)
        return b.commit()

    def add_post(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json: Any = None,
        content: Optional[Union[str, bytes]] = None,
    ) -> HTTPCallBatch:
        """Shorthand: ``add(POST, url)`` with body and optional headers."""
        b = self.add(HTTPMethod.POST, url)
        if headers:
            b.headers(headers)
        if json is not None:
            b.json(json)
        if content is not None:
            b.content(content)
        return b.commit()

    async def dispatch_and_join(self) -> HTTPBatchResponses:
        """
        Run all committed slots concurrently; wait until each has a terminal status.

        Returns:
            :class:`HTTPBatchResponses` in commit order.

        Raises:
            ValueError: If no slots were committed.
        """
        _require_httpx()
        if not self._specs:
            raise ValueError("Batch has no committed calls; add at least one slot.")

        timeout = httpx.Timeout(self._timeout_secs)
        kwargs = self._client._client_kwargs()

        async with httpx.AsyncClient(timeout=timeout, **kwargs) as client:
            tasks = [self._execute_one(client, spec) for spec in self._specs]
            results = await asyncio.gather(*tasks)

        return HTTPBatchResponses(tuple(results))

    async def _execute_one(
        self,
        client: httpx.AsyncClient,
        spec: _BatchCallSpec,
    ) -> HTTPExchangeResult:
        try:
            kw: Dict[str, Any] = {
                "method": spec.method,
                "url": spec.url,
                "headers": spec.headers or None,
                "params": spec.params,
            }
            if spec.json_body is not None:
                kw["json"] = spec.json_body
            elif spec.content is not None:
                kw["content"] = spec.content

            response = await client.request(**kw)
            return _response_to_result(response)
        except httpx.TimeoutException:
            return HTTPExchangeResult(
                status=HTTPExchangeStatus.TIMEOUT,
                error_message="Request timed out",
            )
        except httpx.RequestError as e:
            logger.warning("Async HTTP request failed: %s", e)
            return HTTPExchangeResult(
                status=HTTPExchangeStatus.FAILED,
                error_message=str(e),
            )


class MockAsyncHTTPClient:
    """Test double with preset batch results (no network)."""

    def __init__(self, settings: Optional[HTTPClientSettings] = None) -> None:
        self.settings = settings or HTTPClientSettings()
        self._headers: Dict[str, str] = {}
        self._preset_results: Optional[Tuple[HTTPExchangeResult, ...]] = None

    def add_header(self, key: str, value: str) -> MockAsyncHTTPClient:
        self._headers[key] = value
        return self

    def bearer_token(self, token: str) -> MockAsyncHTTPClient:
        self.add_header("Authorization", f"Bearer {token}")
        return self

    def preset_batch_results(self, *results: HTTPExchangeResult) -> MockAsyncHTTPClient:
        self._preset_results = results
        return self

    def new_batch(self, timeout_secs: Optional[int] = None) -> MockHTTPCallBatch:
        effective = timeout_secs if timeout_secs is not None else self.settings.timeout_secs
        return MockHTTPCallBatch(self, effective)


class MockHTTPCallBatch:
    """Batch paired with :class:`MockAsyncHTTPClient`; counts slots for preset validation."""

    def __init__(self, client: MockAsyncHTTPClient, timeout_secs: int) -> None:
        self._client = client
        self._timeout_secs = timeout_secs
        self._slot_count = 0

    def add(self, method: Union[HTTPMethod, str], url: str) -> MockHTTPBatchSlotBuilder:
        return MockHTTPBatchSlotBuilder(self, method, url)

    def add_get(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> MockHTTPCallBatch:
        b = self.add(HTTPMethod.GET, url)
        if headers:
            b.headers(headers)
        if params:
            b.params(params)
        return b.commit()

    def add_post(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json: Any = None,
        content: Optional[Union[str, bytes]] = None,
    ) -> MockHTTPCallBatch:
        b = self.add(HTTPMethod.POST, url)
        if headers:
            b.headers(headers)
        if json is not None:
            b.json(json)
        if content is not None:
            b.content(content)
        return b.commit()

    async def dispatch_and_join(self) -> HTTPBatchResponses:
        preset = self._client._preset_results
        if preset is None:
            raise RuntimeError("MockAsyncHTTPClient.preset_batch_results was not set")
        if len(preset) != self._slot_count:
            raise ValueError(
                f"Preset has {len(preset)} results but batch recorded {self._slot_count} shorthand adds"
            )
        return HTTPBatchResponses(preset)


class MockHTTPBatchSlotBuilder:
    """Slot builder for mock; ``commit`` increments parent slot count."""

    def __init__(self, batch: MockHTTPCallBatch, method: Union[HTTPMethod, str], url: str) -> None:
        self._batch = batch
        self._method = method
        self._url = url

    def header(self, key: str, value: str) -> MockHTTPBatchSlotBuilder:
        return self

    def headers(self, mapping: Dict[str, str]) -> MockHTTPBatchSlotBuilder:
        return self

    def params(self, mapping: Dict[str, Any]) -> MockHTTPBatchSlotBuilder:
        return self

    def json(self, body: Any) -> MockHTTPBatchSlotBuilder:
        return self

    def content(self, body: Union[str, bytes]) -> MockHTTPBatchSlotBuilder:
        return self

    def commit(self) -> MockHTTPCallBatch:
        self._batch._slot_count += 1
        return self._batch


class AsyncHTTPClientFactory:
    """Factory for :class:`AsyncHTTPClient` and :class:`MockAsyncHTTPClient`."""

    @staticmethod
    def create(settings: HTTPClientSettings) -> AsyncHTTPClient:
        return AsyncHTTPClient(settings)

    @staticmethod
    def create_mock() -> MockAsyncHTTPClient:
        return MockAsyncHTTPClient()


__all__ = [
    "AsyncHTTPClient",
    "AsyncHTTPClientFactory",
    "AsyncHTTPClientProtocol",
    "HTTPBatchResponses",
    "HTTPCallBatch",
    "HTTPExchangeResult",
    "HTTPExchangeStatus",
    "HTTPMethod",
    "HTTPBatchSlotBuilder",
    "MockAsyncHTTPClient",
    "MockHTTPCallBatch",
    "MockHTTPBatchSlotBuilder",
]
