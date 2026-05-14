"""RUNBOOK frontmatter schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter

_RUNBOOK_KINDS = frozenset({
    "deploy", "rollback", "incident-response", "data-migration", "operational",
})


def _validate_kind(v: str) -> str:
    if v not in _RUNBOOK_KINDS:
        raise ValueError(
            f"runbook_kind must be one of {sorted(_RUNBOOK_KINDS)}, got {v!r}"
        )
    return v


def _validate_tz(v: datetime | None) -> datetime | None:
    if v is not None and v.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return v


class RunbookFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.RUNBOOK
    runbook_kind: str = "operational"
    applies_to: list[str] = Field(default_factory=list)
    estimated_duration_minutes: int = Field(default=0, ge=0)
    last_verified_at: datetime | None = None

    _validate_kind = field_validator("runbook_kind")(_validate_kind)
    _validate_verified = field_validator("last_verified_at")(_validate_tz)


class RunbookFrontmatterEnterprise(EnterpriseFrontmatter):
    doc_type: DocType = DocType.RUNBOOK
    runbook_kind: str = "operational"
    applies_to: list[str] = Field(default_factory=list)
    estimated_duration_minutes: int = Field(default=0, ge=0)
    last_verified_at: datetime | None = None

    _validate_kind = field_validator("runbook_kind")(_validate_kind)
    _validate_verified = field_validator("last_verified_at")(_validate_tz)
