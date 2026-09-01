"""HU (user story / work item) frontmatter schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter

_HU_KINDS = frozenset({"story", "task", "bug", "epic"})


def _validate_kind(v: str) -> str:
    if v not in _HU_KINDS:
        raise ValueError(f"kind must be one of {sorted(_HU_KINDS)}, got {v!r}")
    return v


def _validate_tz(v: datetime | None) -> datetime | None:
    if v is not None and v.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return v


class _HUSpecific(BaseModel):
    doc_type: DocType = DocType.HU
    external_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    kind: str = "story"
    assignee: str | None = None
    external_url: str | None = None
    synced_at: datetime | None = None

    _validate_kind = field_validator("kind")(_validate_kind)
    _validate_synced = field_validator("synced_at")(_validate_tz)


class HUFrontmatter(_HUSpecific, CommonFrontmatter):
    """HU frontmatter — campos específicos vía _HUSpecific (V5)."""


class HUFrontmatterEnterprise(_HUSpecific, EnterpriseFrontmatter):
    """HU frontmatter enterprise — hereda _HUSpecific + gobernanza."""
