"""Tests for the legacy-shaped writers exposed via ``cortex.documentation``.

After Fase 04 these writers are wrappers around the canonical writers.
The tests verify the public contract (path, frontmatter, body markers)
under the new canonical schema. Formato YAML exacto (block vs flow style)
NO se asume; verificamos campos por contenido textual.
"""

from __future__ import annotations

from pathlib import Path

from cortex.documentation import (
    parse_frontmatter_lenient,
    write_session_note,
    write_spec_note,
    write_tracked_item_note,
)
from cortex.workitems.models import TrackedItem, WorkItemKind, WorkItemSource


def test_write_session_note_creates_session_file(tmp_path: Path) -> None:
    path = write_session_note(
        tmp_path,
        title="Implement Release 2 flow",
        spec_summary="Replace cortex-work with cortex-SDDwork.",
        changes_made=["Added orchestrator prompt", "Added documenter flow"],
        files_touched=["cortex/ide_installer.py", "cortex/mcp_server.py"],
        key_decisions=["Make cortex-documenter mandatory"],
        next_steps=["Add more ADR coverage"],
        tags=["release-2"],
    )

    assert path.exists()
    assert path.parent.name == "sessions"
    content = path.read_text(encoding="utf-8")
    # Title appears in frontmatter (canonical) instead of an H1 prefix.
    fm = parse_frontmatter_lenient(path)
    assert fm["title"] == "Implement Release 2 flow"
    assert fm["doc_type"] == "session"
    # Original spec summary and files appear in the body.
    assert "Replace cortex-work with cortex-SDDwork." in content
    assert "cortex/ide_installer.py" in content


def test_write_spec_note_creates_spec_file(tmp_path: Path) -> None:
    path = write_spec_note(
        tmp_path,
        title="Release 2 subagent architecture",
        goal="Install sync + SDDwork + documenter workflow.",
        requirements=["Support subagents", "Preserve Cortex isolation"],
        files_in_scope=["cortex/setup/orchestrator.py"],
        constraints=["Do not use external memory tools"],
        acceptance_criteria=["cortex-SDDwork is installed", "documenter is mandatory"],
        tags=["architecture"],
    )

    assert path.exists()
    assert path.parent.name == "specs"
    fm = parse_frontmatter_lenient(path)
    assert fm["title"] == "Release 2 subagent architecture"
    assert fm["doc_type"] == "spec"
    content = path.read_text(encoding="utf-8")
    assert "Preserve Cortex isolation" in content
    assert "documenter is mandatory" in content


# ---------------------------------------------------------------------------
# Tripartita Refinada - Plan 07 §4: cascade save_session(handoff=True) e2e
# ---------------------------------------------------------------------------


def test_write_session_note_handoff_mode_writes_handoff_status(tmp_path: Path) -> None:
    """Cuando ``handoff=True``, la session note canonica debe llevar
    ``status: handoff`` en el frontmatter y el tag ``handoff`` (idempotente,
    no duplicado). Las 4 secciones Tripartita Refinada deben renderizarse
    cuando las listas son no vacias.
    """
    path = write_session_note(
        tmp_path,
        title="Tripartita Refinada - Plan 07 cierre",
        spec_summary="Cierre del bloque Tripartita Refinada con bump 0.5.0",
        changes_made=["MCP tools handoff", "agents canonical"],
        files_touched=["cortex/handoff.py"],
        key_decisions=["Bump 0.5.0"],
        next_steps=["Reunion adopters"],
        tags=["release"],
        handoff=True,
        blockers=["Smoke manual de los 4 IDEs pendiente del usuario"],
        verified_state=["Suite global verde", "MCP tools registrados"],
        unverified_claims=["Performance overhead < 10% no medido en este ciclo"],
        suggested_skills=["cortex-documenter para review de la bitacora"],
    )

    assert path.exists()
    fm = parse_frontmatter_lenient(path)
    assert fm["status"] == "handoff"
    tags = fm["tags"]
    assert "session" in tags
    assert "release" in tags
    assert "handoff" in tags
    # 'handoff' must appear at most once (idempotent).
    assert tags.count("handoff") == 1

    content = path.read_text(encoding="utf-8")
    # The 4 new sections must be emitted because we passed non-empty lists.
    assert "## Verified State" in content
    assert "## Unverified Claims" in content
    assert "## Blockers" in content
    assert "## Suggested Skills" in content
    # Body content rendered.
    assert "Suite global verde" in content
    assert "Smoke manual de los 4 IDEs pendiente del usuario" in content


def test_write_session_note_handoff_false_omits_new_sections(tmp_path: Path) -> None:
    """Negative control: cuando handoff=False (default) las 4 secciones nuevas
    NO aparecen aun pasando listas vacias. Asegura que las extensiones
    Tripartita Refinada estan ligadas al modo handoff."""
    path = write_session_note(
        tmp_path,
        title="Normal session",
        spec_summary="x",
    )
    content = path.read_text(encoding="utf-8")
    fm = parse_frontmatter_lenient(path)
    # Canonical schema replaces legacy "generated" with "completed".
    assert fm["status"] == "completed"
    assert "## Verified State" not in content
    assert "## Unverified Claims" not in content
    assert "## Blockers" not in content
    assert "## Suggested Skills" not in content


def test_write_session_note_handoff_with_empty_lists_skips_sections(tmp_path: Path) -> None:
    """handoff=True but con listas vacias -> status cambia pero no aparecen
    secciones. Solo listas no vacias materializan secciones."""
    path = write_session_note(
        tmp_path,
        title="Empty handoff",
        spec_summary="x",
        handoff=True,
    )
    content = path.read_text(encoding="utf-8")
    fm = parse_frontmatter_lenient(path)
    assert fm["status"] == "handoff"
    assert "## Verified State" not in content
    assert "## Blockers" not in content


def test_write_tracked_item_note_creates_hu_file(tmp_path: Path) -> None:
    path = write_tracked_item_note(
        tmp_path,
        item=TrackedItem(
            id="PROJ-123",
            external_id="PROJ-123",
            source=WorkItemSource.JIRA,
            kind=WorkItemKind.STORY,
            title="Import Jira story",
            description="Read-only import for the current ticket.",
            acceptance_criteria=["Ticket is persisted locally"],
            status="In Progress",
            labels=["jira", "story"],
        ),
    )

    assert path.exists()
    assert path.parent.name == "hu"
    fm = parse_frontmatter_lenient(path)
    assert fm["external_id"] == "PROJ-123"
    assert fm["doc_type"] == "hu"
    assert fm["source"] == "jira"
    assert fm["kind"] == "story"
    content = path.read_text(encoding="utf-8")
    # Description and acceptance criteria rendered in body.
    assert "Read-only import for the current ticket." in content
    assert "Ticket is persisted locally" in content
