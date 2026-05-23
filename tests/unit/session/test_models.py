"""Tests for :mod:`cortex.session.models`.

Covers the invariants documented in Phase 00 task T0.1:
    - session_id pattern (positive + negative)
    - lifecycle invariants (OPEN vs terminal)
    - commit SHA validation
    - immutability of inner records (Checkpoint, VerificationHookResult)
    - YAML / JSON roundtrip exactness
    - rejection of extra fields
    - rejection of naive datetimes
    - property-based roundtrip
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from cortex.session import (
    MAX_VERIFICATION_OUTPUT_BYTES,
    Checkpoint,
    CheckpointSource,
    SessionMode,
    SessionRecord,
    SessionStatus,
    VerificationHookResult,
)
from cortex.session.models import SESSION_ID_PATTERN

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


VALID_SHA = "a" * 40
ANOTHER_VALID_SHA = "b" * 40


def _utc(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _make_open_session(**overrides: object) -> SessionRecord:
    """Build a minimal valid OPEN SessionRecord."""
    defaults: dict[str, object] = {
        "session_id": "2026-05-16_demo",
        "spec_path": Path("vault/specs/2026-05-16_demo.md"),
        "spec_summary": "demo session",
        "start_commit": VALID_SHA,
        "start_branch": "feature/demo",
        "opened_at": _utc(2026, 5, 16, 10),
    }
    defaults.update(overrides)
    return SessionRecord(**defaults)  # type: ignore[arg-type]


def _make_closed_session(**overrides: object) -> SessionRecord:
    """Build a minimal valid CLOSED SessionRecord."""
    defaults: dict[str, object] = {
        "session_id": "2026-05-16_closed",
        "spec_path": Path("vault/specs/2026-05-16_closed.md"),
        "spec_summary": "closed session",
        "start_commit": VALID_SHA,
        "start_branch": "feature/demo",
        "opened_at": _utc(2026, 5, 16, 10),
        "status": SessionStatus.CLOSED,
        "mode": SessionMode.BYO,
        "closed_at": _utc(2026, 5, 16, 12),
        "end_commit": ANOTHER_VALID_SHA,
        "documenter_decision": SessionStatus.CLOSED,
    }
    defaults.update(overrides)
    return SessionRecord(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# session_id pattern
# ---------------------------------------------------------------------------


class TestSessionIdPattern:
    def test_session_id_valid_format(self) -> None:
        session = _make_open_session(session_id="2026-05-16_auth-jwt-refresh")
        assert session.session_id == "2026-05-16_auth-jwt-refresh"

    @pytest.mark.parametrize(
        "bad_id",
        [
            "20260516_demo",  # missing dashes in date
            "2026-5-16_demo",  # short month
            "2026-05-16_",  # empty slug
            "2026-05-16_-demo",  # slug starts with hyphen
            "2026-05-16_Demo",  # uppercase
            "2026-05-16_demo_x",  # underscore in slug
            "2026-05-16",  # no slug separator
            "demo",  # totally off-pattern
            "",  # empty
        ],
    )
    def test_session_id_invalid_format_raises(self, bad_id: str) -> None:
        with pytest.raises(ValidationError, match="session_id"):
            _make_open_session(session_id=bad_id)


# ---------------------------------------------------------------------------
# Status invariants
# ---------------------------------------------------------------------------


class TestStatusInvariants:
    def test_open_session_has_no_closed_fields(self) -> None:
        session = _make_open_session()
        assert session.status is SessionStatus.OPEN
        assert session.closed_at is None
        assert session.end_commit is None
        assert session.documenter_decision is None

    def test_open_session_rejects_close_time_fields(self) -> None:
        with pytest.raises(ValidationError, match="close-time fields"):
            _make_open_session(closed_at=_utc(2026, 5, 16, 12))

    def test_closed_session_requires_closed_fields(self) -> None:
        # Missing closed_at, end_commit, documenter_decision should fail
        with pytest.raises(ValidationError, match="requires non-null"):
            _make_open_session(status=SessionStatus.CLOSED)

    def test_handoff_status_treated_as_terminal(self) -> None:
        with pytest.raises(ValidationError, match="requires non-null"):
            _make_open_session(status=SessionStatus.HANDOFF)

        # Same with all close fields populated → valid.
        session = _make_closed_session(
            status=SessionStatus.HANDOFF,
            documenter_decision=SessionStatus.HANDOFF,
        )
        assert session.status is SessionStatus.HANDOFF

    def test_abandoned_status_treated_as_terminal(self) -> None:
        with pytest.raises(ValidationError, match="requires non-null"):
            _make_open_session(status=SessionStatus.ABANDONED)

        session = _make_closed_session(
            status=SessionStatus.ABANDONED,
            documenter_decision=SessionStatus.ABANDONED,
        )
        assert session.status is SessionStatus.ABANDONED


# ---------------------------------------------------------------------------
# Commit SHA validation
# ---------------------------------------------------------------------------


class TestCommitSha:
    def test_start_commit_must_be_40_hex(self) -> None:
        with pytest.raises(ValidationError, match="start_commit"):
            _make_open_session(start_commit="abc")
        with pytest.raises(ValidationError, match="start_commit"):
            _make_open_session(start_commit="A" * 40)  # uppercase rejected
        with pytest.raises(ValidationError, match="start_commit"):
            _make_open_session(start_commit="g" * 40)  # non-hex letter

    def test_end_commit_must_be_40_hex_when_set(self) -> None:
        with pytest.raises(ValidationError, match="end_commit"):
            _make_closed_session(end_commit="zz")

    def test_end_commit_may_be_none_while_open(self) -> None:
        session = _make_open_session()
        assert session.end_commit is None


# ---------------------------------------------------------------------------
# Datetime tz validation
# ---------------------------------------------------------------------------


class TestDatetimeTz:
    def test_naive_opened_at_rejected(self) -> None:
        naive = datetime(2026, 5, 16, 10)
        with pytest.raises(ValidationError, match="opened_at"):
            _make_open_session(opened_at=naive)

    def test_naive_closed_at_rejected(self) -> None:
        with pytest.raises(ValidationError, match="closed_at"):
            _make_closed_session(closed_at=datetime(2026, 5, 16, 12))

    def test_non_utc_aware_normalized(self) -> None:
        # Aware in a non-UTC timezone is accepted but normalized to UTC.
        offset = timezone(timedelta(hours=-3))
        local = datetime(2026, 5, 16, 9, tzinfo=offset)  # 12:00 UTC
        session = _make_open_session(opened_at=local)
        assert session.opened_at.tzinfo == UTC
        assert session.opened_at == _utc(2026, 5, 16, 12)


# ---------------------------------------------------------------------------
# Extra fields
# ---------------------------------------------------------------------------


class TestExtraFieldsForbidden:
    def test_extra_field_on_session_record_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Extra inputs"):
            SessionRecord(  # type: ignore[call-arg]
                session_id="2026-05-16_demo",
                spec_path=Path("x.md"),
                start_commit=VALID_SHA,
                start_branch="main",
                opened_at=_utc(2026, 5, 16),
                bogus_field="nope",
            )

    def test_extra_field_on_checkpoint_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Extra inputs"):
            Checkpoint(  # type: ignore[call-arg]
                timestamp=_utc(2026, 5, 16),
                source=CheckpointSource.MANUAL,
                bogus="nope",
            )


# ---------------------------------------------------------------------------
# Checkpoint immutability
# ---------------------------------------------------------------------------


class TestCheckpointImmutability:
    def test_checkpoint_is_frozen(self) -> None:
        cp = Checkpoint(timestamp=_utc(2026, 5, 16), source=CheckpointSource.CORTEX_SYNC)
        with pytest.raises(ValidationError):
            cp.note = "mutated"  # type: ignore[misc]

    def test_verification_result_is_frozen(self) -> None:
        result = VerificationHookResult(
            name="tests",
            command="pytest",
            passed=True,
            exit_code=0,
            output="ok",
            duration_ms=12,
            run_at=_utc(2026, 5, 16),
        )
        with pytest.raises(ValidationError):
            result.passed = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Verification hook output truncation
# ---------------------------------------------------------------------------


class TestVerificationOutputTruncation:
    def test_short_output_is_kept_verbatim(self) -> None:
        text = "hello world"
        result = VerificationHookResult(
            name="t",
            command="cmd",
            passed=True,
            exit_code=0,
            output=text,
            duration_ms=1,
            run_at=_utc(2026, 5, 16),
        )
        assert result.output == text

    def test_long_output_is_truncated_keeping_tail(self) -> None:
        long_text = "x" * (MAX_VERIFICATION_OUTPUT_BYTES * 2)
        result = VerificationHookResult(
            name="t",
            command="cmd",
            passed=False,
            exit_code=1,
            output=long_text,
            duration_ms=1,
            run_at=_utc(2026, 5, 16),
        )
        assert result.output.startswith("[... truncated, kept last")
        # The tail content must still be present.
        assert result.output.endswith("x" * 100)
        # Total length is bounded.
        assert len(result.output.encode("utf-8")) <= MAX_VERIFICATION_OUTPUT_BYTES + 200

    def test_duration_ms_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError, match="duration_ms"):
            VerificationHookResult(
                name="t",
                command="cmd",
                passed=True,
                exit_code=0,
                output="",
                duration_ms=-1,
                run_at=_utc(2026, 5, 16),
            )


# ---------------------------------------------------------------------------
# Serialization roundtrip
# ---------------------------------------------------------------------------


class TestSerializationRoundtrip:
    def test_open_session_yaml_roundtrip(self) -> None:
        session = _make_open_session(
            checkpoints=[
                Checkpoint(
                    timestamp=_utc(2026, 5, 16, 11),
                    source=CheckpointSource.CORTEX_SDDWORK,
                    verified_claims=["wrote auth.py"],
                    note="fast track",
                ),
            ],
        )
        dumped = session.model_dump(mode="json")
        yaml_text = yaml.safe_dump(dumped, sort_keys=False, allow_unicode=True)
        reloaded = yaml.safe_load(yaml_text)
        restored = SessionRecord.model_validate(reloaded)
        assert restored == session

    def test_closed_session_yaml_roundtrip(self) -> None:
        session = _make_closed_session(
            verification_results=[
                VerificationHookResult(
                    name="tests",
                    command="pytest tests/",
                    passed=True,
                    exit_code=0,
                    output="ok",
                    duration_ms=42,
                    run_at=_utc(2026, 5, 16, 11, 30),
                ),
            ],
            session_note_path=Path("vault/sessions/2026-05-16_closed.md"),
            adrs_created=[Path("vault/adrs/2026-05-16_decision.md")],
        )
        dumped = session.model_dump(mode="json")
        yaml_text = yaml.safe_dump(dumped, sort_keys=False, allow_unicode=True)
        reloaded = yaml.safe_load(yaml_text)
        restored = SessionRecord.model_validate(reloaded)
        assert restored == session

    def test_enums_serialize_to_string_values(self) -> None:
        session = _make_open_session()
        dumped = session.model_dump(mode="json")
        assert dumped["status"] == "open"
        assert dumped["mode"] == "unknown"


# ---------------------------------------------------------------------------
# Property-based roundtrip
# ---------------------------------------------------------------------------


# Hypothesis strategies for our domain primitives.
_session_id_strategy = st.from_regex(SESSION_ID_PATTERN, fullmatch=True)
_sha_strategy = st.text(alphabet="0123456789abcdef", min_size=40, max_size=40)
_utc_datetime_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 1, 1),
).map(lambda dt: dt.replace(tzinfo=UTC))

# Text strategy that excludes characters PyYAML (YAML 1.1) treats as line
# breaks, which break the safe_dump → safe_load roundtrip:
#   * U+0085 (NEL), U+2028 (LSEP), U+2029 (PSEP), U+000B, U+000C
# Plus NUL (U+0000), which PyYAML refuses outright. This reflects the
# real-world domain of a spec_summary (a short human-readable title) —
# it is not arbitrary binary.
_yaml_safe_text = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),  # surrogates
        blacklist_characters=("\x00", "\x0b", "\x0c", "\x85", " ", " "),
    ),
    max_size=80,
)


@st.composite
def open_session_records(draw: st.DrawFn) -> SessionRecord:
    return SessionRecord(
        session_id=draw(_session_id_strategy),
        spec_path=Path("vault/specs/test.md"),
        spec_summary=draw(_yaml_safe_text),
        start_commit=draw(_sha_strategy),
        start_branch=draw(st.sampled_from(["main", "feature/x", "bugfix/y"])),
        opened_at=draw(_utc_datetime_strategy),
    )


@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(open_session_records())
def test_property_open_session_yaml_roundtrip(session: SessionRecord) -> None:
    yaml_text = yaml.safe_dump(
        session.model_dump(mode="json"),
        sort_keys=False,
        allow_unicode=True,
    )
    restored = SessionRecord.model_validate(yaml.safe_load(yaml_text))
    assert restored == session


# ---------------------------------------------------------------------------
# Mutation pattern of SessionRecord (validated assignment)
# ---------------------------------------------------------------------------


class TestSessionRecordMutation:
    def test_status_assignment_validates(self) -> None:
        session = _make_open_session()
        with pytest.raises(ValidationError, match="requires non-null"):
            # Cannot transition to CLOSED without populating close-time fields.
            session.status = SessionStatus.CLOSED

    def test_checkpoint_append_does_not_revalidate_record(self) -> None:
        # Appending to the list is direct; we accept that Pydantic won't
        # re-run the model validator on list mutations. This is documented in
        # the docstring; the test pins the behaviour.
        session = _make_open_session()
        cp = Checkpoint(timestamp=_utc(2026, 5, 16), source=CheckpointSource.MANUAL)
        session.checkpoints.append(cp)
        assert session.checkpoints == [cp]
