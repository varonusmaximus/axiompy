# Blob stores (object domain)

## Factory

- `create(provider, settings)` with validated settings per cloud (region, credentials, endpoint overrides).
- No direct boto3/gcs/azure imports outside adapter implementations.

## Keys & paths

- Treat object keys as opaque strings; validate path traversal concerns at API boundary.
- Prefer idempotent put/get/delete semantics documented per method.

## Security

- Never log presigned URLs with secrets; redact ARNs and access keys in errors.
