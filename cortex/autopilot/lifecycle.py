"""cortex.autopilot.lifecycle — Request/result types for AutopilotService.

Phase 03 refactor: every model references the canonical
:class:`cortex.session.models.SessionRecord` instead of the now-deleted
``AutopilotSessionState``. ``preflight`` survives as a *dry-run* of the
detector pipeline (it no longer mutates a session — that responsibility
moved to ``cortex.session.SessionService``).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from cortex.autopilot.models import DetectionResult
from cortex.autopilot.policies import AutopilotMode, AutopilotPolicy
from cortex.session.models import Checkpoint, SessionRecord, SessionStatus

# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------


class AutopilotStartRequest(BaseModel):
    """Adopt the currently-active session and apply the requested mode."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    mode: AutopilotMode | None = None


class AutopilotStartResult(BaseModel):
    """Outcome of ``AutopilotService.start``."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    session: SessionRecord
    policy: AutopilotPolicy
    warnings: list[str] = []


# ---------------------------------------------------------------------------
# preflight (dry-run of detectors — no state mutation)
# ---------------------------------------------------------------------------


class AutopilotPreflightRequest(BaseModel):
    user_request: str | None = None
    changed_files: list[str] = []
    git_diff_stat: str | None = None


class AutopilotPreflightResult(BaseModel):
    detection: DetectionResult


# ---------------------------------------------------------------------------
# checkpoint
# ---------------------------------------------------------------------------


class AutopilotCheckpointRequest(BaseModel):
    """Source/payload for a checkpoint to append to the active session."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    source: str  # CheckpointSource value (validated by SessionService)
    verified_claims: list[str] = []
    unverified_claims: list[str] = []
    artifacts_touched: list[str] = []
    note: str = ""
    files_in_scope: list[str] | None = None  # for out_of_scope warning


class AutopilotCheckpointResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    session: SessionRecord
    checkpoint: Checkpoint
    warnings: list[str] = []


# ---------------------------------------------------------------------------
# finish
# ---------------------------------------------------------------------------


class AutopilotFinishRequest(BaseModel):
    """Close the active session.

    With ``auto=True`` the service delegates to the documenter
    (``cortex.documenter.persistence.DocumenterPersister.finalize``) which
    reconstructs context, runs verification hooks, persists the session
    note + ADRs, and closes the record.

    With ``auto=False`` the service closes the record without documenting
    — useful for the ``observe`` mode where the user runs
    ``cortex finish-session`` manually later.
    """

    session_id: str | None = None
    auto: bool = False
    intent: str = "closed"  # one of: closed | handoff | abandoned
    reason: str = ""


class AutopilotFinishResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    session: SessionRecord
    documented: bool = False
    blocked: bool = False
    blocked_reason: str = ""
    session_note_path: str | None = None
    adrs_created: list[str] = []
    summary: str = ""
    warnings: list[str] = []


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


class AutopilotStatusResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    active: bool
    session: SessionRecord | None = None
    policy: AutopilotPolicy | None = None
    checkpoint_count: int = 0
    inferred_mode: str | None = None  # SessionMode value


# ---------------------------------------------------------------------------
# Re-exports
# ---------------------------------------------------------------------------

__all__ = [
    "AutopilotCheckpointRequest",
    "AutopilotCheckpointResult",
    "AutopilotFinishRequest",
    "AutopilotFinishResult",
    "AutopilotPreflightRequest",
    "AutopilotPreflightResult",
    "AutopilotStartRequest",
    "AutopilotStartResult",
    "AutopilotStatusResult",
]


# Suppress unused-import warnings: SessionStatus is re-exported elsewhere
# and only used as an annotation hint here for documentation.
_ = SessionStatus
