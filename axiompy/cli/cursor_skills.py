# @!tooling

"""
Sync bundled Cursor skills to the local filesystem.

Copies **SKILL.md trees** from ``axiompy_skills`` into a skills parent directory.

Destination precedence (highest first):

1. ``--dest <path>`` — parent directory for skill folders (``code-review/``, …).
2. ``--project`` — ``<cwd>/.cursor/skills``.
3. Environment ``AXIOMPY_SKILLS_DEST`` — path to that same parent directory.
4. ``[tool.axiompy.skills]`` in the nearest ``pyproject.toml`` walking upward from
   ``cwd`` — key ``destination``: ``global``, ``project``, or an absolute path string.
5. Default: ``~/.cursor/skills``.

AAL (domain annotations, inject, hooks) lives in the separate ``axiom-aal`` package.
Use ``pip install axiom-aal`` and the ``aal`` CLI.
"""

from __future__ import annotations

import argparse
import importlib.resources
import os
import shutil
import sys
import tomllib
from pathlib import Path
from typing import Iterator, Sequence

_BUNDLE_PACKAGE = "axiompy_skills"


def skills_bundle_root() -> Path:
    """Return the on-disk path of the bundled skills package."""
    ref = importlib.resources.files(_BUNDLE_PACKAGE)
    bundle_path = Path(str(ref))
    if not bundle_path.is_dir():
        print(f"error: bundle not found at {bundle_path}", file=sys.stderr)
        sys.exit(1)
    return bundle_path


def _bundle_root() -> Path:
    """Alias for tests and backward compatibility."""
    return skills_bundle_root()


def _default_global_dest() -> Path:
    return Path.home() / ".cursor" / "skills"


def _axiompy_version() -> str:
    try:
        from axiompy import __version__

        return str(__version__)
    except Exception:
        return "unknown"


def _iter_directories_for_pyproject(start: Path) -> Iterator[Path]:
    cur = start.resolve()
    while True:
        yield cur
        parent = cur.parent
        if parent == cur:
            break
        cur = parent


def _read_tool_axiompy_skills_destination(pyproject_path: Path) -> str | None:
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError):
        return None
    tool = data.get("tool")
    if not isinstance(tool, dict):
        return None
    ax = tool.get("axiompy", {})
    if not isinstance(ax, dict):
        return None
    skills = ax.get("skills", {})
    if not isinstance(skills, dict):
        return None
    dest = skills.get("destination")
    return dest if isinstance(dest, str) else None


def _destination_from_pyproject_value(raw: str, cwd: Path) -> Path:
    key = raw.strip()
    match key:
        case "global":
            return _default_global_dest()
        case "project":
            return cwd / ".cursor" / "skills"
        case _:
            p = Path(key).expanduser()
            if not p.is_absolute():
                p = (cwd / p).resolve()
            return p.resolve()


def resolve_skills_destination(
    *,
    cwd: Path,
    dest: Path | None,
    project: bool,
) -> tuple[Path, str]:
    if dest is not None:
        p = dest.expanduser()
        if not p.is_absolute():
            p = (cwd / p).resolve()
        return p.resolve(), "cli_dest"
    if project:
        return (cwd / ".cursor" / "skills").resolve(), "cli_project"

    env_raw = os.environ.get("AXIOMPY_SKILLS_DEST", "").strip()
    if env_raw:
        p = Path(env_raw).expanduser()
        if not p.is_absolute():
            p = (cwd / p).resolve()
        return p.resolve(), "env"

    for directory in _iter_directories_for_pyproject(cwd):
        pyproject = directory / "pyproject.toml"
        if not pyproject.is_file():
            continue
        raw = _read_tool_axiompy_skills_destination(pyproject)
        if raw is None or raw.strip() == "":
            continue
        return _destination_from_pyproject_value(raw, cwd), "pyproject"

    return _default_global_dest(), "default"


def list_skills(bundle: Path) -> list[str]:
    return sorted(p.name for p in bundle.iterdir() if p.is_dir() and (p / "SKILL.md").exists())


def sync_skills(
    bundle: Path,
    dest: Path,
    *,
    dry_run: bool = False,
    force: bool = True,
) -> list[str]:
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


def _run_sync(args: argparse.Namespace, cwd: Path) -> int:
    bundle = skills_bundle_root()
    dest, source = resolve_skills_destination(
        cwd=cwd,
        dest=args.dest,
        project=args.project,
    )

    if args.show_config:
        print(f"skills_parent: {dest}")
        print(f"source: {source}")
        return 0

    print(f"axiompy-skills  (axiompy {_axiompy_version()})")
    print(f"destination: {dest}")
    print(f"config_source: {source}")
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


def _add_sync_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Print resolved skills parent directory and config source, then exit.",
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
        help="Sync into <cwd>/.cursor/skills/.",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="Custom parent directory for skill folders.",
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


def _build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="axiompy-skills",
        description="Sync bundled AxiomPy Cursor SKILL.md trees to the filesystem.",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    _add_sync_flags(parser)
    args = parser.parse_args(argv)
    cwd = Path.cwd()
    if args.version:
        print(f"axiompy {_axiompy_version()}")
        return 0
    if args.list_only:
        bundle = skills_bundle_root()
        skills = list_skills(bundle)
        print(f"Bundled skills ({len(skills)}):")
        for s in skills:
            print(f"  - {s}")
        return 0
    return _run_sync(args, cwd)


if __name__ == "__main__":
    sys.exit(main())
