"""CLI tests for ``cortex session ...`` (Phase 00 / T0.8)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cortex.cli.session import session_app
from cortex.session import SessionStatus
from cortex.session.errors import InvalidStateTransition
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a Cortex-shaped tmpdir with a git repo and .cortex/ layout."""
    # repo root with git
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "seed.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=tmp_path, check=True)

    # Minimal .cortex/ layout — touch only what the layout discovery looks at.
    cortex_dir = tmp_path / ".cortex"
    cortex_dir.mkdir()
    (cortex_dir / "config.yaml").write_text("episodic: {}\n", encoding="utf-8")
    workspace_yaml = cortex_dir / "workspace.yaml"
    workspace_yaml.write_text("layout_version: 2\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def service(project_root: Path) -> SessionService:
    storage = SessionStorage(project_root / ".cortex" / "sessions")
    return SessionService(storage, repo_root=project_root)


# ---------------------------------------------------------------------------
# current
# ---------------------------------------------------------------------------


class TestCurrent:
    def test_no_active_session_text(self, project_root: Path) -> None:
        result = runner.invoke(session_app, ["current", "--project-root", str(project_root)])
        assert result.exit_code == 0
        assert "(no active session)" in result.stdout

    def test_no_active_session_json(self, project_root: Path) -> None:
        result = runner.invoke(
            session_app, ["current", "--project-root", str(project_root), "--json"]
        )
        assert result.exit_code == 0
        assert json.loads(result.stdout)["session_id"] is None

    def test_active_session_text(self, project_root: Path, service: SessionService) -> None:
        service.open(spec_id="2026-05-16_demo", spec_path=Path("vault/specs/demo.md"))
        result = runner.invoke(session_app, ["current", "--project-root", str(project_root)])
        assert result.exit_code == 0
        assert "2026-05-16_demo" in result.stdout


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestList:
    def test_empty_text_output(self, project_root: Path) -> None:
        result = runner.invoke(session_app, ["list", "--project-root", str(project_root)])
        assert result.exit_code == 0
        assert "(no sessions on disk)" in result.stdout

    def test_lists_open_and_closed(self, project_root: Path, service: SessionService) -> None:
        a = service.open(spec_id="2026-05-16_a", spec_path=Path("specs/a.md"))
        service.open(spec_id="2026-05-16_b", spec_path=Path("specs/b.md"))
        service.close(
            a.session_id,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        result = runner.invoke(session_app, ["list", "--project-root", str(project_root)])
        assert result.exit_code == 0
        assert "2026-05-16_a" in result.stdout
        assert "2026-05-16_b" in result.stdout

    def test_filter_by_status(self, project_root: Path, service: SessionService) -> None:
        a = service.open(spec_id="2026-05-16_a", spec_path=Path("specs/a.md"))
        service.open(spec_id="2026-05-16_b", spec_path=Path("specs/b.md"))
        service.close(
            a.session_id,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        result = runner.invoke(
            session_app,
            ["list", "--status", "open", "--project-root", str(project_root)],
        )
        assert result.exit_code == 0
        assert "2026-05-16_b" in result.stdout
        assert "2026-05-16_a" not in result.stdout

    def test_invalid_status_exits_nonzero(self, project_root: Path) -> None:
        result = runner.invoke(
            session_app,
            ["list", "--status", "garbage", "--project-root", str(project_root)],
        )
        assert result.exit_code == 1
        assert "Invalid status" in result.stderr

    def test_json_output(self, project_root: Path, service: SessionService) -> None:
        service.open(spec_id="2026-05-16_a", spec_path=Path("specs/a.md"))
        result = runner.invoke(session_app, ["list", "--project-root", str(project_root), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data and data[0]["session_id"] == "2026-05-16_a"


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------


class TestShow:
    @staticmethod
    def _plain(text: str) -> str:
        """Strip ANSI escapes so assertions match the rendered text."""
        return re.sub(r"\x1b\[[0-9;]*m", "", text)

    def test_show_active(self, project_root: Path, service: SessionService) -> None:
        service.open(spec_id="2026-05-16_demo", spec_path=Path("specs/demo.md"))
        result = runner.invoke(session_app, ["show", "--project-root", str(project_root)])
        assert result.exit_code == 0
        plain = self._plain(result.stdout)
        assert "2026-05-16_demo" in plain
        assert "status:" in plain

    def test_show_explicit_id(self, project_root: Path, service: SessionService) -> None:
        service.open(spec_id="2026-05-16_demo", spec_path=Path("specs/demo.md"))
        result = runner.invoke(
            session_app,
            ["show", "2026-05-16_demo", "--project-root", str(project_root)],
        )
        assert result.exit_code == 0
        assert "2026-05-16_demo" in self._plain(result.stdout)

    def test_show_missing_id_errors(self, project_root: Path) -> None:
        result = runner.invoke(
            session_app, ["show", "2026-05-16_missing", "--project-root", str(project_root)]
        )
        assert result.exit_code == 1
        assert "not found" in result.stderr

    def test_show_no_active_no_id_errors(self, project_root: Path) -> None:
        result = runner.invoke(session_app, ["show", "--project-root", str(project_root)])
        assert result.exit_code == 1
        assert "No active session" in result.stderr

    def test_show_json(self, project_root: Path, service: SessionService) -> None:
        service.open(spec_id="2026-05-16_demo", spec_path=Path("specs/demo.md"))
        result = runner.invoke(
            session_app,
            ["show", "--project-root", str(project_root), "--json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["session_id"] == "2026-05-16_demo"
        assert data["status"] == "open"


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------


class TestDiff:
    def test_no_changes_returns_friendly_message(
        self, project_root: Path, service: SessionService
    ) -> None:
        service.open(spec_id="2026-05-16_demo", spec_path=Path("specs/demo.md"))
        result = runner.invoke(session_app, ["diff", "--project-root", str(project_root)])
        assert result.exit_code == 0
        assert "no diff" in result.stdout

    def test_diff_shows_added_file(self, project_root: Path, service: SessionService) -> None:
        service.open(spec_id="2026-05-16_demo", spec_path=Path("specs/demo.md"))
        (project_root / "added.md").write_text("hello\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=project_root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "add"], cwd=project_root, check=True)
        result = runner.invoke(session_app, ["diff", "--project-root", str(project_root)])
        assert result.exit_code == 0
        assert "added.md" in result.stdout


# ---------------------------------------------------------------------------
# switch
# ---------------------------------------------------------------------------


class TestSwitch:
    def test_switch_validates_existence(self, project_root: Path) -> None:
        result = runner.invoke(
            session_app,
            ["switch", "2026-05-16_missing", "--project-root", str(project_root)],
        )
        assert result.exit_code == 1

    def test_switch_rejects_closed(self, project_root: Path, service: SessionService) -> None:
        a = service.open(spec_id="2026-05-16_demo", spec_path=Path("specs/demo.md"))
        service.close(
            a.session_id,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        result = runner.invoke(
            session_app,
            ["switch", "2026-05-16_demo", "--project-root", str(project_root)],
        )
        assert result.exit_code == 1

    def test_switch_changes_active(self, project_root: Path, service: SessionService) -> None:
        service.open(spec_id="2026-05-16_a", spec_path=Path("specs/a.md"))
        service.open(spec_id="2026-05-16_b", spec_path=Path("specs/b.md"))
        # By default the latest open is active. Switch back to "a".
        result = runner.invoke(
            session_app,
            ["switch", "2026-05-16_a", "--project-root", str(project_root)],
        )
        assert result.exit_code == 0
        current = runner.invoke(session_app, ["current", "--project-root", str(project_root)])
        assert "2026-05-16_a" in current.stdout


# ---------------------------------------------------------------------------
# abandon
# ---------------------------------------------------------------------------


class TestAbandon:
    def test_abandon_with_confirmation(self, project_root: Path, service: SessionService) -> None:
        service.open(spec_id="2026-05-16_demo", spec_path=Path("specs/demo.md"))
        result = runner.invoke(
            session_app,
            [
                "abandon",
                "2026-05-16_demo",
                "--reason",
                "not pursued",
                "--yes",
                "--project-root",
                str(project_root),
            ],
        )
        assert result.exit_code == 0
        record = service.get("2026-05-16_demo")
        assert record.status is SessionStatus.ABANDONED

    def test_abandon_decline_at_prompt(self, project_root: Path, service: SessionService) -> None:
        service.open(spec_id="2026-05-16_demo", spec_path=Path("specs/demo.md"))
        result = runner.invoke(
            session_app,
            [
                "abandon",
                "2026-05-16_demo",
                "--reason",
                "nope",
                "--project-root",
                str(project_root),
            ],
            input="n\n",
        )
        assert result.exit_code == 0
        assert "aborted" in result.stdout
        record = service.get("2026-05-16_demo")
        assert record.status is SessionStatus.OPEN  # untouched


# ---------------------------------------------------------------------------
# Sanity guard for the unused import (kept for typing reference).
# ---------------------------------------------------------------------------


_ = InvalidStateTransition
