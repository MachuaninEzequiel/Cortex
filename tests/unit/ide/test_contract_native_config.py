"""Characterization tests — native-config adapters (Obra 02, Fase 0).

Documenta el comportamiento ACTUAL de claude_code, claude_desktop,
opencode y codex tal cual es hoy. Los bugs conocidos se marcan
``xfail(strict=True)`` con ``# KNOWN-BUG:`` para que Fase 2 (migración al
contrato IDEAdapterV2) los haga pasar al arreglarlos.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cortex.ide.adapters.claude_code import ClaudeCodeAdapter
from cortex.ide.adapters.claude_desktop import ClaudeDesktopAdapter
from cortex.ide.adapters.codex import CodexAdapter
from cortex.ide.adapters.opencode import OpenCodeAdapter
from cortex.ide.registry import get_adapter

PROMPTS = {
    "cortex-sync": "# cortex-sync body",
    "cortex-SDDwork": "# cortex-sddwork body",
    "cortex-documenter": "# cortex-documenter body",
}


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / ".cortex" / "subagents").mkdir(parents=True)
    (root / ".cortex" / "subagents" / "cortex-code-explorer.md").write_text(
        "---\ntools: read_file\n---\nexplorer body", encoding="utf-8"
    )
    return root


# ---------------------------------------------------------------------------
# registry aliases
# ---------------------------------------------------------------------------


def test_registry_aliases_native_config() -> None:
    assert get_adapter("claude").name == "claude_code"
    assert get_adapter("claude-code").name == "claude_code"
    assert get_adapter("claude-desktop").name == "claude_desktop"
    assert get_adapter("openai-codex").name == "codex"
    assert get_adapter("codex-cli").name == "codex"
    assert get_adapter("opencode").name == "opencode"


# ---------------------------------------------------------------------------
# claude_code
# ---------------------------------------------------------------------------


def test_claude_code_inject_profiles_paths(project_root: Path) -> None:
    written = ClaudeCodeAdapter().inject_profiles(project_root, PROMPTS)
    rel = sorted(Path(p).relative_to(project_root).as_posix() for p in written)
    assert "CLAUDE.md" in rel
    for skill in ("cortex-sync", "cortex-sddwork", "cortex-documenter"):
        assert f".claude/skills/{skill}/SKILL.md" in rel
    for agent in ("cortex-code-explorer", "cortex-code-implementer", "cortex-documenter"):
        assert f".claude/agents/{agent}.md" in rel


def test_claude_code_skills_have_frontmatter_and_autogen(project_root: Path) -> None:
    ClaudeCodeAdapter().inject_profiles(project_root, PROMPTS)
    skill = project_root / ".claude" / "skills" / "cortex-sync" / "SKILL.md"
    content = skill.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "name: cortex-sync" in content
    assert "<!--" in content  # autogen header as HTML comment


def test_claude_code_idempotent_double_install(project_root: Path) -> None:
    adapter = ClaudeCodeAdapter()
    first = set(adapter.inject_profiles(project_root, PROMPTS))
    before = {p: Path(p).read_text(encoding="utf-8") for p in first}
    second = set(adapter.inject_profiles(project_root, PROMPTS))
    assert second == first
    after = {p: Path(p).read_text(encoding="utf-8") for p in second}
    assert before == after


def test_claude_code_mcp_uses_absolute_project_root(project_root: Path) -> None:
    ClaudeCodeAdapter().inject_mcp(project_root)
    mcp = json.loads((project_root / ".mcp.json").read_text(encoding="utf-8"))
    args = mcp["mcpServers"]["cortex"]["args"]
    assert str(project_root.resolve()) in args
    settings = json.loads(
        (project_root / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    assert "cortex" in settings["enabledMcpjsonServers"]


def test_claude_code_mcp_preserves_foreign_servers(project_root: Path) -> None:
    mcp_file = project_root / ".mcp.json"
    mcp_file.parent.mkdir(parents=True, exist_ok=True)
    mcp_file.write_text(
        json.dumps({"mcpServers": {"other": {"command": "foo"}}}), encoding="utf-8"
    )
    ClaudeCodeAdapter().inject_mcp(project_root)
    data = json.loads(mcp_file.read_text(encoding="utf-8"))
    assert set(data["mcpServers"]) == {"other", "cortex"}


@pytest.mark.xfail(strict=True, reason="# KNOWN-BUG: claude_code hereda uninstall() no-op de base")
def test_claude_code_uninstall_removes_written_files(project_root: Path) -> None:
    adapter = ClaudeCodeAdapter()
    written = adapter.inject_profiles(project_root, PROMPTS)
    removed = adapter.uninstall(project_root)
    assert removed, "expected uninstall to remove the files it wrote"
    assert not all(Path(p).exists() for p in written)


# ---------------------------------------------------------------------------
# claude_desktop
# ---------------------------------------------------------------------------


def test_claude_desktop_profiles_are_noop_by_design(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    adapter = ClaudeDesktopAdapter()
    assert adapter.inject_profiles(tmp_path, PROMPTS) == []
    assert adapter.needs_wsl_shielding() is True


def test_claude_desktop_mcp_writes_home_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    adapter = ClaudeDesktopAdapter()
    written = adapter.inject_mcp(home / "proj")
    assert len(written) == 1
    data = json.loads(Path(written[0]).read_text(encoding="utf-8"))
    cfg = data["mcpServers"]["cortex"]
    assert cfg["enabled"] is True


# ---------------------------------------------------------------------------
# opencode
# ---------------------------------------------------------------------------


def _opencode_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home


def test_opencode_inject_profiles_writes_skills_config(
    tmp_path: Path, project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = _opencode_home(tmp_path, monkeypatch)
    written = OpenCodeAdapter().inject_profiles(project_root, PROMPTS)
    rel = sorted(p.replace(str(home), "~") for p in written)
    assert "~/.config/opencode/opencode.json" in rel
    for skill in PROMPTS:
        assert any(skill in p for p in rel)
    # subagents copiados desde el workspace layout
    assert any("cortex-code-explorer.md" in p for p in rel)
    config = json.loads((home / ".config" / "opencode" / "opencode.json").read_text())
    assert config["agent"]["cortex-sync"]["mode"] == "primary"


def test_opencode_mcp_local_type_with_project_root(
    tmp_path: Path, project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = _opencode_home(tmp_path, monkeypatch)
    OpenCodeAdapter().inject_mcp(project_root)
    config = json.loads((home / ".config" / "opencode" / "opencode.json").read_text())
    cortex = config["mcp"]["cortex"]
    assert cortex["type"] == "local"
    assert str(project_root.resolve()) in cortex["command"]


@pytest.mark.xfail(strict=True, reason="# KNOWN-BUG: opencode hereda uninstall() no-op de base")
def test_opencode_uninstall_removes_written_files(
    tmp_path: Path, project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _opencode_home(tmp_path, monkeypatch)
    adapter = OpenCodeAdapter()
    written = adapter.inject_profiles(project_root, PROMPTS)
    removed = adapter.uninstall(project_root)
    assert removed
    assert not any(Path(p).exists() for p in written)


# ---------------------------------------------------------------------------
# codex
# ---------------------------------------------------------------------------


def test_codex_agents_md_uses_marker_block(project_root: Path) -> None:
    adapter = CodexAdapter()
    written = adapter.inject_profiles(project_root, {})
    assert len(written) == 1
    agents_md = project_root / "AGENTS.md"
    content = agents_md.read_text(encoding="utf-8")
    assert "BEGIN CORTEX SECTION" in content
    assert "END CORTEX SECTION" in content


def test_codex_preserves_user_content_around_marker_block(project_root: Path) -> None:
    agents_md = project_root / "AGENTS.md"
    agents_md.parent.mkdir(parents=True, exist_ok=True)
    agents_md.write_text("# User own intro\n", encoding="utf-8")
    CodexAdapter().inject_profiles(project_root, {})
    content = agents_md.read_text(encoding="utf-8")
    assert content.startswith("# User own intro")


def test_codex_uninstall_removes_only_cortex_block(project_root: Path) -> None:
    agents_md = project_root / "AGENTS.md"
    agents_md.write_text("# User own intro\n", encoding="utf-8")
    adapter = CodexAdapter()
    adapter.inject_profiles(project_root, {})
    removed = adapter.uninstall(project_root)
    assert removed
    content = agents_md.read_text(encoding="utf-8")
    assert "BEGIN CORTEX SECTION" not in content
    assert "# User own intro" in content


def test_codex_uninstall_idempotent(project_root: Path) -> None:
    adapter = CodexAdapter()
    adapter.inject_profiles(project_root, {})
    first = adapter.uninstall(project_root)
    second = adapter.uninstall(project_root)
    assert first
    assert second == [] or all("(legacy)" in r or r == [] for r in [second])


def test_codex_mcp_project_scoped_toml(project_root: Path) -> None:
    CodexAdapter().inject_mcp(project_root)
    toml = (project_root / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert "BEGIN CORTEX MCP" in toml
    assert "--project-root" in toml
