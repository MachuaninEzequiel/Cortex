"""Tests for ``cortex.autopilot.policies`` — the consolidated policy layer."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from cortex.autopilot.config import AutopilotConfig
from cortex.autopilot.policies import (
    DEFAULT_BUDGET_PROFILE,
    KNOWN_BUDGET_PROFILES,
    AutopilotMode,
    AutopilotPolicy,
    EnforcementResult,
    EnforcementSeverity,
    PolicyEnforcer,
)
from cortex.session.models import Checkpoint, CheckpointSource, SessionRecord

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def base_session() -> SessionRecord:
    """A fresh OPEN session whose ``spec_summary`` mentions security topics."""
    return SessionRecord(
        session_id="2026-05-16_audit-sample",
        spec_path=Path("vault/specs/2026-05-16_audit-sample.md"),
        spec_summary="Improve auth login flow with JWT refresh",
        start_commit="a" * 40,
        start_branch="feature/sample",
        opened_at=datetime.now(UTC),
    )


def _checkpoint(
    *,
    source: CheckpointSource = CheckpointSource.MANUAL,
    verified: list[str] | None = None,
    artifacts: list[str] | None = None,
    minutes_ago: int = 0,
) -> Checkpoint:
    return Checkpoint(
        timestamp=datetime.now(UTC) - timedelta(minutes=minutes_ago),
        source=source,
        verified_claims=verified or [],
        artifacts_touched=artifacts or [],
        note="",
    )


# ── AutopilotMode ─────────────────────────────────────────────────────


class TestAutopilotMode:
    def test_values(self) -> None:
        assert AutopilotMode.OBSERVE.value == "observe"
        assert AutopilotMode.ASSIST.value == "assist"
        assert AutopilotMode.AUTOPILOT.value == "autopilot"

    def test_is_strenum(self) -> None:
        assert AutopilotMode.OBSERVE == "observe"
        assert AutopilotMode.ASSIST == "assist"


# ── EnforcementResult ────────────────────────────────────────────────


class TestEnforcementResult:
    def test_proceed_helper(self) -> None:
        r = EnforcementResult.proceed()
        assert r.severity is EnforcementSeverity.PROCEED
        assert r.reason == ""
        assert r.allowed is True

    def test_warn_helper(self) -> None:
        r = EnforcementResult.warn("careful")
        assert r.severity is EnforcementSeverity.WARN
        assert r.reason == "careful"
        assert r.allowed is True

    def test_block_helper(self) -> None:
        r = EnforcementResult.block("no")
        assert r.severity is EnforcementSeverity.BLOCK
        assert r.reason == "no"
        assert r.allowed is False

    def test_is_frozen(self) -> None:
        r = EnforcementResult.proceed()
        with pytest.raises((AttributeError, TypeError, FrozenInstanceError)):
            r.severity = EnforcementSeverity.BLOCK  # type: ignore[misc]


# ── AutopilotPolicy ──────────────────────────────────────────────────


class TestAutopilotPolicyDefaults:
    def test_defaults(self) -> None:
        p = AutopilotPolicy()
        assert p.mode is AutopilotMode.ASSIST
        assert p.budget_profile == DEFAULT_BUDGET_PROFILE
        assert p.pre_commit_verification is False
        assert p.out_of_scope_warning is True
        assert p.warn_on_security_summary is True
        assert p.auto_checkpoint_threshold_files == 5
        assert p.auto_checkpoint_threshold_minutes == 10

    def test_is_frozen(self) -> None:
        p = AutopilotPolicy()
        with pytest.raises((AttributeError, TypeError, FrozenInstanceError)):
            p.mode = AutopilotMode.AUTOPILOT  # type: ignore[misc]


class TestAutopilotPolicyValidation:
    def test_unknown_budget_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown budget_profile"):
            AutopilotPolicy(budget_profile="bogus")

    def test_threshold_files_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="threshold_files"):
            AutopilotPolicy(auto_checkpoint_threshold_files=0)

    def test_threshold_minutes_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="threshold_minutes"):
            AutopilotPolicy(auto_checkpoint_threshold_minutes=0)


class TestPolicyFromConfig:
    def test_default_config_yields_assist(self) -> None:
        p = AutopilotPolicy.from_config(AutopilotConfig.defaults())
        assert p.mode is AutopilotMode.ASSIST
        assert p.out_of_scope_warning is True
        assert p.pre_commit_verification is False
        assert p.warn_on_security_summary is True

    def test_observe_mode_disables_all_warnings(self) -> None:
        p = AutopilotPolicy.from_config(AutopilotConfig(mode="observe"))
        assert p.mode is AutopilotMode.OBSERVE
        assert p.out_of_scope_warning is False
        assert p.warn_on_security_summary is False
        assert p.pre_commit_verification is False

    def test_autopilot_mode_enables_pre_commit_verification(self) -> None:
        p = AutopilotPolicy.from_config(AutopilotConfig(mode="autopilot"))
        assert p.mode is AutopilotMode.AUTOPILOT
        assert p.pre_commit_verification is True
        assert p.out_of_scope_warning is True
        assert p.warn_on_security_summary is True

    def test_unknown_mode_falls_back_to_assist(self) -> None:
        p = AutopilotPolicy.from_config(AutopilotConfig(mode="hyperdrive"))
        assert p.mode is AutopilotMode.ASSIST

    def test_unknown_budget_falls_back_to_default(self) -> None:
        p = AutopilotPolicy.from_config(AutopilotConfig(default_budget_profile="warp"))
        assert p.budget_profile == DEFAULT_BUDGET_PROFILE

    def test_propagates_thresholds(self) -> None:
        p = AutopilotPolicy.from_config(
            AutopilotConfig(auto_checkpoint_files=3, auto_checkpoint_minutes=2)
        )
        assert p.auto_checkpoint_threshold_files == 3
        assert p.auto_checkpoint_threshold_minutes == 2

    def test_zero_thresholds_clamped_to_one(self) -> None:
        try:
            cfg = AutopilotConfig(auto_checkpoint_files=0, auto_checkpoint_minutes=0)
        except ValidationError:
            pytest.skip("AutopilotConfig itself rejects 0 thresholds")
        p = AutopilotPolicy.from_config(cfg)
        assert p.auto_checkpoint_threshold_files == 1
        assert p.auto_checkpoint_threshold_minutes == 1


# ── PolicyEnforcer.on_session_open ───────────────────────────────────


class TestOnSessionOpen:
    def test_observe_silent(self, base_session: SessionRecord) -> None:
        enf = PolicyEnforcer(AutopilotPolicy(mode=AutopilotMode.OBSERVE))
        assert enf.on_session_open(base_session) == []

    def test_assist_warns_on_security_summary(self, base_session: SessionRecord) -> None:
        enf = PolicyEnforcer(AutopilotPolicy(mode=AutopilotMode.ASSIST))
        results = enf.on_session_open(base_session)
        assert len(results) == 1
        assert results[0].severity is EnforcementSeverity.WARN
        assert "security" in results[0].reason.lower()

    def test_assist_silent_when_summary_neutral(self, base_session: SessionRecord) -> None:
        record = base_session.model_copy(update={"spec_summary": "refactor parsing module"})
        enf = PolicyEnforcer(AutopilotPolicy(mode=AutopilotMode.ASSIST))
        assert enf.on_session_open(record) == []

    def test_explicit_summary_overrides_session_field(
        self, base_session: SessionRecord
    ) -> None:
        record = base_session.model_copy(update={"spec_summary": "neutral content"})
        enf = PolicyEnforcer(AutopilotPolicy(mode=AutopilotMode.ASSIST))
        results = enf.on_session_open(record, spec_summary="rotate OAuth secret token")
        assert any("security" in r.reason.lower() for r in results)

    def test_security_warning_disabled_by_flag(self, base_session: SessionRecord) -> None:
        enf = PolicyEnforcer(
            AutopilotPolicy(mode=AutopilotMode.ASSIST, warn_on_security_summary=False)
        )
        assert enf.on_session_open(base_session) == []


# ── PolicyEnforcer.on_checkpoint ─────────────────────────────────────


class TestOnCheckpointObserve:
    def test_observe_silent_even_with_out_of_scope(
        self, base_session: SessionRecord
    ) -> None:
        enf = PolicyEnforcer(AutopilotPolicy(mode=AutopilotMode.OBSERVE))
        cp = _checkpoint(artifacts=["src/other.py"])
        base_session.checkpoints.append(cp)
        assert (
            enf.on_checkpoint(base_session, cp, files_in_scope=["src/auth.py"])
            == []
        )


class TestOnCheckpointOutOfScope:
    def test_assist_warns_on_out_of_scope(self, base_session: SessionRecord) -> None:
        enf = PolicyEnforcer(AutopilotPolicy(mode=AutopilotMode.ASSIST))
        cp = _checkpoint(artifacts=["src/auth.py", "src/other.py"])
        base_session.checkpoints.append(cp)
        results = enf.on_checkpoint(
            base_session, cp, files_in_scope=["src/auth.py"]
        )
        assert any("outside spec scope" in r.reason for r in results)

    def test_assist_silent_when_in_scope(self, base_session: SessionRecord) -> None:
        enf = PolicyEnforcer(AutopilotPolicy(mode=AutopilotMode.ASSIST))
        cp = _checkpoint(artifacts=["src/auth.py"])
        base_session.checkpoints.append(cp)
        results = enf.on_checkpoint(
            base_session, cp, files_in_scope=["src/auth.py"]
        )
        assert results == []

    def test_out_of_scope_skipped_without_scope_list(
        self, base_session: SessionRecord
    ) -> None:
        enf = PolicyEnforcer(AutopilotPolicy(mode=AutopilotMode.ASSIST))
        cp = _checkpoint(artifacts=["src/anywhere.py"])
        base_session.checkpoints.append(cp)
        assert enf.on_checkpoint(base_session, cp, files_in_scope=None) == []


class TestOnCheckpointFileVolume:
    def test_warns_when_too_many_files_without_verified(
        self, base_session: SessionRecord
    ) -> None:
        enf = PolicyEnforcer(
            AutopilotPolicy(mode=AutopilotMode.ASSIST, auto_checkpoint_threshold_files=2)
        )
        cp = _checkpoint(artifacts=["a", "b", "c"])
        base_session.checkpoints.append(cp)
        results = enf.on_checkpoint(base_session, cp, files_in_scope=None)
        assert any("without a checkpoint" in r.reason for r in results)

    def test_verified_checkpoint_resets_counter(
        self, base_session: SessionRecord
    ) -> None:
        enf = PolicyEnforcer(
            AutopilotPolicy(mode=AutopilotMode.ASSIST, auto_checkpoint_threshold_files=2)
        )
        base_session.checkpoints.append(
            _checkpoint(artifacts=["x", "y", "z"], verified=["tests pass"])
        )
        cp = _checkpoint(artifacts=["new1"])
        base_session.checkpoints.append(cp)
        results = enf.on_checkpoint(base_session, cp, files_in_scope=None)
        assert not any("without a checkpoint" in r.reason for r in results)


class TestOnCheckpointTimeThreshold:
    def test_warns_when_minutes_exceeded(self, base_session: SessionRecord) -> None:
        enf = PolicyEnforcer(
            AutopilotPolicy(
                mode=AutopilotMode.ASSIST, auto_checkpoint_threshold_minutes=5
            )
        )
        base_session.checkpoints.append(_checkpoint(minutes_ago=30, artifacts=["a"]))
        cp = _checkpoint(artifacts=["b"])
        base_session.checkpoints.append(cp)
        results = enf.on_checkpoint(base_session, cp, files_in_scope=None)
        assert any("minutes since the previous checkpoint" in r.reason for r in results)

    def test_silent_on_first_checkpoint(self, base_session: SessionRecord) -> None:
        enf = PolicyEnforcer(AutopilotPolicy(mode=AutopilotMode.ASSIST))
        cp = _checkpoint(artifacts=["b"])
        base_session.checkpoints.append(cp)
        results = enf.on_checkpoint(base_session, cp, files_in_scope=None)
        assert not any("minutes since" in r.reason for r in results)

    def test_silent_when_new_checkpoint_has_no_artifacts(
        self, base_session: SessionRecord
    ) -> None:
        enf = PolicyEnforcer(
            AutopilotPolicy(
                mode=AutopilotMode.ASSIST, auto_checkpoint_threshold_minutes=1
            )
        )
        base_session.checkpoints.append(_checkpoint(minutes_ago=60, artifacts=["a"]))
        cp = _checkpoint(artifacts=[])
        base_session.checkpoints.append(cp)
        results = enf.on_checkpoint(base_session, cp, files_in_scope=None)
        assert not any("minutes since" in r.reason for r in results)


# ── PolicyEnforcer.on_pre_close ──────────────────────────────────────


class TestOnPreClose:
    def test_observe_never_blocks(self, base_session: SessionRecord) -> None:
        enf = PolicyEnforcer(AutopilotPolicy(mode=AutopilotMode.OBSERVE))
        assert enf.on_pre_close(base_session) == []

    def test_assist_never_blocks(self, base_session: SessionRecord) -> None:
        enf = PolicyEnforcer(AutopilotPolicy(mode=AutopilotMode.ASSIST))
        # No verified checkpoints; assist must still NOT block.
        assert enf.on_pre_close(base_session) == []

    def test_autopilot_blocks_without_verified_when_enabled(
        self, base_session: SessionRecord
    ) -> None:
        enf = PolicyEnforcer(
            AutopilotPolicy(
                mode=AutopilotMode.AUTOPILOT, pre_commit_verification=True
            )
        )
        results = enf.on_pre_close(base_session)
        assert any(r.severity is EnforcementSeverity.BLOCK for r in results)
        assert any("verified claims" in r.reason for r in results)

    def test_autopilot_allows_when_verified_present(
        self, base_session: SessionRecord
    ) -> None:
        enf = PolicyEnforcer(
            AutopilotPolicy(
                mode=AutopilotMode.AUTOPILOT, pre_commit_verification=True
            )
        )
        base_session.checkpoints.append(_checkpoint(verified=["tests pass"]))
        assert enf.on_pre_close(base_session) == []

    def test_autopilot_with_flag_disabled_does_not_block(
        self, base_session: SessionRecord
    ) -> None:
        enf = PolicyEnforcer(
            AutopilotPolicy(
                mode=AutopilotMode.AUTOPILOT, pre_commit_verification=False
            )
        )
        assert enf.on_pre_close(base_session) == []


# ── Module constants ─────────────────────────────────────────────────


class TestBudgetProfileConstants:
    def test_default_is_in_known_set(self) -> None:
        assert DEFAULT_BUDGET_PROFILE in KNOWN_BUDGET_PROFILES

    def test_set_is_frozen(self) -> None:
        with pytest.raises(AttributeError):
            KNOWN_BUDGET_PROFILES.add("anything")  # type: ignore[attr-defined]


class TestEnforcerPolicyProperty:
    def test_exposes_policy(self) -> None:
        pol = AutopilotPolicy(mode=AutopilotMode.AUTOPILOT)
        enf = PolicyEnforcer(pol)
        assert enf.policy is pol
