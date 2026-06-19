# HTTP (io domain)

Domain-specific HTTP rules. Factory construction and fluent APIs are in **design-patterns**.

## Sync client

```python
from axiompy.io.http import HTTPClientFactory, RetryConfig

client = HTTPClientFactory.create(
    base_url="https://api.example.com",
    retry_config=RetryConfig(max_retries=3),
)
```

## I/O-only rules

- Map HTTP status failures to typed errors; redact tokens in logs.
- Keep sync (`http.py`) and async (`http_async.py`) implementations parallel — do not mix async calls into sync adapters.
- `web.py` helpers stay framework-agnostic — no Flask/FastAPI imports.
