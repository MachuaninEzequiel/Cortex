"""Tests for cortex.documentation.audit."""

from __future__ import annotations

from datetime import UTC, datetime

from cortex.documentation.audit import append_audit_event
from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas import ADRFrontmatterEnterprise

_NOW = datetime(2026, 5, 14, 10, 0, 0, tzinfo=UTC)
_FP = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"


def _enterprise_adr() -> ADRFrontmatterEnterprise:
    return ADRFrontmatterEnterprise(
        doc_type=DocType.ADR,
        title="T",
        created_at=_NOW,
        updated_at=_NOW,
        status="accepted",
        fingerprint=_FP,
        vault_scope="enterprise",
        owner="a@b.com",
        team="t",
        classification="internal",
        retention_days=365,
        audit_trail=[],
        adr_number=1,
    )


def test_append_audit_event_returns_new_instance() -> None:
    fm = _enterprise_adr()
    fm2 = append_audit_event(fm, "user@example.com", "created")
    assert fm is not fm2
    assert len(fm.audit_trail) == 0  # original unchanged
    assert len(fm2.audit_trail) == 1


def test_append_audit_event_with_reason() -> None:
    fm = _enterprise_adr()
    fm2 = append_audit_event(fm, "u@e.com", "promoted", reason="Approved")
    assert fm2.audit_trail[0].reason == "Approved"


def test_append_audit_event_preserves_existing_trail() -> None:
    fm = _enterprise_adr()
    fm = append_audit_event(fm, "u@e.com", "created")
    fm = append_audit_event(fm, "reviewer@e.com", "reviewed")
    fm = append_audit_event(fm, "promoter@e.com", "promoted")
    assert len(fm.audit_trail) == 3
    assert fm.audit_trail[0].action == "created"
    assert fm.audit_trail[1].action == "reviewed"
    assert fm.audit_trail[2].action == "promoted"


def test_append_audit_event_returns_same_class() -> None:
    fm = _enterprise_adr()
    fm2 = append_audit_event(fm, "u@e.com", "created")
    assert isinstance(fm2, ADRFrontmatterEnterprise)


def test_append_audit_event_actor_preserved() -> None:
    fm = _enterprise_adr()
    fm2 = append_audit_event(fm, "alice@cortex.ai", "updated")
    assert fm2.audit_trail[0].actor == "alice@cortex.ai"
