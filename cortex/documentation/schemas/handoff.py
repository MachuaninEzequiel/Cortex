"""HANDOFF frontmatter schema."""

from __future__ import annotations

from pydantic import Field

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter


class HandoffFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.HANDOFF
    parent_session_id: str = Field(min_length=1)


class HandoffFrontmatterEnterprise(EnterpriseFrontmatter):
    doc_type: DocType = DocType.HANDOFF
    parent_session_id: str = Field(min_length=1)
