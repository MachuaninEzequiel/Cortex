"""DECISION frontmatter schema (non-ADR decisions)."""

from __future__ import annotations

from pydantic import Field

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter


class DecisionFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.DECISION
    reversible_within_days: int = Field(default=0, ge=0)


class DecisionFrontmatterEnterprise(EnterpriseFrontmatter):
    doc_type: DocType = DocType.DECISION
    reversible_within_days: int = Field(default=0, ge=0)
