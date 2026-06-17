# @!code-style

"""
Sync bundled Cursor skills and AAL tooling to the local filesystem.

Copies **SKILL.md trees** from ``axiompy_skills`` and optionally installs AAL
registry, hooks, and CI templates via ``install --project --hooks``.

Destination precedence (highest first):

1. ``--dest <path>`` — parent directory for skill folders (``code-review/``, …).
2. ``--project`` — ``<cwd>/.cursor/skills``.
3. Environment ``AXIOMPY_SKILLS_DEST`` — path to that same parent directory.
4. ``[tool.axiompy.skills]`` in the nearest ``pyproject.toml`` walking upward from
   ``cwd`` — key ``destination``: ``global``, ``project``, or an absolute path string.
5. Default: ``~/.cursor/skills``.

Usage::

    axiompy-skills --show-config
    axiompy-skills --project
    axiompy-skills install --project --hooks
    axiompy-skills verify-domains --strict
    axiompy-skills resolve --file PATH --line N --json
    axiompy-skills bootstrap suggest
    axiompy-skills doctor --strict
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
    parser = argparse.ArgumentParser(
        prog="axiompy-skills",
        description=(
            "Sync bundled AxiomPy Cursor SKILL.md trees and AAL domain tooling. "
            "Run without a subcommand to sync skills only."
        ),
    )
    _add_sync_flags(parser)

    sub = parser.add_subparsers(dest="command")

    install = sub.add_parser("install", help="Sync skills + AAL registry, hooks, CI templates")
    install.add_argument("--project", action="store_true", help="Install under <cwd>/.cursor/")
    install.add_argument("--hooks", action="store_true", help="Install hooks and aal.mdc rule")
    install.add_argument("--no-ci", action="store_true", help="Skip CI workflow template")
    install.add_argument("--force", action="store_true", help="Overwrite existing config files")
    install.add_argument("--dry-run", action="store_true")

    upgrade = sub.add_parser(
        "upgrade", help="Re-apply manifest-managed paths after package upgrade"
    )
    upgrade.add_argument("--force", action="store_true")
    upgrade.add_argument("--dry-run", action="store_true")

    verify = sub.add_parser("verify-domains", help="Verify @!domain annotations resolve to skills")
    verify.add_argument("--strict", action="store_true")
    verify.add_argument("--files", nargs="+", default=None, help="Only check these paths")

    resolve = sub.add_parser("resolve", help="Resolve domains and skill content for inject")
    resolve.add_argument("--file", required=True)
    resolve.add_argument("--line", type=int, default=None)
    resolve.add_argument("--json", action="store_true")

    bootstrap = sub.add_parser("bootstrap", help="Bootstrap file-level annotations")
    boot_sub = bootstrap.add_subparsers(dest="bootstrap_cmd", required=True)
    boot_sub.add_parser("suggest", help="Suggest domains for unannotated P0 files")
    apply_p = boot_sub.add_parser("apply", help="Apply file-level annotations")
    apply_p.add_argument("--level", choices=["file"], default="file")
    apply_p.add_argument(
        "--apply", action="store_true", help="Write annotations (default: dry-run)"
    )

    annotate = sub.add_parser("annotate", help="Add file-level @!domain to an existing file")
    annotate.add_argument("file")
    annotate.add_argument("--domain", required=True)
    annotate.add_argument("--dry-run", action="store_true")

    doctor = sub.add_parser("doctor", help="Verify AAL installation health")
    doctor.add_argument("--strict", action="store_true")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
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

    if args.command is None:
        return _run_sync(args, cwd)

    root = cwd.resolve()

    if args.command == "install":
        from axiompy.aal.install import InstallOptions, cmd_install

        dest, _ = resolve_skills_destination(cwd=cwd, dest=None, project=args.project)
        opts = InstallOptions(
            root=root,
            project=args.project,
            hooks=args.hooks,
            ci=not args.no_ci,
            force=args.force,
            dry_run=args.dry_run,
        )
        return cmd_install(opts, skills_dest=dest if args.project else None)

    if args.command == "upgrade":
        from axiompy.aal.install import cmd_upgrade

        return cmd_upgrade(root, force=args.force, dry_run=args.dry_run)

    if args.command == "verify-domains":
        from axiompy.aal.verify import cmd_verify_domains

        return cmd_verify_domains(root, args.strict, files=args.files)

    if args.command == "resolve":
        from axiompy.aal.resolve import cmd_resolve

        return cmd_resolve(root, args.file, line=args.line, as_json=args.json)

    if args.command == "bootstrap":
        from axiompy.aal.bootstrap import cmd_bootstrap_apply, cmd_bootstrap_suggest

        if args.bootstrap_cmd == "suggest":
            return cmd_bootstrap_suggest(root)
        return cmd_bootstrap_apply(root, level=args.level, dry_run=not args.apply)

    if args.command == "annotate":
        from axiompy.aal.bootstrap import cmd_annotate

        return cmd_annotate(root, args.file, args.domain, dry_run=args.dry_run)

    if args.command == "doctor":
        from axiompy.aal.doctor import cmd_doctor

        return cmd_doctor(root, strict=args.strict)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
