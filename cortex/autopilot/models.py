"""cortex.autopilot.models — Domain models for the Autopilot module."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field
import uuid


class AutopilotBudgetSnapshot(BaseModel):
    chars_injected: int = 0
    items_retrieved: int = 0
    embeddings_used: bool = False
    subagents_spawned: int = 0
    deep_track_reason: str | None = None


class AutopilotCheckpoint(BaseModel):
    timestamp: datetime
    summary: str
    files_at_checkpoint: list[str] = []
    verified: bool = False


class AutopilotSessionState(BaseModel):
    schema_version: int = 1
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    project_root: str
    workspace_root: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: Literal[
        "started",
        "preflight_done",
        "implementation_seen",
        "documented",
        "finished",
        "failed",
    ] = "started"
    mode: Literal["observe", "assist", "autopilot"] = "assist"
    user_request: str | None = None
    title_hint: str | None = None
    detected_task_type: str | None = None
    complexity: Literal["none", "fast", "deep"] = "none"
    spec_path: str | None = None
    session_note_path: str | None = None
    changed_files: list[str] = []
    commands_seen: list[str] = []
    tools_seen: list[str] = []
    checkpoints: list[AutopilotCheckpoint] = []
    budget: AutopilotBudgetSnapshot = Field(
        default_factory=AutopilotBudgetSnapshot
    )
    warnings: list[str] = []


class AutopilotEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    session_id: str
    event_type: str  # "start", "preflight", "checkpoint", "finish", etc.
    source: Literal["cli", "mcp", "hook", "agent", "detector", "policy"]
    payload: dict[str, Any] = {}


class DetectionRequest(BaseModel):
    user_request: str | None = None
    changed_files: list[str] = []
    git_diff_stat: str | None = None
    session_state: AutopilotSessionState | None = None


class DetectionResult(BaseModel):
    task_type: Literal[
        "question-only", "docs-only", "fast-code",
        "deep-code", "security", "ambiguous", "noop"
    ]
    confidence: float = 0.0
    reason: str = ""
    suggested_complexity: Literal["none", "fast", "deep"] = "none"


class PolicyDecision(BaseModel):
    allowed: bool
    reason: str
    action: Literal["proceed", "warn", "degrade", "block"] = "proceed"
    degrade_to: Literal["observe", "assist", "fast"] | None = None


class SessionDraft(BaseModel):
    title: str
    body: str
    confidence: Literal["high", "medium", "auto-draft"] = "medium"
    warnings: list[str] = []
    source_events: int = 0


class HookSessionStartOutput(BaseModel):
    session_id: str
    mode: Literal["observe", "assist", "autopilot"]
    bootstrap_content: str
    budget_profile: str
    available_tools: list[str] = []
    cortex_version: str = ""


class DelegationResult(BaseModel):
    task_id: str
    status: Literal["completed", "failed", "rejected"]
    diff_summary: str = ""
    files_changed: list[str] = []
    tests_passed: bool | None = None
    spec_path: str | None = None
    rejection_reason: str | None = None
