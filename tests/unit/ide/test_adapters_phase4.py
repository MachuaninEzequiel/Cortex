"""Tests integrales de los adapters refactorizados en Fase 4 del plan
multi-IDE & MCP hardening (2026-05-15).

Cobertura especifica de los cambios:

- claude_code: inyectar `tools` traducido en frontmatter (Task 4.1).
- opencode: migrar de `tools` legacy a `permission` moderno (Task 4.2).
- cursor: 3 subagents canonicos en `.cursor/agents/` con frontmatter
  Cursor 2.4+ (Task 4.3).
- codex: AGENTS.md project-root + MCP TOML + sin agents/skills (Task 4.4).
- pre-flight check de cortex_ping inyectado en renders canonicos (Task 4.6).
- registry: helpers para IDEs validados/no-validados (Task 4.7).

Estos tests son ortogonales a `tests/unit/test_ide_adapters.py` (que tiene
los tests historicos del repo, ya actualizados a Fase 4).
"""
from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest

from cortex.ide.adapters.claude_code import ClaudeCodeAdapter, _parse_canonical_tools
from cortex.ide.adapters.codex import CodexAdapter
from cortex.ide.adapters.cursor import CursorAdapter
from cortex.ide.adapters.opencode import OpenCodeAdapter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def project_with_canonical_subagents(tmp_path: Path) -> Path:
    """Project root con .cortex/subagents/ + .cortex/skills/ copiados de la SSoT real."""
    project = tmp_path / "project"
    shutil.copytree(".cortex", project / ".cortex")
    return project


# ---------------------------------------------------------------------------
# Task 4.1 — claude_code adapter: tools traducido en frontmatter
# ---------------------------------------------------------------------------


def test_claude_code_documenter_has_translated_tools(project_with_canonical_subagents: Path):
    """El subagent documenter inyectado en .claude/agents/ debe tener
    tools traducido (PascalCase + mcp__cortex__ prefix), NO los nombres
    canonicos originales."""
    adapter = ClaudeCodeAdapter()
    adapter.inject_profiles(project_with_canonical_subagents, prompts={
        "cortex-sync": "x", "cortex-SDDwork": "y",
    })

    doc = (project_with_canonical_subagents / ".claude/agents/cortex-documenter.md").read_text(
        encoding="utf-8"
    )
    fm_section = doc.split("---")[1]

    # PascalCase nativos (Read, Write) — NO read_file/write_file canonicos.
    assert "Read" in fm_section
    assert "Write" in fm_section
    assert "read_file" not in fm_section, "Canonical name leaked to claude_code frontmatter"
    assert "write_file" not in fm_section

    # MCP tools con prefijo mcp__cortex__
    assert "mcp__cortex__cortex_save_session" in fm_section
    assert "mcp__cortex__cortex_verify_session_claims" in fm_section
    assert "mcp__cortex__cortex_validate_handoff" in fm_section
    # cortex_ping debe estar (inyectado por Task 4.6).
    assert "mcp__cortex__cortex_ping" in fm_section


def test_claude_code_explorer_has_only_read_tools(project_with_canonical_subagents: Path):
    """Explorer es read-only: NO debe tener Write/Edit/Bash en su frontmatter."""
    adapter = ClaudeCodeAdapter()
    adapter.inject_profiles(project_with_canonical_subagents, prompts={
        "cortex-sync": "x", "cortex-SDDwork": "y",
    })

    explorer = (project_with_canonical_subagents / ".claude/agents/cortex-code-explorer.md").read_text(
        encoding="utf-8"
    )
    fm_section = explorer.split("---")[1]

    assert "Read" in fm_section
    # Explorer NO declara Write/Edit/Bash (solo lee).
    assert "tools: Read" in fm_section or "tools:Read" in fm_section
    # Verificar substring exacto del fm: no debe haber ", Write" o ", Edit" en tools
    tools_line = next(
        (line for line in fm_section.splitlines() if line.strip().startswith("tools:")),
        "",
    )
    assert "Write" not in tools_line
    assert "Edit" not in tools_line
    assert "Bash" not in tools_line


def test_parse_canonical_tools_helper():
    """Helper para parsear ``tools:`` field de frontmatter canonico."""
    fm = "name: foo\ntools: read_file, write_file, cortex_save_session\nmodel: sonnet"
    assert _parse_canonical_tools(fm) == ["read_file", "write_file", "cortex_save_session"]


def test_parse_canonical_tools_handles_empty():
    """Sin frontmatter o sin campo tools → lista vacia."""
    assert _parse_canonical_tools(None) == []
    assert _parse_canonical_tools("") == []
    assert _parse_canonical_tools("name: foo\ndescription: bar") == []


def test_parse_canonical_tools_handles_extra_whitespace():
    """Tolera espacios extra alrededor de cada tool name."""
    fm = "tools:  read_file  ,write_file ,  cortex_ping  "
    assert _parse_canonical_tools(fm) == ["read_file", "write_file", "cortex_ping"]


# ---------------------------------------------------------------------------
# Task 4.2 — opencode adapter: migration to permission
# ---------------------------------------------------------------------------


def test_opencode_uses_permission_field(monkeypatch, tmp_path: Path):
    """OpenCode adapter debe usar el campo permission moderno (no tools legacy)."""
    monkeypatch.setattr("cortex.ide.adapters.opencode.Path.home", staticmethod(lambda: tmp_path))
    adapter = OpenCodeAdapter()
    adapter.inject_profiles(tmp_path / "project", prompts={"cortex-sync": "x", "cortex-SDDwork": "y"})

    config = json.loads((tmp_path / ".config/opencode/opencode.json").read_text(encoding="utf-8"))
    for agent in ("cortex-sync", "cortex-SDDwork"):
        assert "permission" in config["agent"][agent], agent
        assert "tools" not in config["agent"][agent], agent


def test_opencode_no_mcp_in_permission(monkeypatch, tmp_path: Path):
    """Ningun cortex_* debe aparecer en permission — los MCP tools se descubren."""
    monkeypatch.setattr("cortex.ide.adapters.opencode.Path.home", staticmethod(lambda: tmp_path))
    adapter = OpenCodeAdapter()
    adapter.inject_profiles(tmp_path / "project", prompts={"cortex-sync": "x", "cortex-SDDwork": "y"})

    config = json.loads((tmp_path / ".config/opencode/opencode.json").read_text(encoding="utf-8"))
    for agent in ("cortex-sync", "cortex-SDDwork"):
        perm = config["agent"][agent]["permission"]
        leaks = [k for k in perm if k.startswith("cortex_")]
        assert not leaks, f"[{agent}] MCP tools en permission: {leaks}"


# ---------------------------------------------------------------------------
# Task 4.3 — cursor adapter: 3 subagents canonicos
# ---------------------------------------------------------------------------


def test_cursor_writes_three_canonical_subagents(project_with_canonical_subagents: Path, tmp_path: Path):
    """Cursor debe inyectar exactamente los 3 subagents canonicos en .cursor/agents/."""
    home = tmp_path / "home"
    home.mkdir()
    with patch("cortex.ide.adapters.cursor.Path.home", staticmethod(lambda: home)):
        adapter = CursorAdapter()
        adapter.inject_profiles(project_with_canonical_subagents)

    agents_dir = project_with_canonical_subagents / ".cursor" / "agents"
    assert (agents_dir / "cortex-code-explorer.md").exists()
    assert (agents_dir / "cortex-code-implementer.md").exists()
    assert (agents_dir / "cortex-documenter.md").exists()


