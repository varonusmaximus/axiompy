# @!code-style,testing

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from axiompy.aal import __version__
from axiompy.aal.bundle import bundled_file, load_manifest
from axiompy.aal.constants import BOOTSTRAP_FILE, MANIFEST_FILE, cursor_config_dir_name
from axiompy.aal.domains import skill_path_for_domain
from axiompy.cli.cursor_skills import list_skills, skills_bundle_root, sync_skills


@dataclass
class InstallOptions:
    root: Path
    project: bool = True
    hooks: bool = False
    ci: bool = True
    force: bool = False
    dry_run: bool = False


def _copy_template(src: Path, dest: Path, opts: InstallOptions) -> bool:
    if dest.exists() and not opts.force:
        print(f"  skip (exists): {dest.relative_to(opts.root)}")
        return False
    if opts.dry_run:
        print(f"  would write: {dest.relative_to(opts.root)}")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    if dest.suffix == ".sh":
        dest.chmod(dest.stat().st_mode | 0o111)
    print(f"  wrote: {dest.relative_to(opts.root)}")
    return True


def _generate_domains_yaml(skill_names: list[str]) -> str:
    lines = ["domains:"]
    for name in skill_names:
        lines.append(f"  {name}:")
        lines.append("    skills:")
        lines.append(f"      - {skill_path_for_domain(name)}")
    return "\n".join(lines) + "\n"


def _write_text(dest: Path, content: str, opts: InstallOptions) -> bool:
    if dest.exists() and not opts.force:
        print(f"  skip (exists): {dest.relative_to(opts.root)}")
        return False
    if opts.dry_run:
        print(f"  would write: {dest.relative_to(opts.root)}")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    print(f"  wrote: {dest.relative_to(opts.root)}")
    return True


def cmd_install(opts: InstallOptions, *, skills_dest: Path | None = None) -> int:
    manifest = load_manifest()
    cursor_dir = opts.root / cursor_config_dir_name()
    skills_parent = skills_dest or (cursor_dir / "skills")

    print(f"[AAL] Installing into {opts.root}")

    bundle = skills_bundle_root()
    skill_names = list_skills(bundle)
    print("[AAL] Skills:")
    if opts.dry_run:
        for skill in skill_names:
            print(f"  would sync  {skill}/ -> {skills_parent / skill}")
    else:
        skills_parent.mkdir(parents=True, exist_ok=True)
        sync_skills(bundle, skills_parent, dry_run=False, force=opts.force)

    print("[AAL] Registry:")
    domains_path = cursor_dir / "domains.yaml"
    _write_text(domains_path, _generate_domains_yaml(skill_names), opts)

    for rel in ("aal.yaml", BOOTSTRAP_FILE):
        src = bundled_file(rel)
        if src.is_file():
            _copy_template(src, cursor_dir / rel, opts)

    if opts.hooks:
        print("[AAL] Cursor hooks:")
        _copy_template(bundled_file("cursor/hooks.json"), cursor_dir / "hooks.json", opts)
        _copy_template(
            bundled_file("cursor/hooks/aal-inject.sh"),
            cursor_dir / "hooks" / "aal-inject.sh",
            opts,
        )
        _copy_template(
            bundled_file("cursor/rules/aal.mdc"),
            cursor_dir / "rules" / "aal.mdc",
            opts,
        )

    if opts.ci:
        print("[AAL] CI:")
        _copy_template(
            bundled_file("github/workflows/axiompy-aal-gate.yml"),
            opts.root / ".github" / "workflows" / "axiompy-aal-gate.yml",
            opts,
        )

    managed = manifest.get("managed_paths", [])
    manifest_doc = {
        "version": manifest.get("version", "1.0"),
        "axiompy_version": __version__,
        "managed_paths": managed,
        "skills": skill_names,
    }
    manifest_path = cursor_dir / MANIFEST_FILE
    if opts.dry_run:
        print(f"  would write: {manifest_path.relative_to(opts.root)}")
    else:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest_doc, indent=2) + "\n", encoding="utf-8")
        print(f"  wrote: {manifest_path.relative_to(opts.root)}")

    if opts.dry_run:
        print("\n[AAL] Dry run complete. Re-run without --dry-run to apply.")
        return 0

    print("\n[AAL] Installation complete.")
    print("\nNext steps:")
    print("  1. axiompy-skills bootstrap suggest")
    print("  2. axiompy-skills bootstrap apply --level file")
    print("  3. axiompy-skills verify-domains --strict")
    return 0


def cmd_upgrade(root: Path, *, force: bool = False, dry_run: bool = False) -> int:
    manifest_path = root / cursor_config_dir_name() / MANIFEST_FILE
    if not manifest_path.is_file():
        print(
            "ERROR: missing .cursor/.axiompy-manifest.json — run: axiompy-skills install --project --hooks"
        )
        return 1

    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    opts = InstallOptions(root=root, hooks=True, ci=True, force=force, dry_run=dry_run)
    return cmd_install(opts)
