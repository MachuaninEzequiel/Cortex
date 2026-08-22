"""POSTMORTEM frontmatter schema."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter

_SEVERITIES = frozenset({"low", "medium", "high", "critical"})


def _validate_severity(v: str) -> str:
    if v not in _SEVERITIES:
        raise ValueError(f"severity must be one of {sorted(_SEVERITIES)}, got {v!r}")
    return v


class _PostmortemSpecific(BaseModel):
    doc_type: DocType = DocType.POSTMORTEM
    incident_number: int = Field(ge=1)
    incident_path: str = Field(min_length=1)
    severity: str

    _validate_severity = field_validator("severity")(_validate_severity)


class PostmortemFrontmatter(_PostmortemSpecific, CommonFrontmatter):
    """Postmortem frontmatter — campos específicos vía _PostmortemSpecific (V5)."""


class PostmortemFrontmatterEnterprise(_PostmortemSpecific, EnterpriseFrontmatter):
    """Postmortem frontmatter enterprise — hereda _PostmortemSpecific + gobernanza."""
