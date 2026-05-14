"""Tests for cortex.documentation.templates_engine."""

from __future__ import annotations

import pytest

from cortex.documentation.errors import TemplateRenderError
from cortex.documentation.templates_engine import render_template


def test_render_adr_minimal() -> None:
    body = render_template(
        "adr.md.j2",
        {
            "title": "T",
            "context": "ctx",
            "decision": "d",
            "alternatives_considered": [],
            "consequences": "cs",
            "supersedes": [],
        },
    )
    assert "## Decision" in body
    assert "## Context" in body
    # Empty supersedes -> section omitted
    assert "## Supersedes" not in body


def test_render_adr_with_supersedes() -> None:
    body = render_template(
        "adr.md.j2",
        {
            "title": "T",
            "context": "ctx",
            "decision": "d",
            "alternatives_considered": [],
            "consequences": "cs",
            "supersedes": ["ADR-003"],
        },
    )
    assert "## Supersedes" in body
    assert "[[ADR-003]]" in body


def test_render_runbook_with_procedure_steps() -> None:
    body = render_template(
        "runbook.md.j2",
        {
            "title": "T",
            "description": "Deploy procedure",
            "runbook_kind": "deploy",
            "applies_to": ["auth"],
            "prerequisites": ["have access"],
            "procedure": ["step1", "step2"],
            "rollback_procedure": [],
            "verification": [],
            "estimated_duration_minutes": 0,
            "last_verified_at": None,
        },
    )
    assert "### Step 1" in body
    assert "### Step 2" in body
    assert "step1" in body
    assert "## Rollback Procedure" not in body  # empty list omitted


def test_render_incident_postmortem_link() -> None:
    body = render_template(
        "incident.md.j2",
        {
            "title": "T",
            "short_description": "Auth down",
            "severity": "high",
            "affected_services": ["auth"],
            "impact": "users can't log in",
            "timeline": ["10:00 - alert"],
            "root_cause_postmortem": "postmortems/PM-001-auth.md",
        },
    )
    assert "**HIGH**" in body
    assert "[[postmortems/PM-001-auth.md]]" in body


def test_render_changelog_omits_empty_sections() -> None:
    body = render_template(
        "changelog.md.j2",
        {
            "title": "T",
            "version": "v1.0.0",
            "release_date": None,
            "added": ["new feature"],
            "changed": [],
            "deprecated": [],
            "removed": [],
            "fixed": [],
            "security": [],
        },
    )
    assert "# v1.0.0" in body
    assert "## Added" in body
    assert "new feature" in body
    assert "## Changed" not in body
    assert "## Security" not in body


def test_render_glossary_with_related_terms() -> None:
    body = render_template(
        "glossary.md.j2",
        {
            "title": "DocType",
            "term": "DocType",
            "definition": "An enum",
            "examples": ["adr", "session"],
            "related_terms": ["RouteSpec"],
            "domain": "documentation",
        },
    )
    assert "# DocType" in body
    assert "**Domain:** documentation" in body
    assert "[[RouteSpec]]" in body


def test_render_unknown_template_raises() -> None:
    with pytest.raises(TemplateRenderError, match="bogus.md.j2"):
        render_template("bogus.md.j2", {})


def test_render_all_12_templates_work_with_minimal_data() -> None:
    """Every canonical template renders without error given its minimum data."""
    cases = [
        (
            "session.md.j2",
            {
                "title": "T", "session_id": "abc", "spec_summary": "",
                "changes_made": [], "files_touched": [], "key_decisions": [],
                "next_steps": [], "verified_state": [], "unverified_claims": [],
                "blockers": [], "suggested_skills": [],
            },
        ),
        (
            "handoff.md.j2",
            {
                "title": "T", "parent_session_id": "abc", "context_required": "",
                "verified_state": [], "unverified_claims": [], "blockers": [],
                "next_session_needs": [], "suggested_skills": [],
            },
        ),
        (
            "spec.md.j2",
            {
                "title": "T", "goal": "", "requirements": [],
                "files_in_scope": [], "constraints": [], "acceptance_criteria": [],
            },
        ),
        (
            "decision.md.j2",
            {
                "title": "T", "context": "c", "decision": "d",
                "alternative_rejected": "ar", "reason": "r",
                "reversible_within_days": 0,
            },
        ),
        (
            "postmortem.md.j2",
            {
                "title": "T", "incident_path": "incidents/INC-001.md",
                "severity": "high", "root_cause": "rc",
                "contributing_factors": [], "timeline": [],
                "what_went_well": [], "what_went_wrong": [], "action_items": [],
            },
        ),
        (
            "architecture.md.j2",
            {
                "title": "T", "summary": "s", "components": [], "diagrams": [],
                "contracts": [], "rationale": "r", "related_adrs": [],
            },
        ),
        (
            "hu.md.j2",
            {
                "title": "T", "description": "d", "acceptance_criteria": [],
                "external_id": "X-1", "source": "linear", "kind": "story",
                "assignee": None, "external_url": None, "synced_at": None,
            },
        ),
    ]
    for template_name, data in cases:
        body = render_template(template_name, data)
        assert isinstance(body, str)
        assert len(body) > 0
