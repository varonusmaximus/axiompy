#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"
if command -v aal >/dev/null 2>&1; then
  CLI=(aal)
elif [[ -x "$ROOT/venv/bin/aal" ]]; then
  CLI=("$ROOT/venv/bin/aal")
else
  CLI=(python -m aal.cli)
fi
exec "${CLI[@]}" hook cursor-pretooluse
