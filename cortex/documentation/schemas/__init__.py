"""cortex.documentation.schemas - Pydantic models for frontmatter validation.

Exports:
    - Base models: CommonFrontmatter, EnterpriseFrontmatter, AuditEvent.
    - 12 type-specific models (CommonFrontmatter + EnterpriseFrontmatter pair each).
    - SCHEMA_BY_TYPE: lookup map DocType -> CommonFrontmatter subclass.
    - SCHEMA_BY_TYPE_ENTERPRISE: lookup map DocType -> EnterpriseFrontmatter subclass.
"""

from __future__ import annotations

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.adr import ADRFrontmatter, ADRFrontmatterEnterprise
from cortex.documentation.schemas.architecture import (
    ArchitectureFrontmatter,
    ArchitectureFrontmatterEnterprise,
)
from cortex.documentation.schemas.base import (
    AuditEvent,
    CommonFrontmatter,
    EnterpriseFrontmatter,
)
from cortex.documentation.schemas.changelog import (
    ChangelogFrontmatter,
    ChangelogFrontmatterEnterprise,
)
from cortex.documentation.schemas.decision import (
    DecisionFrontmatter,
    DecisionFrontmatterEnterprise,
)
from cortex.documentation.schemas.glossary import (
    GlossaryFrontmatter,
    GlossaryFrontmatterEnterprise,
)
from cortex.documentation.schemas.handoff import (
    HandoffFrontmatter,
    HandoffFrontmatterEnterprise,
)
from cortex.documentation.schemas.hu import HUFrontmatter, HUFrontmatterEnterprise
from cortex.documentation.schemas.incident import (
    IncidentFrontmatter,
    IncidentFrontmatterEnterprise,
)
from cortex.documentation.schemas.postmortem import (
    PostmortemFrontmatter,
    PostmortemFrontmatterEnterprise,
)
from cortex.documentation.schemas.runbook import (
    RunbookFrontmatter,
    RunbookFrontmatterEnterprise,
)
from cortex.documentation.schemas.session import (
    CortexTelemetry,
    SessionFrontmatter,
    SessionFrontmatterEnterprise,
)
from cortex.documentation.schemas.spec import (
    SpecFrontmatter,
    SpecFrontmatterEnterprise,
)


SCHEMA_BY_TYPE: dict[DocType, type[CommonFrontmatter]] = {
    DocType.SESSION: SessionFrontmatter,
    DocType.HANDOFF: HandoffFrontmatter,
    DocType.SPEC: SpecFrontmatter,
    DocType.ADR: ADRFrontmatter,
    DocType.DECISION: DecisionFrontmatter,
    DocType.INCIDENT: IncidentFrontmatter,
    DocType.POSTMORTEM: PostmortemFrontmatter,
    DocType.RUNBOOK: RunbookFrontmatter,
    DocType.ARCHITECTURE: ArchitectureFrontmatter,
    DocType.CHANGELOG: ChangelogFrontmatter,
    DocType.HU: HUFrontmatter,
    DocType.GLOSSARY: GlossaryFrontmatter,
}

SCHEMA_BY_TYPE_ENTERPRISE: dict[DocType, type[EnterpriseFrontmatter]] = {
    DocType.SESSION: SessionFrontmatterEnterprise,
    DocType.HANDOFF: HandoffFrontmatterEnterprise,
    DocType.SPEC: SpecFrontmatterEnterprise,
    DocType.ADR: ADRFrontmatterEnterprise,
    DocType.DECISION: DecisionFrontmatterEnterprise,
    DocType.INCIDENT: IncidentFrontmatterEnterprise,
    DocType.POSTMORTEM: PostmortemFrontmatterEnterprise,
    DocType.RUNBOOK: RunbookFrontmatterEnterprise,
    DocType.ARCHITECTURE: ArchitectureFrontmatterEnterprise,
    DocType.CHANGELOG: ChangelogFrontmatterEnterprise,
    DocType.HU: HUFrontmatterEnterprise,
    DocType.GLOSSARY: GlossaryFrontmatterEnterprise,
}


__all__ = [
    # Base
    "AuditEvent",
    "CommonFrontmatter",
    "EnterpriseFrontmatter",
    # Type-specific
    "ADRFrontmatter",
    "ADRFrontmatterEnterprise",
    "ArchitectureFrontmatter",
    "ArchitectureFrontmatterEnterprise",
    "ChangelogFrontmatter",
    "ChangelogFrontmatterEnterprise",
    "CortexTelemetry",
    "DecisionFrontmatter",
    "DecisionFrontmatterEnterprise",
    "GlossaryFrontmatter",
    "GlossaryFrontmatterEnterprise",
    "HUFrontmatter",
    "HUFrontmatterEnterprise",
    "HandoffFrontmatter",
    "HandoffFrontmatterEnterprise",
    "IncidentFrontmatter",
    "IncidentFrontmatterEnterprise",
    "PostmortemFrontmatter",
    "PostmortemFrontmatterEnterprise",
    "RunbookFrontmatter",
    "RunbookFrontmatterEnterprise",
    "SessionFrontmatter",
    "SessionFrontmatterEnterprise",
    "SpecFrontmatter",
    "SpecFrontmatterEnterprise",
    # Maps
    "SCHEMA_BY_TYPE",
    "SCHEMA_BY_TYPE_ENTERPRISE",
]
