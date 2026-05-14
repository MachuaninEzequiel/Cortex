"""Tests for cortex.documentation.backup (Fase 11)."""

from __future__ import annotations

import tarfile
from pathlib import Path

import pytest

from cortex.documentation.backup import (
    create_backup,
    list_backups,
    restore_backup,
)


def _seed_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "decisions").mkdir(parents=True)
    (vault / "decisions" / "ADR-001.md").write_text("body 1", encoding="utf-8")
    (vault / "sessions").mkdir()
    (vault / "sessions" / "session.md").write_text("body 2", encoding="utf-8")
    return vault


def test_create_backup_returns_existing_tar_gz(tmp_path: Path) -> None:
    vault = _seed_vault(tmp_path)
    backup = create_backup(vault)
    assert backup.exists()
    assert backup.suffix == ".gz"
    assert "vault-" in backup.name


def test_create_backup_includes_contents(tmp_path: Path) -> None:
    vault = _seed_vault(tmp_path)
    backup = create_backup(vault)
    with tarfile.open(backup, "r:gz") as tar:
        names = tar.getnames()
    # Top-level folder uses the vault directory name.
    assert any("vault/decisions/ADR-001.md" in n for n in names)
    assert any("vault/sessions/session.md" in n for n in names)


def test_create_backup_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        create_backup(tmp_path / "does-not-exist")


def test_create_backup_with_label(tmp_path: Path) -> None:
    vault = _seed_vault(tmp_path)
    backup = create_backup(vault, label="pre-migrate")
    assert "pre-migrate" in backup.name


def test_list_backups_sorted(tmp_path: Path) -> None:
    vault = _seed_vault(tmp_path)
    b1 = create_backup(vault, label="first")
    b2 = create_backup(vault, label="second")
    backups = list_backups(b1.parent)
    assert b1 in backups
    assert b2 in backups


def test_list_backups_missing_dir(tmp_path: Path) -> None:
    assert list_backups(tmp_path / "no") == []


def test_restore_roundtrip(tmp_path: Path) -> None:
    vault = _seed_vault(tmp_path)
    backup = create_backup(vault)

    # Replace the vault contents to simulate a destructive operation.
    (vault / "decisions" / "ADR-001.md").write_text("CORRUPTED", encoding="utf-8")

    # Restore inside a sibling directory.
    restore_root = tmp_path / "restored"
    restored_vault = restore_backup(backup, restore_root)
    assert restored_vault.exists()
    content = (restored_vault / "decisions" / "ADR-001.md").read_text(encoding="utf-8")
    assert content == "body 1"


def test_restore_missing_backup_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        restore_backup(tmp_path / "no.tar.gz", tmp_path)
