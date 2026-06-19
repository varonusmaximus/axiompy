# Serialization (io domain)

## Scope

`axiompy/io/serialization.py` — converting between bytes, text, and structured formats at transport boundaries.

## Rules

- Keep serializers **pure** where possible; side effects belong in callers.
- Validate decoded payloads with `axiompy.validators` before use.
- Prefer explicit format parameters over magic sniffing unless documented.
