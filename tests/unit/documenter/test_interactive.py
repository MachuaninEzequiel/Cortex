"""Tests for :class:`InteractiveSession` (T4.1)."""

from __future__ import annotations

import io
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console

from cortex.documenter.adr_evaluator import ADRSuggestion
from cortex.documenter.interactive import (
    InteractiveAction,
    InteractiveResult,
    InteractiveSession,
)
from cortex.documenter.reconstruction import ReconstructionOutput
from cortex.documenter.spec_loader import LoadedSpec
from cortex.handoff import AgentHandoff
from cortex.session.models import Checkpoint, CheckpointSource, SessionRecord, SessionStatus

# ── Fixtures ─────────────────────────────────────────────────────────


def _spec() -> LoadedSpec:
    return LoadedSpec(
        path=Path("vault/specs/2026-05-16_demo.md"),
        title="Demo Spec",
        goal="Validate the interactive prompt",
        files_in_scope=[Path("src/a.py")],
        constraints=[],
        acceptance_criteria=["a.py is touched"],
        verification_hooks=[],
        raw_frontmatter={},
    )


def _session_record() -> SessionRecord:
    return SessionRecord(
        session_id="2026-05-16_demo",
        spec_path=Path("vault/specs/2026-05-16_demo.md"),
        spec_summary="demo",
        start_commit="a" * 40,
        start_branch="feature/demo",
        opened_at=datetime.now(UTC),
        checkpoints=[
            Checkpoint(
                timestamp=datetime.now(UTC),
                source=CheckpointSource.MANUAL,
                verified_claims=[],
                unverified_claims=[],
                artifacts_touched=["src/a.py"],
                note="hardcoded the TTL for now",
            )
        ],
    )


def _empty_handoff() -> AgentHandoff:
    return AgentHandoff(
        agent="cortex-documenter",
        status="partial",
        verified_claims=[],
        unverified_claims=[],
        artifacts_produced=[],
        context_for_next=[],
    )


def _reconstruction(
    *,
    suggested_adrs: list[ADRSuggestion] | None = None,
    unimplemented: list[Path] | None = None,
    out_of_scope: list[Path] | None = None,
) -> ReconstructionOutput:
    return ReconstructionOutput(
        session_id="2026-05-16_demo",
        handoff=_empty_handoff(),
        spec=_spec(),
        session_record=_session_record(),
        diff_text="diff --git a/src/a.py b/src/a.py\n+x\n",
        diff_entries=[],
        files_touched=[Path("src/a.py")],
        in_scope_files=[Path("src/a.py")],
        out_of_scope_files=out_of_scope or [],
        unimplemented_files=unimplemented or [],
        verification_results=[],
        contradictions=[],
        suggested_status=SessionStatus.HANDOFF,
        suggested_adrs=suggested_adrs or [],
        raw_checkpoints=_session_record().checkpoints,
        end_commit="b" * 40,
    )


def _console() -> Console:
    return Console(file=io.StringIO(), force_terminal=False, width=120)


def _make_session(inputs: Iterable[str], *, editor_value: str | None = None) -> InteractiveSession:
    queue = list(inputs)
    def input_provider(prompt: str = "") -> str:
        if not queue:
            raise AssertionError(f"InteractiveSession asked for more input than supplied. prompt={prompt!r}")
        return queue.pop(0)
    return InteractiveSession(
        console=_console(),
        input_provider=input_provider,
        editor=lambda seed=None: editor_value,
    )


# ── Top-level actions ───────────────────────────────────────────────


class TestApprove:
    def test_approve_returns_approve_action(self) -> None:
        sess = _make_session(["A"])
        out = sess.prompt(_reconstruction())
        assert out.action is InteractiveAction.APPROVE
        assert out.cancelled is False
        assert out.forced_status is None
        assert out.approved_adr_indices is None

    def test_approve_case_insensitive(self) -> None:
        for raw in ("a", "approve", "APPROVE"):
            sess = _make_session([raw])
            assert sess.prompt(_reconstruction()).action is InteractiveAction.APPROVE


class TestCancel:
    def test_cancel_returns_cancel_action(self) -> None:
        sess = _make_session(["C"])
        out = sess.prompt(_reconstruction())
        assert out.action is InteractiveAction.CANCEL
        assert out.cancelled is True


