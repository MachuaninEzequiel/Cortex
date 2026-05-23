"""Tests for :mod:`cortex.session.service`."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cortex.session import (
    Checkpoint,
    CheckpointSource,
    SessionMode,
    SessionRecord,
    SessionStatus,
)
from cortex.session.errors import InvalidStateTransition, SessionNotFound
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage

VALID_SHA = "a" * 40


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo,
        check=True,
    )
    (repo / "seed.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    return repo


@pytest.fixture
def service(tmp_path: Path, git_repo: Path) -> SessionService:
    storage = SessionStorage(tmp_path / "sessions")
    return SessionService(storage, repo_root=git_repo)


def _utc(year: int, month: int, day: int, hour: int = 12) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)


def _add_commit(repo: Path, file_name: str, content: str = "x") -> None:
    (repo / file_name).write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"add {file_name}"], cwd=repo, check=True)


# ---------------------------------------------------------------------------
# open
# ---------------------------------------------------------------------------


class TestOpen:
    def test_open_creates_record_and_sets_active(self, service: SessionService) -> None:
        record = service.open(
            spec_id="2026-05-16_demo",
            spec_path=Path("vault/specs/2026-05-16_demo.md"),
            spec_summary="demo",
        )
        assert record.session_id == "2026-05-16_demo"
        assert record.status is SessionStatus.OPEN
        assert record.start_commit and len(record.start_commit) == 40
        assert record.start_branch == "main"
        assert service.get_active().session_id == "2026-05-16_demo"  # type: ignore[union-attr]

    def test_open_duplicate_id_appends_counter(self, service: SessionService) -> None:
        first = service.open(
            spec_id="2026-05-16_foo",
            spec_path=Path("vault/specs/2026-05-16_foo.md"),
        )
        second = service.open(
            spec_id="2026-05-16_foo",
            spec_path=Path("vault/specs/2026-05-16_foo.md"),
        )
        third = service.open(
            spec_id="2026-05-16_foo",
            spec_path=Path("vault/specs/2026-05-16_foo.md"),
        )
        assert first.session_id == "2026-05-16_foo"
        assert second.session_id == "2026-05-16_foo-2"
        assert third.session_id == "2026-05-16_foo-3"


# ---------------------------------------------------------------------------
# checkpoint
# ---------------------------------------------------------------------------


class TestCheckpoint:
    def test_checkpoint_appends_to_open_session(self, service: SessionService) -> None:
        record = service.open(
            spec_id="2026-05-16_demo",
            spec_path=Path("vault/specs/2026-05-16_demo.md"),
        )
        updated = service.checkpoint(
            record.session_id,
            source=CheckpointSource.CORTEX_SDDWORK,
            verified_claims=["did thing"],
            note="ok",
        )
        assert len(updated.checkpoints) == 1
        assert updated.checkpoints[0].source is CheckpointSource.CORTEX_SDDWORK
        assert updated.checkpoints[0].verified_claims == ["did thing"]
        # Persisted as well.
        reloaded = service.get(record.session_id)
        assert reloaded.checkpoints == updated.checkpoints

    def test_checkpoint_rejects_closed_session(self, service: SessionService) -> None:
        record = service.open(
            spec_id="2026-05-16_demo",
            spec_path=Path("vault/specs/2026-05-16_demo.md"),
        )
        service.close(
            record.session_id,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        with pytest.raises(InvalidStateTransition):
            service.checkpoint(record.session_id, source=CheckpointSource.MANUAL)


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestClose:
    def test_close_captures_end_commit_and_clears_active(
        self, service: SessionService, git_repo: Path
    ) -> None:
        record = service.open(
            spec_id="2026-05-16_demo",
            spec_path=Path("vault/specs/2026-05-16_demo.md"),
        )
        _add_commit(git_repo, "new.md")

        closed = service.close(
            record.session_id,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
            session_note_path=Path("vault/sessions/2026-05-16_demo.md"),
        )
        assert closed.status is SessionStatus.CLOSED
        assert closed.end_commit and closed.end_commit != record.start_commit
        assert closed.closed_at is not None
        assert closed.session_note_path == Path("vault/sessions/2026-05-16_demo.md")
        # Active pointer cleared.
        assert service.get_active() is None

    def test_close_infers_mode_byo_without_checkpoints(self, service: SessionService) -> None:
        record = service.open(
            spec_id="2026-05-16_demo",
            spec_path=Path("vault/specs/2026-05-16_demo.md"),
        )
        closed = service.close(
            record.session_id,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        assert closed.mode is SessionMode.BYO

    def test_close_infers_mode_managed_with_cortex_checkpoints(
        self, service: SessionService
    ) -> None:
        record = service.open(
            spec_id="2026-05-16_demo",
            spec_path=Path("vault/specs/2026-05-16_demo.md"),
        )
        service.checkpoint(record.session_id, source=CheckpointSource.CORTEX_SDDWORK)
        service.checkpoint(record.session_id, source=CheckpointSource.CORTEX_CODE_EXPLORER)
        closed = service.close(
            record.session_id,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        assert closed.mode is SessionMode.MANAGED

    def test_close_infers_mode_observed_with_ide_hook(self, service: SessionService) -> None:
        record = service.open(
            spec_id="2026-05-16_demo",
            spec_path=Path("vault/specs/2026-05-16_demo.md"),
        )
        service.checkpoint(record.session_id, source=CheckpointSource.IDE_HOOK)
        closed = service.close(
            record.session_id,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        assert closed.mode is SessionMode.OBSERVED

    def test_close_rejects_non_terminal_status(self, service: SessionService) -> None:
        record = service.open(
            spec_id="2026-05-16_demo",
            spec_path=Path("vault/specs/2026-05-16_demo.md"),
        )
        with pytest.raises(ValueError, match="terminal"):
            service.close(
                record.session_id,
                status=SessionStatus.OPEN,
                documenter_decision=SessionStatus.OPEN,
            )

    def test_close_rejects_already_closed(self, service: SessionService) -> None:
        record = service.open(
            spec_id="2026-05-16_demo",
            spec_path=Path("vault/specs/2026-05-16_demo.md"),
        )
        service.close(
            record.session_id,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        with pytest.raises(InvalidStateTransition):
            service.close(
                record.session_id,
                status=SessionStatus.CLOSED,
                documenter_decision=SessionStatus.CLOSED,
            )


# ---------------------------------------------------------------------------
# abandon
# ---------------------------------------------------------------------------


class TestAbandon:
    def test_abandon_closes_with_abandoned_status_and_records_reason(
        self, service: SessionService
    ) -> None:
        record = service.open(
            spec_id="2026-05-16_demo",
            spec_path=Path("vault/specs/2026-05-16_demo.md"),
        )
        abandoned = service.abandon(record.session_id, reason="not pursued")
        assert abandoned.status is SessionStatus.ABANDONED
        assert abandoned.documenter_decision is SessionStatus.ABANDONED
        # The reason is captured as a MANUAL checkpoint for traceability.
        assert any(
            cp.source is CheckpointSource.MANUAL and "not pursued" in cp.note
            for cp in abandoned.checkpoints
        )


# ---------------------------------------------------------------------------
# Active pointer
# ---------------------------------------------------------------------------


class TestActive:
    def test_get_active_returns_none_when_no_active(self, service: SessionService) -> None:
        assert service.get_active() is None

    def test_get_active_returns_none_on_stale_pointer(
        self,
        service: SessionService,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # Force a stale pointer by writing the file manually.
        service._storage.set_active_session_id("2026-05-16_missing")  # type: ignore[reportPrivateUsage]
        import logging

        with caplog.at_level(logging.WARNING, logger="cortex.session.service"):
            assert service.get_active() is None
        assert any("missing" in rec.message for rec in caplog.records)

    def test_set_active_validates_existence(self, service: SessionService) -> None:
        with pytest.raises(SessionNotFound):
            service.set_active("2026-05-16_missing")

    def test_set_active_rejects_closed_session(self, service: SessionService) -> None:
        record = service.open(
            spec_id="2026-05-16_demo",
            spec_path=Path("vault/specs/2026-05-16_demo.md"),
        )
        service.close(
            record.session_id,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        with pytest.raises(InvalidStateTransition):
            service.set_active(record.session_id)

    def test_set_active_promotes_open_session(self, service: SessionService) -> None:
        # Open two sessions; the second becomes active. Switching back must
        # actually update the pointer.
        first = service.open(
            spec_id="2026-05-16_first",
            spec_path=Path("vault/specs/first.md"),
        )
        second = service.open(
            spec_id="2026-05-16_second",
            spec_path=Path("vault/specs/second.md"),
        )
        assert service.get_active() == second
        service.set_active(first.session_id)
        active = service.get_active()
        assert active is not None
        assert active.session_id == first.session_id


# ---------------------------------------------------------------------------
# compute_diff
# ---------------------------------------------------------------------------


class TestComputeDiff:
    def test_compute_diff_open_session_uses_head(
        self, service: SessionService, git_repo: Path
    ) -> None:
        record = service.open(
            spec_id="2026-05-16_demo",
            spec_path=Path("vault/specs/2026-05-16_demo.md"),
        )
        _add_commit(git_repo, "added.md", content="added\n")
        diff_text = service.compute_diff(record.session_id)
        assert "added.md" in diff_text

    def test_compute_diff_closed_session_uses_end_commit(
        self, service: SessionService, git_repo: Path
    ) -> None:
        record = service.open(
            spec_id="2026-05-16_demo",
            spec_path=Path("vault/specs/2026-05-16_demo.md"),
        )
        _add_commit(git_repo, "added.md", content="added\n")
        service.close(
            record.session_id,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        # After close, further commits should NOT appear in the diff.
        _add_commit(git_repo, "post.md", content="post\n")
        diff_text = service.compute_diff(record.session_id)
        assert "added.md" in diff_text
        assert "post.md" not in diff_text


# ---------------------------------------------------------------------------
# infer_mode static helper
# ---------------------------------------------------------------------------


class TestInferModeStatic:
    def _cp(self, source: CheckpointSource) -> Checkpoint:
        return Checkpoint(timestamp=_utc(2026, 5, 16), source=source)

    def test_no_checkpoints_byo(self) -> None:
        assert SessionService.infer_mode([]) is SessionMode.BYO

    def test_only_sddwork_managed(self) -> None:
        assert (
            SessionService.infer_mode([self._cp(CheckpointSource.CORTEX_SDDWORK)])
            is SessionMode.MANAGED
        )

    def test_mixed_cortex_only_managed(self) -> None:
        cps = [
            self._cp(CheckpointSource.CORTEX_SYNC),
            self._cp(CheckpointSource.CORTEX_SDDWORK),
            self._cp(CheckpointSource.CORTEX_CODE_EXPLORER),
            self._cp(CheckpointSource.CORTEX_CODE_IMPLEMENTER),
        ]
        assert SessionService.infer_mode(cps) is SessionMode.MANAGED

    def test_ide_hook_observed(self) -> None:
        assert (
            SessionService.infer_mode([self._cp(CheckpointSource.IDE_HOOK)]) is SessionMode.OBSERVED
        )

    def test_user_skill_observed(self) -> None:
        assert (
            SessionService.infer_mode([self._cp(CheckpointSource.USER_SKILL)])
            is SessionMode.OBSERVED
        )

    def test_manual_observed(self) -> None:
        assert (
            SessionService.infer_mode([self._cp(CheckpointSource.MANUAL)]) is SessionMode.OBSERVED
        )

    def test_mixed_cortex_and_external_observed(self) -> None:
        cps = [
            self._cp(CheckpointSource.CORTEX_SDDWORK),
            self._cp(CheckpointSource.IDE_HOOK),
        ]
        assert SessionService.infer_mode(cps) is SessionMode.OBSERVED


# ---------------------------------------------------------------------------
# list passthrough
# ---------------------------------------------------------------------------


class TestList:
    def test_list_all_and_filter(self, service: SessionService) -> None:
        a = service.open(spec_id="2026-05-16_a", spec_path=Path("specs/a.md"))
        service.open(spec_id="2026-05-16_b", spec_path=Path("specs/b.md"))
        service.close(
            a.session_id,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        all_records = service.list()
        opens = service.list(SessionStatus.OPEN)
        closeds = service.list(SessionStatus.CLOSED)
        assert {r.session_id for r in all_records} == {"2026-05-16_a", "2026-05-16_b"}
        assert {r.session_id for r in opens} == {"2026-05-16_b"}
        assert {r.session_id for r in closeds} == {"2026-05-16_a"}


# Reference an unused import to keep linters quiet when we ever stop using
# SessionRecord directly in this file.
_ = SessionRecord
