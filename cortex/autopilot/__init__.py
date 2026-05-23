"""cortex.autopilot — Policy + hooks layer over the cortex.session primitive.

Phase 03 of the Pluggable Middle architecture turned this module from a
parallel session-lifecycle implementation into a *thin orchestrator* that
applies an :class:`AutopilotPolicy` over the canonical
:class:`cortex.session.service.SessionService`.

Public API:
    :class:`AutopilotService`  — entry point, factory ``from_project_root``.
    :class:`AutopilotMode`     — observe / assist / autopilot.
    :class:`AutopilotPolicy`   — declarative policy (frozen dataclass).
    :class:`PolicyEnforcer`    — evaluates the policy at lifecycle hooks.
"""

from __future__ import annotations

from cortex.autopilot.policies import (
    AutopilotMode,
    AutopilotPolicy,
    EnforcementResult,
    EnforcementSeverity,
    PolicyEnforcer,
)
from cortex.autopilot.service import AutopilotService

__all__ = [
    "AutopilotMode",
    "AutopilotPolicy",
    "AutopilotService",
    "EnforcementResult",
    "EnforcementSeverity",
    "PolicyEnforcer",
]
