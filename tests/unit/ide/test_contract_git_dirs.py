"""Tests de caracterizacion — Obra 02 Fase 0.

Caracterizan el comportamiento ACTUAL de los adapters de IDE basados en
git-hooks/directorios + registry: cursor, vscode, windsurf, zed,
antigravity, hermes (y el adapter de git hook post-commit).

Que caracterizan estos tests:
- install/setup: paths exactos creados bajo ``project_root`` (tmp_path)
  y bajo el home falso, mas contenido esperado.
- uninstall: que borra y que preserva cada adapter.
- registry: ``name`` + aliases + tiers (community/experimental).
- idempotencia: instalar dos veces deja el mismo resultado.

Bugs reales detectados: NO se arreglan aca; se marcan con
``xfail(strict=True)`` y comentario ``# KNOWN-BUG:``.
"""
from __future__ import annotations

import json
import os
import pathlib
import stat
from pathlib import Path

import pytest

from cortex.ide.adapters.antigravity import AntigravityAdapter
from cortex.ide.adapters.cursor import CursorAdapter
from cortex.ide.adapters.hermes import HermesAdapter
from cortex.ide.adapters.vscode import VSCodeAdapter
from cortex.ide.adapters.windsurf import WindsurfAdapter
from cortex.ide.adapters.zed import ZedAdapter
from cortex.ide.registry import get_adapter
from cortex.session.hooks.adapters.cursor import (
    END_MARKER,
    START_MARKER,
    CursorGitHookAdapter,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROMPTS = {"cortex-sync": "SYNC BODY", "cortex-SDDwork": "WORK BODY"}

SUBAGENT_NAMES = [
    "cortex-code-explorer",
    "cortex-code-implementer",
    "cortex-code-designer",
    "cortex-documenter",
]
SKILL_NAMES = ["cortex-sync", "cortex-SDDwork", "cortex-documenter"]


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch) -> Path:
    """Redirige ``Path.home()`` a un dir temporal (configs user-level)."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(pathlib.Path, "home", staticmethod(lambda: home))
    return home


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Proyecto minimo con la SSoT ``.cortex/`` que leen los adapters."""
    root = tmp_path / "project"
    (root / ".cortex" / "skills").mkdir(parents=True)
    (root / ".cortex" / "subagents").mkdir(parents=True)
    for skill in SKILL_NAMES:
        (root / ".cortex" / "skills" / f"{skill}.md").write_text(
            f"---\nname: {skill}\n---\n\nSKILL-BODY-{skill}\n", encoding="utf-8"
        )
    for sub in SUBAGENT_NAMES:
        (root / ".cortex" / "subagents" / f"{sub}.md").write_text(
            f"---\nname: {sub}\n---\n\nSUBAGENT-BODY-{sub}\n", encoding="utf-8"
        )
    return root


# ---------------------------------------------------------------------------
# CursorAdapter (.cursor/)
# ---------------------------------------------------------------------------


