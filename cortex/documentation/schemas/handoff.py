"""HANDOFF frontmatter schema."""

from __future__ import annotations

from pydantic import BaseModel, Field

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter


class _HandoffSpecific(BaseModel):
    doc_type: DocType = DocType.HANDOFF
    parent_session_id: str = Field(min_length=1)


class HandoffFrontmatter(_HandoffSpecific, CommonFrontmatter):
    """Handoff frontmatter — campos específicos vía _HandoffSpecific (V5)."""


class HandoffFrontmatterEnterprise(_HandoffSpecific, EnterpriseFrontmatter):
    """Handoff frontmatter enterprise — hereda _HandoffSpecific + gobernanza."""
