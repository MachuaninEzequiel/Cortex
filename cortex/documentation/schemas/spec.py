"""SPEC frontmatter schema."""

from __future__ import annotations

from pydantic import Field

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter
from cortex.session.models import VerificationHook


class SpecFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.SPEC
    # Pluggable Middle (Phase 01 / T1.1).
    # An empty list is accepted only as a backward-compatible read path for
    # specs created before this field existed. ``SpecService.create`` logs
    # a warning when a caller persists a new spec with no hooks.
    verification_hooks: list[VerificationHook] = Field(default_factory=list)


class SpecFrontmatterEnterprise(EnterpriseFrontmatter):
    doc_type: DocType = DocType.SPEC
    verification_hooks: list[VerificationHook] = Field(default_factory=list)