class TestCursorAdapter:
    def test_name_and_display(self):
        adapter = CursorAdapter()
        assert adapter.name == "cursor"
        assert adapter.display_name == "Cursor"

    def test_inject_profiles_paths(self, project_root: Path):
        written = CursorAdapter().inject_profiles(project_root, PROMPTS)

        expected_agents = {
            project_root / ".cursor" / "agents" / f"{n}.md" for n in SUBAGENT_NAMES
        }
        expected_skills = {
            project_root / ".cursor" / "skills" / n / "SKILL.md"
            for n in ("cortex-sync", "cortex-sddwork", "cortex-documenter")
        }
        assert {Path(p) for p in written} == expected_agents | expected_skills
        for path in expected_agents | expected_skills:
            assert path.exists(), path

    def test_subagent_frontmatter_format(self, project_root: Path):
        CursorAdapter().inject_profiles(project_root, PROMPTS)
        explorer = (
            project_root / ".cursor" / "agents" / "cortex-code-explorer.md"
        ).read_text(encoding="utf-8")
        assert explorer.startswith("---\n")
        fm = explorer.split("---")[1]
        assert "name: cortex-code-explorer" in fm
        assert "model: inherit" in fm
        # Explorer es read-only.
        assert "readonly: true" in fm
        # NO se declara tools: en Cursor subagents.
        assert "tools:" not in fm
        # El cuerpo viene de la SSoT sin frontmatter canonico.
        assert "SUBAGENT-BODY-cortex-code-explorer" in explorer
        assert "SUBAGENT-BODY-cortex-code-implementer" not in explorer

    def test_skill_file_format(self, project_root: Path):
        CursorAdapter().inject_profiles(project_root, PROMPTS)
        skill = (
            project_root / ".cursor" / "skills" / "cortex-sddwork" / "SKILL.md"
        ).read_text(encoding="utf-8")
        fm = skill.split("---")[1]
        assert "name: cortex-sddwork" in fm
        assert "description:" in fm
        assert "SKILL-BODY-cortex-SDDwork" in skill

    def test_inject_mcp_user_level_json(self, project_root: Path, fake_home: Path):
        written = CursorAdapter().inject_mcp(project_root)
        mcp_file = fake_home / ".cursor" / "mcp.json"
        assert [str(mcp_file)] == written
        data = json.loads(mcp_file.read_text(encoding="utf-8"))
        cfg = data["mcpServers"]["cortex"]
        assert cfg["command"] == "cortex"
        assert str(project_root) in cfg["args"]

    def test_inject_mcp_preserves_other_servers(
        self, project_root: Path, fake_home: Path
    ):
        mcp_file = fake_home / ".cursor" / "mcp.json"
        mcp_file.parent.mkdir(parents=True)
        mcp_file.write_text(
            json.dumps({"mcpServers": {"other": {"command": "foo"}}}), encoding="utf-8"
        )
        CursorAdapter().inject_mcp(project_root)
        data = json.loads(mcp_file.read_text(encoding="utf-8"))
        assert data["mcpServers"]["other"] == {"command": "foo"}
        assert "cortex" in data["mcpServers"]

    def test_uninstall_removes_agents_keeps_user_files(
        self, project_root: Path, fake_home: Path
    ):
        adapter = CursorAdapter()
        adapter.inject_profiles(project_root, PROMPTS)
        # Un agent del usuario convive en el mismo dir.
        user_agent = project_root / ".cursor" / "agents" / "my-agent.md"
        user_agent.write_text("mine", encoding="utf-8")

        removed = adapter.uninstall(project_root)

        for n in SUBAGENT_NAMES:
            assert not (project_root / ".cursor" / "agents" / f"{n}.md").exists()
        assert user_agent.exists(), "no debe borrar agents del usuario"
        assert any(str(p).endswith(f"{n}.md") for p in removed for n in SUBAGENT_NAMES)
        # El dir queda porque tiene el archivo del usuario.
        assert (project_root / ".cursor" / "agents").exists()

    def test_uninstall_cleans_cortex_entry_only(
        self, project_root: Path, fake_home: Path
    ):
        adapter = CursorAdapter()
        adapter.inject_mcp(project_root)
        removed = adapter.uninstall(project_root)
        data = json.loads(
            (fake_home / ".cursor" / "mcp.json").read_text(encoding="utf-8")
        )
        assert "cortex" not in data.get("mcpServers", {})
        assert any("cortex entry removed" in r for r in removed)

    # KNOWN-BUG: CursorAdapter.uninstall() no elimina los slash skills
    # instalados por inject_profiles en .cursor/skills/<n>/SKILL.md ni sus
    # directorios; quedan huerfanos tras el uninstall.
    @pytest.mark.xfail(reason="# KNOWN-BUG: uninstall deja .cursor/skills/", strict=True)
    def test_uninstall_removes_slash_skills(self, project_root: Path):
        adapter = CursorAdapter()
        adapter.inject_profiles(project_root, PROMPTS)
        adapter.uninstall(project_root)
        assert not (project_root / ".cursor" / "skills").exists()

    def test_double_install_is_idempotent(self, project_root: Path, fake_home: Path):
        adapter = CursorAdapter()
        first = adapter.inject_profiles(project_root, PROMPTS)
        snapshot = {p: Path(p).read_text(encoding="utf-8") for p in first}
        second = adapter.inject_profiles(project_root, PROMPTS)
        assert sorted(first) == sorted(second)
        for p, text in snapshot.items():
            assert Path(p).read_text(encoding="utf-8") == text


