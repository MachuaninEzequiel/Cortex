"""Tests for the ``cortex session task ...`` CLI subapp (Phase 09.C)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cortex.cli.session import session_app
from cortex.session import Task, TaskStatus
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage

runner = CliRunner()


@pytest.fixture
def repo_with_session(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)
    (repo / ".cortex").mkdir()
    (repo / ".cortex" / "workspace.yaml").write_text(
        "layout_version: 2\n", encoding="utf-8"
    )
    (repo / ".cortex" / "sessions").mkdir()
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)

    storage = SessionStorage(repo / ".cortex" / "sessions")
    service = SessionService(storage, repo_root=repo)
    record = service.open(
        spec_id="2026-05-17_cli-task",
        spec_path=Path("vault/specs/x.md"),
    )
    service.add_task(record.session_id, Task(id="T1", description="explore"))
    service.add_task(record.session_id, Task(id="T2", description="implement"))
    return repo, record.session_id


class TestTaskListCommand:
    def test_lists_all_tasks(self, repo_with_session: tuple[Path, str]) -> None:
        repo, _ = repo_with_session
        result = runner.invoke(
            session_app,
            ["task", "list", "--project-root", str(repo)],
        )
        assert result.exit_code == 0
        assert "T1" in result.stdout
        assert "T2" in result.stdout

    def test_filters_by_status(self, repo_with_session: tuple[Path, str]) -> None:
        repo, _ = repo_with_session
        result = runner.invoke(
            session_app,
            ["task", "list", "--status", "pending", "--project-root", str(repo)],
        )
        assert result.exit_code == 0
        assert "T1" in result.stdout
        assert "T2" in result.stdout

    def test_invalid_status_rejected(self, repo_with_session: tuple[Path, str]) -> None:
        repo, _ = repo_with_session
        result = runner.invoke(
            session_app,
            ["task", "list", "--status", "bogus", "--project-root", str(repo)],
        )
        assert result.exit_code == 1

    def test_json_output(self, repo_with_session: tuple[Path, str]) -> None:
        repo, _ = repo_with_session
        result = runner.invoke(
            session_app,
            ["task", "list", "--json", "--project-root", str(repo)],
        )
        assert result.exit_code == 0
        import json

        payload = json.loads(result.stdout)
        assert isinstance(payload, list)
        assert {t["id"] for t in payload} == {"T1", "T2"}


class TestTaskMutationCommands:
    def test_done_marks_task_complete(
        self, repo_with_session: tuple[Path, str]
    ) -> None:
        repo, session_id = repo_with_session
        result = runner.invoke(
            session_app,
            ["task", "done", "T1", "--project-root", str(repo)],
        )
        assert result.exit_code == 0, result.stdout
        # Re-load and assert status.
        storage = SessionStorage(repo / ".cortex" / "sessions")
        record = storage.load(session_id)
        t1 = next(t for t in record.tasks if t.id == "T1")
        assert t1.status is TaskStatus.DONE
        assert t1.completed_at is not None

    def test_in_progress_marks_active(
        self, repo_with_session: tuple[Path, str]
    ) -> None:
        repo, session_id = repo_with_session
        result = runner.invoke(
            session_app,
            ["task", "in-progress", "T1", "--project-root", str(repo)],
        )
        assert result.exit_code == 0
        storage = SessionStorage(repo / ".cortex" / "sessions")
        record = storage.load(session_id)
        t1 = next(t for t in record.tasks if t.id == "T1")
        assert t1.status is TaskStatus.IN_PROGRESS

    def test_skip_requires_reason(self, repo_with_session: tuple[Path, str]) -> None:
        repo, _ = repo_with_session
        # Missing --reason should fail before any state change.
        result = runner.invoke(
            session_app,
            ["task", "skip", "T1", "--project-root", str(repo)],
        )
        assert result.exit_code != 0

    def test_block_with_reason_records_note(
        self, repo_with_session: tuple[Path, str]
    ) -> None:
        repo, session_id = repo_with_session
        result = runner.invoke(
            session_app,
            [
                "task",
                "block",
                "T2",
                "--reason",
                "waiting for upstream PR",
                "--project-root",
                str(repo),
            ],
        )
        assert result.exit_code == 0, result.stdout
        storage = SessionStorage(repo / ".cortex" / "sessions")
        record = storage.load(session_id)
        t2 = next(t for t in record.tasks if t.id == "T2")
        assert t2.status is TaskStatus.BLOCKED
        assert "waiting" in t2.note

    def test_done_unknown_task_fails(
        self, repo_with_session: tuple[Path, str]
    ) -> None:
        repo, _ = repo_with_session
        result = runner.invoke(
            session_app,
            ["task", "done", "T99", "--project-root", str(repo)],
        )
        assert result.exit_code == 1
