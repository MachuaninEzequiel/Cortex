"""Tests for cortex.enterprise.maintenance (Fase 10)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from cortex.enterprise.maintenance import (
    RetentionViolation,
    archive_violations,
    scan_retention_violations,
)
from cortex.enterprise.models import EnterpriseOrgConfig, RetentionPolicy


_FP = "a" * 64


def _write_note(
    folder: Path,
    name: str,
    *,
    doc_type: str = "session",
    created_at: datetime | None = None,
    retention_days: int | None = None,
) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    fm = {
        "schema_version": 1,
        "doc_type": doc_type,
        "title": name,
        "created_at": (created_at or datetime.now(UTC)).isoformat(),
        "updated_at": (created_at or datetime.now(UTC)).isoformat(),
        "tags": [],
        "status": "draft",
        "fingerprint": _FP,
    }
    if retention_days is not None:
        fm["retention_days"] = retention_days
    path = folder / f"{name}.md"
    path.write_text(
        "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n\nbody",
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# scan_retention_violations
# ---------------------------------------------------------------------------


def test_scan_empty_vault(tmp_path: Path) -> None:
    assert scan_retention_violations(tmp_path / "missing") == []
    (tmp_path / "vault").mkdir()
    assert scan_retention_violations(tmp_path / "vault") == []


def test_scan_no_violations_recent_notes(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    _write_note(tmp_path / "vault", "fresh", doc_type="session", created_at=now)
    violations = scan_retention_violations(
        tmp_path / "vault", defaults=RetentionPolicy(session=365), now=now,
    )
    assert violations == []


def test_scan_detects_expired_note(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    old = now - timedelta(days=400)
    _write_note(tmp_path / "vault", "old", doc_type="session", created_at=old)
    violations = scan_retention_violations(
        tmp_path / "vault", defaults=RetentionPolicy(session=365), now=now,
    )
    assert len(violations) == 1
    assert violations[0].doc_type == "session"
    assert violations[0].days_overdue >= 35


def test_scan_explicit_retention_overrides_default(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    _write_note(
        tmp_path / "vault", "custom", doc_type="session",
        created_at=now - timedelta(days=50),
        retention_days=30,
    )
    violations = scan_retention_violations(
        tmp_path / "vault", defaults=RetentionPolicy(session=365), now=now,
    )
    assert len(violations) == 1


def test_scan_zero_retention_never_expires(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    _write_note(
        tmp_path / "vault", "forever", doc_type="changelog",
        created_at=now - timedelta(days=9999),
    )
    violations = scan_retention_violations(
        tmp_path / "vault", defaults=RetentionPolicy(changelog=0), now=now,
    )
    assert violations == []


def test_scan_skips_notes_without_doc_type(tmp_path: Path) -> None:
    (tmp_path / "vault").mkdir()
    bad = tmp_path / "vault" / "bad.md"
    bad.write_text("---\ntitle: x\ncreated_at: 2020-01-01T00:00:00+00:00\n---\nbody", encoding="utf-8")
    violations = scan_retention_violations(tmp_path / "vault")
    assert violations == []


def test_scan_skips_notes_without_frontmatter(tmp_path: Path) -> None:
    (tmp_path / "vault").mkdir()
    (tmp_path / "vault" / "plain.md").write_text("just body", encoding="utf-8")
    violations = scan_retention_violations(tmp_path / "vault")
    assert violations == []


def test_scan_uses_org_retention_defaults(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    _write_note(
        tmp_path / "vault", "hu-old", doc_type="hu",
        created_at=now - timedelta(days=200),
    )
    org = EnterpriseOrgConfig()  # default retention_defaults.hu = 90
    violations = scan_retention_violations(tmp_path / "vault", org=org, now=now)
    assert len(violations) == 1


def test_scan_ignores_archived_subfolder(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    _write_note(
        tmp_path / "vault" / "_archived" / "sessions", "old",
        doc_type="session",
        created_at=now - timedelta(days=400),
    )
    violations = scan_retention_violations(
        tmp_path / "vault", defaults=RetentionPolicy(session=365), now=now,
    )
    assert violations == []


def test_scan_sorts_by_days_overdue(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    _write_note(
        tmp_path / "vault", "slightly_old", doc_type="session",
        created_at=now - timedelta(days=370),
    )
    _write_note(
        tmp_path / "vault", "very_old", doc_type="session",
        created_at=now - timedelta(days=1000),
    )
    violations = scan_retention_violations(
        tmp_path / "vault", defaults=RetentionPolicy(session=365), now=now,
    )
    assert len(violations) == 2
    assert violations[0].path.stem == "very_old"


# ---------------------------------------------------------------------------
# archive_violations
# ---------------------------------------------------------------------------


def test_archive_moves_files(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    src = _write_note(
        tmp_path / "vault" / "sessions", "old", doc_type="session",
        created_at=now - timedelta(days=400),
    )
    violations = scan_retention_violations(
        tmp_path / "vault", defaults=RetentionPolicy(session=365), now=now,
    )
    moved = archive_violations(violations, tmp_path / "vault")
    assert not src.exists()
    assert moved[0].exists()
    assert "_archived" in moved[0].parts


def test_archive_dry_run_does_not_move(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    src = _write_note(
        tmp_path / "vault" / "sessions", "old", doc_type="session",
        created_at=now - timedelta(days=400),
    )
    violations = scan_retention_violations(
        tmp_path / "vault", defaults=RetentionPolicy(session=365), now=now,
    )
    planned = archive_violations(violations, tmp_path / "vault", dry_run=True)
    assert src.exists()
    assert not planned[0].exists()  # planned but not moved


def test_archive_preserves_relative_path(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    src = _write_note(
        tmp_path / "vault" / "decisions", "ADR-001-foo", doc_type="adr",
        created_at=now - timedelta(days=9999),
        retention_days=30,
    )
    violations = scan_retention_violations(tmp_path / "vault", now=now)
    moved = archive_violations(violations, tmp_path / "vault")
    assert moved[0].relative_to(tmp_path / "vault" / "_archived") == Path("decisions/ADR-001-foo.md")
