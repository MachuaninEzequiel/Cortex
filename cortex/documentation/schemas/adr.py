"""ADR frontmatter schema."""

from __future__ import annotations

from pydantic import BaseModel, Field

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter


class _ADRSpecific(BaseModel):
    doc_type: DocType = DocType.ADR
    adr_number: int = Field(ge=1)
    supersedes: list[str] = Field(default_factory=list)
    superseded_by: str | None = None
    alternatives_considered: list[str] = Field(default_factory=list)
    acceptance_criteria_met: bool = False


class ADRFrontmatter(_ADRSpecific, CommonFrontmatter):
    """ADR frontmatter — campos específicos vía _ADRSpecific (V5)."""


class ADRFrontmatterEnterprise(_ADRSpecific, EnterpriseFrontmatter):
    """ADR frontmatter enterprise — hereda _ADRSpecific + gobernanza."""
