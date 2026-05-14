"""GLOSSARY frontmatter schema."""

from __future__ import annotations

from pydantic import Field

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter


class GlossaryFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.GLOSSARY
    term: str = Field(min_length=1)
    domain: str | None = None
    related_terms: list[str] = Field(default_factory=list)


class GlossaryFrontmatterEnterprise(EnterpriseFrontmatter):
    doc_type: DocType = DocType.GLOSSARY
    term: str = Field(min_length=1)
    domain: str | None = None
    related_terms: list[str] = Field(default_factory=list)
