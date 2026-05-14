"""Tests for cortex.documentation.inventory."""

from __future__ import annotations

from pathlib import Path

from cortex.documentation.inventory import (
    VaultInventory,
    classify_path,
    inventory_vault,
)


def test_inventory_empty_vault(tmp_empty_vault: Path) -> None:
    inv = inventory_vault(tmp_empty_vault)
    assert inv.total_files == 0
    assert inv.classifiable == 0
    assert inv.unclassifiable == []


def test_inventory_counts_md_files(tmp_vault_with_notes: Path) -> None:
    inv = inventory_vault(tmp_vault_with_notes)
    # 3 sessions + 2 ADRs + 1 decision + 1 incident = 7
    assert inv.total_files == 7


def test_inventory_groups_by_subfolder(tmp_vault_with_notes: Path) -> None:
    inv = inventory_vault(tmp_vault_with_notes)
    assert inv.by_subfolder["sessions"] == 3
    assert inv.by_subfolder["decisions"] == 3  # 2 ADR + 1 DEC
    assert inv.by_subfolder["incidents"] == 1


def test_inventory_with_frontmatter_count(tmp_vault_with_notes: Path) -> None:
    inv = inventory_vault(tmp_vault_with_notes)
    # All notes in fixture have frontmatter except the "incidents/2026-04-15_outage.md".
    assert inv.with_frontmatter == 6
    assert inv.without_frontmatter == 1


def test_inventory_legacy_keys_counted(tmp_vault_with_notes: Path) -> None:
    inv = inventory_vault(tmp_vault_with_notes)
    # All sessions + ADRs + decision have "title".
    assert inv.legacy_frontmatter_keys["title"] == 6


def test_inventory_classifiable_count(tmp_vault_with_notes: Path) -> None:
    inv = inventory_vault(tmp_vault_with_notes)
    # 3 sessions + 2 ADR + 1 decision + 1 incident -> all classifiable
    assert inv.classifiable == 7
    assert inv.unclassifiable == []


def test_inventory_missing_path_returns_empty() -> None:
    inv = inventory_vault(Path("/non/existent/vault"))
    assert inv == VaultInventory()


def test_inventory_marks_unclassifiable(tmp_vault_with_random: Path) -> None:
    inv = inventory_vault(tmp_vault_with_random)
    # x.md in 'random/' and root-level.md both unclassifiable
    assert inv.classifiable == 0
    assert len(inv.unclassifiable) == 2


def test_classify_path_session(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    p = vault / "sessions" / "2026-01-01_foo.md"
    assert classify_path(p, vault) == "session"


def test_classify_path_adr_by_prefix(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    p = vault / "decisions" / "ADR-007-foo.md"
    assert classify_path(p, vault) == "adr"


def test_classify_path_decision_non_adr(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    p = vault / "decisions" / "DEC-2026-05-14-foo.md"
    assert classify_path(p, vault) == "decision"


def test_classify_path_runbook(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    p = vault / "runbooks" / "RB-deploy.md"
    assert classify_path(p, vault) == "runbook"


def test_classify_path_unknown_subfolder_returns_none(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    p = vault / "random" / "x.md"
    assert classify_path(p, vault) is None


def test_classify_path_root_file_returns_none(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    p = vault / "CONTEXT.md"
    assert classify_path(p, vault) is None


def test_classify_path_outside_vault_returns_none(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    p = tmp_path / "other" / "x.md"
    assert classify_path(p, vault) is None


def test_classify_all_known_subfolders(tmp_path: Path) -> None:
    """Every supported subfolder maps to a non-None doc_type."""
    vault = tmp_path / "vault"
    expected = {
        "sessions": "session",
        "handoffs": "handoff",
        "specs": "spec",
        "decisions": "decision",
        "incidents": "incident",
        "postmortems": "postmortem",
        "runbooks": "runbook",
        "architecture": "architecture",
        "changelog": "changelog",
        "hu": "hu",
        "glossary": "glossary",
    }
    for sub, expected_type in expected.items():
        p = vault / sub / "foo.md"
        assert classify_path(p, vault) == expected_type
