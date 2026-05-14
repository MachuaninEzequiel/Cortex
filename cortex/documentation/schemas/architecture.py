"""ARCHITECTURE frontmatter schema."""

from __future__ import annotations

from pydantic import Field

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter


class ArchitectureFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.ARCHITECTURE
    related_adrs: list[str] = Field(default_factory=list)


class ArchitectureFrontmatterEnterprise(EnterpriseFrontmatter):
    doc_type: DocType = DocType.ARCHITECTURE
    related_adrs: list[str] = Field(default_factory=list)
