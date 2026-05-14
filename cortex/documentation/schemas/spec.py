"""SPEC frontmatter schema."""

from __future__ import annotations

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter


class SpecFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.SPEC


class SpecFrontmatterEnterprise(EnterpriseFrontmatter):
    doc_type: DocType = DocType.SPEC
