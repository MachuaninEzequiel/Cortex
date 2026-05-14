"""INCIDENT frontmatter schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter

_SEVERITIES = frozenset({"low", "medium", "high", "critical"})


def _validate_severity(v: str) -> str:
    if v not in _SEVERITIES:
        raise ValueError(
            f"severity must be one of {sorted(_SEVERITIES)}, got {v!r}"
        )
    return v


def _validate_tz(v: datetime | None) -> datetime | None:
    if v is not None and v.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return v


class IncidentFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.INCIDENT
    incident_number: int = Field(ge=1)
    severity: str
    opened_at: datetime
    closed_at: datetime | None = None
    affected_services: list[str] = Field(default_factory=list)
    root_cause_postmortem: str | None = None

    _validate_severity = field_validator("severity")(_validate_severity)
    _validate_opened = field_validator("opened_at")(_validate_tz)
    _validate_closed = field_validator("closed_at")(_validate_tz)


class IncidentFrontmatterEnterprise(EnterpriseFrontmatter):
    doc_type: DocType = DocType.INCIDENT
    incident_number: int = Field(ge=1)
    severity: str
    opened_at: datetime
    closed_at: datetime | None = None
    affected_services: list[str] = Field(default_factory=list)
    root_cause_postmortem: str | None = None

    _validate_severity = field_validator("severity")(_validate_severity)
    _validate_opened = field_validator("opened_at")(_validate_tz)
    _validate_closed = field_validator("closed_at")(_validate_tz)
