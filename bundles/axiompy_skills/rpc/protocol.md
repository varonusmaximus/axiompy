# JSON-RPC protocol (rpc domain)

## Errors

- Map application failures to JSON-RPC error codes consistently on server side.
- Client: surface transport failures separately from JSON-RPC `error` payloads.

## Handlers

- Register methods explicitly; reject unknown methods with standard error response.
- Keep handler signatures small — validate params dict before dispatch.

## Testing

- Round-trip tests with mock transport; no live network required for unit tests.
