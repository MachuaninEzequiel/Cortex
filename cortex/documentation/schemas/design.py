"""DESIGN frontmatter schema (Pluggable Middle Phase 09.B).

The ``design`` doc type captures the architecture / data-model / API
contract / test-plan decisions taken **before** implementation. Written
by the ``cortex-code-designer`` subagent in Deep Track. Linked back to
both the originating spec and the open Session via ``spec_path`` and
``session_id``.
"""

from __future__ import annotations

from pydantic import Field

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter


class DesignFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.DESIGN
    session_id: str = Field(min_length=1)
    spec_path: str = Field(min_length=1)


class DesignFrontmatterEnterprise(EnterpriseFrontmatter):
    doc_type: DocType = DocType.DESIGN
    session_id: str = Field(min_length=1)
    spec_path: str = Field(min_length=1)
