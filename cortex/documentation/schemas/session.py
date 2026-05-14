"""SESSION frontmatter schema."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter


class CortexTelemetry(BaseModel):
    """Telemetry block embedded in session frontmatter (Fase 05)."""

    model_config = ConfigDict(frozen=True, extra="allow")

    enricher_run_id: str
    context_items_offered: int = Field(ge=0)
    context_items_used: int = Field(ge=0)
    context_hit_rate: float = Field(ge=0.0, le=1.0)
    context_by_type: dict[str, int] = Field(default_factory=dict)
    context_by_strategy: dict[str, int] = Field(default_factory=dict)
    context_by_scope: dict[str, int] = Field(default_factory=dict)
    enriched_score_p50: float = 0.0
    enriched_score_p95: float = 0.0
    enricher_latency_ms: int = Field(default=0, ge=0)
    filters_applied: dict | None = None


class _SessionFields(BaseModel):
    """Fields specific to SESSION (mixed into both local and enterprise)."""

    model_config = ConfigDict(frozen=True)

    session_id: str = Field(min_length=1)
    pr: str | None = None
    branch: str | None = None
    commit: str | None = None
    cortex_telemetry: CortexTelemetry | None = None


class SessionFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.SESSION
    session_id: str = Field(min_length=1)
    pr: str | None = None
    branch: str | None = None
    commit: str | None = None
    cortex_telemetry: CortexTelemetry | None = None


class SessionFrontmatterEnterprise(EnterpriseFrontmatter):
    doc_type: DocType = DocType.SESSION
    session_id: str = Field(min_length=1)
    pr: str | None = None
    branch: str | None = None
    commit: str | None = None
    cortex_telemetry: CortexTelemetry | None = None
