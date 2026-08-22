"""DECISION frontmatter schema (non-ADR decisions)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter


class _DecisionSpecific(BaseModel):
    doc_type: DocType = DocType.DECISION
    reversible_within_days: int = Field(default=0, ge=0)


class DecisionFrontmatter(_DecisionSpecific, CommonFrontmatter):
    """Decision frontmatter — campos específicos vía _DecisionSpecific (V5)."""


class DecisionFrontmatterEnterprise(_DecisionSpecific, EnterpriseFrontmatter):
    """Decision frontmatter enterprise — hereda _DecisionSpecific + gobernanza."""
