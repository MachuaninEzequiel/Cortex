"""cortex.documentation.backup - Tar.gz backup helpers for migrate operations.

The migration tool (``cortex docs migrate --apply``) calls
``create_backup`` before writing anything to disk so the operator can
``cortex docs restore`` if something goes sideways.

Backups live in ``<workspace>/.cortex/backups/`` and are named after a
UTC timestamp.
"""

from __future__ import annotations

import logging
import tarfile
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_BACKUP_PREFIX = "vault"
_BACKUP_SUFFIX = ".tar.gz"


def create_backup(
    vault_path: Path,
    *,
    backups_dir: Path | None = None,
    label: str | None = None,
) -> Path:
    """Create a tar.gz snapshot of ``vault_path``.

    Args:
        vault_path: directory to archive (must exist).
        backups_dir: where to write the .tar.gz; defaults to
            ``<vault_path.parent>/.cortex/backups/``.
        label: optional label appended to the filename (slugified by
            caller).

    Returns:
        Path of the newly created backup file.
    """
    if not vault_path.exists():
        raise FileNotFoundError(f"vault path not found: {vault_path}")

    target_dir = backups_dir or (vault_path.parent / ".cortex" / "backups")
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%SZ")
    name = f"{_BACKUP_PREFIX}-{timestamp}"
    if label:
        name = f"{name}-{label}"
    backup_path = target_dir / f"{name}{_BACKUP_SUFFIX}"

    with tarfile.open(backup_path, "w:gz") as tar:
        tar.add(vault_path, arcname=vault_path.name)
    logger.info("Backup created: %s", backup_path)
    return backup_path


def restore_backup(backup_path: Path, target_parent: Path) -> Path:
    """Extract ``backup_path`` into ``target_parent``.

    The backup contains a top-level folder (the original vault name), so
    the restored vault appears at ``target_parent / <vault_name>``.

    Returns the path of the restored vault root.
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"backup not found: {backup_path}")
    target_parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(backup_path, "r:gz") as tar:
        # Resolve the top-level folder name from the archive.
        members = tar.getmembers()
        if not members:
            raise ValueError(f"empty backup: {backup_path}")
        top = members[0].name.split("/", 1)[0]
        tar.extractall(target_parent)
    return target_parent / top


def list_backups(backups_dir: Path) -> list[Path]:
    """Return backups in ``backups_dir`` sorted by name (timestamp asc)."""
    if not backups_dir.exists():
        return []
    return sorted(backups_dir.glob(f"{_BACKUP_PREFIX}-*{_BACKUP_SUFFIX}"))


__all__ = ["create_backup", "list_backups", "restore_backup"]
