"""ARCHITECTURE frontmatter schema."""

from __future__ import annotations

from pydantic import BaseModel, Field

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter


class _ArchitectureSpecific(BaseModel):
    doc_type: DocType = DocType.ARCHITECTURE
    related_adrs: list[str] = Field(default_factory=list)


class ArchitectureFrontmatter(_ArchitectureSpecific, CommonFrontmatter):
    """Architecture frontmatter — campos específicos vía _ArchitectureSpecific (V5)."""


class ArchitectureFrontmatterEnterprise(_ArchitectureSpecific, EnterpriseFrontmatter):
    """Architecture frontmatter enterprise — hereda _ArchitectureSpecific + gobernanza."""
