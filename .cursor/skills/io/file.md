# File I/O (io domain)

## Preferred APIs

Use `axiompy.io` read helpers (`read_text`, `read_json`, `read_csv`) rather than reopening files ad hoc.

## Rules

- Encoding and `default` fallbacks are explicit parameters.
- Do not swallow `OSError` without logging context (path, operation).
- Large files: document streaming behavior if bypassing helper APIs.
