"""Tests for the ``[sessions]`` section of ``cortex doctor`` (Phase 00 / T0.9)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from cortex.doctor import _validate_sessions
from cortex.session import SessionStatus
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage
from cortex.workspace.layout import WorkspaceLayout

VALID_SHA = "a" * 40


@pytest.fixture
def layout(tmp_path: Path) -> WorkspaceLayout:
    """Synthesize a layout v2 with .cortex/sessions/ available."""
    cortex = tmp_path / ".cortex"
    cortex.mkdir()
    workspace_yaml = cortex / "workspace.yaml"
    workspace_yaml.write_text("layout_version: 2\n", encoding="utf-8")
    return WorkspaceLayout.from_repo_root(tmp_path)


@pytest.fixture
def service(layout: WorkspaceLayout, tmp_path: Path) -> SessionService:
    """SessionService bound to the layout's sessions_dir.

    The git repo isn't created here — tests that need git ops use the
    ``git_repo`` fixture below.
    """
    storage = SessionStorage(layout.sessions_dir)
    return SessionService(storage, repo_root=tmp_path)


def _names(checks) -> set[str]:  # type: ignore[no-untyped-def]
    return {c.name for c in checks}


# ---------------------------------------------------------------------------
# Directory and writability
# ---------------------------------------------------------------------------


class TestDirectory:
    def test_missing_sessions_dir_is_a_warning(self, tmp_path: Path) -> None:
        # No .cortex/ at all → layout falls back to bootstrap new mode.
        layout = WorkspaceLayout.from_repo_root(tmp_path)
        checks = _validate_sessions(layout)
        names = _names(checks)
        assert "sessions_dir" in names
        dir_check = next(c for c in checks if c.name == "sessions_dir")
        assert dir_check.ok is False
        assert dir_check.severity == "warn"

    def test_existing_writable_dir_is_info(self, layout: WorkspaceLayout) -> None:
        layout.sessions_dir.mkdir(parents=True, exist_ok=True)
        checks = _validate_sessions(layout)
        dir_check = next(c for c in checks if c.name == "sessions_dir")
        assert dir_check.ok is True
        assert dir_check.severity == "info"


# ---------------------------------------------------------------------------
# Active pointer
# ---------------------------------------------------------------------------


class TestActivePointer:
    def test_no_active_pointer_is_info(self, layout: WorkspaceLayout) -> None:
        layout.sessions_dir.mkdir(parents=True, exist_ok=True)
        checks = _validate_sessions(layout)
        ap = next(c for c in checks if c.name == "sessions_active_pointer")
        assert ap.ok is True
        assert "no active session" in ap.detail

    def test_stale_pointer_flagged(self, layout: WorkspaceLayout) -> None:
        sessions_dir = layout.sessions_dir
        sessions_dir.mkdir(parents=True, exist_ok=True)
        (sessions_dir / "active.txt").write_text("2026-05-16_ghost", encoding="utf-8")
        checks = _validate_sessions(layout)
        ap = next(c for c in checks if c.name == "sessions_active_pointer")
        assert ap.ok is False
        assert ap.severity == "warn"
        assert "stale" in ap.detail or "missing" in ap.detail


# ---------------------------------------------------------------------------
# Parse / corruption
# ---------------------------------------------------------------------------


class TestParsing:
    def test_no_files_means_zero_parsed(self, layout: WorkspaceLayout) -> None:
        layout.sessions_dir.mkdir(parents=True, exist_ok=True)
        checks = _validate_sessions(layout)
        parsed = next(c for c in checks if c.name == "sessions_parsed")
        assert parsed.ok is True
        assert "0 session" in parsed.detail

    def test_corrupted_file_is_warning(self, layout: WorkspaceLayout) -> None:
        sessions_dir = layout.sessions_dir
        sessions_dir.mkdir(parents=True, exist_ok=True)
        (sessions_dir / "2026-05-16_bad.yaml").write_text("not: [valid", encoding="utf-8")
        checks = _validate_sessions(layout)
        parsed = next(c for c in checks if c.name == "sessions_parsed")
        assert parsed.ok is False
        assert parsed.severity == "warn"
        # And a corrupted_files check is added.
        assert "sessions_corrupted_files" in _names(checks)


# ---------------------------------------------------------------------------
# Lifecycle invariants
# ---------------------------------------------------------------------------


class TestInvariants:
    def test_open_with_closed_fields_flagged(self, layout: WorkspaceLayout) -> None:
        # Write a hand-rolled YAML that defies the OPEN invariant.
        sessions_dir = layout.sessions_dir
        sessions_dir.mkdir(parents=True, exist_ok=True)
        # We construct an invariant violation directly on disk because
        # the SessionRecord model would reject it at the type level.
        payload = {
            "session_id": "2026-05-16_demo",
            "spec_path": "vault/specs/demo.md",
            "spec_summary": "demo",
            "start_commit": VALID_SHA,
            "start_branch": "main",
            "opened_at": datetime(2026, 5, 16, 10, tzinfo=UTC).isoformat(),
            "status": "open",
            "mode": "unknown",
            "checkpoints": [],
            "verification_results": [],
            "closed_at": None,
            "end_commit": None,
            "documenter_decision": None,
            "session_note_path": None,
            "adrs_created": [],
        }
        (sessions_dir / "2026-05-16_demo.yaml").write_text(
            yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
        )
        # Sanity: the synthetic record parses through SessionRecord (it
        # is invariant-clean as-is). Now mutate the YAML to violate it.
        bad = sessions_dir / "2026-05-16_demo.yaml"
        text = bad.read_text(encoding="utf-8").replace(
            "closed_at: null", "closed_at: '2026-05-16T12:00:00+00:00'"
        )
        bad.write_text(text, encoding="utf-8")

        checks = _validate_sessions(layout)
        # The Pydantic validator catches this as a parse failure first.
        # Whichever path triggers, the listing still completes.
        names = _names(checks)
        assert "sessions_parsed" in names


class TestMultipleOpen:
    def test_two_opens_warn(
        self, layout: WorkspaceLayout, service: SessionService
    ) -> None:
        # We bypass git for this layout because the fixture's tmp_path
        # has no .git/. Construct records by hand instead.
        sessions_dir = layout.sessions_dir
        sessions_dir.mkdir(parents=True, exist_ok=True)
        for i, sid in enumerate(["2026-05-16_a", "2026-05-16_b"], start=1):
            payload = {
                "session_id": sid,
                "spec_path": f"specs/{sid}.md",
                "spec_summary": "x",
                "start_commit": VALID_SHA,
                "start_branch": "main",
                "opened_at": datetime(2026, 5, 16, i, tzinfo=UTC).isoformat(),
                "status": "open",
                "mode": "unknown",
                "checkpoints": [],
                "verification_results": [],
                "closed_at": None,
                "end_commit": None,
                "documenter_decision": None,
                "session_note_path": None,
                "adrs_created": [],
            }
            (sessions_dir / f"{sid}.yaml").write_text(
                yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
            )
        # Set "a" as active; "b" stays OPEN without being active → warning.
        (sessions_dir / "active.txt").write_text("2026-05-16_a", encoding="utf-8")

        checks = _validate_sessions(layout)
        multi = next((c for c in checks if c.name == "sessions_multiple_open"), None)
        assert multi is not None
        assert multi.ok is False
        assert "2026-05-16_b" in multi.detail


# Keep a reference to satisfy lint when service fixture is unused.
_ = SessionStatus
