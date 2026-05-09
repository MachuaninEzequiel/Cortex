"""Tests for cortex.autopilot.session_builder."""
from __future__ import annotations

from datetime import datetime

from cortex.autopilot.models import AutopilotSessionState, AutopilotCheckpoint, SessionDraft
from cortex.autopilot.session_builder import (
    SessionBuilder,
    self_review,
    _scan_placeholders,
    _check_file_consistency,
    _check_evidence,
)


class TestScanPlaceholders:
    def test_finds_todo(self) -> None:
        assert _scan_placeholders("Fix TODO later") == ["TODO"]

    def test_finds_multiple(self) -> None:
        assert set(_scan_placeholders("TODO and FIXME and TBD")) == {"TODO", "FIXME", "TBD"}

    def test_none(self) -> None:
        assert _scan_placeholders("All good") == []


class TestCheckFileConsistency:
    def test_missing_files(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            changed_files=["a.py", "b.py"],
        )
        warnings = _check_file_consistency(state, "Only a.py here")
        assert len(warnings) == 1
        assert "b.py" in warnings[0]

    def test_all_present(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            changed_files=["a.py"],
        )
        warnings = _check_file_consistency(state, "Content with a.py inside")
        assert warnings == []


class TestCheckEvidence:
    def test_claim_without_verification(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            checkpoints=[
                AutopilotCheckpoint(timestamp=datetime.now(), summary="ck", verified=False),
            ],
        )
        warnings = _check_evidence(state, "Tests pass")
        assert len(warnings) == 1
        assert "without verification" in warnings[0]

    def test_claim_with_verification(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            checkpoints=[
                AutopilotCheckpoint(timestamp=datetime.now(), summary="ck", verified=True),
            ],
        )
        warnings = _check_evidence(state, "Tests pass")
        assert warnings == []

    def test_no_claim(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
        )
        warnings = _check_evidence(state, "Some neutral text")
        assert warnings == []


class TestSelfReview:
    def test_placeholder_downgrades(self) -> None:
        draft = SessionDraft(title="X", body="TODO fix this", confidence="high", source_events=1)
        state = AutopilotSessionState(project_root="/repo", workspace_root="/repo/.cortex")
        reviewed = self_review(draft, state)
        assert reviewed.confidence == "auto-draft"
        assert any("TODO" in w for w in reviewed.warnings)

    def test_no_issues_keeps_confidence(self) -> None:
        draft = SessionDraft(title="X", body="All good with a.py", confidence="high", source_events=1)
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            changed_files=["a.py"],
        )
        reviewed = self_review(draft, state)
        assert reviewed.confidence == "high"
        assert reviewed.warnings == []

    def test_file_consistency_warning(self) -> None:
        draft = SessionDraft(title="X", body="Only a.py", confidence="medium", source_events=1)
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            changed_files=["a.py", "b.py"],
        )
        reviewed = self_review(draft, state)
        assert reviewed.confidence == "auto-draft"
        assert any("b.py" in w for w in reviewed.warnings)

    def test_evidence_warning(self) -> None:
        draft = SessionDraft(title="X", body="Tests pass", confidence="high", source_events=1)
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            checkpoints=[
                AutopilotCheckpoint(timestamp=datetime.now(), summary="ck", verified=False),
            ],
        )
        reviewed = self_review(draft, state)
        assert reviewed.confidence == "auto-draft"
        assert any("without verification" in w for w in reviewed.warnings)


class TestSessionBuilder:
    def test_selects_minimal_for_question(self) -> None:
        b = SessionBuilder()
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            detected_task_type="question-only",
        )
        assert b.select_renderer_name(state) == "minimal"

    def test_selects_implementation_for_fast_code(self) -> None:
        b = SessionBuilder()
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            detected_task_type="fast-code",
        )
        assert b.select_renderer_name(state) == "implementation"

    def test_selects_docs_only(self) -> None:
        b = SessionBuilder()
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            detected_task_type="docs-only",
        )
        assert b.select_renderer_name(state) == "docs_only"

    def test_selects_fallback_for_ambiguous(self) -> None:
        b = SessionBuilder()
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            detected_task_type="ambiguous",
        )
        assert b.select_renderer_name(state) == "fallback_draft"

    def test_build_runs_self_review(self) -> None:
        b = SessionBuilder()
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            detected_task_type="fast-code",
            changed_files=["a.py"],
            checkpoints=[
                AutopilotCheckpoint(timestamp=datetime.now(), summary="ck", verified=True),
            ],
        )
        draft = b.build(state)
        assert draft.confidence in ("medium", "high", "auto-draft")
        assert draft.title
        assert draft.body

    def test_build_downgrades_on_issues(self) -> None:
        b = SessionBuilder()
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            detected_task_type="fast-code",
            changed_files=["a.py", "b.py"],
        )
        draft = b.build(state)
        # Implementation renderer lists a.py and b.py, but self-review
        # shouldn't find missing files because they're in the body.
        # Let's force an issue with a placeholder.
        state.user_request = "Fix TODO"
        draft = b.build(state)
        assert draft.confidence == "auto-draft"
        assert any("TODO" in w for w in draft.warnings)
