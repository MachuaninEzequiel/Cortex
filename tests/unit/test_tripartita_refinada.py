"""Tests for the Tripartita Refinada canonical changes (Plan 01).

Groups regression coverage for items §2 (ADR criteria), §3 (CONTEXT.md
path), §5 (handoff status tag), §6 (confidence levels in MemoryEntry).
The schema tests for §8 (AgentHandoff) live in ``test_handoff.py``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cortex.doc_generator import _meets_adr_criteria
from cortex.models import MemoryEntry, PRContext
from cortex.workspace.layout import WorkspaceLayout


# ---------------------------------------------------------------------------
# §2 ADR 3 criteria filter
# ---------------------------------------------------------------------------


class TestMeetsAdrCriteria:
    def _ctx(self, body: str) -> PRContext:
        return PRContext(
            pr_number=1,
            title="t",
            body=body,
            author="dev",
            source_branch="feat/x",
            commit_sha="abc",
        )

    def test_all_three_criteria_present(self) -> None:
        body = (
            "This is a schema migration with major breaking changes. "
            "We decided to go with event sourcing because the alternative "
            "of CRUD was considered and rejected for trade-off reasons."
        )
        assert _meets_adr_criteria(self._ctx(body)) is True

    def test_missing_hard_to_reverse(self) -> None:
        body = "We decided X. Considered alternative Y. Real trade-off explained."
        # No "migration/refactor/schema/breaking/contract" → fail.
        assert _meets_adr_criteria(self._ctx(body)) is False

    def test_missing_surprising(self) -> None:
        body = (
            "Schema migration. Considered alternative X but went with Y. "
            "Rejected the third option."
        )
        # No "decided/rationale/tradeoff/why" → fail.
        assert _meets_adr_criteria(self._ctx(body)) is False

    def test_missing_tradeoff(self) -> None:
        body = (
            "Schema migration with breaking changes. We decided based on "
            "the rationale of long-term maintainability. Why? Because we said so."
        )
        # No "alternative/considered/instead of/rejected" → fail.
        assert _meets_adr_criteria(self._ctx(body)) is False

    def test_empty_body(self) -> None:
        assert _meets_adr_criteria(self._ctx("")) is False

    def test_case_insensitive(self) -> None:
        body = (
            "SCHEMA MIGRATION here. WE DECIDED based on trade-off. "
            "ALTERNATIVE was considered."
        )
        assert _meets_adr_criteria(self._ctx(body)) is True


# ---------------------------------------------------------------------------
# §3 CONTEXT.md path resolution
# ---------------------------------------------------------------------------


class TestContextMdPath:
    def test_new_layout_context_in_workspace_root(self, tmp_path: Path) -> None:
        repo = tmp_path / "myproject"
        repo.mkdir()
        (repo / ".cortex").mkdir()
        (repo / ".cortex" / "workspace.yaml").write_text(
            "layout_version: 2\n", encoding="utf-8"
        )
        (repo / ".cortex" / "config.yaml").write_text("episodic:\n  persist_dir: memory\n", encoding="utf-8")
        (repo / ".git").mkdir()

        layout = WorkspaceLayout.discover(repo)
        assert layout.is_new_layout
        assert layout.context_md_path == repo / ".cortex" / "CONTEXT.md"

    def test_legacy_layout_context_in_repo_root(self, tmp_path: Path) -> None:
        repo = tmp_path / "legacy-proj"
        repo.mkdir()
        (repo / "config.yaml").write_text("episodic:\n  persist_dir: .memory/chroma\n", encoding="utf-8")
        (repo / ".git").mkdir()

        layout = WorkspaceLayout.discover(repo)
        assert layout.is_legacy_layout
        assert layout.context_md_path == repo / "CONTEXT.md"


# ---------------------------------------------------------------------------
# §5 Handoff status tag in episodic memory metadata
# ---------------------------------------------------------------------------


class TestHandoffTag:
    def test_session_writer_tags_include_handoff_when_state_is_handoff(self) -> None:
        from cortex.autopilot.models import AutopilotSessionState, SessionDraft
        from cortex.autopilot.session_writer import IndexingSessionWriter

        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            status="handoff",
        )
        draft = SessionDraft(title="t", body="b", confidence="medium")

        tags = IndexingSessionWriter._build_tags(draft, state)
        assert "handoff" in tags
        assert "session" in tags
        assert "autopilot" in tags

    def test_session_writer_tags_do_not_include_handoff_when_documented(self) -> None:
        from cortex.autopilot.models import AutopilotSessionState, SessionDraft
        from cortex.autopilot.session_writer import IndexingSessionWriter

        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            status="documented",
        )
        draft = SessionDraft(title="t", body="b", confidence="medium")

        tags = IndexingSessionWriter._build_tags(draft, state)
        assert "handoff" not in tags

    def test_build_tags_backwards_compat_without_state(self) -> None:
        """Calling _build_tags(draft) without state must still work."""
        from cortex.autopilot.models import SessionDraft
        from cortex.autopilot.session_writer import IndexingSessionWriter

        draft = SessionDraft(title="t", body="b", confidence="medium")
        tags = IndexingSessionWriter._build_tags(draft)
        assert tags == ["session", "autopilot"]


# ---------------------------------------------------------------------------
# §6 Confidence levels in MemoryEntry
# ---------------------------------------------------------------------------


class TestMemoryEntryConfidence:
    def test_default_confidence_is_none(self) -> None:
        entry = MemoryEntry(content="test")
        assert entry.confidence is None

    def test_confidence_accepts_three_states(self) -> None:
        for value in ("verified", "asserted", "contradicted"):
            entry = MemoryEntry(content="test", confidence=value)  # type: ignore[arg-type]
            assert entry.confidence == value

    def test_invalid_confidence_rejected(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            MemoryEntry(content="test", confidence="probably")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §5 + §6 SessionDraft.confidence_level
# ---------------------------------------------------------------------------


class TestSessionDraftConfidenceLevel:
    def test_default_confidence_level_is_none(self) -> None:
        from cortex.autopilot.models import SessionDraft

        draft = SessionDraft(title="t", body="b")
        assert draft.confidence_level is None

    def test_session_draft_accepts_confidence_level(self) -> None:
        from cortex.autopilot.models import SessionDraft

        draft = SessionDraft(title="t", body="b", confidence_level="verified")
        assert draft.confidence_level == "verified"


# ---------------------------------------------------------------------------
# AutopilotSessionState.status accepts 'handoff'
# ---------------------------------------------------------------------------


class TestSessionStateHandoffStatus:
    def test_status_handoff_accepted(self) -> None:
        from cortex.autopilot.models import AutopilotSessionState

        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            status="handoff",
        )
        assert state.status == "handoff"
