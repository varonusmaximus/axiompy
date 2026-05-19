"""Tests for axiompy.cli.cursor_skills sync CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from axiompy.cli.cursor_skills import (
    _bundle_root,
    list_skills,
    main,
    sync_skills,
)

EXPECTED_SKILLS = [
    "code-review",
    "code-style",
    "design-patterns",
    "documentation",
    "ship-it",
    "testing",
]


class TestBundleRoot:
    """Tests for locating the bundled skills package."""

    def test_bundle_root_is_directory(self):
        bundle = _bundle_root()
        assert bundle.is_dir()

    def test_bundle_contains_skill_dirs(self):
        bundle = _bundle_root()
        skill_dirs = {p.name for p in bundle.iterdir() if p.is_dir()}
        for skill in EXPECTED_SKILLS:
            assert skill in skill_dirs, f"Missing skill directory: {skill}"


class TestListSkills:
    """Tests for listing bundled skills."""

    def test_lists_all_skills(self):
        bundle = _bundle_root()
        skills = list_skills(bundle)
        assert skills == EXPECTED_SKILLS

    def test_list_is_sorted(self):
        bundle = _bundle_root()
        skills = list_skills(bundle)
        assert skills == sorted(skills)


class TestSyncSkills:
    """Tests for syncing skills to a target directory."""

    def test_sync_creates_skill_directories(self, tmp_path: Path):
        bundle = _bundle_root()
        dest = tmp_path / "skills"
        dest.mkdir()

        synced = sync_skills(bundle, dest)

        assert sorted(synced) == EXPECTED_SKILLS
        for skill in EXPECTED_SKILLS:
            assert (dest / skill).is_dir()
            assert (dest / skill / "SKILL.md").is_file()

    def test_sync_copies_sidecars(self, tmp_path: Path):
        bundle = _bundle_root()
        dest = tmp_path / "skills"
        dest.mkdir()

        sync_skills(bundle, dest)

        assert (dest / "code-review" / "reference.md").is_file()

    def test_sync_idempotent(self, tmp_path: Path):
        """Running sync twice yields the same result."""
        bundle = _bundle_root()
        dest = tmp_path / "skills"
        dest.mkdir()

        first = sync_skills(bundle, dest)
        second = sync_skills(bundle, dest)

        assert first == second
        for skill in EXPECTED_SKILLS:
            assert (dest / skill / "SKILL.md").is_file()

    def test_sync_dry_run_does_not_write(self, tmp_path: Path):
        bundle = _bundle_root()
        dest = tmp_path / "skills"
        dest.mkdir()

        synced = sync_skills(bundle, dest, dry_run=True)

        assert len(synced) == len(EXPECTED_SKILLS)
        for skill in EXPECTED_SKILLS:
            assert not (dest / skill).exists()

    def test_sync_no_force_skips_existing(self, tmp_path: Path):
        bundle = _bundle_root()
        dest = tmp_path / "skills"
        dest.mkdir()

        (dest / "code-review").mkdir()
        (dest / "code-review" / "SKILL.md").write_text("custom")

        synced = sync_skills(bundle, dest, force=False)

        assert "code-review" not in synced
        assert (dest / "code-review" / "SKILL.md").read_text() == "custom"

    def test_sync_force_overwrites_existing(self, tmp_path: Path):
        bundle = _bundle_root()
        dest = tmp_path / "skills"
        dest.mkdir()

        (dest / "testing").mkdir()
        (dest / "testing" / "SKILL.md").write_text("old")

        synced = sync_skills(bundle, dest, force=True)

        assert "testing" in synced
        assert (dest / "testing" / "SKILL.md").read_text() != "old"


class TestMainCLI:
    """Integration tests for the CLI entry-point."""

    def test_version_flag(self, capsys: pytest.CaptureFixture[str]):
        rc = main(["--version"])
        assert rc == 0
        assert "axiompy" in capsys.readouterr().out

    def test_list_flag(self, capsys: pytest.CaptureFixture[str]):
        rc = main(["--list"])
        assert rc == 0
        out = capsys.readouterr().out
        for skill in EXPECTED_SKILLS:
            assert skill in out

    def test_sync_to_custom_dest(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
        dest = tmp_path / "custom_skills"
        rc = main(["--dest", str(dest)])
        assert rc == 0
        for skill in EXPECTED_SKILLS:
            assert (dest / skill / "SKILL.md").is_file()

    def test_dry_run_does_not_write(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
        dest = tmp_path / "dry_run_dest"
        rc = main(["--dry-run", "--dest", str(dest)])
        assert rc == 0
        assert not dest.exists()

    def test_project_flag(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        rc = main(["--project"])
        assert rc == 0
        project_dest = tmp_path / ".cursor" / "skills"
        for skill in EXPECTED_SKILLS:
            assert (project_dest / skill / "SKILL.md").is_file()

    def test_default_dest_uses_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        fake_home = tmp_path / "fakehome"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))
        monkeypatch.delenv("USERPROFILE", raising=False)

        rc = main([])
        assert rc == 0

        expected = fake_home / ".cursor" / "skills"
        for skill in EXPECTED_SKILLS:
            assert (expected / skill / "SKILL.md").is_file()
