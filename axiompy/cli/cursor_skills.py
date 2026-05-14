"""
Sync bundled Cursor skills to the local filesystem.

Default target: ``~/.cursor/skills/<skill-name>/``
Optional:       ``<cwd>/.cursor/skills/<skill-name>/`` via ``--project``

Usage::

    axiompy-skills                # sync to ~/.cursor/skills/
    axiompy-skills --list         # list bundled skills
    axiompy-skills --dry-run      # preview without writing
    axiompy-skills --project      # sync into <cwd>/.cursor/skills/
    axiompy-skills --dest /tmp/x  # sync into a custom directory
    python -m axiompy.cli.cursor_skills   # same as axiompy-skills
"""

from __future__ import annotations

import argparse
import importlib.resources
import shutil
import sys
from pathlib import Path
from typing import Sequence

_BUNDLE_PACKAGE = "axiompy_skills"


def _bundle_root() -> Path:
    """Return the on-disk path of the bundled skills package."""
    ref = importlib.resources.files(_BUNDLE_PACKAGE)
    bundle_path = Path(str(ref))
    if not bundle_path.is_dir():
        print(f"error: bundle not found at {bundle_path}", file=sys.stderr)
        sys.exit(1)
    return bundle_path


def _default_dest() -> Path:
    """``~/.cursor/skills``."""
    return Path.home() / ".cursor" / "skills"


def _axiompy_version() -> str:
    try:
        from axiompy import __version__

        return str(__version__)
    except Exception:
        return "unknown"


def list_skills(bundle: Path) -> list[str]:
    """Return sorted skill directory names found in the bundle."""
    return sorted(p.name for p in bundle.iterdir() if p.is_dir() and (p / "SKILL.md").exists())


def sync_skills(
    bundle: Path,
    dest: Path,
    *,
    dry_run: bool = False,
    force: bool = True,
) -> list[str]:
    """
    Copy each bundled skill directory into *dest*.

    Args:
        bundle: Path to the bundle package on disk.
        dest: Target directory (e.g. ``~/.cursor/skills``).
        dry_run: If True, print what would happen but do not write.
        force: Overwrite existing skill directories (default True).

    Returns:
        List of skill names that were synced (or would be synced).
    """
    skills = list_skills(bundle)
    synced: list[str] = []

    for skill in skills:
        src = bundle / skill
        target = dest / skill

        if target.exists() and not force:
            print(f"  skip  {skill}/ (exists, use --force to overwrite)")
            continue

        if dry_run:
            print(f"  would sync  {skill}/ -> {target}")
        else:
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(src, target)
            print(f"  synced  {skill}/ -> {target}")

        synced.append(skill)

    return synced


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="axiompy-skills",
        description="Sync bundled AxiomPy Cursor skills to the local filesystem.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_only",
        help="List bundled skills and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without writing files.",
    )
    parser.add_argument(
        "--project",
        action="store_true",
        help="Sync into <cwd>/.cursor/skills/ instead of ~/.cursor/skills/.",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="Custom destination directory (overrides --project and default).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=True,
        help="Overwrite existing skill directories (default: True).",
    )
    parser.add_argument(
        "--no-force",
        action="store_false",
        dest="force",
        help="Skip existing skill directories instead of overwriting.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print axiompy version and exit.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry-point for ``axiompy-skills``."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"axiompy {_axiompy_version()}")
        return 0

    bundle = _bundle_root()

    if args.list_only:
        skills = list_skills(bundle)
        print(f"Bundled skills ({len(skills)}):")
        for s in skills:
            print(f"  - {s}")
        return 0

    if args.dest is not None:
        dest = args.dest
    elif args.project:
        dest = Path.cwd() / ".cursor" / "skills"
    else:
        dest = _default_dest()

    print(f"axiompy-skills  (axiompy {_axiompy_version()})")
    print(f"destination: {dest}")
    if args.dry_run:
        print("(dry run — no files will be written)\n")
    else:
        dest.mkdir(parents=True, exist_ok=True)
        print()

    synced = sync_skills(bundle, dest, dry_run=args.dry_run, force=args.force)

    if not synced:
        print("\nNo skills synced.")
    else:
        print(f"\n{len(synced)} skill(s) {'would be synced' if args.dry_run else 'synced'}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
