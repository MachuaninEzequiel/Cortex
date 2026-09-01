"""CHANGELOG frontmatter schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter


def _validate_tz(v: datetime | None) -> datetime | None:
    if v is not None and v.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return v


class _ChangelogSpecific(BaseModel):
    doc_type: DocType = DocType.CHANGELOG
    version: str = Field(min_length=1)
    release_date: datetime | None = None

    _validate_release = field_validator("release_date")(_validate_tz)


class ChangelogFrontmatter(_ChangelogSpecific, CommonFrontmatter):
    """Changelog frontmatter — campos específicos vía _ChangelogSpecific (V5)."""


class ChangelogFrontmatterEnterprise(_ChangelogSpecific, EnterpriseFrontmatter):
    """Changelog frontmatter enterprise — hereda _ChangelogSpecific + gobernanza."""
