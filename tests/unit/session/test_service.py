"""Tests for :mod:`cortex.session.service`."""

from __future__ import annotations

import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cortex.session import (
    Checkpoint,
    CheckpointSource,
    GITLESS_COMMIT_PLACEHOLDER,
    SessionMode,
    git,
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

    def test_open_reopen_returns_same_session_while_open(self, service: SessionService) -> None:
        """Re-opening an OPEN session is idempotent: same id, set active."""
        first = service.open(
            spec_id="2026-05-16_foo",
            spec_path=Path("vault/specs/2026-05-16_foo.md"),
        )
        second = service.open(
            spec_id="2026-05-16_foo",
            spec_path=Path("vault/specs/2026-05-16_foo.md"),
        )
        assert first.session_id == "2026-05-16_foo"
        assert second.session_id == "2026-05-16_foo"

    def test_open_after_close_appends_counter(self, service: SessionService) -> None:
        """Once the previous session is closed, a new open appends -2, -3..."""
        first = service.open(
            spec_id="2026-05-16_foo",
            spec_path=Path("vault/specs/2026-05-16_foo.md"),
        )
        from cortex.session.models import SessionStatus as _SS
        service.close(session_id=first.session_id, status=_SS.CLOSED, documenter_decision=_SS.CLOSED)
        second = service.open(
            spec_id="2026-05-16_foo",
            spec_path=Path("vault/specs/2026-05-16_foo.md"),
        )
        service.close(session_id=second.session_id, status=_SS.CLOSED, documenter_decision=_SS.CLOSED)
        third = service.open(
            spec_id="2026-05-16_foo",
            spec_path=Path("vault/specs/2026-05-16_foo.md"),
        )
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


# ---------------------------------------------------------------------------
# .cortex/session.lock — Pi 2.5+net cortex-net integration
# ---------------------------------------------------------------------------


class TestSessionLockFile:
    """``SessionService`` mantiene ``<repo_root>/.cortex/session.lock``
    sincronizado con la sesión activa para que extensiones IDE externas
    (notablemente ``cortex-net.ts`` del bundle Pi 2.5+net) puedan descubrir
    el ``session_id`` sin pasar por el MCP server.

    Formato esperado por ``cortex-net.ts``:
    ``readFileSync(lock, "utf-8").trim()`` → session_id.
    """

    def _lock_path(self, service: SessionService) -> Path:
        return service._repo_root / ".cortex" / "session.lock"  # noqa: SLF001

    def test_open_writes_session_lock(self, service: SessionService) -> None:
        record = service.open(
            spec_id="2026-05-16_lock",
            spec_path=Path("vault/specs/2026-05-16_lock.md"),
        )
        lock = self._lock_path(service)
        assert lock.is_file()
        assert lock.read_text(encoding="utf-8").strip() == record.session_id

    def test_close_clears_session_lock(self, service: SessionService) -> None:
        record = service.open(
            spec_id="2026-05-16_lock",
            spec_path=Path("vault/specs/2026-05-16_lock.md"),
        )
        service.close(
            record.session_id,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        assert not self._lock_path(service).exists()

    def test_set_active_updates_session_lock(self, service: SessionService) -> None:
        first = service.open(
            spec_id="2026-05-16_a",
            spec_path=Path("vault/specs/2026-05-16_a.md"),
        )
        second = service.open(
            spec_id="2026-05-16_b",
            spec_path=Path("vault/specs/2026-05-16_b.md"),
        )
        # tras dos opens, el lock apunta al ultimo (active).
        assert self._lock_path(service).read_text(encoding="utf-8").strip() == second.session_id
        # promover el primero y el lock se actualiza.
        service.set_active(first.session_id)
        assert self._lock_path(service).read_text(encoding="utf-8").strip() == first.session_id

    def test_lock_format_is_plain_text_with_trailing_newline(
        self, service: SessionService
    ) -> None:
        """``cortex-net.ts`` usa ``.trim()``, por lo que el newline final
        es benigno; pero confirmamos el formato esperado: texto plano,
        sin JSON ni frontmatter, terminado en ``\\n``."""
        record = service.open(
            spec_id="2026-05-16_fmt",
            spec_path=Path("vault/specs/2026-05-16_fmt.md"),
        )
        raw = self._lock_path(service).read_bytes()
        assert raw.endswith(b"\n")
        # Sin caracteres de control salvo el newline final.
        assert raw.decode("utf-8") == f"{record.session_id}\n"

    def test_lock_write_is_best_effort_when_dir_missing(
        self, tmp_path: Path, git_repo: Path
    ) -> None:
        """Si ``.cortex/`` no se puede crear, el ciclo de vida de la
        sesión sigue funcionando (el lock es presentación, no SSoT)."""
        storage = SessionStorage(tmp_path / "sessions")
        # Bloqueamos la creacion de .cortex/ poniendo un FILE en su lugar.
        (git_repo / ".cortex").write_text("not-a-directory", encoding="utf-8")
        svc = SessionService(storage, repo_root=git_repo)
        # No debe levantar excepcion.
        record = svc.open(
            spec_id="2026-05-16_besteffort",
            spec_path=Path("vault/specs/2026-05-16_besteffort.md"),
        )
        assert record.session_id.startswith("2026-05-16_besteffort")


# ---------------------------------------------------------------------------
# Fix 2: CORTEX_CODE_DESIGNER counts as a Cortex source (MANAGED)
# ---------------------------------------------------------------------------


class TestDesignerSourceManaged:
    def test_infer_mode_designer_is_managed(self) -> None:
        cp = Checkpoint(timestamp=_utc(2026, 8, 1), source=CheckpointSource.CORTEX_CODE_DESIGNER)
        assert SessionService.infer_mode([cp]) is SessionMode.MANAGED

    def test_close_with_only_designer_checkpoints_is_managed(
        self, service: SessionService
    ) -> None:
        record = service.open(
            spec_id="2026-08-01_designer",
            spec_path=Path("vault/specs/2026-08-01_designer.md"),
        )
        service.checkpoint(record.session_id, source=CheckpointSource.CORTEX_CODE_DESIGNER)
        closed = service.close(
            record.session_id,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        assert closed.mode is SessionMode.MANAGED


# ---------------------------------------------------------------------------
# Fix 3: close() falls back to the gitless placeholder if HEAD capture fails
# ---------------------------------------------------------------------------


class TestCloseGitFallback:
    def test_close_survives_git_error_after_open(
        self, service: SessionService, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        record = service.open(
            spec_id="2026-08-01_brokenhead",
            spec_path=Path("vault/specs/2026-08-01_brokenhead.md"),
        )
        assert not record.is_gitless  # opened on a valid repo

        def _boom(repo_root: Path) -> str:
            raise git.GitError("simulated corrupted .git")

        monkeypatch.setattr(git, "get_head_commit", _boom)
        closed = service.close(
            record.session_id,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        assert closed.status is SessionStatus.CLOSED
        assert closed.end_commit == GITLESS_COMMIT_PLACEHOLDER


# ---------------------------------------------------------------------------
# Fix 1: concurrent checkpoint() calls must not lose updates
# ---------------------------------------------------------------------------


class TestConcurrentCheckpoints:
    def test_two_threads_checkpoint_same_session_no_lost_update(
        self, tmp_path: Path, git_repo: Path
    ) -> None:
        storage = SessionStorage(tmp_path / "sessions")
        service = SessionService(storage, repo_root=git_repo)
        record = service.open(
            spec_id="2026-08-01_race",
            spec_path=Path("vault/specs/2026-08-01_race.md"),
        )

        barrier = threading.Barrier(2)
        errors: list[Exception] = []

        def worker() -> None:
            try:
                barrier.wait()
                service.checkpoint(
                    record.session_id,
                    source=CheckpointSource.MANUAL,
                    note=f"from {threading.current_thread().name}",
                )
            except Exception as exc:  # noqa: BLE001 — collected for assertion
                errors.append(exc)

        threads = [threading.Thread(target=worker, name=f"w{i}") for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == []
        final = service.get(record.session_id)
        assert len(final.checkpoints) == 2
        notes = {cp.note for cp in final.checkpoints}
        assert notes == {"from w0", "from w1"}


# Reference an unused import to keep linters quiet when we ever stop using
# SessionRecord directly in this file.
_ = SessionRecord
