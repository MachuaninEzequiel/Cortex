"""GLOSSARY frontmatter schema."""

from __future__ import annotations

from pydantic import BaseModel, Field

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter


class _GlossarySpecific(BaseModel):
    doc_type: DocType = DocType.GLOSSARY
    term: str = Field(min_length=1)
    domain: str | None = None
    related_terms: list[str] = Field(default_factory=list)


class GlossaryFrontmatter(_GlossarySpecific, CommonFrontmatter):
    """Glossary frontmatter — campos específicos vía _GlossarySpecific (V5)."""


class GlossaryFrontmatterEnterprise(_GlossarySpecific, EnterpriseFrontmatter):
    """Glossary frontmatter enterprise — hereda _GlossarySpecific + gobernanza."""
