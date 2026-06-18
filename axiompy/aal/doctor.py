# @!tooling

from __future__ import annotations

import shutil
from pathlib import Path

from axiompy.aal import __version__
from axiompy.aal.bundle import list_bundled_domains
from axiompy.aal.config import cursor_config_dir, load_config
from axiompy.aal.constants import BOOTSTRAP_FILE, DOMAINS_FILE, MANIFEST_FILE


def cmd_doctor(root: Path, *, strict: bool = False) -> int:
    issues = 0
    print(f"[AAL] Doctor v{__version__} — {root}")
    print()

    cli = shutil.which("axiompy-skills")
    if cli:
        print(f"OK: `axiompy-skills` CLI available ({cli})")
    else:
        try:
            import axiompy.aal  # noqa: F401

            print("OK: `axiompy.aal` importable (use `python -m axiompy.cli.cursor_skills`)")
        except ImportError:
            print("MISSING: pip install axiompy")
            issues += 1

    cursor_dir = cursor_config_dir(root)
    if not cursor_dir.is_dir():
        print("MISSING: .cursor/ — run: axiompy-skills install --project --hooks")
        issues += 1
    else:
        print("OK: .cursor/ present")
        for name in ("aal.yaml", DOMAINS_FILE, BOOTSTRAP_FILE, MANIFEST_FILE):
            path = cursor_dir / name
            if path.is_file():
                print(f"OK: {path.relative_to(root)}")
            elif name in (BOOTSTRAP_FILE, MANIFEST_FILE) and not strict:
                print(f"OPTIONAL: {path.relative_to(root)}")
            else:
                print(f"MISSING: {path.relative_to(root)}")
                issues += 1

        skills_dir = cursor_dir / "skills"
        if skills_dir.is_dir() and any(
            (skills_dir / d / "SKILL.md").exists() for d in skills_dir.iterdir() if d.is_dir()
        ):
            count = sum(
                1 for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").is_file()
            )
            print(f"OK: .cursor/skills/ ({count} SKILL.md tree(s))")
        else:
            print(
                "MISSING: .cursor/skills/*/SKILL.md — run: axiompy-skills install --project --hooks"
            )
            issues += 1

    cursor_rule = cursor_dir / "rules" / "aal.mdc"
    if cursor_rule.is_file():
        print("OK: .cursor/rules/aal.mdc")
    else:
        print("OPTIONAL: .cursor/rules/aal.mdc — run: axiompy-skills install --project --hooks")

    ci_workflow = root / ".github/workflows/axiompy-aal-gate.yml"
    if ci_workflow.is_file():
        print("OK: .github/workflows/axiompy-aal-gate.yml")
    else:
        print("OPTIONAL: CI workflow — run: axiompy-skills install --project --hooks")

    config = load_config(root)
    print(f"OK: scan_entire_file={config.get('scan_entire_file', True)}")

    bundled = list_bundled_domains()
    print(f"INFO: bundled domain templates: {', '.join(bundled)}")

    print()
    if issues:
        print(f"[AAL] Doctor found {issues} issue(s).")
        return 1
    print("[AAL] Doctor: all required components present.")
    return 0
