"""Characterization + regression tests for IDE adapter ``uninstall`` fixes.

Bugs under test (deep review 2026-08):

1. ``PiAdapter.uninstall()`` borraba AGENTS.md/README.md/justfile COMPLETOS
   del proyecto sin marcadores ni backup. Ahora: solo elimina contenido
   creado por Cortex (bloques marcados o archivos identicos al bundle).
2. ``CodexAdapter.uninstall()`` y ``CursorAdapter.uninstall()`` usaban
   ``Path.cwd()`` ignorando el project root del proyecto.
3. ``PiAdapter.uninstall(project_root=None)`` era un no-op silencioso;
   ahora emite un warning explicito.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest

from cortex.ide.adapters.codex import (
    _CORTEX_AGENTS_MD_MARKER_CLOSE,
    _CORTEX_AGENTS_MD_MARKER_OPEN,
    CodexAdapter,
)
from cortex.ide.adapters.cursor import CursorAdapter, _CORTEX_SUBAGENTS
from cortex.ide.adapters.pi import PiAdapter


# ---------------------------------------------------------------------------
# Bug 1 + 3: PiAdapter.uninstall
# ---------------------------------------------------------------------------


def test_pi_uninstall_removes_only_marker_block_from_agents_md(tmp_path: Path) -> None:
    """AGENTS.md mixto (usuario + bloque Cortex marcado): solo se extrae el bloque."""
    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text(
        "# My project rules (user)\n\n"
        f"{_CORTEX_AGENTS_MD_MARKER_OPEN}\nCortex rules here\n"
        f"{_CORTEX_AGENTS_MD_MARKER_CLOSE}\n",
        encoding="utf-8",
    )
    removed = PiAdapter().uninstall(tmp_path)

    assert agents_md.exists(), "el archivo del usuario NO debe borrarse completo"
    text = agents_md.read_text(encoding="utf-8")
    assert "# My project rules (user)" in text
    assert "BEGIN CORTEX SECTION" not in text
    assert any("Cortex section removed" in r for r in removed)


def test_pi_uninstall_deletes_file_created_entirely_by_cortex(tmp_path: Path) -> None:
    """Un archivo identico al del bundle cortex-pi fue creado por Cortex → borrar."""
    from cortex.ide.adapters.pi import _default_pi_bundle_dir

    bundle_agents = _default_pi_bundle_dir() / "AGENTS.md"
    if not bundle_agents.exists():
        pytest.skip("cortex-pi bundle AGENTS.md missing in tree")
    (tmp_path / "AGENTS.md").write_text(
        bundle_agents.read_text(encoding="utf-8"), encoding="utf-8"
    )
    removed = PiAdapter().uninstall(tmp_path)
    assert not (tmp_path / "AGENTS.md").exists()
    assert "AGENTS.md" in removed


def test_pi_uninstall_leaves_unknown_mixed_files_intact(tmp_path: Path) -> None:
    """Contenido desconocido (ni bundle ni marcadores) → intacto y 'skipped'."""
    unknown = "Just my own notes, never touch this.\n"
    for name in ("AGENTS.md", "README.md", "justfile"):
        (tmp_path / name).write_text(unknown, encoding="utf-8")

    removed = PiAdapter().uninstall(tmp_path)

    for name in ("AGENTS.md", "README.md", "justfile"):
        assert (tmp_path / name).read_text(encoding="utf-8") == unknown
        assert any(name in r and "skipped" in r for r in removed), removed


def test_pi_uninstall_still_removes_pi_dir_and_cortex_extensions(tmp_path: Path) -> None:
    (tmp_path / ".pi").mkdir()
    (tmp_path / ".pi" / "agents").mkdir()
    (tmp_path / ".pi" / "agents" / "cortex-sync.md").write_text("x", encoding="utf-8")
    ext = tmp_path / "extensions"
    ext.mkdir()
    (ext / "cortex-dashboard.ts").write_text("x", encoding="utf-8")
    (ext / "user-extension.ts").write_text("user", encoding="utf-8")

    removed = PiAdapter().uninstall(tmp_path)

    assert not (tmp_path / ".pi").exists()
    assert ".pi/" in removed
    # Solo la extension de Cortex se va; la del usuario queda.
    assert not (ext / "cortex-dashboard.ts").exists()
    assert (ext / "user-extension.ts").exists()


def test_pi_uninstall_with_none_warns_and_is_not_silent(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (tmp_path / "AGENTS.md").write_text("user content\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="cortex.ide.adapters.pi"):
        removed = PiAdapter().uninstall(None)
    assert removed == []
    assert (tmp_path / "AGENTS.md").exists(), "no debe tocar nada sin project_root"
    assert caplog.records, "debe loguear un warning, nunca silencio total"


# ---------------------------------------------------------------------------
# Bug 2: codex/cursor uninstall respetan project_root
# ---------------------------------------------------------------------------


def test_codex_uninstall_uses_project_root_not_cwd(tmp_path: Path) -> None:
    """uninstall(project_root=X) limpia X aunque el cwd sea otro lado."""
    project_root = tmp_path / "proj"
    other_dir = tmp_path / "elsewhere"
    project_root.mkdir()
    other_dir.mkdir()

    # Simular lo que inject escribe en project_root.
    agents_md = project_root / "AGENTS.md"
    agents_md.write_text(
        "User intro.\n"
        f"{_CORTEX_AGENTS_MD_MARKER_OPEN}\ncortex block\n"
        f"{_CORTEX_AGENTS_MD_MARKER_CLOSE}\n",
        encoding="utf-8",
    )
    codex_cfg = project_root / ".codex" / "config.toml"
    codex_cfg.parent.mkdir()
    codex_cfg.write_text(
        "[mcp_servers.user_server]\ncommand = 'u'\n\n"
        "# BEGIN CORTEX MCP (auto-generated, do not edit)\n"
        "[mcp_servers.cortex]\ncommand = 'cortex'\n"
        "# END CORTEX MCP\n",
        encoding="utf-8",
    )

    import os

    old_cwd = os.getcwd()
    try:
        os.chdir(other_dir)
        removed = CodexAdapter().uninstall(project_root)
    finally:
        os.chdir(old_cwd)

    assert any("Cortex section removed" in r for r in removed), removed
    assert any("Cortex MCP block removed" in r for r in removed), removed
    atext = agents_md.read_text(encoding="utf-8")
    assert "User intro." in atext and "BEGIN CORTEX" not in atext
    ctext = codex_cfg.read_text(encoding="utf-8")
    assert "user_server" in ctext and "BEGIN CORTEX MCP" not in ctext


def test_cursor_uninstall_uses_project_root_not_cwd(tmp_path: Path) -> None:
    """uninstall(project_root=X) limpia los subagents Cortex en X aunque el
    cwd sea otro lado, y preserva agents del adopter."""
    project_root = tmp_path / "proj"
    other_dir = tmp_path / "elsewhere"
    agents_dir = project_root / ".cursor" / "agents"
    agents_dir.mkdir(parents=True)
    other_dir.mkdir()

    for agent_name in _CORTEX_SUBAGENTS:
        (agents_dir / f"{agent_name}.md").write_text("cortex", encoding="utf-8")
    (agents_dir / "my-own-agent.md").write_text("user", encoding="utf-8")

    import os

    old_cwd = os.getcwd()
    try:
        os.chdir(other_dir)
        removed = CursorAdapter().uninstall(project_root)
    finally:
        os.chdir(old_cwd)

    assert len([r for r in removed if r.endswith(".md")]) == len(_CORTEX_SUBAGENTS)
    for agent_name in _CORTEX_SUBAGENTS:
        assert not (agents_dir / f"{agent_name}.md").exists()
    assert (agents_dir / "my-own-agent.md").exists(), "agent del usuario intacto"
