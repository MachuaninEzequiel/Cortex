"""cortex.enterprise.maintenance - Retention scan and archival.

Implements the *retention policy enforcement* part of Fase 10:

- ``scan_retention_violations`` walks a vault and returns notes whose
  ``retention_days`` (or the default for their DocType) has elapsed.
- ``archive_violations`` moves the violators to ``<vault>/_archived/``
  preserving the original directory structure.

No automatic execution: callers must invoke the functions explicitly. A
CLI wrapper (e.g. ``cortex docs maintenance``) is the natural entrypoint
but lives outside this module.
"""

from __future__ import annotations

import logging
import shutil
from datetime import UTC, datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

from cortex.documentation.common import parse_frontmatter_lenient
from cortex.enterprise.models import EnterpriseOrgConfig, RetentionPolicy

logger = logging.getLogger(__name__)

# Default subfolder where archived notes go.
_ARCHIVE_FOLDER = "_archived"


@dataclass(frozen=True)
class RetentionViolation:
    """A note whose retention window has elapsed."""

    path: Path
    doc_type: str | None
    retention_days: int
    created_at: datetime
    days_overdue: int


def scan_retention_violations(
    vault_root: Path,
    *,
    org: EnterpriseOrgConfig | None = None,
    defaults: RetentionPolicy | None = None,
    now: datetime | None = None,
) -> list[RetentionViolation]:
    """Return notes in ``vault_root`` whose retention window has elapsed.

    Resolution order for retention days per note:
        1. ``retention_days`` in the note's frontmatter (if present).
        2. ``org.retention_defaults`` per DocType, when ``org`` is given.
        3. ``defaults`` argument, when provided.
        4. ``0`` -> no expiration (skip).

    Args:
        vault_root: directory to scan recursively.
        org: optional org config; its ``retention_defaults`` is used when
            a note doesn't override.
        defaults: explicit fallback if ``org`` is not given.
        now: clock injection for tests; defaults to ``datetime.now(UTC)``.

    Returns:
        Violations sorted by ``days_overdue`` descending.
    """
    now = now or datetime.now(UTC)
    policy = defaults or (org.retention_defaults if org else RetentionPolicy())

    violations: list[RetentionViolation] = []
    if not vault_root.exists():
        return violations

    for path in vault_root.rglob("*.md"):
        # Skip already-archived notes.
        if _ARCHIVE_FOLDER in path.parts:
            continue
        try:
            fm = parse_frontmatter_lenient(path)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Skipping unreadable note %s: %s", path, exc)
            continue
        if not fm:
            continue
        doc_type = fm.get("doc_type")
        retention_days = _resolve_retention(fm, doc_type, policy)
        if retention_days <= 0:
            continue
        created_at = _parse_dt(fm.get("created_at"))
        if created_at is None:
            continue
        elapsed = (now - created_at).days
        if elapsed >= retention_days:
            violations.append(RetentionViolation(
                path=path,
                doc_type=doc_type if isinstance(doc_type, str) else None,
                retention_days=retention_days,
                created_at=created_at,
                days_overdue=elapsed - retention_days,
            ))

    violations.sort(key=lambda v: v.days_overdue, reverse=True)
    return violations


def archive_violations(
    violations: list[RetentionViolation],
    vault_root: Path,
    *,
    dry_run: bool = False,
) -> list[Path]:
    """Move ``violations`` into ``<vault_root>/_archived/`` preserving paths.

    Returns the list of *new* paths (or planned paths in dry-run mode).
    """
    archive_root = vault_root / _ARCHIVE_FOLDER
    moved: list[Path] = []
    for v in violations:
        try:
            rel = v.path.relative_to(vault_root)
        except ValueError:
            continue
        target = archive_root / rel
        moved.append(target)
        if dry_run:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(v.path), str(target))
        except OSError as exc:
            logger.warning("Failed to archive %s -> %s: %s", v.path, target, exc)
    return moved


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_retention(
    fm: dict, doc_type: str | None, policy: RetentionPolicy,
) -> int:
    explicit = fm.get("retention_days")
    if isinstance(explicit, int) and explicit >= 0:
        return explicit
    if isinstance(doc_type, str):
        return policy.for_doc_type(doc_type)
    return 0


def _parse_dt(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    return None


__all__ = [
    "RetentionViolation",
    "archive_violations",
    "scan_retention_violations",
]
