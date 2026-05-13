"""Allow ``python -m axiompy.cli.cursor_skills`` as an alias for ``axiompy-skills``."""

from __future__ import annotations

import sys

from axiompy.cli.cursor_skills import main

sys.exit(main())