class TestHandoff:
    def test_handoff_sets_forced_status(self) -> None:
        sess = _make_session(["H", "bcrypt incompatible with Lambda"])
        out = sess.prompt(_reconstruction())
        assert out.action is InteractiveAction.HANDOFF
        assert out.forced_status is SessionStatus.HANDOFF

    def test_handoff_empty_reason_returns_to_main(self) -> None:
        # First H with empty reason → back to main. Then A.
        sess = _make_session(["H", "", "A"])
        out = sess.prompt(_reconstruction())
        assert out.action is InteractiveAction.APPROVE


class TestInvalidInputLoops:
    def test_unknown_letter_re_prompts(self) -> None:
        sess = _make_session(["x", "?", "A"])
        out = sess.prompt(_reconstruction())
        assert out.action is InteractiveAction.APPROVE


# ── Edit flow ───────────────────────────────────────────────────────


class TestEditFlow:
    def test_edit_skip_title_skip_body_no_adrs_then_approve(self) -> None:
        sess = _make_session(["E", "", "N", "A"])
        out = sess.prompt(_reconstruction())
        assert out.action is InteractiveAction.APPROVE
        assert out.edited_note_title is None
        assert out.edited_note_body is None
        assert out.approved_adr_indices is None

    def test_edit_replaces_title(self) -> None:
        sess = _make_session(["E", "Brand new title", "N", "A"])
        out = sess.prompt(_reconstruction())
        assert out.edited_note_title == "Brand new title"

    def test_edit_body_via_editor(self) -> None:
        sess = _make_session(
            ["E", "", "y", "A"],
            editor_value="# Brand new body\n\nNew content here.\n",
        )
        out = sess.prompt(_reconstruction())
        assert out.edited_note_body is not None
        assert "Brand new body" in out.edited_note_body

    def test_edit_body_user_aborts_editor(self) -> None:
        sess = _make_session(["E", "", "y", "A"], editor_value=None)
        out = sess.prompt(_reconstruction())
        assert out.edited_note_body is None

    def test_edit_then_cancel(self) -> None:
        sess = _make_session(["E", "New Title", "N", "C"])
        out = sess.prompt(_reconstruction())
        assert out.action is InteractiveAction.CANCEL

    def test_edit_then_handoff(self) -> None:
        sess = _make_session(["E", "", "N", "H", "blockers exist"])
        out = sess.prompt(_reconstruction())
        assert out.action is InteractiveAction.HANDOFF
        assert out.forced_status is SessionStatus.HANDOFF


# ── ADR review ──────────────────────────────────────────────────────


class TestAdrReview:
    def _adrs(self) -> list[ADRSuggestion]:
        return [
            ADRSuggestion(
                title="ADR 1",
                rationale="rationale 1",
                source_checkpoint_index=0,
                evidence="evidence 1",
                confidence="low",
            ),
            ADRSuggestion(
                title="ADR 2",
                rationale="rationale 2",
                source_checkpoint_index=None,
                evidence="evidence 2",
                confidence="low",
            ),
        ]

    def test_approve_default_keeps_all_adrs(self) -> None:
        recon = _reconstruction(suggested_adrs=self._adrs())
        sess = _make_session(["A"])
        out = sess.prompt(recon)
        assert out.approved_adr_indices is None  # None means "approve all"

    def test_edit_with_reject_one_adr(self) -> None:
        recon = _reconstruction(suggested_adrs=self._adrs())
        # E → skip title → skip body → y for ADR 0 → n for ADR 1 → A
        sess = _make_session(["E", "", "N", "y", "n", "A"])
        out = sess.prompt(recon)
        assert out.approved_adr_indices == [0]

    def test_edit_approve_all_adrs_explicitly(self) -> None:
        recon = _reconstruction(suggested_adrs=self._adrs())
        sess = _make_session(["E", "", "N", "", "y", "A"])
        out = sess.prompt(recon)
        assert out.approved_adr_indices == [0, 1]


# ── Result dataclass smoke ──────────────────────────────────────────


class TestInteractiveResultDataclass:
    def test_cancelled_property(self) -> None:
        assert InteractiveResult(action=InteractiveAction.CANCEL).cancelled is True
        assert InteractiveResult(action=InteractiveAction.APPROVE).cancelled is False
