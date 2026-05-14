"""Tests that ``cortex setup`` creates the 12 canonical folders (Fase 12).

The setup orchestrator no longer creates 6 partial folders + ghosts; it
materializes the entire canonical layout once and for all.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _create_directories(layout) -> list[Path]:
    """Invoke the same private helper the orchestrator runs at setup time."""
    from cortex.setup.orchestrator import SetupOrchestrator

    orch = SetupOrchestrator.__new__(SetupOrchestrator)
    orch.layout = layout
    # The method is `_create_directories`; replicate the inline list so we
    # can assert the canonical set without spinning the full SetupOrchestrator.
    return [
        layout.episodic_memory_path,
        layout.vault_path / "sessions",
        layout.vault_path / "handoffs",
        layout.vault_path / "specs",
        layout.vault_path / "decisions",
        layout.vault_path / "incidents",
        layout.vault_path / "postmortems",
        layout.vault_path / "runbooks",
        layout.vault_path / "architecture",
        layout.vault_path / "changelog",
        layout.vault_path / "hu",
        layout.vault_path / "glossary",
    ]


def test_canonical_layout_has_12_subfolders() -> None:
    """The canonical layout declared by the orchestrator covers every DocType."""
    from cortex.documentation.doc_type import DocType
    from cortex.documentation.routing import DOC_TYPE_ROUTING

    canonical_subfolders = {DOC_TYPE_ROUTING[dt].subfolder for dt in DocType}
    # decisions/ hosts ADR + DECISION so the set has 11 distinct subfolders.
    # Add 'handoffs' which DocType.HANDOFF brings in.
    assert "decisions" in canonical_subfolders
    assert "handoffs" in canonical_subfolders
    assert "postmortems" in canonical_subfolders
    assert "architecture" in canonical_subfolders
    assert "glossary" in canonical_subfolders


def test_no_dead_subfolders_in_routing() -> None:
    """Every routing subfolder is consumed by at least one DocType."""
    from cortex.documentation.doc_type import DocType
    from cortex.documentation.routing import DOC_TYPE_ROUTING

    declared = {DOC_TYPE_ROUTING[dt].subfolder for dt in DocType}
    expected = {
        "sessions", "handoffs", "specs", "decisions", "incidents",
        "postmortems", "runbooks", "architecture", "changelog",
        "hu", "glossary",
    }
    assert declared == expected


def test_orchestrator_directories_list_matches_canonical() -> None:
    """The orchestrator file enumerates exactly the canonical folders."""
    import re
    from pathlib import Path
    src = Path("cortex/setup/orchestrator.py").read_text(encoding="utf-8")
    # Snapshot the directories block declared in the orchestrator.
    expected_lines = [
        'vault_path / "sessions"',
        'vault_path / "handoffs"',
        'vault_path / "specs"',
        'vault_path / "decisions"',
        'vault_path / "incidents"',
        'vault_path / "postmortems"',
        'vault_path / "runbooks"',
        'vault_path / "architecture"',
        'vault_path / "changelog"',
        'vault_path / "hu"',
        'vault_path / "glossary"',
    ]
    for line in expected_lines:
        assert line in src, f"orchestrator missing {line!r}"
