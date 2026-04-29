from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


PromotionStatus = Literal["draft", "candidate", "reviewed", "promoted", "rejected"]
PromotionDecisionType = Literal["approve", "reject"]


class PromotionIssue(BaseModel):
    file: str
    field: str
    message: str
    severity: Literal["error", "warning", "info"] = "warning"


class PromotionCandidate(BaseModel):
    origin_id: str
    doc_type: str
    local_rel_path: str
    local_abs_path: str
    dest_rel_path: str
    fingerprint: str
    status: PromotionStatus = "candidate"
    issues: list[PromotionIssue] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromotionDecision(BaseModel):
    decision: PromotionDecisionType
    actor: str
    decided_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    reason: str | None = None


class PromotionRecordEvent(BaseModel):
    event: Literal["candidate", "reviewed", "promoted", "rejected"]
    at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    actor: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class PromotionRecord(BaseModel):
    """
    Append-only record describing the lifecycle of one promotable document.

    `origin_id` is the stable idempotency key (project + local path).
    `fingerprint` is the content fingerprint of the source markdown (normalized).
    """

    origin_id: str
    local_rel_path: str
    doc_type: str
    dest_rel_path: str
    fingerprint: str
    status: PromotionStatus
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    decision: PromotionDecision | None = None
    events: list[PromotionRecordEvent] = Field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