def test_cursor_subagent_frontmatter_uses_cursor_24_format(
    project_with_canonical_subagents: Path, tmp_path: Path
):
    """Cursor 2.4+ frontmatter: name, description, model, readonly. NO tools."""
    home = tmp_path / "home"
    home.mkdir()
    with patch("cortex.ide.adapters.cursor.Path.home", staticmethod(lambda: home)):
        adapter = CursorAdapter()
        adapter.inject_profiles(project_with_canonical_subagents)

    explorer = (project_with_canonical_subagents / ".cursor/agents/cortex-code-explorer.md").read_text(
        encoding="utf-8"
    )
    fm = explorer.split("---")[1]

    assert "name: cortex-code-explorer" in fm
    assert "description:" in fm
    assert "model: inherit" in fm
    assert "readonly: true" in fm  # explorer is read-only
    # Cursor heredra tools del padre — frontmatter NO debe declarar tools.
    assert "tools:" not in fm


def test_cursor_no_more_sddwork_cursor_hybrid(
    project_with_canonical_subagents: Path, tmp_path: Path
):
    """Garantia post-Fase 4: cortex-SDDwork-cursor.md NO se genera nunca mas."""
    home = tmp_path / "home"
    home.mkdir()
    with patch("cortex.ide.adapters.cursor.Path.home", staticmethod(lambda: home)):
        adapter = CursorAdapter()
        adapter.inject_profiles(project_with_canonical_subagents)

    agents_dir = project_with_canonical_subagents / ".cursor" / "agents"
    assert not (agents_dir / "cortex-SDDwork-cursor.md").exists()
    assert not (agents_dir / "cortex-sync.md").exists()  # sync no es subagent


# ---------------------------------------------------------------------------
# Task 4.4 — codex adapter: rediseno completo (cubierto en
# tests/unit/test_ide_adapters.py::TestCodexTripartitaRefinada)
# ---------------------------------------------------------------------------


def test_codex_writes_toml_not_json_for_mcp(tmp_path: Path):
    """Codex MCP en TOML, no JSON."""
    project = tmp_path / "project"
    project.mkdir()
    adapter = CodexAdapter()
    adapter.inject_mcp(project)

    config_toml = project / ".codex" / "config.toml"
    assert config_toml.exists()
    parsed = tomllib.loads(config_toml.read_text(encoding="utf-8"))
    assert "mcp_servers" in parsed
    assert parsed["mcp_servers"]["cortex"]["command"] == "cortex"


# ---------------------------------------------------------------------------
# Task 4.6 — pre-flight check en renders canonicos
# ---------------------------------------------------------------------------


def test_renders_include_preflight_check():
    """Cada render canonico (explorer/implementer/documenter) debe contener
    el bloque de Pre-flight check con cortex_ping."""
    from cortex.setup.cortex_workspace import (
        render_subagent_documenter,
        render_subagent_explorer,
        render_subagent_implementer,
    )

    for renderer in (render_subagent_explorer, render_subagent_implementer, render_subagent_documenter):
        rendered = renderer()
        assert "Pre-flight check" in rendered, f"{renderer.__name__} missing Pre-flight section"
        assert "cortex_ping" in rendered, f"{renderer.__name__} missing cortex_ping reference"
        assert "cortex_ping" in rendered.split("tools:")[1].split("---")[0], (
            f"{renderer.__name__}: cortex_ping debe estar en frontmatter tools field"
        )


def test_canonical_subagent_files_in_disk_match_renders():
    """Los archivos en .cortex/subagents/ siguen alineados con sus renders
    despues de la inyeccion del pre-flight check."""
    import hashlib

    from cortex.setup.cortex_workspace import (
        render_subagent_documenter,
        render_subagent_explorer,
        render_subagent_implementer,
    )

    pairs = [
        (".cortex/subagents/cortex-code-explorer.md", render_subagent_explorer()),
        (".cortex/subagents/cortex-code-implementer.md", render_subagent_implementer()),
        (".cortex/subagents/cortex-documenter.md", render_subagent_documenter()),
    ]
    for path, rendered in pairs:
        disk = Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")
        rendered_lf = rendered.replace("\r\n", "\n")
        h_disk = hashlib.sha256(disk.encode()).hexdigest()
        h_rendered = hashlib.sha256(rendered_lf.encode()).hexdigest()
        assert h_disk == h_rendered, (
            f"{path} drifted from its render. Re-run setup or regenerate."
        )
