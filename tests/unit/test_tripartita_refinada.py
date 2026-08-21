"""Tests for the Tripartita Refinada canonical changes (Plan 01).

Groups regression coverage for items §2 (ADR criteria), §3 (CONTEXT.md
path), §5 (handoff status tag), §6 (confidence levels in MemoryEntry).
The schema tests for §8 (AgentHandoff) live in ``test_handoff.py``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cortex.models import MemoryEntry
from cortex.workspace.layout import WorkspaceLayout

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


@pytest.mark.skip(
    reason=(
        "Phase 03 retired IndexingSessionWriter + AutopilotSessionState. "
        "The equivalent 'handoff' tagging now lives in "
        "cortex.documenter.persistence — its own tests cover the contract."
    )
)
class TestHandoffTag:
    def test_session_writer_tags_include_handoff_when_state_is_handoff(self) -> None:
        pass

    def test_session_writer_tags_do_not_include_handoff_when_documented(self) -> None:
        pass

    def test_build_tags_backwards_compat_without_state(self) -> None:
        pass


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


@pytest.mark.skip(
    reason=(
        "Phase 03 retired SessionDraft. The equivalent confidence semantics "
        "live in MemoryEntry.confidence — covered by TestMemoryEntryConfidence above."
    )
)
class TestSessionDraftConfidenceLevel:
    def test_default_confidence_level_is_none(self) -> None:
        pass

    def test_session_draft_accepts_confidence_level(self) -> None:
        pass


# ---------------------------------------------------------------------------
# AutopilotSessionState.status accepts 'handoff'
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason=(
        "Phase 03 retired AutopilotSessionState. The HANDOFF status is now "
        "enforced by SessionStatus.HANDOFF in cortex.session.models — covered "
        "by tests/unit/session/test_models.py."
    )
)
class TestSessionStateHandoffStatus:
    def test_status_handoff_accepted(self) -> None:
        pass
