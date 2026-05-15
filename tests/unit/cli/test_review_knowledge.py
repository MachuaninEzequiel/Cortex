"""Tests for ``cortex review-knowledge`` typer subapp (Item #9).

Exercises the pending / approve / reject subcommands operating on the
DocType-aware promotion queue (``status: draft`` notes inside the
enterprise vault).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cortex.cli.review_knowledge import review_app
from cortex.documentation.common import parse_frontmatter_lenient
from cortex.enterprise.promotion_doctype import (
    PromotionError,
    list_pending_drafts,
    mark_as_accepted,
    mark_as_rejected,
)

runner = CliRunner()


def _write_note(
    path: Path,
    *,
    doc_type: str = "runbook",
    status: str = "draft",
    title: str = "Test note",
    owner: str = "alice",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = (
        "---\n"
        "schema_version: 1\n"
        f"doc_type: {doc_type}\n"
        f"title: \"{title}\"\n"
        f"status: {status}\n"
        f"owner: {owner}\n"
        "team: platform\n"
        "classification: internal\n"
        "retention_days: 365\n"
        f"created_at: \"{datetime.now(UTC).isoformat()}\"\n"
        f"updated_at: \"{datetime.now(UTC).isoformat()}\"\n"
        "tags: []\n"
        "links: []\n"
        "fingerprint: abc123\n"
        "vault_scope: enterprise\n"
        "audit_trail: []\n"
        "---\n\n"
        "# Body\n\n"
        "Sample content.\n"
    )
    path.write_text(fm, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def test_list_pending_drafts_returns_only_draft_notes(tmp_path: Path) -> None:
    vault = tmp_path / "vault-enterprise"
    _write_note(vault / "runbooks" / "rb-1.md", status="draft")
    _write_note(vault / "runbooks" / "rb-2.md", status="accepted")
    _write_note(vault / "specs" / "spec-1.md", status="draft", doc_type="spec")

    pending = list_pending_drafts(vault)
    paths = [p["path"] for p in pending]
    assert "runbooks/rb-1.md" in paths
    assert "specs/spec-1.md" in paths
    assert "runbooks/rb-2.md" not in paths


def test_list_pending_drafts_filters_by_doc_type(tmp_path: Path) -> None:
    vault = tmp_path / "vault-enterprise"
    _write_note(vault / "runbooks" / "rb-1.md", status="draft", doc_type="runbook")
    _write_note(vault / "specs" / "spec-1.md", status="draft", doc_type="spec")

    only_specs = list_pending_drafts(vault, doc_types=["spec"])
    assert [p["doc_type"] for p in only_specs] == ["spec"]


def test_list_pending_drafts_excludes_rejected_folder(tmp_path: Path) -> None:
    vault = tmp_path / "vault-enterprise"
    _write_note(vault / "runbooks" / "rejected" / "old.md", status="draft")
    pending = list_pending_drafts(vault)
    assert pending == []


def test_mark_as_accepted_updates_status_and_audit_trail(tmp_path: Path) -> None:
    note = _write_note(tmp_path / "rb-1.md", status="draft")

    mark_as_accepted(note, reviewer="bob", reason="LGTM")

    fm = parse_frontmatter_lenient(note)
    assert fm["status"] == "accepted"
    trail = fm["audit_trail"]
    assert trail[-1]["actor"] == "bob"
    assert trail[-1]["action"] == "accepted"
    assert trail[-1]["reason"] == "LGTM"


def test_mark_as_accepted_rejects_non_draft(tmp_path: Path) -> None:
    note = _write_note(tmp_path / "rb-1.md", status="accepted")
    with pytest.raises(PromotionError, match="expected 'draft'"):
        mark_as_accepted(note, reviewer="bob")


def test_mark_as_rejected_moves_to_rejected_folder(tmp_path: Path) -> None:
    note = _write_note(tmp_path / "runbooks" / "rb-1.md", status="draft")

    new_path = mark_as_rejected(note, reviewer="bob", reason="duplicated")

    assert new_path is not None
    assert new_path.exists()
    assert new_path.parent.name == "rejected"
    assert not note.exists()
    fm = parse_frontmatter_lenient(new_path)
    assert fm["status"] == "rejected"
    assert fm["audit_trail"][-1]["actor"] == "bob"
    assert fm["audit_trail"][-1]["reason"] == "duplicated"


def test_mark_as_rejected_with_delete_removes_file(tmp_path: Path) -> None:
    note = _write_note(tmp_path / "rb-1.md", status="draft")
    new_path = mark_as_rejected(note, reviewer="bob", reason="spam", delete=True)
    assert new_path is None
    assert not note.exists()


def test_mark_as_rejected_rejects_non_draft(tmp_path: Path) -> None:
    note = _write_note(tmp_path / "rb-1.md", status="accepted")
    with pytest.raises(PromotionError, match="expected 'draft'"):
        mark_as_rejected(note, reviewer="bob", reason="x")


# ---------------------------------------------------------------------------
# Typer subapp wiring
# ---------------------------------------------------------------------------


def _setup_workspace(tmp_path: Path) -> Path:
    """Build a minimal new-layout workspace with an enterprise vault."""
    cortex_dir = tmp_path / ".cortex"
    cortex_dir.mkdir(parents=True)
    (cortex_dir / "config.yaml").write_text("layout_version: 2\n", encoding="utf-8")
    (cortex_dir / "vault-enterprise").mkdir(parents=True)
    (tmp_path / ".git").mkdir()
    return tmp_path


def test_cli_pending_lists_draft_notes(tmp_path: Path) -> None:
    root = _setup_workspace(tmp_path)
    enterprise_vault = root / ".cortex" / "vault-enterprise"
    _write_note(enterprise_vault / "runbooks" / "rb-1.md", status="draft", doc_type="runbook")
    _write_note(enterprise_vault / "specs" / "spec-1.md", status="accepted", doc_type="spec")

    result = runner.invoke(
        review_app,
        ["pending", "--project-root", str(root), "--json"],
    )

    assert result.exit_code == 0, result.output
    assert "runbooks/rb-1.md" in result.output
    assert "specs/spec-1.md" not in result.output


def test_cli_approve_changes_status_and_emits_audit(tmp_path: Path) -> None:
    root = _setup_workspace(tmp_path)
    enterprise_vault = root / ".cortex" / "vault-enterprise"
    note = _write_note(
        enterprise_vault / "runbooks" / "rb-1.md", status="draft", doc_type="runbook"
    )

    result = runner.invoke(
        review_app,
        [
            "approve",
            "runbooks/rb-1.md",
            "--reviewer",
            "carol",
            "--reason",
            "Looks good",
            "--project-root",
            str(root),
        ],
    )

    assert result.exit_code == 0, result.output
    fm = parse_frontmatter_lenient(note)
    assert fm["status"] == "accepted"
    assert fm["audit_trail"][-1]["actor"] == "carol"


def test_cli_reject_moves_to_rejected(tmp_path: Path) -> None:
    root = _setup_workspace(tmp_path)
    enterprise_vault = root / ".cortex" / "vault-enterprise"
    note = _write_note(
        enterprise_vault / "runbooks" / "rb-1.md", status="draft", doc_type="runbook"
    )

    result = runner.invoke(
        review_app,
        [
            "reject",
            "runbooks/rb-1.md",
            "--reviewer",
            "dan",
            "--reason",
            "duplicate",
            "--project-root",
            str(root),
        ],
    )

    assert result.exit_code == 0, result.output
    assert not note.exists()
    rejected = enterprise_vault / "runbooks" / "rejected" / "rb-1.md"
    assert rejected.exists()


def test_cli_reject_with_delete_removes_file(tmp_path: Path) -> None:
    root = _setup_workspace(tmp_path)
    enterprise_vault = root / ".cortex" / "vault-enterprise"
    note = _write_note(
        enterprise_vault / "runbooks" / "rb-1.md", status="draft", doc_type="runbook"
    )

    result = runner.invoke(
        review_app,
        [
            "reject",
            "runbooks/rb-1.md",
            "--reviewer",
            "dan",
            "--reason",
            "spam",
            "--delete",
            "--project-root",
            str(root),
        ],
    )

    assert result.exit_code == 0, result.output
    assert not note.exists()
    assert not (enterprise_vault / "runbooks" / "rejected" / "rb-1.md").exists()


def test_cli_approve_fails_when_status_not_draft(tmp_path: Path) -> None:
    root = _setup_workspace(tmp_path)
    enterprise_vault = root / ".cortex" / "vault-enterprise"
    _write_note(
        enterprise_vault / "runbooks" / "rb-1.md", status="accepted", doc_type="runbook"
    )

    result = runner.invoke(
        review_app,
        [
            "approve",
            "runbooks/rb-1.md",
            "--reviewer",
            "eve",
            "--project-root",
            str(root),
        ],
    )

    assert result.exit_code == 1
    assert "expected 'draft'" in result.stderr or "expected 'draft'" in result.output


def test_cli_approve_rejects_path_outside_vault(tmp_path: Path) -> None:
    root = _setup_workspace(tmp_path)

    result = runner.invoke(
        review_app,
        [
            "approve",
            "../../etc/passwd",
            "--reviewer",
            "eve",
            "--project-root",
            str(root),
        ],
    )

    assert result.exit_code == 1
    assert "escapes" in (result.stderr + result.output)
