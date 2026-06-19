# Inbound servers (servers domain)

## Layering

```
Route / handler  →  service  →  ports (io, storage, secrets)
```

## Web factories

- Enum or settings-driven `ServerFactory.create(...)` — same app code, swapped framework adapter.
- Health and resource routes stay minimal — delegate to domain services.

## Testing

- Test handlers with factory mocks; integration tests optional behind `[servers]` extra.
