"""Tests for cortex.documentation.schemas.base."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import (
    AuditEvent,
    CommonFrontmatter,
    EnterpriseFrontmatter,
)

# Reusable values.
_NOW = datetime(2026, 5, 14, 10, 0, 0, tzinfo=UTC)
_FP = "a" * 64
_VALID_FP_HEX = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"


def _common_kwargs() -> dict:
    return {
        "doc_type": DocType.SPEC,
        "title": "Test",
        "created_at": _NOW,
        "updated_at": _NOW,
        "status": "draft",
        "fingerprint": _VALID_FP_HEX,
    }


def _enterprise_kwargs() -> dict:
    return {
        **_common_kwargs(),
        "vault_scope": "enterprise",
        "owner": "ezequiel@cortex.ai",
        "team": "cortex-core",
        "classification": "internal",
        "retention_days": 365,
    }


# --- CommonFrontmatter -----------------------------------------------------


def test_common_frontmatter_minimal_valid() -> None:
    fm = CommonFrontmatter(**_common_kwargs())
    assert fm.schema_version == 1
    assert fm.tags == []
    assert fm.links == []
    assert fm.vault_scope == "local"


def test_common_frontmatter_missing_title_raises() -> None:
    kwargs = _common_kwargs()
    kwargs["title"] = ""
    with pytest.raises(ValidationError, match="title"):
        CommonFrontmatter(**kwargs)


def test_common_frontmatter_invalid_status_raises() -> None:
    kwargs = _common_kwargs()
    kwargs["status"] = "bogus"
    with pytest.raises(ValidationError, match="status"):
        CommonFrontmatter(**kwargs)


def test_common_frontmatter_naive_datetime_raises() -> None:
    kwargs = _common_kwargs()
    kwargs["created_at"] = datetime(2026, 5, 14)  # no tz
    with pytest.raises(ValidationError, match="timezone"):
        CommonFrontmatter(**kwargs)


def test_common_frontmatter_updated_before_created_raises() -> None:
    kwargs = _common_kwargs()
    kwargs["updated_at"] = _NOW - timedelta(days=1)
    with pytest.raises(ValidationError, match=">= created_at"):
        CommonFrontmatter(**kwargs)


def test_common_frontmatter_invalid_vault_scope_raises() -> None:
    kwargs = _common_kwargs()
    kwargs["vault_scope"] = "shared"
    with pytest.raises(ValidationError, match="vault_scope"):
        CommonFrontmatter(**kwargs)


def test_common_frontmatter_invalid_fingerprint_format_raises() -> None:
    kwargs = _common_kwargs()
    kwargs["fingerprint"] = "not-64-hex"
    with pytest.raises(ValidationError, match="fingerprint"):
        CommonFrontmatter(**kwargs)


def test_common_frontmatter_short_fingerprint_raises() -> None:
    kwargs = _common_kwargs()
    kwargs["fingerprint"] = "abcd"
    with pytest.raises(ValidationError):
        CommonFrontmatter(**kwargs)


def test_common_frontmatter_uppercase_fingerprint_raises() -> None:
    kwargs = _common_kwargs()
    kwargs["fingerprint"] = "A" * 64
    with pytest.raises(ValidationError):
        CommonFrontmatter(**kwargs)


def test_common_frontmatter_non_utc_tz_allowed() -> None:
    """Any timezone-aware datetime is valid, not just UTC."""
    eastern = timezone(timedelta(hours=-5))
    kwargs = _common_kwargs()
    kwargs["created_at"] = datetime(2026, 5, 14, 10, 0, 0, tzinfo=eastern)
    kwargs["updated_at"] = datetime(2026, 5, 14, 10, 0, 0, tzinfo=eastern)
    fm = CommonFrontmatter(**kwargs)
    assert fm.created_at.tzinfo is not None


# --- AuditEvent ------------------------------------------------------------


def test_audit_event_minimal_valid() -> None:
    e = AuditEvent(actor="user@example.com", action="created", timestamp=_NOW)
    assert e.reason is None


def test_audit_event_with_reason() -> None:
    e = AuditEvent(
        actor="user@example.com",
        action="promoted",
        timestamp=_NOW,
        reason="Approved by tech lead",
    )
    assert e.reason == "Approved by tech lead"


def test_audit_event_naive_timestamp_raises() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        AuditEvent(actor="u", action="created", timestamp=datetime(2026, 1, 1))


def test_audit_event_empty_actor_raises() -> None:
    with pytest.raises(ValidationError):
        AuditEvent(actor="", action="created", timestamp=_NOW)


# --- EnterpriseFrontmatter -------------------------------------------------


def test_enterprise_frontmatter_full_valid() -> None:
    fm = EnterpriseFrontmatter(**_enterprise_kwargs())
    assert fm.owner == "ezequiel@cortex.ai"
    assert fm.audit_trail == []


def test_enterprise_frontmatter_requires_enterprise_scope() -> None:
    kwargs = _enterprise_kwargs()
    kwargs["vault_scope"] = "local"
    with pytest.raises(ValidationError, match="enterprise"):
        EnterpriseFrontmatter(**kwargs)


def test_enterprise_frontmatter_invalid_email_raises() -> None:
    kwargs = _enterprise_kwargs()
    kwargs["owner"] = "not an email"
    with pytest.raises(ValidationError, match="owner"):
        EnterpriseFrontmatter(**kwargs)


def test_enterprise_frontmatter_invalid_team_slug_raises() -> None:
    kwargs = _enterprise_kwargs()
    kwargs["team"] = "Has Spaces"
    with pytest.raises(ValidationError, match="team"):
        EnterpriseFrontmatter(**kwargs)


def test_enterprise_frontmatter_invalid_classification_raises() -> None:
    kwargs = _enterprise_kwargs()
    kwargs["classification"] = "secret"
    with pytest.raises(ValidationError, match="classification"):
        EnterpriseFrontmatter(**kwargs)


def test_enterprise_frontmatter_negative_retention_raises() -> None:
    kwargs = _enterprise_kwargs()
    kwargs["retention_days"] = -1
    with pytest.raises(ValidationError):
        EnterpriseFrontmatter(**kwargs)


def test_enterprise_frontmatter_with_audit_trail() -> None:
    kwargs = _enterprise_kwargs()
    kwargs["audit_trail"] = [
        {"actor": "u@e.com", "action": "created", "timestamp": _NOW.isoformat()},
        {"actor": "u@e.com", "action": "promoted", "timestamp": _NOW.isoformat()},
    ]
    fm = EnterpriseFrontmatter(**kwargs)
    assert len(fm.audit_trail) == 2


def test_enterprise_frontmatter_frozen_immutable() -> None:
    """frozen=True prevents attribute mutation."""
    fm = EnterpriseFrontmatter(**_enterprise_kwargs())
    with pytest.raises(ValidationError):
        fm.owner = "another@example.com"  # type: ignore[misc]
