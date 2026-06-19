# MCP tools & sessions (mcp domain)

## Tools

- One registered tool per capability; descriptions agent-facing and accurate.
- Side-effecting tools log at info without leaking secrets or PII.

## Sessions

- Session IDs are opaque; document lifetime and cleanup.
- Reasoning hooks (`mcp_reasoning`) stay separate from basic tool dispatch — avoid circular imports.

## Validators

- Reuse `axiompy.validators` for tool argument validation before execution.
