"""
cortex.workitems.models
-----------------------
Shared models for optional tracked work items imported from external systems.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkItemSource(str, Enum):
    JIRA = "jira"


class WorkItemKind(str, Enum):
    STORY = "story"
    TASK = "task"
    BUG = "bug"
    EPIC = "epic"
    INCIDENT = "incident"
    OTHER = "other"


class TrackedItem(BaseModel):
    """Canonical internal representation of an imported work item."""

    id: str
    external_id: str
    source: WorkItemSource
    kind: WorkItemKind = WorkItemKind.OTHER
    title: str
    description: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)
    status: str | None = None
    labels: list[str] = Field(default_factory=list)
    assignee: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    vault_path: str | None = None
    external_url: str | None = None
    sync_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
