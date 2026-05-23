"""Tests for ``cortex.ci.review_session`` (Phase 07 Level 3)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cortex.ci.review_session import (
    close_review_session,
    open_review_session,
    report_ci_checkpoint,
)
from cortex.session import (
    CheckpointSource,
    SessionMode,
    SessionStatus,
)
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
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    return repo


@pytest.fixture
def service(repo: Path, tmp_path: Path) -> SessionService:
    return SessionService(SessionStorage(tmp_path / "sessions"), repo_root=repo)


class TestOpenReviewSession:
    def test_opens_with_supplied_base_commit(self, service: SessionService) -> None:
        rec = open_review_session(
            service,
            spec_id="2026-05-17_pr-42-review",
            base_commit="a" * 40,
            head_branch="feature/x",
            pr_number=42,
        )
        assert rec.start_commit == "a" * 40
        assert rec.start_branch == "feature/x"
        assert "PR #42 review" in rec.spec_summary

    def test_does_not_promote_to_active(self, service: SessionService) -> None:
        active_before = service.get_active()
        open_review_session(
            service,
            spec_id="2026-05-17_pr-99-review",
            base_commit="b" * 40,
            head_branch="feature/y",
            pr_number=99,
        )
        assert service.get_active() == active_before  # active pointer untouched


class TestReportCheckpoint:
    def test_from_validation_payload(self, service: SessionService) -> None:
        rec = open_review_session(
            service,
            spec_id="2026-05-17_pr-1-review",
            base_commit="c" * 40,
            head_branch="feature/z",
            pr_number=1,
        )
        payload = {
            "verification_results": [
                {"name": "tests", "passed": True, "exit_code": 0},
                {"name": "lint", "passed": False, "exit_code": 1},
            ],
            "warnings": ["out-of-scope file: src/y.py"],
            "blockers": [],
            "files_in_diff": ["src/x.py", "src/y.py"],
            "summary_text": "session=… status=warn",
        }
        updated = report_ci_checkpoint(
            service,
            session_id=rec.session_id,
            validation_payload=payload,
        )
        assert len(updated.checkpoints) == 1
        cp = updated.checkpoints[0]
        assert cp.source is CheckpointSource.CI_BOT
        assert any("tests" in c for c in cp.verified_claims)
        assert any("lint" in c for c in cp.unverified_claims)
        assert "src/y.py" in cp.artifacts_touched

    def test_manual_only(self, service: SessionService) -> None:
        rec = open_review_session(
            service,
            spec_id="2026-05-17_pr-2-review",
            base_commit="d" * 40,
            head_branch="feature/w",
            pr_number=2,
        )
        updated = report_ci_checkpoint(
            service,
            session_id=rec.session_id,
            manual_claims=["manual claim"],
            manual_artifacts=["src/x.py"],
            note="initial review",
        )
        cp = updated.checkpoints[0]
        assert cp.verified_claims == ["manual claim"]
        assert cp.artifacts_touched == ["src/x.py"]
        assert cp.note == "initial review"


class TestCloseReviewSession:
    def test_close_marks_terminal_status(self, service: SessionService) -> None:
        rec = open_review_session(
            service,
            spec_id="2026-05-17_pr-3-review",
            base_commit="e" * 40,
            head_branch="feature/v",
            pr_number=3,
        )
        report_ci_checkpoint(
            service,
            session_id=rec.session_id,
            manual_claims=["x"],
            manual_artifacts=["src/x.py"],
        )
        closed = close_review_session(
            service,
            session_id=rec.session_id,
            status=SessionStatus.CLOSED,
        )
        assert closed.status is SessionStatus.CLOSED
        assert closed.mode is SessionMode.CI_REVIEW  # all checkpoints were CI_BOT

    def test_close_with_reason_records_manual_checkpoint(
        self, service: SessionService
    ) -> None:
        rec = open_review_session(
            service,
            spec_id="2026-05-17_pr-4-review",
            base_commit="f" * 40,
            head_branch="feature/u",
            pr_number=4,
        )
        closed = close_review_session(
            service,
            session_id=rec.session_id,
            status=SessionStatus.HANDOFF,
            reason="hooks failed",
        )
        # Reason captured as a manual checkpoint → mixed sources → mode
        # falls back to OBSERVED, not CI_REVIEW.
        assert closed.mode is SessionMode.OBSERVED
        assert any("hooks failed" in cp.note for cp in closed.checkpoints)

    def test_invalid_status_raises(self, service: SessionService) -> None:
        rec = open_review_session(
            service,
            spec_id="2026-05-17_pr-5-review",
            base_commit="0" * 40,
            head_branch="feature/q",
            pr_number=5,
        )
        with pytest.raises(ValueError):
            close_review_session(
                service,
                session_id=rec.session_id,
                status=SessionStatus.OPEN,  # not terminal
            )


class TestInferModeCiReview:
    def test_all_ci_bot_yields_ci_review(self, service: SessionService) -> None:
        rec = open_review_session(
            service,
            spec_id="2026-05-17_pr-6-review",
            base_commit="1" * 40,
            head_branch="feature/p",
            pr_number=6,
        )
        report_ci_checkpoint(
            service,
            session_id=rec.session_id,
            manual_claims=["x"],
            manual_artifacts=["src/x.py"],
        )
        closed = close_review_session(
            service,
            session_id=rec.session_id,
            status=SessionStatus.CLOSED,
        )
        assert closed.mode is SessionMode.CI_REVIEW