# ---------------------------------------------------------------------------
# VSCodeAdapter (.github/, .claude/, .vscode/)
# ---------------------------------------------------------------------------


class TestVSCodeAdapter:
    def test_name(self):
        assert VSCodeAdapter().name == "vscode"

    def test_inject_profiles_paths(self, project_root: Path):
        written = VSCodeAdapter().inject_profiles(project_root, PROMPTS)
        expected = {
            project_root / ".github" / "agents" / "cortex-sync.agent.md",
            project_root / ".github" / "agents" / "cortex-SDDwork.agent.md",
            project_root / ".claude" / "agents" / "cortex-code-explorer.md",
            project_root / ".claude" / "agents" / "cortex-code-implementer.md",
            project_root / ".claude" / "agents" / "cortex-documenter.md",
        }
        assert {Path(p) for p in written} == expected
        sync = (project_root / ".github" / "agents" / "cortex-sync.agent.md").read_text(
            encoding="utf-8"
        )
        assert "name: cortex-sync" in sync
        assert "SYNC BODY" in sync
        claude_agent = (
            project_root / ".claude" / "agents" / "cortex-code-explorer.md"
        ).read_text(encoding="utf-8")
        assert "SUBAGENT-BODY-cortex-code-explorer" in claude_agent

    def test_inject_mcp_project_level_workspace_folder(self, project_root: Path):
        written = VSCodeAdapter().inject_mcp(project_root)
        mcp_path = project_root / ".vscode" / "mcp.json"
        assert [str(mcp_path)] == written
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
        cfg = data["servers"]["cortex"]
        assert cfg["type"] == "stdio"
        assert "${workspaceFolder}" in cfg["args"]

    def test_uninstall_is_noop_base_default(self, project_root: Path):
        adapter = VSCodeAdapter()
        adapter.inject_profiles(project_root, PROMPTS)
        adapter.inject_mcp(project_root)
        assert adapter.uninstall() == []
        # Caracterizacion: todo lo escrito sigue en disco.
        assert (project_root / ".vscode" / "mcp.json").exists()
        assert (project_root / ".github" / "agents" / "cortex-sync.agent.md").exists()

    def test_double_install_is_idempotent(self, project_root: Path):
        adapter = VSCodeAdapter()
        first = adapter.inject_profiles(project_root, PROMPTS)
        snapshot = {p: Path(p).read_text(encoding="utf-8") for p in first}
        second = adapter.inject_profiles(project_root, PROMPTS)
        assert sorted(first) == sorted(second)
        for p, text in snapshot.items():
            assert Path(p).read_text(encoding="utf-8") == text


# ---------------------------------------------------------------------------
# WindsurfAdapter (AGENTS.md + ~/.codeium/windsurf/mcp_config.json)
# ---------------------------------------------------------------------------


class TestWindsurfAdapter:
    def test_name(self):
        assert WindsurfAdapter().name == "windsurf"

    def test_inject_profiles_overwrites_agents_md(self, project_root: Path):
        written = WindsurfAdapter().inject_profiles(project_root, PROMPTS)
        assert written == [str(project_root / "AGENTS.md")]
        text = (project_root / "AGENTS.md").read_text(encoding="utf-8")
        assert text.startswith("# Cortex Workflow")
        assert "cortex_sync_ticket" in text

    def test_inject_profiles_backs_up_existing_agents_md(self, project_root: Path):
        (project_root / "AGENTS.md").write_text("USER RULES", encoding="utf-8")
        WindsurfAdapter().inject_profiles(project_root, PROMPTS)
        backups = list(project_root.glob("AGENTS.md.cortex_backup_*"))
        assert backups, "debe dejar backup del contenido previo"
        assert backups[0].read_text(encoding="utf-8") == "USER RULES"

    def test_inject_mcp_user_level_absolute_root(
        self, project_root: Path, fake_home: Path
    ):
        written = WindsurfAdapter().inject_mcp(project_root)
        mcp_file = fake_home / ".codeium" / "windsurf" / "mcp_config.json"
        assert [str(mcp_file)] == written
        cfg = json.loads(mcp_file.read_text(encoding="utf-8"))["mcpServers"]["cortex"]
        assert cfg["args"][-1] == str(project_root)

    def test_uninstall_is_noop(self, project_root: Path, fake_home: Path):
        adapter = WindsurfAdapter()
        adapter.inject_profiles(project_root, PROMPTS)
        adapter.inject_mcp(project_root)
        assert adapter.uninstall() == []
        assert (project_root / "AGENTS.md").exists()


