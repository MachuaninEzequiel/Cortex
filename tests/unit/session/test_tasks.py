"""Tests for the Pluggable Middle Phase 09.C ``Task`` primitive."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from cortex.session import (
    SessionStatus,
    Task,
    TaskStatus,
)
from cortex.session.errors import InvalidStateTransition
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)
    (repo / "src").mkdir()
    (repo / "src" / "x.py").write_text("def f(): return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    return repo


@pytest.fixture
def service(repo: Path, tmp_path: Path) -> SessionService:
    storage = SessionStorage(tmp_path / "sessions")
    return SessionService(storage, repo_root=repo)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class TestTaskModel:
    @pytest.mark.parametrize("good", ["T1", "T1.2", "T1.2.3", "T42"])
    def test_id_pattern_accepts_valid(self, good: str) -> None:
        Task(id=good, description="x")

    @pytest.mark.parametrize("bad", ["task-1", "t-1", "1", "T", "T1-2", "TT1"])
    def test_id_pattern_rejects_invalid(self, bad: str) -> None:
        with pytest.raises(ValidationError):
            Task(id=bad, description="x")

    def test_default_status_is_pending(self) -> None:
        t = Task(id="T1", description="x")
        assert t.status is TaskStatus.PENDING
        assert t.completed_at is None

    def test_done_requires_completed_at(self) -> None:
        with pytest.raises(ValidationError):
            Task(id="T1", description="x", status=TaskStatus.DONE)

    def test_pending_must_not_have_completed_at(self) -> None:
        with pytest.raises(ValidationError):
            Task(
                id="T1",
                description="x",
                status=TaskStatus.PENDING,
                completed_at=datetime.now(UTC),
            )


# ---------------------------------------------------------------------------
# SessionRecord compat
# ---------------------------------------------------------------------------


class TestSessionRecordTasksField:
    def test_default_empty_list(self, service: SessionService) -> None:
        record = service.open(
            spec_id="2026-05-17_demo",
            spec_path=Path("vault/specs/demo.md"),
        )
        assert record.tasks == []

    def test_session_without_tasks_round_trips(self, service: SessionService) -> None:
        """A fresh session loads without tasks (forward-compat for legacy YAML)."""
        rec = service.open(
            spec_id="2026-05-17_demo",
            spec_path=Path("vault/specs/demo.md"),
        )
        loaded = service.get(rec.session_id)
        assert loaded.tasks == []


# ---------------------------------------------------------------------------
# Service API
# ---------------------------------------------------------------------------


class TestSessionServiceTaskApi:
    def test_add_task_appends_to_record(self, service: SessionService) -> None:
        rec = service.open(
            spec_id="2026-05-17_add",
            spec_path=Path("vault/specs/x.md"),
        )
        service.add_task(rec.session_id, Task(id="T1", description="prep"))
        loaded = service.get(rec.session_id)
        assert [t.id for t in loaded.tasks] == ["T1"]

    def test_add_task_rejects_duplicate_id(self, service: SessionService) -> None:
        rec = service.open(
            spec_id="2026-05-17_dup",
            spec_path=Path("vault/specs/x.md"),
        )
        service.add_task(rec.session_id, Task(id="T1", description="a"))
        with pytest.raises(ValueError, match="already exists"):
            service.add_task(rec.session_id, Task(id="T1", description="b"))

    def test_update_task_status_to_done_stamps_completed_at(
        self, service: SessionService
    ) -> None:
        rec = service.open(
            spec_id="2026-05-17_done",
            spec_path=Path("vault/specs/x.md"),
        )
        service.add_task(rec.session_id, Task(id="T1", description="a"))
        updated = service.update_task_status(rec.session_id, "T1", TaskStatus.DONE)
        assert updated.tasks[0].status is TaskStatus.DONE
        assert updated.tasks[0].completed_at is not None

    def test_update_task_status_clears_completed_at_on_revert(
        self, service: SessionService
    ) -> None:
        rec = service.open(
            spec_id="2026-05-17_revert",
            spec_path=Path("vault/specs/x.md"),
        )
        service.add_task(rec.session_id, Task(id="T1", description="a"))
        service.update_task_status(rec.session_id, "T1", TaskStatus.DONE)
        reverted = service.update_task_status(rec.session_id, "T1", TaskStatus.PENDING)
        assert reverted.tasks[0].completed_at is None

    def test_update_task_missing_id_raises(self, service: SessionService) -> None:
        rec = service.open(
            spec_id="2026-05-17_miss",
            spec_path=Path("vault/specs/x.md"),
        )
        with pytest.raises(ValueError, match="not found"):
            service.update_task_status(rec.session_id, "T99", TaskStatus.DONE)

    def test_list_tasks_filters_by_status(self, service: SessionService) -> None:
        rec = service.open(
            spec_id="2026-05-17_filter",
            spec_path=Path("vault/specs/x.md"),
        )
        service.add_task(rec.session_id, Task(id="T1", description="a"))
        service.add_task(rec.session_id, Task(id="T2", description="b"))
        service.update_task_status(rec.session_id, "T1", TaskStatus.DONE)

        done = service.list_tasks(rec.session_id, status=TaskStatus.DONE)
        pending = service.list_tasks(rec.session_id, status=TaskStatus.PENDING)
        assert [t.id for t in done] == ["T1"]
        assert [t.id for t in pending] == ["T2"]

    def test_add_task_to_closed_session_raises(self, service: SessionService) -> None:
        rec = service.open(
            spec_id="2026-05-17_closed",
            spec_path=Path("vault/specs/x.md"),
        )
        # Close it.
        service.close(
            rec.session_id,
            status=SessionStatus.ABANDONED,
            documenter_decision=SessionStatus.ABANDONED,
        )
        with pytest.raises(InvalidStateTransition):
            service.add_task(rec.session_id, Task(id="T1", description="x"))
