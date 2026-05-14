"""Tests for type-specific frontmatter schemas.

One canonical test per DocType: minimal valid construction. Type-specific
constraints (e.g. severity, runbook_kind) are tested individually.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas import (
    SCHEMA_BY_TYPE,
    SCHEMA_BY_TYPE_ENTERPRISE,
    ADRFrontmatter,
    ChangelogFrontmatter,
    CortexTelemetry,
    GlossaryFrontmatter,
    HUFrontmatter,
    HandoffFrontmatter,
    IncidentFrontmatter,
    PostmortemFrontmatter,
    RunbookFrontmatter,
    SessionFrontmatter,
)

_NOW = datetime(2026, 5, 14, 10, 0, 0, tzinfo=UTC)
_FP = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"


def _common(doc_type: DocType, status: str) -> dict:
    return {
        "doc_type": doc_type,
        "title": "Test",
        "created_at": _NOW,
        "updated_at": _NOW,
        "status": status,
        "fingerprint": _FP,
    }


# --- Schema map integrity --------------------------------------------------


def test_schema_by_type_has_all_doc_types() -> None:
    for dt in DocType:
        assert dt in SCHEMA_BY_TYPE
        assert dt in SCHEMA_BY_TYPE_ENTERPRISE


def test_each_schema_has_correct_doc_type_default() -> None:
    """A schema's default ``doc_type`` matches its key in SCHEMA_BY_TYPE."""
    for dt, cls in SCHEMA_BY_TYPE.items():
        # Pydantic v2 stores defaults on the field info.
        field = cls.model_fields["doc_type"]
        assert field.default == dt


# --- SESSION ---------------------------------------------------------------


def test_session_minimal_valid() -> None:
    fm = SessionFrontmatter(
        **_common(DocType.SESSION, "completed"),
        session_id="abc123",
    )
    assert fm.session_id == "abc123"


def test_session_with_telemetry() -> None:
    telemetry = CortexTelemetry(
        enricher_run_id="run1",
        context_items_offered=8,
        context_items_used=3,
        context_hit_rate=0.375,
        context_by_type={"adr": 1},
        context_by_strategy={"topic_search": 2},
        context_by_scope={"local": 3},
    )
    fm = SessionFrontmatter(
        **_common(DocType.SESSION, "completed"),
        session_id="abc",
        cortex_telemetry=telemetry,
    )
    assert fm.cortex_telemetry is not None
    assert fm.cortex_telemetry.context_hit_rate == 0.375


def test_session_missing_session_id_raises() -> None:
    with pytest.raises(ValidationError):
        SessionFrontmatter(**_common(DocType.SESSION, "completed"))


def test_session_hit_rate_out_of_range_raises() -> None:
    with pytest.raises(ValidationError):
        CortexTelemetry(
            enricher_run_id="r",
            context_items_offered=1,
            context_items_used=1,
            context_hit_rate=1.5,  # invalid
        )


# --- HANDOFF ---------------------------------------------------------------


def test_handoff_minimal_valid() -> None:
    fm = HandoffFrontmatter(
        **_common(DocType.HANDOFF, "open"),
        parent_session_id="abc123",
    )
    assert fm.parent_session_id == "abc123"


# --- ADR -------------------------------------------------------------------


def test_adr_minimal_valid() -> None:
    fm = ADRFrontmatter(
        **_common(DocType.ADR, "accepted"),
        adr_number=7,
    )
    assert fm.adr_number == 7
    assert fm.supersedes == []


def test_adr_zero_number_raises() -> None:
    with pytest.raises(ValidationError):
        ADRFrontmatter(**_common(DocType.ADR, "accepted"), adr_number=0)


def test_adr_supersedes_list() -> None:
    fm = ADRFrontmatter(
        **_common(DocType.ADR, "accepted"),
        adr_number=7,
        supersedes=["ADR-003"],
    )
    assert fm.supersedes == ["ADR-003"]


# --- INCIDENT --------------------------------------------------------------


def test_incident_minimal_valid() -> None:
    fm = IncidentFrontmatter(
        **_common(DocType.INCIDENT, "open"),
        incident_number=1,
        severity="high",
        opened_at=_NOW,
    )
    assert fm.severity == "high"
    assert fm.closed_at is None


def test_incident_invalid_severity_raises() -> None:
    with pytest.raises(ValidationError, match="severity"):
        IncidentFrontmatter(
            **_common(DocType.INCIDENT, "open"),
            incident_number=1,
            severity="catastrophic",
            opened_at=_NOW,
        )


def test_incident_naive_opened_at_raises() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        IncidentFrontmatter(
            **_common(DocType.INCIDENT, "open"),
            incident_number=1,
            severity="high",
            opened_at=datetime(2026, 5, 14),
        )


# --- POSTMORTEM ------------------------------------------------------------


def test_postmortem_minimal_valid() -> None:
    fm = PostmortemFrontmatter(
        **_common(DocType.POSTMORTEM, "draft"),
        incident_number=1,
        incident_path="incidents/INC-001.md",
        severity="high",
    )
    assert fm.incident_path == "incidents/INC-001.md"


# --- RUNBOOK ---------------------------------------------------------------


def test_runbook_minimal_valid() -> None:
    fm = RunbookFrontmatter(
        **_common(DocType.RUNBOOK, "draft"),
    )
    assert fm.runbook_kind == "operational"


def test_runbook_invalid_kind_raises() -> None:
    with pytest.raises(ValidationError, match="runbook_kind"):
        RunbookFrontmatter(
            **_common(DocType.RUNBOOK, "draft"),
            runbook_kind="bogus",
        )


def test_runbook_all_valid_kinds() -> None:
    for kind in ("deploy", "rollback", "incident-response", "data-migration", "operational"):
        fm = RunbookFrontmatter(
            **_common(DocType.RUNBOOK, "draft"),
            runbook_kind=kind,
        )
        assert fm.runbook_kind == kind


# --- CHANGELOG -------------------------------------------------------------


def test_changelog_minimal_valid() -> None:
    fm = ChangelogFrontmatter(
        **_common(DocType.CHANGELOG, "released"),
        version="v1.2.3",
    )
    assert fm.version == "v1.2.3"


def test_changelog_missing_version_raises() -> None:
    with pytest.raises(ValidationError):
        ChangelogFrontmatter(**_common(DocType.CHANGELOG, "released"))


# --- HU --------------------------------------------------------------------


def test_hu_minimal_valid() -> None:
    fm = HUFrontmatter(
        **_common(DocType.HU, "backlog"),
        external_id="PROJ-1234",
        source="linear",
        kind="story",
    )
    assert fm.external_id == "PROJ-1234"


def test_hu_invalid_kind_raises() -> None:
    with pytest.raises(ValidationError, match="kind"):
        HUFrontmatter(
            **_common(DocType.HU, "backlog"),
            external_id="X",
            source="linear",
            kind="bogus",
        )


# --- GLOSSARY --------------------------------------------------------------


def test_glossary_minimal_valid() -> None:
    fm = GlossaryFrontmatter(
        **_common(DocType.GLOSSARY, "canonical"),
        term="Ubiquitous Language",
    )
    assert fm.term == "Ubiquitous Language"
    assert fm.related_terms == []


# --- All schemas: serialization roundtrip ----------------------------------


def test_all_schemas_serialize_and_revalidate() -> None:
    """A schema instance can serialize and revalidate equivalently."""
    fm = ADRFrontmatter(
        **_common(DocType.ADR, "accepted"),
        adr_number=7,
    )
    raw = fm.model_dump(mode="json")
    fm2 = ADRFrontmatter.model_validate(raw)
    assert fm == fm2
