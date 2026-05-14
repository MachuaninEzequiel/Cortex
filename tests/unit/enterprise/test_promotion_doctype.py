"""Tests for cortex.enterprise.promotion_doctype (Fase 10)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from cortex.documentation.common import (
    parse_frontmatter_lenient,
    split_frontmatter_and_body,
)
from cortex.enterprise.governance import GovernancePermissionError
from cortex.enterprise.models import (
    EnterpriseOrgConfig,
    EnterprisePolicies,
    TeamConfig,
)
from cortex.enterprise.promotion_doctype import (
    PromotionError,
    PromotionResult,
    promote_note_doctype_aware,
)


_FP = "a" * 64


def _write_adr(folder: Path, *, severity: str | None = None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "ADR-007-onnx.md"
    fm = {
        "schema_version": 1,
        "doc_type": "adr",
        "title": "ADR-007 ONNX",
        "created_at": "2026-05-14T10:00:00+00:00",
        "updated_at": "2026-05-14T10:00:00+00:00",
        "tags": ["onnx"],
        "status": "accepted",
        "fingerprint": _FP,
        "adr_number": 7,
        "supersedes": [],
        "alternatives_considered": [],
        "acceptance_criteria_met": True,
    }
    body = "## Context\nctx body\n\n## Decision\nadopt ONNX\n\n## Consequences\nno torch needed\n"
    path.write_text("---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n\n" + body, encoding="utf-8")
    return path


def _write_session(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "2026-05-14_abc_session.md"
    fm = {
        "schema_version": 1,
        "doc_type": "session",
        "title": "Session foo",
        "created_at": "2026-05-14T10:00:00+00:00",
        "updated_at": "2026-05-14T10:00:00+00:00",
        "tags": ["session"],
        "status": "completed",
        "fingerprint": _FP,
        "session_id": "abc",
    }
    body = (
        "## Original Specification\nfoo\n\n"
        "## Changes Made\n- did A\n\n"
        "## Key Decisions\n- decided X\n\n"
        "## Verified State\n- tests green\n\n"
        "## Next Steps\n- step\n"
    )
    path.write_text("---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n\n" + body, encoding="utf-8")
    return path


def _write_runbook(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "RB-deploy.md"
    fm = {
        "schema_version": 1,
        "doc_type": "runbook",
        "title": "Deploy",
        "created_at": "2026-05-14T10:00:00+00:00",
        "updated_at": "2026-05-14T10:00:00+00:00",
        "tags": ["deploy"],
        "status": "verified",
        "fingerprint": _FP,
        "runbook_kind": "deploy",
    }
    body = "## Description\nDeploy procedure.\n"
    path.write_text("---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n\n" + body, encoding="utf-8")
    return path


def _write_incident(folder: Path, severity: str = "high") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "INC-001.md"
    fm = {
        "schema_version": 1,
        "doc_type": "incident",
        "title": "Outage",
        "created_at": "2026-05-14T10:00:00+00:00",
        "updated_at": "2026-05-14T10:00:00+00:00",
        "tags": [],
        "status": "closed",
        "fingerprint": _FP,
        "incident_number": 1,
        "severity": severity,
        "opened_at": "2026-05-14T08:00:00+00:00",
    }
    body = "## Short Description\nDown\n"
    path.write_text("---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n\n" + body, encoding="utf-8")
    return path


def _write_handoff(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "2026-05-14_x.md"
    fm = {
        "schema_version": 1,
        "doc_type": "handoff",
        "title": "Continue",
        "created_at": "2026-05-14T10:00:00+00:00",
        "updated_at": "2026-05-14T10:00:00+00:00",
        "tags": [],
        "status": "open",
        "fingerprint": _FP,
        "parent_session_id": "abc",
    }
    body = "## Context Required\nfoo\n"
    path.write_text("---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n\n" + body, encoding="utf-8")
    return path


@pytest.fixture
def org() -> EnterpriseOrgConfig:
    return EnterpriseOrgConfig(
        teams=[
            TeamConfig(id="core", members=["alice@cx.com"], can_promote=True, can_review=True),
            TeamConfig(id="ml", members=["bob@cx.com"], can_promote=False),
        ],
        policies=EnterprisePolicies(confidential_visible_to=["core"]),
    )


@pytest.fixture
def vault_dirs(tmp_path: Path) -> tuple[Path, Path]:
    local = tmp_path / "vault"
    enterprise = tmp_path / "vault-enterprise"
    return local, enterprise


# ---------------------------------------------------------------------------
# Mode: as-is
# ---------------------------------------------------------------------------


def test_promote_adr_as_is(org: EnterpriseOrgConfig, vault_dirs) -> None:
    local, enterprise = vault_dirs
    src = _write_adr(local / "decisions")
    result = promote_note_doctype_aware(
        src, enterprise_vault_root=enterprise, org=org,
        project_id="proj-a", actor="alice@cx.com",
    )
    assert result.promotion_mode == "as-is"
    assert result.target_path.parts[-3:] == ("decisions", "proj-a", "ADR-007-onnx.md")
    assert not result.summarized
    fm = parse_frontmatter_lenient(result.target_path)
    assert fm["vault_scope"] == "enterprise"
    assert fm["owner"] == "alice@cx.com"
    assert fm["team"] == "core"
    assert fm["status"] == "accepted"
    # Retention default for ADR is 2555 days.
    assert fm["retention_days"] == 2555


def test_promote_preserves_body(org: EnterpriseOrgConfig, vault_dirs) -> None:
    local, enterprise = vault_dirs
    src = _write_adr(local / "decisions")
    result = promote_note_doctype_aware(
        src, enterprise_vault_root=enterprise, org=org,
        project_id="proj-a", actor="alice@cx.com",
    )
    raw = result.target_path.read_text(encoding="utf-8")
    assert "adopt ONNX" in raw
    assert "no torch needed" in raw


def test_promote_audit_trail_appended(org: EnterpriseOrgConfig, vault_dirs) -> None:
    local, enterprise = vault_dirs
    src = _write_adr(local / "decisions")
    result = promote_note_doctype_aware(
        src, enterprise_vault_root=enterprise, org=org,
        project_id="proj-a", actor="alice@cx.com", reason="Approved",
    )
    fm = parse_frontmatter_lenient(result.target_path)
    trail = fm["audit_trail"]
    assert any(e["action"] == "promoted" and e["actor"] == "alice@cx.com" for e in trail)
    promoted_event = next(e for e in trail if e["action"] == "promoted")
    assert promoted_event["reason"] == "Approved"


# ---------------------------------------------------------------------------
# Mode: summarize (SESSION)
# ---------------------------------------------------------------------------


def test_promote_session_summarizes(org: EnterpriseOrgConfig, vault_dirs) -> None:
    local, enterprise = vault_dirs
    src = _write_session(local / "sessions")
    result = promote_note_doctype_aware(
        src, enterprise_vault_root=enterprise, org=org,
        project_id="proj-a", actor="alice@cx.com",
    )
    assert result.promotion_mode == "summarize"
    assert result.summarized is True
    body_after_fm = split_frontmatter_and_body(
        result.target_path.read_text(encoding="utf-8")
    )[1]
    assert "Promoted session digest" in body_after_fm
    # The summarized body keeps high-signal sections only.
    assert "Key Decisions" in body_after_fm
    assert "Verified State" in body_after_fm
    # ...and drops the noisier ones.
    assert "Original Specification" not in body_after_fm
    assert "Next Steps" not in body_after_fm


# ---------------------------------------------------------------------------
# Mode: review-required (RUNBOOK)
# ---------------------------------------------------------------------------


def test_promote_runbook_requires_review(org: EnterpriseOrgConfig, vault_dirs) -> None:
    local, enterprise = vault_dirs
    src = _write_runbook(local / "runbooks")
    result = promote_note_doctype_aware(
        src, enterprise_vault_root=enterprise, org=org,
        project_id="proj-a", actor="alice@cx.com",
    )
    assert result.promotion_mode == "review-required"
    fm = parse_frontmatter_lenient(result.target_path)
    assert fm["status"] == "draft"
    assert result.requires_review is True


# ---------------------------------------------------------------------------
# Incident severity gate
# ---------------------------------------------------------------------------


def test_promote_incident_high_severity_succeeds(org: EnterpriseOrgConfig, vault_dirs) -> None:
    local, enterprise = vault_dirs
    src = _write_incident(local / "incidents", severity="high")
    result = promote_note_doctype_aware(
        src, enterprise_vault_root=enterprise, org=org,
        project_id="proj-a", actor="alice@cx.com",
    )
    assert result.target_path.exists()


def test_promote_incident_low_severity_blocked(org: EnterpriseOrgConfig, vault_dirs) -> None:
    local, enterprise = vault_dirs
    src = _write_incident(local / "incidents", severity="low")
    with pytest.raises(PromotionError, match="severity=low"):
        promote_note_doctype_aware(
            src, enterprise_vault_root=enterprise, org=org,
            project_id="proj-a", actor="alice@cx.com",
        )


# ---------------------------------------------------------------------------
# Non-promotable types
# ---------------------------------------------------------------------------


def test_promote_handoff_raises(org: EnterpriseOrgConfig, vault_dirs) -> None:
    local, enterprise = vault_dirs
    src = _write_handoff(local / "handoffs")
    with pytest.raises(PromotionError, match="not promotable"):
        promote_note_doctype_aware(
            src, enterprise_vault_root=enterprise, org=org,
            project_id="proj-a", actor="alice@cx.com",
        )


# ---------------------------------------------------------------------------
# Governance
# ---------------------------------------------------------------------------


def test_promote_unauthorised_actor_raises(org: EnterpriseOrgConfig, vault_dirs) -> None:
    local, enterprise = vault_dirs
    src = _write_adr(local / "decisions")
    with pytest.raises(GovernancePermissionError, match="cannot promote"):
        promote_note_doctype_aware(
            src, enterprise_vault_root=enterprise, org=org,
            project_id="proj-a", actor="bob@cx.com",
        )


def test_promote_unknown_actor_raises(org: EnterpriseOrgConfig, vault_dirs) -> None:
    local, enterprise = vault_dirs
    src = _write_adr(local / "decisions")
    with pytest.raises(GovernancePermissionError):
        promote_note_doctype_aware(
            src, enterprise_vault_root=enterprise, org=org,
            project_id="proj-a", actor="eve@external.com",
        )


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


def test_promote_missing_source_raises(org: EnterpriseOrgConfig, vault_dirs) -> None:
    _, enterprise = vault_dirs
    with pytest.raises(PromotionError, match="source not found"):
        promote_note_doctype_aware(
            Path("/non/existent.md"), enterprise_vault_root=enterprise,
            org=org, project_id="p", actor="alice@cx.com",
        )


def test_promote_no_doc_type_in_frontmatter_raises(
    org: EnterpriseOrgConfig, vault_dirs, tmp_path: Path,
) -> None:
    _, enterprise = vault_dirs
    bad = tmp_path / "bad.md"
    bad.write_text("---\ntitle: x\n---\nbody", encoding="utf-8")
    with pytest.raises(PromotionError, match="no doc_type"):
        promote_note_doctype_aware(
            bad, enterprise_vault_root=enterprise, org=org,
            project_id="p", actor="alice@cx.com",
        )


def test_promote_unknown_doc_type_raises(
    org: EnterpriseOrgConfig, vault_dirs, tmp_path: Path,
) -> None:
    _, enterprise = vault_dirs
    bad = tmp_path / "bad.md"
    bad.write_text("---\ndoc_type: bogus\ntitle: x\n---\nbody", encoding="utf-8")
    with pytest.raises(PromotionError, match="unknown doc_type"):
        promote_note_doctype_aware(
            bad, enterprise_vault_root=enterprise, org=org,
            project_id="p", actor="alice@cx.com",
        )


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------


def test_dry_run_does_not_write(org: EnterpriseOrgConfig, vault_dirs) -> None:
    local, enterprise = vault_dirs
    src = _write_adr(local / "decisions")
    result = promote_note_doctype_aware(
        src, enterprise_vault_root=enterprise, org=org,
        project_id="proj-a", actor="alice@cx.com", dry_run=True,
    )
    assert not result.target_path.exists()