# ---------------------------------------------------------------------------
# ZedAdapter (~/.zed/agents.json)
# ---------------------------------------------------------------------------


class TestZedAdapter:
    def test_name(self):
        assert ZedAdapter().name == "zed"

    def test_inject_profiles_writes_agents_json(
        self, project_root: Path, fake_home: Path
    ):
        written = ZedAdapter().inject_profiles(project_root, PROMPTS)
        agents_path = fake_home / ".zed" / "agents.json"
        assert [str(agents_path)] == written
        data = json.loads(agents_path.read_text(encoding="utf-8"))
        assert set(data["agents"]) == {"cortex-sync", "cortex-SDDwork"}
        assert "SYNC BODY" in data["agents"]["cortex-sync"]["system_prompt"]
        assert "WORK BODY" in data["agents"]["cortex-SDDwork"]["system_prompt"]

    def test_missing_prompts_are_skipped(self, project_root: Path, fake_home: Path):
        ZedAdapter().inject_profiles(project_root, {"cortex-sync": "ONLY SYNC"})
        data = json.loads((fake_home / ".zed" / "agents.json").read_text())
        assert set(data["agents"]) == {"cortex-sync"}

    def test_preserves_other_agents(self, project_root: Path, fake_home: Path):
        agents_path = fake_home / ".zed" / "agents.json"
        agents_path.parent.mkdir(parents=True)
        agents_path.write_text(
            json.dumps({"agents": {"mine": {"name": "Mine"}}}), encoding="utf-8"
        )
        ZedAdapter().inject_profiles(project_root, PROMPTS)
        data = json.loads(agents_path.read_text(encoding="utf-8"))
        assert data["agents"]["mine"] == {"name": "Mine"}

    def test_inject_mcp_is_stub(self, project_root: Path):
        assert ZedAdapter().inject_mcp(project_root) == []

    def test_uninstall_is_noop(self, project_root: Path, fake_home: Path):
        adapter = ZedAdapter()
        adapter.inject_profiles(project_root, PROMPTS)
        assert adapter.uninstall() == []
        assert (fake_home / ".zed" / "agents.json").exists()


# ---------------------------------------------------------------------------
# AntigravityAdapter (~/.gemini/settings.json)
# ---------------------------------------------------------------------------


class TestAntigravityAdapter:
    def test_name(self):
        assert AntigravityAdapter().name == "antigravity"

    def test_inject_profiles_replaces_system_instructions(
        self, project_root: Path, fake_home: Path
    ):
        settings = fake_home / ".gemini" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text(
            json.dumps({"system_instructions": "OLD"}), encoding="utf-8"
        )
        written = AntigravityAdapter().inject_profiles(project_root, PROMPTS)
        assert [str(settings)] == written
        data = json.loads(settings.read_text(encoding="utf-8"))
        assert "OLD" not in data["system_instructions"], "reemplaza, no agrega"
        assert "SYNC BODY" in data["system_instructions"]
        assert "WORK BODY" in data["system_instructions"]

    def test_inject_mcp_no_project_root_flag(
        self, project_root: Path, fake_home: Path
    ):
        AntigravityAdapter().inject_profiles(project_root, PROMPTS)
        written = AntigravityAdapter().inject_mcp(project_root)
        settings = fake_home / ".gemini" / "settings.json"
        assert [str(settings)] == written
        cfg = json.loads(settings.read_text(encoding="utf-8"))["mcp_servers"]["cortex"]
        assert cfg["command"] == "cortex"
        # Caracterizacion: _get_mcp_command NO pasa --project-root como arg;
        # el root viaja solo en PYTHONPATH.
        assert "--project-root" not in cfg["args"]
        assert cfg["args"] == ["mcp-server", "--stdio"]
        assert cfg["env"]["PYTHONPATH"] == str(project_root)

    def test_uninstall_is_noop(self, project_root: Path, fake_home: Path):
        adapter = AntigravityAdapter()
        adapter.inject_profiles(project_root, PROMPTS)
        assert adapter.uninstall() == []
        assert (fake_home / ".gemini" / "settings.json").exists()


