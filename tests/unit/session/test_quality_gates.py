"""Tests for :func:`cortex.session.quality_gates.review_checkpoint`.

Cover the two stages of the review:

Stage 1 — Spec compliance:
    * Artifacts touched within scope.
    * At least one signal of progress (claims or artifacts).

Stage 2 — Quality:
    * No placeholder tokens in note.
    * Test/build claims are non-trivial.

Plus edge case: empty spec scope is treated as a wildcard.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from cortex.documenter.spec_loader import LoadedSpec
from cortex.session.models import Checkpoint, CheckpointSource
from cortex.session.quality_gates import ReviewVerdict, review_checkpoint


def _spec(files_in_scope: list[str] | None = None) -> LoadedSpec:
    return LoadedSpec(
        path=Path("/repo/vault/specs/test.md"),
        title="test spec",
        goal="ensure quality_gates works",
        files_in_scope=[Path(p) for p in (files_in_scope or [])],
        constraints=[],
        acceptance_criteria=[],
        verification_hooks=[],
    )


def _checkpoint(
    *,
    source: CheckpointSource = CheckpointSource.CORTEX_CODE_IMPLEMENTER,
    verified_claims: list[str] | None = None,
    unverified_claims: list[str] | None = None,
    artifacts_touched: list[str] | None = None,
    note: str = "",
) -> Checkpoint:
    return Checkpoint(
        timestamp=datetime(2026, 5, 17, 12, 0, 0, tzinfo=UTC),
        source=source,
        verified_claims=verified_claims or [],
        unverified_claims=unverified_claims or [],
        artifacts_touched=artifacts_touched or [],
        note=note,
    )


class TestStage1SpecCompliance:
    def test_review_accept_when_compliant_and_quality_ok(self) -> None:
        spec = _spec(["src/foo.py", "tests/test_foo.py"])
        ck = _checkpoint(
            verified_claims=["added handler with full unit coverage"],
            artifacts_touched=["src/foo.py"],
            note="foo handler in place, ready for the implementer step",
        )
        verdict = review_checkpoint(ck, spec)
        assert isinstance(verdict, ReviewVerdict)
        assert verdict.accepted is True
        assert verdict.stage_1_passed is True
        assert verdict.stage_2_passed is True
        assert verdict.action == "accept"

    def test_review_redelegate_when_out_of_scope(self) -> None:
        spec = _spec(["src/foo.py"])
        ck = _checkpoint(
            verified_claims=["edited unrelated module"],
            artifacts_touched=["src/foo.py", "src/bar.py"],
            note="touched bar.py too",
        )
        verdict = review_checkpoint(ck, spec)
        assert verdict.accepted is False
        assert verdict.stage_1_passed is False
        assert verdict.action == "redelegate"
        assert "src/bar.py" in verdict.reason

    def test_review_handles_empty_spec_scope_as_wildcard(self) -> None:
        """A spec without ``files_in_scope`` (docs-only / research) accepts any path."""
        spec = _spec([])  # empty scope
        ck = _checkpoint(
            verified_claims=["wrote section 4 of the design doc"],
            artifacts_touched=["docs/design.md"],
            note="design doc ready for review",
        )
        verdict = review_checkpoint(ck, spec)
        assert verdict.accepted is True
        assert verdict.action == "accept"

    def test_review_redelegate_when_no_progress_signal(self) -> None:
        """An empty checkpoint with empty claims AND empty artifacts fails stage 1."""
        spec = _spec(["src/foo.py"])
        ck = _checkpoint()  # all empty
        verdict = review_checkpoint(ck, spec)
        assert verdict.accepted is False
        assert verdict.stage_1_passed is False
        assert verdict.action == "redelegate"


class TestStage2Quality:
    def test_review_warn_when_tbd_in_note(self) -> None:
        spec = _spec(["src/foo.py"])
        ck = _checkpoint(
            verified_claims=["scaffolded handler"],
            artifacts_touched=["src/foo.py"],
            note="handler shape in place; TBD: error path",
        )
        verdict = review_checkpoint(ck, spec)
        assert verdict.accepted is False
        assert verdict.stage_1_passed is True
        assert verdict.stage_2_passed is False
        assert verdict.action == "warn"
        assert "tbd" in verdict.reason.lower()

    def test_review_warn_when_fixme_in_note(self) -> None:
        spec = _spec(["src/foo.py"])
        ck = _checkpoint(
            verified_claims=["wired the new client"],
            artifacts_touched=["src/foo.py"],
            note="works locally — FIXME: retry policy is wrong",
        )
        verdict = review_checkpoint(ck, spec)
        assert verdict.action == "warn"
        assert "fixme" in verdict.reason.lower()

    def test_review_warn_when_test_claims_without_evidence(self) -> None:
        """A bare 'tests' claim is too short to be auditable evidence."""
        spec = _spec(["src/foo.py"])
        ck = _checkpoint(
            verified_claims=["tests"],  # 5 chars — below the 10-char floor
            artifacts_touched=["src/foo.py"],
            note="all good",
        )
        verdict = review_checkpoint(ck, spec)
        assert verdict.accepted is False
        assert verdict.stage_1_passed is True
        assert verdict.stage_2_passed is False
        assert verdict.action == "warn"
        assert "test" in verdict.reason.lower()

    def test_review_accepts_substantive_test_claim(self) -> None:
        """A test claim with detail (>10 chars) passes stage 2."""
        spec = _spec(["src/foo.py"])
        ck = _checkpoint(
            verified_claims=["tests/test_foo.py: 7 passed, 0 failed"],
            artifacts_touched=["src/foo.py"],
            note="suite green",
        )
        verdict = review_checkpoint(ck, spec)
        assert verdict.accepted is True
        assert verdict.action == "accept"
