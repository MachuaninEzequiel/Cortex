"""cortex.autopilot.lifecycle — Request/result types for AutopilotService."""
from __future__ import annotations

from pydantic import BaseModel

from cortex.autopilot.models import AutopilotSessionState, DetectionResult, PolicyDecision, SessionDraft


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------
class StartRequest(BaseModel):
    project_root: str
    workspace_root: str
    mode: str = "assist"
    user_request: str | None = None
    title_hint: str | None = None


class StartResult(BaseModel):
    session_id: str
    state: AutopilotSessionState


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------
class PreflightRequest(BaseModel):
    session_id: str
    user_request: str | None = None
    changed_files: list[str] = []
    git_diff_stat: str | None = None


class PreflightResult(BaseModel):
    detection: DetectionResult
    policy_decisions: list[PolicyDecision]
    can_proceed: bool
    state: AutopilotSessionState


# ---------------------------------------------------------------------------
# checkpoint
# ---------------------------------------------------------------------------
class CheckpointRequest(BaseModel):
    session_id: str
    summary: str
    files_at_checkpoint: list[str] = []
    verified: bool = False


class CheckpointResult(BaseModel):
    state: AutopilotSessionState


# ---------------------------------------------------------------------------
# finish
# ---------------------------------------------------------------------------
class FinishRequest(BaseModel):
    session_id: str
    auto: bool = False


class FinishResult(BaseModel):
    state: AutopilotSessionState
    draft: SessionDraft | None = None
    saved: bool = False


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------
class StatusResult(BaseModel):
    active: bool
    state: AutopilotSessionState | None = None
    event_count: int = 0
