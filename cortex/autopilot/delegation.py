"""cortex.autopilot.delegation — Delegation engine with two-stage review.

This module handles task delegation results and enforces the two-stage
review protocol (§9.5):

  Stage 1: Spec compliance (automated)
  Stage 2: Quality review (orchestrator-assisted)

All functions are pure logic over ``DelegationResult`` and session state.
They do NOT spawn real subagents — that is the responsibility of the
harness or IDE-native delegation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from cortex.autopilot.models import AutopilotSessionState, DelegationResult


@dataclass
class ReviewVerdict:
    """Outcome of the two-stage review."""

    accepted: bool
    stage_1_passed: bool
    stage_2_passed: bool
    reason: str = ""
    action: Literal["accept", "reject", "degrade"] = "accept"


class DelegationEngine:
    """Two-stage review engine for ``DelegationResult``."""

    def review(
        self,
        result: DelegationResult,
        state: AutopilotSessionState,
    ) -> ReviewVerdict:
        """Run two-stage review on *result*.

        Returns a ``ReviewVerdict`` with ``accepted=True`` only if both
        stages pass.
        """
        s1 = self._stage_1_spec_compliance(result, state)
        if not s1.passed:
            return ReviewVerdict(
                accepted=False,
                stage_1_passed=False,
                stage_2_passed=False,
                reason=s1.reason,
                action="reject",
            )

        s2 = self._stage_2_quality(result, state)
        if not s2.passed:
            return ReviewVerdict(
                accepted=False,
                stage_1_passed=True,
                stage_2_passed=False,
                reason=s2.reason,
                action="reject",
            )

        return ReviewVerdict(
            accepted=True,
            stage_1_passed=True,
            stage_2_passed=True,
            reason="Review passed",
            action="accept",
        )

    @staticmethod
    def _stage_1_spec_compliance(
        result: DelegationResult, state: AutopilotSessionState
    ) -> "_StageResult":
        """Stage 1 — automated spec compliance.

        Checks:
        - Files changed are within the scope of ``state.changed_files``.
        - Diff summary is not empty if files were changed.
        - Status is not ``failed``.
        """
        if result.status == "failed":
            return _StageResult(
                passed=False, reason="Delegation result status is 'failed'"
            )

        if result.files_changed and not result.diff_summary.strip():
            return _StageResult(
                passed=False,
                reason="Files changed but diff_summary is empty",
            )

        # Verify changed files are within session scope (if any)
        session_files = set(state.changed_files or [])
        if session_files:
            unknown = [
                f for f in result.files_changed if f not in session_files
            ]
            if unknown:
                return _StageResult(
                    passed=False,
                    reason=f"Files outside session scope: {unknown}",
                )

        return _StageResult(passed=True, reason="Spec compliance OK")

    @staticmethod
    def _stage_2_quality(
        result: DelegationResult, _state: AutopilotSessionState
    ) -> "_StageResult":
        """Stage 2 — quality review.

        Checks:
        - Tests passed (if they were run).
        - No rejection reason present.
        """
        if result.rejection_reason:
            return _StageResult(
                passed=False,
                reason=f"Rejection reason present: {result.rejection_reason}",
            )

        if result.tests_passed is False:
            return _StageResult(
                passed=False, reason="Tests did not pass"
            )

        return _StageResult(passed=True, reason="Quality review OK")


@dataclass
class _StageResult:
    passed: bool
    reason: str = ""


# In-memory store for delegated tasks (used by MCP tools as a lightweight
# registry).  In production this would be backed by StateStore.
_task_registry: dict[str, DelegationResult] = {}


def register_task(result: DelegationResult) -> None:
    """Store *result* in the lightweight in-memory registry."""
    _task_registry[result.task_id] = result


def get_task_result(task_id: str) -> DelegationResult | None:
    """Return the ``DelegationResult`` for *task_id* if known."""
    return _task_registry.get(task_id)


def list_tasks() -> list[str]:
    """Return all known task IDs."""
    return list(_task_registry)
