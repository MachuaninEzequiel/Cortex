"""cortex.documentation.data - Dataclasses for writer inputs.

Each ``write_X_note`` function accepts a typed ``XData`` dataclass.
These are *inputs*, not frontmatter schemas (those live in pydantic models
in ``cortex.documentation.schemas``).

Rationale: dataclasses are lighter for incremental construction by callers
(agents, services). Pydantic validation happens later when the writer
builds the frontmatter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CommonWriteData:
    """Fields common to every writer."""

    title: str = ""
    tags: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    status: str = ""

    # Enterprise-only (validated by writer when vault_scope='enterprise').
    owner: str | None = None
    team: str | None = None
    classification: str | None = None
    retention_days: int | None = None


@dataclass
class SessionData(CommonWriteData):
    session_id: str = ""
    spec_summary: str = ""
    changes_made: list[str] = field(default_factory=list)
    files_touched: list[str] = field(default_factory=list)
    key_decisions: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    pr: str | None = None
    branch: str | None = None
    commit: str | None = None
    verified_state: list[str] = field(default_factory=list)
    unverified_claims: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    suggested_skills: list[str] = field(default_factory=list)
    cortex_telemetry: dict[str, Any] | None = None


@dataclass
class HandoffData(CommonWriteData):
    parent_session_id: str = ""
    next_session_needs: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    verified_state: list[str] = field(default_factory=list)
    unverified_claims: list[str] = field(default_factory=list)
    suggested_skills: list[str] = field(default_factory=list)
    context_required: str = ""


@dataclass
class SpecData(CommonWriteData):
    goal: str = ""
    requirements: list[str] = field(default_factory=list)
    files_in_scope: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)


@dataclass
class ADRData(CommonWriteData):
    context: str = ""
    decision: str = ""
    alternatives_considered: list[str] = field(default_factory=list)
    consequences: str = ""
    adr_number: int = 0  # 0 = auto-assign next available
    supersedes: list[str] = field(default_factory=list)
    superseded_by: str | None = None
    acceptance_criteria_met: bool = False


@dataclass
class DecisionData(CommonWriteData):
    context: str = ""
    decision: str = ""
    alternative_rejected: str = ""
    reason: str = ""
    reversible_within_days: int = 0


@dataclass
class IncidentData(CommonWriteData):
    incident_number: int = 0  # 0 = auto-assign
    severity: str = "medium"  # low | medium | high | critical
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    affected_services: list[str] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)
    impact: str = ""
    short_description: str = ""
    root_cause_postmortem: str | None = None


@dataclass
class PostmortemData(CommonWriteData):
    incident_number: int = 0
    incident_path: str = ""
    root_cause: str = ""
    contributing_factors: list[str] = field(default_factory=list)
    what_went_well: list[str] = field(default_factory=list)
    what_went_wrong: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)
    severity: str = "medium"


@dataclass
class RunbookData(CommonWriteData):
    runbook_kind: str = "operational"  # deploy | rollback | incident-response | data-migration | operational
    description: str = ""
    prerequisites: list[str] = field(default_factory=list)
    procedure: list[str] = field(default_factory=list)
    rollback_procedure: list[str] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    applies_to: list[str] = field(default_factory=list)
    estimated_duration_minutes: int = 0
    last_verified_at: datetime | None = None


@dataclass
class ArchitectureData(CommonWriteData):
    summary: str = ""
    components: list[str] = field(default_factory=list)
    diagrams: list[str] = field(default_factory=list)
    contracts: list[str] = field(default_factory=list)
    rationale: str = ""
    related_adrs: list[str] = field(default_factory=list)


@dataclass
class ChangelogData(CommonWriteData):
    version: str = ""
    release_date: datetime | None = None
    added: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    deprecated: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    fixed: list[str] = field(default_factory=list)
    security: list[str] = field(default_factory=list)


@dataclass
class HUData(CommonWriteData):
    external_id: str = ""
    source: str = ""  # "jira" | "linear" | "github" | ...
    kind: str = "story"  # story | task | bug | epic
    description: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    assignee: str | None = None
    external_url: str | None = None
    synced_at: datetime | None = None


@dataclass
class GlossaryEntryData(CommonWriteData):
    term: str = ""
    definition: str = ""
    examples: list[str] = field(default_factory=list)
    related_terms: list[str] = field(default_factory=list)
    domain: str | None = None
