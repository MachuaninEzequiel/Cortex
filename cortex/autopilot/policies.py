"""cortex.autopilot.policies — Consolidated policy layer for the Autopilot module.

Replaces the previous ``cortex.autopilot.policies.{base,default,auto_checkpoint}``
subpackage with a single module designed for the post-Phase-03 architecture:
**Autopilot is a thin policy + hook layer over the cortex.session primitive.**

Public API:
    :class:`AutopilotMode`        — observe / assist / autopilot
    :class:`AutopilotPolicy`      — frozen dataclass: mode + thresholds + flags
    :class:`EnforcementSeverity`  — proceed / warn / block
    :class:`EnforcementResult`    — frozen dataclass: severity + reason
    :class:`PolicyEnforcer`       — applies the policy at lifecycle hooks

The enforcer's hooks return a list of :class:`EnforcementResult` so the caller
(typically :class:`cortex.autopilot.service.AutopilotService`) decides how to
surface warnings or stop the operation on a block.

Design note:
    All time comparisons use timezone-aware UTC. The enforcer is stateless
    beyond its immutable policy, and pure functions of the inputs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from cortex.autopilot.config import AutopilotConfig
from cortex.session.models import Checkpoint, SessionRecord


class AutopilotMode(StrEnum):
    """Operational stance of the Autopilot layer for a session.

    - ``OBSERVE``   — hooks register checkpoints; no warnings, no interventions.
    - ``ASSIST``    — observe + warnings (out-of-scope, stalled work, security).
    - ``AUTOPILOT`` — assist + active interventions (block on missing
      verification, etc.).
    """

    OBSERVE = "observe"
    ASSIST = "assist"
    AUTOPILOT = "autopilot"


class EnforcementSeverity(StrEnum):
    """How strongly a policy enforcement signals its decision."""

    PROCEED = "proceed"
    WARN = "warn"
    BLOCK = "block"


@dataclass(frozen=True)
class EnforcementResult:
    """Outcome of one policy rule applied at a hook.

    A hook may return multiple results (one per rule). The caller is
    responsible for combining them — usually by aggregating WARNs and
    raising / aborting on the first BLOCK.
    """

    severity: EnforcementSeverity
    reason: str = ""

    @property
    def allowed(self) -> bool:
        """True unless severity is BLOCK."""
        return self.severity is not EnforcementSeverity.BLOCK

    @classmethod
    def proceed(cls) -> EnforcementResult:
        return cls(severity=EnforcementSeverity.PROCEED, reason="")

    @classmethod
    def warn(cls, reason: str) -> EnforcementResult:
        return cls(severity=EnforcementSeverity.WARN, reason=reason)

    @classmethod
    def block(cls, reason: str) -> EnforcementResult:
        return cls(severity=EnforcementSeverity.BLOCK, reason=reason)


# Budget-profile registry — single source of truth (formerly
# cortex.autopilot.context_budget.BUDGET_PROFILES, kept here so the policy
# layer has no cross-module data dependency).
DEFAULT_BUDGET_PROFILE = "fast_code"
KNOWN_BUDGET_PROFILES: frozenset[str] = frozenset(
    {"question_only", "docs_only", "fast_code", "deep_code", "finish_only"}
)


# Security keyword set reused from the old SecuritySensitiveDetector. Drives
# the on_session_open warning when a spec summary mentions risky topics.
_SECURITY_KEYWORDS = frozenset(
    {
        "password",
        "secret",
        "token",
        "jwt",
        "oauth",
        "auth",
        "login",
        "permission",
        "role",
        "rbac",
        "acl",
        "crypto",
        "encrypt",
        "decrypt",
        "hash",
        "salt",
    }
)
_SECURITY_KEYWORD_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _SECURITY_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AutopilotPolicy:
    """Declarative policy applied to a Session under Autopilot supervision.

    The policy is immutable per session. The caller selects a mode at
    start-time and :class:`PolicyEnforcer` evaluates the same instance at
    every lifecycle hook.

    Attributes:
        mode: Operational stance. See :class:`AutopilotMode`.
        budget_profile: Name of the context-budget profile from
            :data:`KNOWN_BUDGET_PROFILES`. Documentational; the actual
            budget enforcement lives in ``cortex.context_enricher``.
        pre_commit_verification: When True (effective only in AUTOPILOT
            mode), :meth:`PolicyEnforcer.on_pre_close` blocks unless at
            least one checkpoint carries verified claims.
        out_of_scope_warning: When True (effective in ASSIST and
            AUTOPILOT), :meth:`PolicyEnforcer.on_checkpoint` warns if the
            new checkpoint touches files outside the spec's scope.
        auto_checkpoint_threshold_files: After N artifact paths touched
            without an intervening verified checkpoint, the enforcer
            nudges the user with a warning.
        auto_checkpoint_threshold_minutes: After M minutes since the prior
            checkpoint (when the new one touches any files), the enforcer
            nudges the user with a warning.
        warn_on_security_summary: When True (effective in ASSIST and
            AUTOPILOT), :meth:`PolicyEnforcer.on_session_open` warns if
            the spec summary mentions security-sensitive terms.
    """

    mode: AutopilotMode = AutopilotMode.ASSIST
    budget_profile: str = DEFAULT_BUDGET_PROFILE
    pre_commit_verification: bool = False
    out_of_scope_warning: bool = True
    auto_checkpoint_threshold_files: int = 5
    auto_checkpoint_threshold_minutes: int = 10
    warn_on_security_summary: bool = True

    def __post_init__(self) -> None:
        if self.budget_profile not in KNOWN_BUDGET_PROFILES:
            raise ValueError(
                f"unknown budget_profile {self.budget_profile!r}; "
                f"must be one of {sorted(KNOWN_BUDGET_PROFILES)}"
            )
        if self.auto_checkpoint_threshold_files < 1:
            raise ValueError(
                "auto_checkpoint_threshold_files must be >= 1, "
                f"got {self.auto_checkpoint_threshold_files}"
            )
        if self.auto_checkpoint_threshold_minutes < 1:
            raise ValueError(
                "auto_checkpoint_threshold_minutes must be >= 1, "
                f"got {self.auto_checkpoint_threshold_minutes}"
            )

    @classmethod
    def from_config(cls, config: AutopilotConfig) -> AutopilotPolicy:
        """Build a policy from an :class:`AutopilotConfig` (YAML-backed).

        Unknown ``config.mode`` or ``config.default_budget_profile`` values
        fall back to safe defaults so a typo in ``autopilot.yaml`` never
        crashes the CLI. The mistake is surfaced by
        :mod:`cortex.autopilot.doctor`.

        Higher modes default to more enforcement:
            OBSERVE    — all warnings off, no pre-commit verification.
            ASSIST     — warnings on, no pre-commit verification.
            AUTOPILOT  — warnings on, pre-commit verification on.
        """
        try:
            mode = AutopilotMode(config.mode)
        except ValueError:
            mode = AutopilotMode.ASSIST

        budget = (
            config.default_budget_profile
            if config.default_budget_profile in KNOWN_BUDGET_PROFILES
            else DEFAULT_BUDGET_PROFILE
        )

        is_observe = mode is AutopilotMode.OBSERVE
        return cls(
            mode=mode,
            budget_profile=budget,
            pre_commit_verification=mode is AutopilotMode.AUTOPILOT,
            out_of_scope_warning=not is_observe,
            warn_on_security_summary=not is_observe,
            auto_checkpoint_threshold_files=max(1, config.auto_checkpoint_files),
            auto_checkpoint_threshold_minutes=max(1, config.auto_checkpoint_minutes),
        )


class PolicyEnforcer:
    """Apply an :class:`AutopilotPolicy` at lifecycle hooks of a SessionRecord.

    Stateless beyond the immutable policy. All time comparisons use UTC.
    """

    def __init__(self, policy: AutopilotPolicy) -> None:
        self._policy = policy

    @property
    def policy(self) -> AutopilotPolicy:
        return self._policy

    # ── Hook: on_session_open ─────────────────────────────────────

    def on_session_open(
        self,
        session: SessionRecord,
        *,
        spec_summary: str | None = None,
    ) -> list[EnforcementResult]:
        """Pre-check after the session is opened.

        Warnings issued:
            - Spec summary mentions security-sensitive terms (when the
              policy has ``warn_on_security_summary``).
        """
        results: list[EnforcementResult] = []
        if self._policy.mode is AutopilotMode.OBSERVE:
            return results

        summary = spec_summary if spec_summary is not None else session.spec_summary
        if self._policy.warn_on_security_summary and _looks_security_sensitive(summary):
            results.append(
                EnforcementResult.warn(
                    "Spec summary mentions security-sensitive terms — review the diff "
                    "carefully before closing the session."
                )
            )
        return results

    # ── Hook: on_checkpoint ───────────────────────────────────────

    def on_checkpoint(
        self,
        session: SessionRecord,
        checkpoint: Checkpoint,
        *,
        files_in_scope: list[str] | None = None,
    ) -> list[EnforcementResult]:
        """Evaluate after a checkpoint is appended.

        Warnings issued:
            - WARN if ``out_of_scope_warning`` is set, the spec declares
              ``files_in_scope``, and the checkpoint touches paths outside
              that scope.
            - WARN if more than ``auto_checkpoint_threshold_files`` distinct
              artifact paths have been touched since the last checkpoint
              with verified claims.
            - WARN if more than ``auto_checkpoint_threshold_minutes`` have
              passed since the previous checkpoint AND the new one touches
              any files.
        """
        results: list[EnforcementResult] = []
        if self._policy.mode is AutopilotMode.OBSERVE:
            return results

        if self._policy.out_of_scope_warning and files_in_scope is not None:
            in_scope_set = set(files_in_scope)
            drift = [a for a in checkpoint.artifacts_touched if a not in in_scope_set]
            if drift:
                results.append(
                    EnforcementResult.warn(
                        f"Checkpoint touches files outside spec scope: {sorted(drift)}"
                    )
                )

        files_since_verified = _files_since_last_verified(session)
        if files_since_verified > self._policy.auto_checkpoint_threshold_files:
            results.append(
                EnforcementResult.warn(
                    f"{files_since_verified} artifact paths touched without a "
                    "checkpoint that records verified claims"
                )
            )

        # Time-since-previous-checkpoint test excludes the checkpoint we
        # just appended (``session.checkpoints[-1] is checkpoint``).
        prior_checkpoints = session.checkpoints[:-1] if session.checkpoints else []
        if prior_checkpoints and checkpoint.artifacts_touched:
            elapsed = datetime.now(UTC) - prior_checkpoints[-1].timestamp
            threshold = timedelta(minutes=self._policy.auto_checkpoint_threshold_minutes)
            if elapsed > threshold:
                minutes = int(elapsed.total_seconds() // 60)
                results.append(
                    EnforcementResult.warn(
                        f"{minutes} minutes since the previous checkpoint and the new "
                        "one already touches files — consider checkpointing more often"
                    )
                )
        return results

    # ── Hook: on_pre_close ────────────────────────────────────────

    def on_pre_close(self, session: SessionRecord) -> list[EnforcementResult]:
        """Evaluate before transitioning the session to a terminal status.

        Blocks issued:
            - In AUTOPILOT with ``pre_commit_verification``, BLOCK if no
              checkpoint contains any ``verified_claims``.
        """
        results: list[EnforcementResult] = []
        if (
            self._policy.mode is AutopilotMode.AUTOPILOT
            and self._policy.pre_commit_verification
            and not _has_verified_checkpoint(session)
        ):
            results.append(
                EnforcementResult.block(
                    "Autopilot mode requires at least one checkpoint with verified "
                    "claims before closing the session (set "
                    "pre_commit_verification=False to opt out)."
                )
            )
        return results


# ── Module-private helpers ────────────────────────────────────────


def _looks_security_sensitive(text: str) -> bool:
    if not text:
        return False
    return bool(_SECURITY_KEYWORD_PATTERN.search(text))


def _has_verified_checkpoint(session: SessionRecord) -> bool:
    return any(cp.verified_claims for cp in session.checkpoints)


def _files_since_last_verified(session: SessionRecord) -> int:
    """Distinct artifact paths touched since the last verified checkpoint."""
    touched: set[str] = set()
    for cp in reversed(session.checkpoints):
        if cp.verified_claims:
            break
        touched.update(cp.artifacts_touched)
    return len(touched)


__all__ = [
    "AutopilotMode",
    "AutopilotPolicy",
    "DEFAULT_BUDGET_PROFILE",
    "EnforcementResult",
    "EnforcementSeverity",
    "KNOWN_BUDGET_PROFILES",
    "PolicyEnforcer",
]
