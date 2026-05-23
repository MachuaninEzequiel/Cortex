"""Tests for :class:`SessionService` operating without a git repository.

Phase 09.A+ added support for opening sessions in workspaces that lack a
usable git repo. The service signals the degraded mode by:

* Recording ``start_commit = GITLESS_COMMIT_PLACEHOLDER`` (40 zeros)
* Recording ``start_branch = ""``
* Returning a :class:`SessionRecord` whose ``is_gitless`` property is True

Downstream calls (``compute_diff``, ``close``) recognise the sentinel and
skip git entirely instead of failing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.session import (
    GITLESS_COMMIT_PLACEHOLDER,
    SessionStatus,
)
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage


@pytest.fixture
def service_no_git(tmp_path: Path) -> SessionService:
    """A SessionService anchored on a directory without git."""
    workspace = tmp_path / "workspace_no_git"
    workspace.mkdir()
    storage = SessionStorage(tmp_path / "sessions")
    return SessionService(storage, repo_root=workspace)


class TestOpenGitless:
    def test_open_uses_placeholder_when_no_git(
        self, service_no_git: SessionService
    ) -> None:
        record = service_no_git.open(
            spec_id="2026-05-18_no-git-demo",
            spec_path=Path("vault/specs/2026-05-18_no-git-demo.md"),
            spec_summary="no git here",
        )
        assert record.start_commit == GITLESS_COMMIT_PLACEHOLDER
        assert record.start_branch == ""
        assert record.is_gitless is True
        assert record.status is SessionStatus.OPEN

    def test_open_gitless_still_sets_active(
        self, service_no_git: SessionService
    ) -> None:
        record = service_no_git.open(
            spec_id="2026-05-18_active",
            spec_path=Path("vault/specs/2026-05-18_active.md"),
        )
        active = service_no_git.get_active()
        assert active is not None
        assert active.session_id == record.session_id
        assert active.is_gitless is True

    def test_open_gitless_logs_warning(
        self,
        service_no_git: SessionService,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        with caplog.at_level("WARNING", logger="cortex.session.service"):
            service_no_git.open(
                spec_id="2026-05-18_warned",
                spec_path=Path("vault/specs/2026-05-18_warned.md"),
            )
        messages = " ".join(r.getMessage() for r in caplog.records)
        assert "gitless mode" in messages


class TestComputeDiffGitless:
    def test_compute_diff_returns_empty_string(
        self, service_no_git: SessionService
    ) -> None:
        record = service_no_git.open(
            spec_id="2026-05-18_diff-test",
            spec_path=Path("vault/specs/2026-05-18_diff-test.md"),
        )
        diff = service_no_git.compute_diff(record.session_id)
        assert diff == ""


class TestCloseGitless:
    def test_close_uses_placeholder_for_end_commit(
        self, service_no_git: SessionService
    ) -> None:
        record = service_no_git.open(
            spec_id="2026-05-18_close-test",
            spec_path=Path("vault/specs/2026-05-18_close-test.md"),
        )
        closed = service_no_git.close(
            record.session_id,
            status=SessionStatus.CLOSED,
            documenter_decision=SessionStatus.CLOSED,
        )
        assert closed.end_commit == GITLESS_COMMIT_PLACEHOLDER
        assert closed.status is SessionStatus.CLOSED
        assert closed.is_gitless is True
