"""Shared fixtures for cortex.documentation tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_vault_with_notes(tmp_path: Path) -> Path:
    """Create a small vault with notes across several subfolders."""
    vault = tmp_path / "vault"
    (vault / "sessions").mkdir(parents=True)
    (vault / "decisions").mkdir(parents=True)
    (vault / "incidents").mkdir(parents=True)

    for i in range(3):
        (vault / "sessions" / f"2026-04-{10 + i:02d}_foo-{i}.md").write_text(
            "---\ntitle: Session foo\ndate: 2026-04-10\n---\n\nbody",
            encoding="utf-8",
        )
    for i in range(2):
        (vault / "decisions" / f"ADR-00{i + 1}-foo.md").write_text(
            "---\ntitle: ADR foo\ndate: 2026-04-15\nstatus: accepted\n---\n\nbody",
            encoding="utf-8",
        )
    (vault / "decisions" / "DEC-2026-05-14-foo.md").write_text(
        "---\ntitle: Decision foo\n---\n\nbody", encoding="utf-8"
    )
    (vault / "incidents" / "2026-04-15_outage.md").write_text(
        "no frontmatter here", encoding="utf-8"
    )

    return vault


@pytest.fixture
def tmp_vault_with_random(tmp_path: Path) -> Path:
    """Create a vault with notes outside known subfolders (unclassifiable)."""
    vault = tmp_path / "vault"
    (vault / "random").mkdir(parents=True)
    (vault / "random" / "x.md").write_text("body", encoding="utf-8")
    (vault / "root-level.md").write_text("body", encoding="utf-8")
    return vault


@pytest.fixture
def tmp_empty_vault(tmp_path: Path) -> Path:
    """Create an empty vault directory."""
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault
