"""Tests for axiompy-skills destination resolution and --show-config."""

from __future__ import annotations

from pathlib import Path

import pytest

from axiompy.cli.cursor_skills import main, resolve_skills_destination


class TestResolveSkillsDestination:
    """Precedence for resolve_skills_destination."""

    def test_cli_dest_wins_over_project(self, tmp_path: Path) -> None:
        cwd = tmp_path / "w"
        cwd.mkdir()
        custom = tmp_path / "out"
        dest, source = resolve_skills_destination(
            cwd=cwd,
            dest=custom,
            project=True,
        )
        assert dest == custom.resolve()
        assert source == "cli_dest"

    def test_cli_project(self, tmp_path: Path) -> None:
        cwd = tmp_path / "proj"
        cwd.mkdir()
        dest, source = resolve_skills_destination(cwd=cwd, dest=None, project=True)
        assert dest == (cwd / ".cursor" / "skills").resolve()
        assert source == "cli_project"

    def test_env_when_no_cli(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cwd = tmp_path / "e"
        cwd.mkdir()
        target = tmp_path / "env_skills"
        monkeypatch.setenv("AXIOMPY_SKILLS_DEST", str(target))
        dest, source = resolve_skills_destination(cwd=cwd, dest=None, project=False)
        assert dest == target.resolve()
        assert source == "env"

    def test_env_over_pyproject(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cwd = tmp_path / "mix"
        cwd.mkdir()
        (cwd / "pyproject.toml").write_text(
            '[tool.axiompy.skills]\ndestination = "project"\n',
            encoding="utf-8",
        )
        env_dir = tmp_path / "from_env"
        monkeypatch.setenv("AXIOMPY_SKILLS_DEST", str(env_dir))
        dest, source = resolve_skills_destination(cwd=cwd, dest=None, project=False)
        assert dest == env_dir.resolve()
        assert source == "env"

    def test_pyproject_nearest(self, tmp_path: Path) -> None:
        root = tmp_path / "repo"
        root.mkdir()
        (root / "pyproject.toml").write_text(
            '[tool.axiompy.skills]\ndestination = "global"\n',
            encoding="utf-8",
        )
        sub = root / "pkg" / "deep"
        sub.mkdir(parents=True)
        (sub / "pyproject.toml").write_text(
            '[tool.axiompy.skills]\ndestination = "project"\n',
            encoding="utf-8",
        )
        dest, source = resolve_skills_destination(cwd=sub, dest=None, project=False)
        assert dest == (sub / ".cursor" / "skills").resolve()
        assert source == "pyproject"

    def test_pyproject_global(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cwd = tmp_path / "g"
        cwd.mkdir()
        (cwd / "pyproject.toml").write_text(
            '[tool.axiompy.skills]\ndestination = "global"\n',
            encoding="utf-8",
        )
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))
        monkeypatch.delenv("USERPROFILE", raising=False)
        dest, source = resolve_skills_destination(cwd=cwd, dest=None, project=False)
        assert dest == fake_home / ".cursor" / "skills"
        assert source == "pyproject"

    def test_pyproject_absolute_path(self, tmp_path: Path) -> None:
        cwd = tmp_path / "abs"
        cwd.mkdir()
        target = tmp_path / "abs_target"
        target.mkdir()
        (cwd / "pyproject.toml").write_text(
            f'[tool.axiompy.skills]\ndestination = "{target.as_posix()}"\n',
            encoding="utf-8",
        )
        dest, source = resolve_skills_destination(cwd=cwd, dest=None, project=False)
        assert dest == target.resolve()
        assert source == "pyproject"

    def test_default_uses_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cwd = tmp_path / "nodc"
        cwd.mkdir()
        monkeypatch.delenv("AXIOMPY_SKILLS_DEST", raising=False)
        fake_home = tmp_path / "h2"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))
        monkeypatch.delenv("USERPROFILE", raising=False)
        dest, source = resolve_skills_destination(cwd=cwd, dest=None, project=False)
        assert dest == fake_home / ".cursor" / "skills"
        assert source == "default"


class TestShowConfig:
    """--show-config prints and does not write."""

    def test_show_config_no_write(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.chdir(tmp_path)
        rc = main(["--show-config"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "skills_parent:" in out
        assert "source: default" in out
        assert not (tmp_path / ".cursor").exists()
