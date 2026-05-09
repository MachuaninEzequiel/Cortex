"""cortex.autopilot.policies.base — Policy protocol and evaluation helpers."""
from __future__ import annotations

from typing import Protocol

from cortex.autopilot.models import AutopilotSessionState, PolicyDecision


class AutopilotPolicy(Protocol):
    """Protocol for policies that decide whether a transition is allowed."""

    name: str

    def evaluate(self, state: AutopilotSessionState) -> PolicyDecision:
        ...


def evaluate_policies(
    policies: list[AutopilotPolicy],
    state: AutopilotSessionState,
) -> list[PolicyDecision]:
    """Evaluate all *policies* against *state* and return their decisions.

    The caller (usually ``AutopilotService``) is responsible for acting on
    the most restrictive decision (e.g. ``block`` > ``degrade`` > ``warn`` >
    ``proceed``).
    """
    decisions: list[PolicyDecision] = []
    for pol in policies:
        try:
            decisions.append(pol.evaluate(state))
        except Exception:
            # Malfunctioning policies are ignored rather than crashing
            continue
    return decisions


def most_restrictive(decisions: list[PolicyDecision]) -> PolicyDecision | None:
    """Return the most restrictive decision from a list.

    Priority: block > degrade > warn > proceed.
    """
    if not decisions:
        return None
    priority = {"block": 4, "degrade": 3, "warn": 2, "proceed": 1}
    return max(decisions, key=lambda d: priority.get(d.action, 0))