# ---------------------------------------------------------------------------
# HermesAdapter (~/.config/hermes/config.json)
# ---------------------------------------------------------------------------


class TestHermesAdapter:
    def test_name(self):
        assert HermesAdapter().name == "hermes"

    def test_inject_profiles_prompts_merged(
        self, project_root: Path, fake_home: Path
    ):
        config = fake_home / ".config" / "hermes" / "config.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"prompts": {"mine": "M"}}), encoding="utf-8")
        written = HermesAdapter().inject_profiles(project_root, PROMPTS)
        assert [str(config)] == written
        data = json.loads(config.read_text(encoding="utf-8"))
        assert data["prompts"]["mine"] == "M"
        assert "SYNC BODY" in data["prompts"]["cortex-sync"]
        assert "WORK BODY" in data["prompts"]["cortex-SDDwork"]

    def test_inject_mcp_with_pythonpath_env(self, project_root: Path, fake_home: Path):
        written = HermesAdapter().inject_mcp(project_root)
        config = fake_home / ".config" / "hermes" / "config.json"
        assert [str(config)] == written
        cfg = json.loads(config.read_text(encoding="utf-8"))["mcp"]["cortex"]
        assert cfg["env"]["PYTHONPATH"] == str(project_root)
        assert "--project-root" not in cfg["args"]

    def test_uninstall_is_noop(self, project_root: Path, fake_home: Path):
        adapter = HermesAdapter()
        adapter.inject_profiles(project_root, PROMPTS)
        assert adapter.uninstall() == []
        assert (fake_home / ".config" / "hermes" / "config.json").exists()


# ---------------------------------------------------------------------------
# Registry: names, aliases, tiers
# ---------------------------------------------------------------------------


class TestRegistryNamesAndAliases:
    @pytest.mark.parametrize(
        "ide,expected_name",
        [
            ("cursor", "cursor"),
            ("vscode", "vscode"),
            ("windsurf", "windsurf"),
            ("zed", "zed"),
            ("antigravity", "antigravity"),
            ("hermes", "hermes"),
        ],
    )
    def test_get_adapter_by_name(self, ide, expected_name):
        assert get_adapter(ide).name == expected_name

    @pytest.mark.parametrize("alias", ["code", "vs-code", "visual-studio-code"])
    def test_vscode_aliases(self, alias):
        assert get_adapter(alias).name == "vscode"

    def test_unknown_ide_raises_keyerror_with_tiers(self):
        with pytest.raises(KeyError) as excinfo:
            get_adapter("noexiste")
        msg = str(excinfo.value)
        assert "Unknown IDE" in msg
        assert "Target" in msg and "Community" in msg and "Experimental" in msg

    @pytest.mark.parametrize("ide", ["cursor", "vscode", "windsurf"])
    def test_community_tier(self, ide):
        from cortex.ide.registry import get_ide_tier

        assert get_ide_tier(ide) == "community"

    @pytest.mark.parametrize("ide", ["zed", "antigravity", "hermes"])
    def test_experimental_tier(self, ide):
        from cortex.ide.registry import get_ide_tier

        assert get_ide_tier(ide) == "experimental"


# ---------------------------------------------------------------------------
# CursorGitHookAdapter (.git/hooks/post-commit)
# ---------------------------------------------------------------------------


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".git" / "hooks").mkdir(parents=True)
    return repo


