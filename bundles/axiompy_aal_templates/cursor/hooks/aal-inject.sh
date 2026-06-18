# @!tooling

#!/usr/bin/env bash
# AAL inject hook — resolves domain skills before Write/Edit.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

FILE="${CURSOR_FILE_PATH:-${FILE:-}}"
LINE="${CURSOR_LINE:-${LINE:-1}}"

if [[ -z "$FILE" ]]; then
  # No file context — allow tool use
  exit 0
fi

if command -v axiompy-skills >/dev/null 2>&1; then
  CLI=(axiompy-skills)
elif [[ -x "$ROOT/venv/bin/axiompy-skills" ]]; then
  CLI=("$ROOT/venv/bin/axiompy-skills")
else
  CLI=(python -m axiompy.cli.cursor_skills)
fi

"${CLI[@]}" resolve --file "$FILE" --line "$LINE" --json >/dev/null
