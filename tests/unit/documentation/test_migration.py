"""Tests for cortex.documentation.migration (Fase 11)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from cortex.documentation.migration import (
    MigrationResult,
    format_report,
    migrate_vault,
    validate_vault,
)


def _write_legacy_note(
    folder: Path, name: str, *, body: str = "body", fm: dict | None = None,
) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.md"
    fm_dict = fm or {"title": name, "tags": ["legacy"], "status": "accepted",
                     "date": "2026-04-01"}
    path.write_text(
        "---\n" + yaml.safe_dump(fm_dict, sort_keys=False) + "---\n\n" + body,
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    src = _write_legacy_note(vault / "decisions", "ADR-007-foo")
    before = src.read_text(encoding="utf-8")
    result = migrate_vault(vault, apply=False, create_backup_archive=False)
    assert not result.applied
    assert len(result.migrated) == 1
    # File unchanged.
    assert src.read_text(encoding="utf-8") == before


def test_apply_writes_canonical_frontmatter(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    src = _write_legacy_note(vault / "decisions", "ADR-007-foo")
    result = migrate_vault(vault, apply=True, create_backup_archive=False)
    assert result.applied
    assert len(result.migrated) == 1
    new_fm = yaml.safe_load(
        src.read_text(encoding="utf-8").split("---", 2)[1]
    )
    assert new_fm["doc_type"] == "adr"
    assert new_fm["schema_version"] == 1
    assert new_fm["adr_number"] == 7
    assert new_fm["fingerprint"] is not None


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_migration_idempotent(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_legacy_note(vault / "decisions", "ADR-007-foo")
    migrate_vault(vault, apply=True, create_backup_archive=False)
    result2 = migrate_vault(vault, apply=True, create_backup_archive=False)
    assert len(result2.migrated) == 0
    assert len(result2.already_migrated) >= 1


def test_force_re_migrates(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_legacy_note(vault / "decisions", "ADR-007-foo")
    migrate_vault(vault, apply=True, create_backup_archive=False)
    result2 = migrate_vault(vault, apply=True, force=True, create_backup_archive=False)
    assert len(result2.migrated) >= 1


# ---------------------------------------------------------------------------
# DocType inference
# ---------------------------------------------------------------------------


def test_session_infers_doc_type_from_path(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_legacy_note(vault / "sessions", "2026-04-14_abc123_foo",
                       fm={"title": "S", "date": "2026-04-14"})
    result = migrate_vault(vault, apply=True, create_backup_archive=False)
    diff = result.migrated[0]
    assert diff.doc_type.value == "session"


def test_runbook_infers_doc_type(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_legacy_note(vault / "runbooks", "RB-deploy")
    result = migrate_vault(vault, apply=True, create_backup_archive=False)
    diff = result.migrated[0]
    assert diff.doc_type.value == "runbook"


def test_unclassifiable_note(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_legacy_note(vault / "random", "unknown")
    result = migrate_vault(vault, apply=False, create_backup_archive=False)
    assert len(result.unclassifiable) == 1
    assert "unable to infer" in result.unclassifiable[0].reason


# ---------------------------------------------------------------------------
# Preserve legacy fields
# ---------------------------------------------------------------------------


def test_preserve_legacy_fields(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    src = _write_legacy_note(
        vault / "decisions", "ADR-007-foo",
        fm={
            "title": "ADR-007",
            "date": "2026-04-01",
            "status": "accepted",
            "tags": ["foo"],
            "author": "alice",
        },
    )
    migrate_vault(vault, apply=True, create_backup_archive=False)
    fm = yaml.safe_load(src.read_text(encoding="utf-8").split("---", 2)[1])
    assert fm["legacy_author"] == "alice"


def test_skip_preserve_legacy_drops_unknown_fields(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    src = _write_legacy_note(
        vault / "decisions", "ADR-007-foo",
        fm={
            "title": "ADR-007",
            "date": "2026-04-01",
            "status": "accepted",
            "author": "alice",
        },
    )
    migrate_vault(vault, apply=True, preserve_legacy=False, create_backup_archive=False)
    fm = yaml.safe_load(src.read_text(encoding="utf-8").split("---", 2)[1])
    assert "legacy_author" not in fm
    assert "author" not in fm


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------


def test_apply_creates_backup_by_default(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_legacy_note(vault / "decisions", "ADR-007-foo")
    result = migrate_vault(vault, apply=True)
    assert result.backup_path is not None
    assert result.backup_path.exists()
    assert result.backup_path.suffix == ".gz"


def test_apply_no_backup_skips_archive(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_legacy_note(vault / "decisions", "ADR-007-foo")
    result = migrate_vault(vault, apply=True, create_backup_archive=False)
    assert result.backup_path is None


# ---------------------------------------------------------------------------
# validate_vault
# ---------------------------------------------------------------------------


def test_validate_after_migrate_zero_invalid(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_legacy_note(vault / "decisions", "ADR-007-foo")
    _write_legacy_note(vault / "decisions", "ADR-008-bar")
    migrate_vault(vault, apply=True, create_backup_archive=False)
    payload = validate_vault(vault)
    assert payload["invalid"] == 0
    assert payload["valid"] == 2


def test_validate_unmigrated_vault_reports_invalid(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_legacy_note(vault / "decisions", "ADR-007-foo")
    payload = validate_vault(vault)
    assert payload["invalid"] == 1


def test_validate_empty_vault(tmp_path: Path) -> None:
    payload = validate_vault(tmp_path / "missing")
    assert payload["total"] == 0


# ---------------------------------------------------------------------------
# Status mapping
# ---------------------------------------------------------------------------


def test_session_status_generated_maps_to_completed(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    src = _write_legacy_note(
        vault / "sessions", "2026-04-14_abc_foo",
        fm={"title": "S", "date": "2026-04-14", "status": "generated"},
    )
    migrate_vault(vault, apply=True, create_backup_archive=False)
    fm = yaml.safe_load(src.read_text(encoding="utf-8").split("---", 2)[1])
    assert fm["status"] == "completed"


def test_hu_status_imported_maps_to_backlog(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    src = _write_legacy_note(
        vault / "hu", "PROJ-1",
        fm={"title": "PROJ-1", "external_id": "PROJ-1", "source": "linear",
            "kind": "story", "status": "imported"},
    )
    migrate_vault(vault, apply=True, create_backup_archive=False)
    fm = yaml.safe_load(src.read_text(encoding="utf-8").split("---", 2)[1])
    assert fm["status"] == "backlog"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def test_format_report_includes_counts(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_legacy_note(vault / "decisions", "ADR-007-foo")
    _write_legacy_note(vault / "random", "unknown")
    result = migrate_vault(vault, apply=False, create_backup_archive=False)
    report = format_report(result)
    assert "Migrated: 1" in report
    assert "Unclassifiable: 1" in report


def test_archived_folder_is_skipped(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_legacy_note(vault / "_archived" / "decisions", "old")
    result = migrate_vault(vault, apply=False, create_backup_archive=False)
    assert result.total_scanned == 0