class TestCursorGitHookAdapter:
    def test_name(self):
        assert CursorGitHookAdapter.name == "cursor"

    def test_install_requires_git_repo(self, tmp_path: Path):
        plain = tmp_path / "not-a-repo"
        plain.mkdir()
        with pytest.raises(ValueError, match="not a git repository"):
            CursorGitHookAdapter().install(plain)

    def test_install_fresh_creates_hook(self, git_repo: Path):
        result = CursorGitHookAdapter().install(git_repo)
        hook = git_repo / ".git" / "hooks" / "post-commit"
        assert result.installed is True
        assert [hook] == result.modified_paths
        text = hook.read_text(encoding="utf-8")
        assert text.startswith("#!/bin/sh")
        assert START_MARKER in text and END_MARKER in text
        assert "cortex session checkpoint --source ide-hook" in text
        assert os.access(hook, os.X_OK), "el hook debe quedar ejecutable"

    def test_install_appends_after_user_script(self, git_repo: Path):
        hook = git_repo / ".git" / "hooks" / "post-commit"
        hook.write_text("#!/bin/sh\necho user-hook\n", encoding="utf-8")
        CursorGitHookAdapter().install(git_repo)
        text = hook.read_text(encoding="utf-8")
        assert text.index("echo user-hook") < text.index(START_MARKER)
        assert "echo user-hook" in text.split(END_MARKER)[0]

    def test_install_adds_shebang_if_missing(self, git_repo: Path):
        hook = git_repo / ".git" / "hooks" / "post-commit"
        hook.write_text("echo no-shebang\n", encoding="utf-8")
        CursorGitHookAdapter().install(git_repo)
        text = hook.read_text(encoding="utf-8")
        assert text.startswith("#!/bin/sh")
        assert "echo no-shebang" in text

    def test_double_install_idempotent(self, git_repo: Path):
        adapter = CursorGitHookAdapter()
        first = adapter.install(git_repo)
        hook = git_repo / ".git" / "hooks" / "post-commit"
        before = hook.read_text(encoding="utf-8")
        second = adapter.install(git_repo)
        assert second.installed is True
        assert second.modified_paths == []
        assert "already installed" in second.message
        assert hook.read_text(encoding="utf-8") == before
        assert first.modified_paths != []

    def test_status(self, git_repo: Path):
        adapter = CursorGitHookAdapter()
        status_before = adapter.status(git_repo)
        assert status_before.installed is False
        adapter.install(git_repo)
        assert adapter.status(git_repo).installed is True

    def test_uninstall_removes_block_keeps_user_content(self, git_repo: Path):
        adapter = CursorGitHookAdapter()
        hook = git_repo / ".git" / "hooks" / "post-commit"
        hook.write_text("#!/bin/sh\necho user-hook\n", encoding="utf-8")
        adapter.install(git_repo)
        result = adapter.uninstall(git_repo)
        assert result.uninstalled is True
        text = hook.read_text(encoding="utf-8")
        assert START_MARKER not in text and END_MARKER not in text
        assert "echo user-hook" in text

    def test_uninstall_deletes_file_if_only_shebang_left(self, git_repo: Path):
        adapter = CursorGitHookAdapter()
        adapter.install(git_repo)
        result = adapter.uninstall(git_repo)
        assert result.uninstalled is True
        assert not (git_repo / ".git" / "hooks" / "post-commit").exists()

    def test_uninstall_without_block_is_noop(self, git_repo: Path):
        hook = git_repo / ".git" / "hooks" / "post-commit"
        hook.write_text("#!/bin/sh\necho user-only\n", encoding="utf-8")
        result = CursorGitHookAdapter().uninstall(git_repo)
        assert result.uninstalled is False
        assert result.removed_paths == []
        assert "user-only" in hook.read_text(encoding="utf-8")

    def test_uninstall_when_hook_absent(self, git_repo: Path):
        result = CursorGitHookAdapter().uninstall(git_repo)
        assert result.uninstalled is False
        assert result.removed_paths == []
