# @!testing

"""Ensure authoring (.cursor/skills) matches the shipped bundle (bundles/axiompy_skills)."""

from __future__ import annotations

import filecmp
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CURSOR_SKILLS = REPO_ROOT / ".cursor" / "skills"
BUNDLE_SKILLS = REPO_ROOT / "bundles" / "axiompy_skills"


def _skill_name_to_path(skills_root: Path) -> dict[str, Path]:
    """Map skill name -> directory for each child containing SKILL.md."""
    if not skills_root.is_dir():
        return {}
    out: dict[str, Path] = {}
    for child in skills_root.iterdir():
        if child.is_dir() and (child / "SKILL.md").is_file():
            out[child.name] = child
    return out


def _list_files_under(skill_dir: Path) -> list[Path]:
    """Sorted relative paths for all files (not dirs), excluding __pycache__."""
    files: list[Path] = []
    for p in skill_dir.rglob("*"):
        if "__pycache__" in p.parts:
            continue
        if p.is_file():
            files.append(p.relative_to(skill_dir))
    return sorted(files)


def test_authoring_and_bundle_skills_match() -> None:
    """Skill names and markdown (and other) file contents must match."""
    assert CURSOR_SKILLS.is_dir(), f"Missing authoring tree: {CURSOR_SKILLS}"
    assert BUNDLE_SKILLS.is_dir(), f"Missing bundle tree: {BUNDLE_SKILLS}"

    cursor_map = _skill_name_to_path(CURSOR_SKILLS)
    bundle_map = _skill_name_to_path(BUNDLE_SKILLS)

    assert cursor_map.keys() == bundle_map.keys(), (
        f"Skill set mismatch.\n  .cursor/skills: {sorted(cursor_map)}\n"
        f"  bundles/axiompy_skills: {sorted(bundle_map)}"
    )

    for name in sorted(cursor_map):
        a = cursor_map[name]
        b = bundle_map[name]
        files_a = _list_files_under(a)
        files_b = _list_files_under(b)
        assert files_a == files_b, f"{name}: file lists differ:\n  {files_a}\n  {files_b}"
        for rel in files_a:
            fa = a / rel
            fb = b / rel
            assert filecmp.cmp(fa, fb, shallow=False), (
                f"{name}/{rel}: content differs between authoring and bundle"
            )
