"""Smoke test multi-IDE — cierre de Fase 7 del plan multi-IDE & MCP hardening.

Para los 5 IDEs validados (claude_code, opencode, codex, cursor, pi) verifica
que ``cortex_ide.inject(ide, project_root)`` produce los archivos esperados
EN EL FORMATO NATIVO confirmado contra docs oficiales 2026.

Este test consolida lo que cada Fase 4 task validaba por separado, ahora
en un unico smoke run end-to-end. Si alguien rompe la inyeccion de un
adapter, este test lo detecta.

Decisiones del creador respetadas:
- claude_code: subagents en .claude/agents/ con tools traducido (Fase 4.1).
- opencode: agent profiles con permission (no tools), MCP en opencode.json (Fase 4.2).
- codex: AGENTS.md en project root + MCP TOML en .codex/config.toml (Fase 4.4).
- cursor: 3 subagents en .cursor/agents/ con frontmatter Cursor 2.4+ (Fase 4.3).
- pi: bundle estatico copia entera (NO TOCADO, Decision 1).
"""
from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def project_with_canonical(tmp_path: Path) -> Path:
    """Project root con .cortex/ copiado desde la SSoT real del repo."""
    project = tmp_path / "project"
    shutil.copytree(".cortex", project / ".cortex")
    return project


# ---------------------------------------------------------------------------
# claude_code (TARGET) — subagents nativos + MCP via .mcp.json
# ---------------------------------------------------------------------------


def test_smoke_claude_code(project_with_canonical: Path):
    """claude_code: 3 subagents en .claude/agents/ + .mcp.json + CLAUDE.md."""
    from cortex.ide import inject

    files = inject("claude_code", project_root=project_with_canonical)
    assert files, "inject() devolvio lista vacia"

    # Subagents canonicos en .claude/agents/
    agents_dir = project_with_canonical / ".claude" / "agents"
    for agent in ("cortex-code-explorer", "cortex-code-implementer", "cortex-documenter"):
        path = agents_dir / f"{agent}.md"
        assert path.exists(), f"Falta {path}"
        # Frontmatter debe incluir tools traducido (Fase 4.1)
        content = path.read_text(encoding="utf-8")
        assert "name:" in content
        assert "tools:" in content, f"{agent} debe tener tools traducido"
        # Pre-flight check inyectado en el body (Fase 4.6)
        assert "Pre-flight check" in content
        assert "cortex_ping" in content

    # MCP config en .mcp.json
    mcp_json = project_with_canonical / ".mcp.json"
    assert mcp_json.exists()
    mcp_data = json.loads(mcp_json.read_text(encoding="utf-8"))
    assert "cortex" in mcp_data["mcpServers"]


# ---------------------------------------------------------------------------
# opencode (TARGET) — permission moderno + MCP local discovery
# ---------------------------------------------------------------------------


def test_smoke_opencode(project_with_canonical: Path, tmp_path: Path):
    """opencode: agent profile con permission (NO tools); MCP via discovery."""
    home = tmp_path / "fake-home"
    home.mkdir()
    with patch("cortex.ide.adapters.opencode.Path.home", staticmethod(lambda: home)):
        from cortex.ide import inject

        inject("opencode", project_root=project_with_canonical)

    config = json.loads((home / ".config/opencode/opencode.json").read_text(encoding="utf-8"))

    # Agents con campo permission moderno (Fase 4.2)
    for agent_name in ("cortex-sync", "cortex-SDDwork"):
        agent = config["agent"][agent_name]
        assert "permission" in agent, f"{agent_name} debe usar permission moderno"
        assert "tools" not in agent, f"{agent_name} NO debe usar tools (deprecated)"

    # MCP server config en formato local
    assert "mcp" in config
    assert config["mcp"]["cortex"]["type"] == "local"
    assert config["mcp"]["cortex"]["enabled"] is True


# ---------------------------------------------------------------------------
# codex (TARGET) — AGENTS.md root + MCP TOML
# ---------------------------------------------------------------------------


def test_smoke_codex(project_with_canonical: Path):
    """codex: AGENTS.md project root + .codex/config.toml. NO genera
    .codex/agents ni .codex/skills (Decision 2 firmada)."""
    from cortex.ide import inject

    inject("codex", project_root=project_with_canonical)

    # AGENTS.md va al PROJECT ROOT (no a .codex/)
    agents_md = project_with_canonical / "AGENTS.md"
    assert agents_md.exists()
    body = agents_md.read_text(encoding="utf-8")
    # Marcadores de Tripartita Refinada en single-agent flow (Fase 4.4)
    assert "Phase 1" in body and "Phase 2" in body and "Phase 3" in body
    assert "single-agent sequence" in body
    assert "cortex_ping" in body  # pre-flight check (Fase 2)

    # MCP config en TOML
    config_toml = project_with_canonical / ".codex" / "config.toml"
    assert config_toml.exists()
    parsed = tomllib.loads(config_toml.read_text(encoding="utf-8"))
    assert parsed["mcp_servers"]["cortex"]["command"] == "cortex"
    assert parsed["mcp_servers"]["cortex"]["enabled"] is True

    # NO debe generar paths obsoletos
    assert not (project_with_canonical / ".codex" / "agents").exists()
    assert not (project_with_canonical / ".codex" / "skills").exists()
    assert not (project_with_canonical / ".codex" / "mcp.json").exists()


# ---------------------------------------------------------------------------
# cursor (TARGET, validado en Fase 4) — 3 subagents en .cursor/agents/
# ---------------------------------------------------------------------------


def test_smoke_cursor(project_with_canonical: Path, tmp_path: Path):
    """cursor: 3 subagents canonicos en .cursor/agents/ con frontmatter
    Cursor 2.4+. Sin variante hibrida cortex-SDDwork-cursor (Decision 3)."""
    home = tmp_path / "fake-home"
    home.mkdir()
    with patch("cortex.ide.adapters.cursor.Path.home", staticmethod(lambda: home)):
        from cortex.ide import inject

        inject("cursor", project_root=project_with_canonical)

    agents_dir = project_with_canonical / ".cursor" / "agents"
    for agent in ("cortex-code-explorer", "cortex-code-implementer", "cortex-documenter"):
        path = agents_dir / f"{agent}.md"
        assert path.exists(), f"Falta {path}"
        content = path.read_text(encoding="utf-8")
        # Frontmatter Cursor 2.4+
        assert "model: inherit" in content
        assert "readonly:" in content

    # NO genera el hibrido obsoleto
    assert not (agents_dir / "cortex-SDDwork-cursor.md").exists()

    # MCP config en ~/.cursor/mcp.json
    mcp_json = home / ".cursor" / "mcp.json"
    assert mcp_json.exists()


# ---------------------------------------------------------------------------
# pi (TARGET, NO TOCADO — Decision 1) — bundle estatico copia entera
# ---------------------------------------------------------------------------


def test_smoke_pi(project_with_canonical: Path):
    """pi: bundle estatico se copia tal cual (NO se toca el adapter).
    Decision 1 firmada del creador: respetar contribuciones de comunidad."""
    from cortex.ide import inject

    files = inject("pi", project_root=project_with_canonical)

    # Pi copia bundle entero — debe haber escrito muchos archivos
    assert len(files) > 0
    # AGENTS.md en project root + .pi/ directory
    assert (project_with_canonical / "AGENTS.md").exists()
    assert (project_with_canonical / ".pi").is_dir()
