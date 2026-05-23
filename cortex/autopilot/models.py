"""cortex.autopilot.models — Domain models for detectors and policies.

Phase 03 deleted the parallel session-lifecycle models that used to live
here (``AutopilotSessionState``, ``AutopilotCheckpoint``, ``AutopilotEvent``,
``SessionDraft``, ``AutopilotBudgetSnapshot``, ``HookSessionStartOutput``).
Their roles are now played by :mod:`cortex.session.models`
(``SessionRecord``, ``Checkpoint``) and the documenter's session-note
writers.

What remains here is the **decision-layer vocabulary**: the structured
inputs/outputs of the detector and policy primitives that still belong to
the Autopilot module.

Phase 04 cleanup completed the deletion of ``HookSessionStartOutput`` —
the legacy ``cortex/autopilot/hooks/`` scripts and adapters that consumed
it have been retired in favour of ``cortex/session/hooks/``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DetectionRequest(BaseModel):
    """Input to the detector pipeline.

    ``session_state`` was historically an ``AutopilotSessionState``; the new
    pipeline does not consult any session state during preflight (detection
    is a pure function of the user request + changed files), so the field
    is now optional and untyped.
    """

    model_config = ConfigDict(extra="forbid")

    user_request: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    git_diff_stat: str | None = None
    # Free-form metadata bag for custom detectors.
    session_state: Any | None = None


class DetectionResult(BaseModel):
    """Output of ``resolve_detectors``."""

    model_config = ConfigDict(extra="forbid")

    task_type: Literal[
        "question-only",
        "docs-only",
        "fast-code",
        "deep-code",
        "security",
        "ambiguous",
        "noop",
    ]
    confidence: float = 0.0
    reason: str = ""
    suggested_complexity: Literal["none", "fast", "deep"] = "none"


class PolicyDecision(BaseModel):
    """Legacy Pydantic model preserved for tests still using the old protocol.

    The new ``cortex.autopilot.policies.EnforcementResult`` is what
    :class:`cortex.autopilot.policies.PolicyEnforcer` returns. This model
    sticks around so detector tests (which build PolicyDecision in
    fixtures) keep compiling during the Phase 03 transition.
    """

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    reason: str
    action: Literal["proceed", "warn", "degrade", "block"] = "proceed"
    degrade_to: Literal["observe", "assist", "fast"] | None = None


__all__ = [
    "DetectionRequest",
    "DetectionResult",
    "PolicyDecision",
]
