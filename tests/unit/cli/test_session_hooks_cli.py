"""Tests for the ``cortex session hooks ...`` subapp (T3.10)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cortex.cli.session import session_app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Project root that doubles as a git repo (needed by cursor adapter)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git" / "hooks").mkdir(parents=True)
    return repo


class TestHooksList:
    def test_lists_bundled_adapters(self, runner: CliRunner, git_repo: Path) -> None:
        result = runner.invoke(
            session_app,
            ["hooks", "list", "--project-root", str(git_repo), "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        names = {entry["ide"] for entry in payload}
        # Phase 03 shipped 3; Phase 05 added opencode.
        assert {"claude-code", "cursor", "opencode", "pi"} <= names

    def test_initial_state_is_uninstalled(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        result = runner.invoke(
            session_app,
            ["hooks", "list", "--project-root", str(git_repo), "--json"],
        )
        payload = json.loads(result.output)
        assert all(entry["installed"] is False for entry in payload)


class TestHooksInstall:
    def test_install_claude_code(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        result = runner.invoke(
            session_app,
            [
                "hooks",
                "install",
                "--ide",
                "claude-code",
                "--project-root",
                str(git_repo),
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["installed"] is True
        normalized = [p.replace("\\", "/") for p in payload["modified_paths"]]
        assert any(".claude/settings.json" in p for p in normalized)

    def test_install_cursor_creates_post_commit(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        result = runner.invoke(
            session_app,
            [
                "hooks",
                "install",
                "--ide",
                "cursor",
                "--project-root",
                str(git_repo),
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        hook = git_repo / ".git" / "hooks" / "post-commit"
        assert hook.exists()

    def test_install_pi_creates_justfile(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        result = runner.invoke(
            session_app,
            [
                "hooks",
                "install",
                "--ide",
                "pi",
                "--project-root",
                str(git_repo),
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        assert (git_repo / "justfile").exists()

    def test_install_opencode_creates_hooks_md(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        result = runner.invoke(
            session_app,
            [
                "hooks",
                "install",
                "--ide",
                "opencode",
                "--project-root",
                str(git_repo),
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        assert (git_repo / ".opencode" / "hooks.md").exists()

    def test_status_opencode_after_install(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        runner.invoke(
            session_app,
            ["hooks", "install", "--ide", "opencode", "--project-root", str(git_repo)],
        )
        result = runner.invoke(
            session_app,
            [
                "hooks",
                "status",
                "--ide",
                "opencode",
                "--project-root",
                str(git_repo),
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload[0]["installed"] is True

    def test_uninstall_opencode_after_install(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        runner.invoke(
            session_app,
            ["hooks", "install", "--ide", "opencode", "--project-root", str(git_repo)],
        )
        result = runner.invoke(
            session_app,
            [
                "hooks",
                "uninstall",
                "--ide",
                "opencode",
                "--project-root",
                str(git_repo),
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        # File disappears when only the cortex block was inside.
        assert not (git_repo / ".opencode" / "hooks.md").exists()

    def test_install_unknown_ide_exits_1(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        result = runner.invoke(
            session_app,
            [
                "hooks",
                "install",
                "--ide",
                "definitely-not-a-real-ide",
                "--project-root",
                str(git_repo),
            ],
        )
        assert result.exit_code == 1
        assert "unknown" in result.output.lower()

    def test_install_cursor_in_non_git_dir_exits_1(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        result = runner.invoke(
            session_app,
            [
                "hooks",
                "install",
                "--ide",
                "cursor",
                "--project-root",
                str(tmp_path / "no-git"),
            ],
        )
        assert result.exit_code == 1


class TestHooksUninstall:
    def test_uninstall_after_install(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        runner.invoke(
            session_app,
            [
                "hooks",
                "install",
                "--ide",
                "claude-code",
                "--project-root",
                str(git_repo),
                "--json",
            ],
        )
        result = runner.invoke(
            session_app,
            [
                "hooks",
                "uninstall",
                "--ide",
                "claude-code",
                "--project-root",
                str(git_repo),
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["uninstalled"] is True

    def test_uninstall_when_not_installed_is_noop(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        result = runner.invoke(
            session_app,
            [
                "hooks",
                "uninstall",
                "--ide",
                "pi",
                "--project-root",
                str(git_repo),
                "--json",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["uninstalled"] is False


class TestHooksStatus:
    def test_status_single_adapter(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        result = runner.invoke(
            session_app,
            [
                "hooks",
                "status",
                "--ide",
                "claude-code",
                "--project-root",
                str(git_repo),
                "--json",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert len(payload) == 1
        assert payload[0]["ide"] == "claude-code"

    def test_status_all_adapters(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        result = runner.invoke(
            session_app,
            ["hooks", "status", "--project-root", str(git_repo), "--json"],
        )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        ides = {entry["ide"] for entry in payload}
        assert {"claude-code", "cursor", "pi"} <= ides

    def test_status_after_install_reports_installed(
        self, runner: CliRunner, git_repo: Path
    ) -> None:
        runner.invoke(
            session_app,
            [
                "hooks",
                "install",
                "--ide",
                "pi",
                "--project-root",
                str(git_repo),
                "--json",
            ],
        )
        result = runner.invoke(
            session_app,
            [
                "hooks",
                "status",
                "--ide",
                "pi",
                "--project-root",
                str(git_repo),
                "--json",
            ],
        )
        payload = json.loads(result.output)
        assert payload[0]["installed"] is True
