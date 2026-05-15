from __future__ import annotations

import json
from pathlib import Path

from cortex.ide import get_supported_ides
from cortex.ide.registry import (
    TARGET_IDES,
    get_adapter,
    get_ide_tier,
    get_target_ides,
)


def test_supported_ides_registry() -> None:
    ides = get_supported_ides()
    assert "opencode" in ides
    assert "cursor" in ides
    assert "vscode" in ides
    assert "windsurf" in ides
    assert "antigravity" not in ides
    assert "hermes" not in ides
    assert "zed" not in ides


# ---------------------------------------------------------------------------
# Target IDE matrix — the 4 officially supported IDEs (claude_code,
# opencode, pi, codex). Regression of Ola 1.
# ---------------------------------------------------------------------------


def test_target_ides_are_registered() -> None:
    """The 4 IDEs Cortex officially targets must be available out of the box."""
    registered = set(get_supported_ides(include_experimental=True))
    expected = {"claude_code", "opencode", "pi", "codex"}
    missing = expected - registered
    assert not missing, f"Target IDEs missing from registry: {sorted(missing)}"


def test_target_ides_helper_lists_the_four() -> None:
    assert set(get_target_ides()) == {"claude_code", "opencode", "pi", "codex"}


def test_target_constant_matches_helper() -> None:
    assert set(get_target_ides()) == set(TARGET_IDES)


def test_get_ide_tier_classifies_each_adapter() -> None:
    for name in ("claude_code", "opencode", "pi", "codex"):
        assert get_ide_tier(name) == "target", name
    for name in ("cursor", "vscode", "windsurf", "claude_desktop"):
        assert get_ide_tier(name) == "community", name
    for name in ("zed", "antigravity", "hermes"):
        assert get_ide_tier(name) == "experimental", name


def test_get_ide_tier_supports_aliases() -> None:
    # 'claude-code' and 'claude' both resolve to the claude_code adapter.
    assert get_ide_tier("claude-code") == "target"
    assert get_ide_tier("claude") == "target"
    assert get_ide_tier("codex-cli") == "target"


def test_unknown_ide_error_lists_tiers() -> None:
    """The error message must guide the user to a valid IDE name."""
    import pytest

    with pytest.raises(KeyError) as info:
        get_adapter("does-not-exist")
    message = str(info.value)
    assert "Target" in message
    assert "claude_code" in message


# ---------------------------------------------------------------------------
# Validation status (Fase 4 plan multi-IDE & MCP hardening, 2026-05-15)
# ---------------------------------------------------------------------------


def test_validated_ides_list_matches_decisions_firmadas() -> None:
    """get_validated_ides_list debe contener exactamente los 5 IDEs que el
    creador certifico en Decision 1+2+3 firmadas el 2026-05-15."""
    from cortex.ide.registry import get_validated_ides_list
    assert get_validated_ides_list() == ["claude_code", "codex", "cursor", "opencode", "pi"]


def test_unvalidated_ides_list_includes_all_remaining() -> None:
    """Adapters NO validados: vscode, claude_desktop, windsurf,
    antigravity, hermes, zed (Decision 4 firmada)."""
    from cortex.ide.registry import get_unvalidated_ides_list
    expected = sorted({"vscode", "claude_desktop", "windsurf", "antigravity", "hermes", "zed"})
    assert get_unvalidated_ides_list() == expected


def test_is_ide_validated_true_for_target_5() -> None:
    from cortex.ide.registry import is_ide_validated
    for name in ("claude_code", "opencode", "codex", "cursor", "pi"):
        assert is_ide_validated(name) is True, name


def test_is_ide_validated_false_for_community_experimental() -> None:
    from cortex.ide.registry import is_ide_validated
    for name in ("vscode", "claude_desktop", "windsurf", "antigravity", "hermes", "zed"):
        assert is_ide_validated(name) is False, name


def test_is_ide_validated_supports_aliases() -> None:
    from cortex.ide.registry import is_ide_validated
    assert is_ide_validated("claude") is True
    assert is_ide_validated("claude-code") is True
    assert is_ide_validated("codex-cli") is True


def test_is_ide_validated_raises_on_unknown() -> None:
    """KeyError para IDEs no registrados (no es una decision silenciosa)."""
    import pytest

    from cortex.ide.registry import is_ide_validated
    with pytest.raises(KeyError):
        is_ide_validated("does-not-exist")


# ---------------------------------------------------------------------------
# Codex adapter — fresh in Ola 1
# ---------------------------------------------------------------------------


def test_codex_adapter_inject_profiles(tmp_path: Path) -> None:
    """Codex no soporta subagents personalizados (Decision 2 firmada
    2026-05-15, ver docs/multi-ide-mcp-hardening/MATRIZ-NATIVA-IDES.md
    seccion 4). El adapter inyecta SOLO ``AGENTS.md`` en project root con
    el flujo tripartito secuencial. NO genera ``.codex/agents/*.md`` ni
    ``.codex/skills/*.md`` (Codex los ignora segun docs oficiales)."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    adapter = get_adapter("codex")
    files = adapter.inject_profiles(project_root, prompts={})

    # AGENTS.md va al project root, NO ``.codex/AGENTS.md``.
    agents_md = project_root / "AGENTS.md"
    assert agents_md.exists()
    body = agents_md.read_text(encoding="utf-8")
    assert "Cortex Workflow for Codex" in body
    assert "single-agent sequence" in body
    assert "cortex_create_spec" in body
    assert "cortex_sync_ticket" in body

    # NO se debe generar .codex/agents/ ni .codex/skills/
    assert not (project_root / ".codex" / "agents").exists()
    assert not (project_root / ".codex" / "skills").exists()
    # Tampoco .codex/AGENTS.md (path obsoleto pre-Fase 4).
    assert not (project_root / ".codex" / "AGENTS.md").exists()

    # All written paths are reported.
    assert str(agents_md) in files


# ---------------------------------------------------------------------------
# Tripartita Refinada — Plan 06 (Codex)
# ---------------------------------------------------------------------------


class TestCodexTripartitaRefinada:
    """Decision 2 firmada del creador (2026-05-15): Codex NO soporta
    subagents personalizados. El flujo tripartito se materializa como
    secuencia inline en ``AGENTS.md`` (project root). Los tests viejos
    que verificaban ``.codex/agents/*.md`` fueron eliminados (esos
    archivos ya no se generan porque Codex los ignora segun docs
    oficiales).
    """

    def test_agents_md_mentions_verification_gate(self, tmp_path: Path) -> None:
        """AGENTS.md en project root debe mencionar todos los gates."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        adapter = get_adapter("codex")
        adapter.inject_profiles(project_root, prompts={})

        # AGENTS.md va al PROJECT ROOT, no .codex/.
        agents_md = (project_root / "AGENTS.md").read_text(encoding="utf-8")
        assert "Verification Gate" in agents_md
        assert "cortex_validate_handoff" in agents_md
        assert "cortex_verify_session_claims" in agents_md
        assert "AgentHandoff" in agents_md
        assert "status: handoff" in agents_md.lower() or "`handoff`" in agents_md
        assert "CONTEXT.md" in agents_md
        assert "no native `Task`" in agents_md

    def test_agents_md_describes_sequential_tripartite_flow(self, tmp_path: Path) -> None:
        """AGENTS.md describe las 3 fases tripartitas como SECUENCIA,
        no como subagents paralelos (Codex no los soporta)."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        adapter = get_adapter("codex")
        adapter.inject_profiles(project_root, prompts={})

        agents_md = (project_root / "AGENTS.md").read_text(encoding="utf-8")
        for marker in ("Phase 1", "Phase 2", "Phase 3", "Explorer", "Implementer", "Documenter"):
            assert marker in agents_md, f"missing flow marker: {marker!r}"
        # Pre-flight check obligatorio (Fase 2 del plan multi-IDE).
        assert "cortex_ping" in agents_md
        assert "Pre-flight check" in agents_md

    def test_agents_md_uses_cortex_section_markers(self, tmp_path: Path) -> None:
        """El bloque Cortex va entre marcadores para coexistir con
        AGENTS.md preexistente del adopter."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        adapter = get_adapter("codex")
        adapter.inject_profiles(project_root, prompts={})

        agents_md = (project_root / "AGENTS.md").read_text(encoding="utf-8")
        assert "BEGIN CORTEX SECTION" in agents_md
        assert "END CORTEX SECTION" in agents_md

    def test_agents_md_preserves_user_content_when_existing(self, tmp_path: Path) -> None:
        """Si el adopter ya tiene AGENTS.md, su contenido se preserva."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        agents_md = project_root / "AGENTS.md"
        user_content = "# My Project\n\nUser-authored guidance here.\n"
        agents_md.write_text(user_content, encoding="utf-8")

        adapter = get_adapter("codex")
        adapter.inject_profiles(project_root, prompts={})

        merged = agents_md.read_text(encoding="utf-8")
        assert "User-authored guidance here." in merged
        assert "BEGIN CORTEX SECTION" in merged

    def test_agents_md_replaces_cortex_block_idempotent(self, tmp_path: Path) -> None:
        """Re-inyectar reemplaza el bloque Cortex anterior, no lo duplica."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        adapter = get_adapter("codex")
        adapter.inject_profiles(project_root, prompts={})
        adapter.inject_profiles(project_root, prompts={})  # idempotente

        agents_md = (project_root / "AGENTS.md").read_text(encoding="utf-8")
        # Solo debe haber UN bloque Cortex.
        assert agents_md.count("BEGIN CORTEX SECTION") == 1
        assert agents_md.count("END CORTEX SECTION") == 1


def test_codex_adapter_inject_mcp_uses_absolute_path(tmp_path: Path) -> None:
    """Codex MCP debe usar absolute --project-root, no '.'.

    Decision 2 firmada: Codex MCP config va en .codex/config.toml (TOML),
    no .codex/mcp.json (JSON). Sintaxis: [mcp_servers.cortex] (snake_case).
    """
    import tomllib

    project_root = (tmp_path / "project").resolve()
    project_root.mkdir()
    adapter = get_adapter("codex")
    files = adapter.inject_mcp(project_root)

    config_path = project_root / ".codex" / "config.toml"
    assert config_path.exists(), "MCP config debe ir en .codex/config.toml (TOML, no JSON)"

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    cortex_cfg = data["mcp_servers"]["cortex"]
    args = cortex_cfg["args"]
    assert "--project-root" in args
    idx = args.index("--project-root")
    assert args[idx + 1] == str(project_root)
    assert args[idx + 1] != "."
    assert cortex_cfg["enabled"] is True
    assert cortex_cfg["env"] == {"PYTHONWARNINGS": "ignore"}
    assert str(config_path) in files

    # Confirma que NO se genera el path obsoleto .codex/mcp.json
    assert not (project_root / ".codex" / "mcp.json").exists()


def test_claude_code_adapter_inject_mcp_uses_absolute_path(tmp_path: Path) -> None:
    """Regression: Claude Code must not write a relative '.' as --project-root."""
    project_root = (tmp_path / "project").resolve()
    project_root.mkdir()
    adapter = get_adapter("claude_code")
    adapter.inject_mcp(project_root)

    mcp_path = project_root / ".mcp.json"
    import json

    data = json.loads(mcp_path.read_text(encoding="utf-8"))
    args = data["mcpServers"]["cortex"]["args"]
    idx = args.index("--project-root")
    assert args[idx + 1] == str(project_root)
    assert args[idx + 1] != "."


def test_opencode_adapter_inject_profiles(monkeypatch, tmp_path: Path) -> None:
    """OpenCode usa el campo ``permission`` (moderno) en lugar de ``tools``
    (deprecated). Los MCP tools NO se declaran en el agent profile — se
    descubren dinamicamente al conectarse al MCP server (ver Fase 4 plan
    multi-IDE & MCP hardening, 2026-05-15)."""
    project_root = tmp_path / "project"

    # Mock home dir for the adapter to write to
    monkeypatch.setattr("cortex.ide.adapters.opencode.Path.home", staticmethod(lambda: tmp_path))

    adapter = get_adapter("opencode")
    prompts = {
        "cortex-sync": "Pre-flight prompt",
        "cortex-SDDwork": "Orchestrator prompt"
    }

    files = adapter.inject_profiles(project_root, prompts)

    config_path = tmp_path / ".config" / "opencode" / "opencode.json"
    assert config_path.exists()
    assert str(config_path) in files

    data = json.loads(config_path.read_text(encoding="utf-8"))

    # Estructura basica
    assert "cortex-sync" in data["agent"]
    assert "cortex-SDDwork" in data["agent"]

    # Cortex-sync usa permission (no tools) y es read-only.
    sync_perm = data["agent"]["cortex-sync"]["permission"]
    assert sync_perm["read"] == "allow"
    assert sync_perm["write"] == "deny"
    assert sync_perm["edit"] == "deny"
    assert sync_perm["bash"] == "deny"

    # Cortex-SDDwork puede modificar archivos.
    sddwork_perm = data["agent"]["cortex-SDDwork"]["permission"]
    assert sddwork_perm["read"] == "allow"
    assert sddwork_perm["write"] == "allow"
    assert sddwork_perm["edit"] == "allow"
    # bash queda en "ask" para que el usuario apruebe ejecuciones de shell.
    assert sddwork_perm["bash"] == "ask"

    # Verificar que los MCP tools NO estan en permission (descubrimiento dinamico).
    for mcp_tool in ("cortex_save_session", "cortex_search", "cortex_validate_handoff"):
        assert mcp_tool not in sync_perm, (
            f"MCP tool '{mcp_tool}' no debe estar en permission de opencode "
            "(se descubre dinamicamente)"
        )
        assert mcp_tool not in sddwork_perm

    # El campo legacy 'tools' NO debe estar (migrado a permission).
    assert "tools" not in data["agent"]["cortex-sync"]
    assert "tools" not in data["agent"]["cortex-SDDwork"]

    # Skills files
    skills_dir = tmp_path / ".config" / "opencode" / "skills"
    sync_content = (skills_dir / "cortex-sync.md").read_text(encoding="utf-8")
    work_content = (skills_dir / "cortex-SDDwork.md").read_text(encoding="utf-8")

    assert "AUTOGENERATED BY CORTEX" in sync_content
    assert "Pre-flight prompt" in sync_content
    assert "AUTOGENERATED BY CORTEX" in work_content
    assert "Orchestrator prompt" in work_content


# ---------------------------------------------------------------------------
# Tripartita Refinada — Plan 04 (OpenCode)
# ---------------------------------------------------------------------------


class TestOpenCodeTripartitaRefinada:
    """Decision 4 firmada (2026-05-15): los MCP tools de Cortex en opencode
    se descubren DINAMICAMENTE al conectarse al MCP server. NO se declaran
    en el agent profile (eso es invalido segun docs oficiales — el campo
    permission solo acepta tools NATIVOS de opencode).

    Tests viejos que verificaban ``tools["cortex_validate_handoff"] is True``
    fueron eliminados. Estos tests garantizan lo opuesto: que los MCP tools
    NO esten declarados (regression guard contra el bug que detecto el
    creador en la sesion del 2026-05-15).
    """

    def _inject(self, monkeypatch, tmp_path: Path) -> dict:
        monkeypatch.setattr(
            "cortex.ide.adapters.opencode.Path.home",
            staticmethod(lambda: tmp_path),
        )
        adapter = get_adapter("opencode")
        adapter.inject_profiles(
            tmp_path / "project",
            prompts={"cortex-sync": "Sync prompt", "cortex-SDDwork": "Work prompt"},
        )
        config_path = tmp_path / ".config" / "opencode" / "opencode.json"
        return json.loads(config_path.read_text(encoding="utf-8"))

    def test_sync_agent_uses_permission_not_tools(self, monkeypatch, tmp_path: Path) -> None:
        """OpenCode adapter DEBE usar el campo moderno 'permission'."""
        data = self._inject(monkeypatch, tmp_path)
        agent = data["agent"]["cortex-sync"]
        assert "permission" in agent
        assert "tools" not in agent  # Campo legacy debe estar AUSENTE.

    def test_sddwork_agent_uses_permission_not_tools(self, monkeypatch, tmp_path: Path) -> None:
        data = self._inject(monkeypatch, tmp_path)
        agent = data["agent"]["cortex-SDDwork"]
        assert "permission" in agent
        assert "tools" not in agent

    def test_no_mcp_tools_declared_in_permission(self, monkeypatch, tmp_path: Path) -> None:
        """Regression guard: ningun cortex_* debe aparecer en permission.

        Los MCP tools se descubren dinamicamente al conectarse al MCP
        server. Declararlos aqui es invalido segun docs oficiales de
        opencode y reproduce el bug del 2026-05-15.
        """
        data = self._inject(monkeypatch, tmp_path)
        for agent_name in ("cortex-sync", "cortex-SDDwork"):
            perm = data["agent"][agent_name]["permission"]
            mcp_keys_found = [k for k in perm if k.startswith("cortex_")]
            assert not mcp_keys_found, (
                f"[{agent_name}] MCP tools en permission: {mcp_keys_found}. "
                "Estos se descubren dinamicamente, no van declarados."
            )

    def test_permission_uses_allow_ask_deny_values(self, monkeypatch, tmp_path: Path) -> None:
        """Los valores en permission son strings 'allow'|'ask'|'deny',
        no booleanos (ese era el formato del campo legacy 'tools')."""
        data = self._inject(monkeypatch, tmp_path)
        for agent_name in ("cortex-sync", "cortex-SDDwork"):
            perm = data["agent"][agent_name]["permission"]
            for key, value in perm.items():
                assert value in ("allow", "ask", "deny"), (
                    f"[{agent_name}.{key}] valor '{value}' invalido. "
                    "Permitidos: 'allow', 'ask', 'deny'."
                )


def test_opencode_adapter_inject_mcp_uses_opencode_local_command_shape(
    monkeypatch, tmp_path: Path
) -> None:
    project_root = tmp_path / "project"

    monkeypatch.setattr("cortex.ide.adapters.opencode.Path.home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr("cortex.ide.base.Path.home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr("cortex.ide.adapters.opencode._is_wsl", lambda: False)

    adapter = get_adapter("opencode")
    files = adapter.inject_mcp(project_root)

    config_path = tmp_path / ".config" / "opencode" / "opencode.json"
    assert config_path.exists()
    assert str(config_path) in files

    data = json.loads(config_path.read_text(encoding="utf-8"))
    cortex_config = data["mcp"]["cortex"]

    assert cortex_config["type"] == "local"
    assert cortex_config["command"] == [
        "cortex",
        "mcp-server",
        "--stdio",
        "--project-root",
        str(project_root),
    ]
    assert cortex_config["enabled"] is True
    assert cortex_config["environment"]["PYTHONWARNINGS"] == "ignore"
    assert "args" not in cortex_config
    assert "env" not in cortex_config


def test_opencode_adapter_inject_mcp_wsl_wrapper_uses_cortex_binary(
    monkeypatch, tmp_path: Path
) -> None:
    project_root = tmp_path / "project"

    monkeypatch.setattr("cortex.ide.adapters.opencode.Path.home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr("cortex.ide.base.Path.home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr("cortex.ide.adapters.opencode._is_wsl", lambda: True)
    monkeypatch.setattr("cortex.ide.base._is_wsl", lambda: True)
    monkeypatch.setattr("cortex.ide.base.shutil.which", lambda name: "/home/test/.local/bin/cortex")

    adapter = get_adapter("opencode")
    adapter.inject_mcp(project_root)

    config_path = tmp_path / ".config" / "opencode" / "opencode.json"
    wrapper_path = tmp_path / ".cortex" / "bin" / "cortex-mcp-wrapper"

    data = json.loads(config_path.read_text(encoding="utf-8"))
    cortex_config = data["mcp"]["cortex"]
    wrapper_content = wrapper_path.read_text(encoding="utf-8")

    assert cortex_config["command"] == [str(wrapper_path)]
    assert cortex_config["enabled"] is True
    assert wrapper_path.exists()
    assert 'exec "/home/test/.local/bin/cortex" mcp-server --stdio --project-root' in wrapper_content
    assert str(project_root) in wrapper_content
    assert "python3 -m cortex.cli.main" not in wrapper_content
    assert "PYTHONPATH" not in wrapper_content


def test_cursor_adapter_inject_mcp(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    
    monkeypatch.setattr("cortex.ide.adapters.cursor.Path.home", staticmethod(lambda: tmp_path))

    adapter = get_adapter("cursor")
    files = adapter.inject_mcp(project_root)

    mcp_path = tmp_path / ".cursor" / "mcp.json"
    assert mcp_path.exists()
    assert str(mcp_path) in files

    data = json.loads(mcp_path.read_text(encoding="utf-8"))
    
    assert "cortex" in data["mcpServers"]
    assert data["mcpServers"]["cortex"]["command"] == "cortex"
    assert "mcp-server" in data["mcpServers"]["cortex"]["args"]
    assert "--stdio" in data["mcpServers"]["cortex"]["args"]
    assert "--project-root" in data["mcpServers"]["cortex"]["args"]
    assert data["mcpServers"]["cortex"]["env"]["PYTHONWARNINGS"] == "ignore"


def test_vscode_adapter_writes_workspace_agents_and_mcp(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    (project_root / ".cortex" / "subagents").mkdir(parents=True)
    (project_root / ".cortex" / "subagents" / "cortex-code-explorer.md").write_text(
        "---\nname: cortex-code-explorer\ndescription: explorer\n---\n\nExplorer body",
        encoding="utf-8",
    )
    (project_root / ".cortex" / "subagents" / "cortex-code-implementer.md").write_text(
        "---\nname: cortex-code-implementer\ndescription: implementer\n---\n\nImplementer body",
        encoding="utf-8",
    )
    (project_root / ".cortex" / "subagents" / "cortex-documenter.md").write_text(
        "---\nname: cortex-documenter\ndescription: documenter\n---\n\nDocumenter body",
        encoding="utf-8",
    )

    adapter = get_adapter("vscode")
    prompts = {
        "cortex-sync": "---\nname: cortex-sync\n---\n\nSync body",
        "cortex-SDDwork": "---\nname: cortex-SDDwork\n---\n\nWork body",
    }

    files = adapter.inject_profiles(project_root, prompts)
    files.extend(adapter.inject_mcp(project_root))

    sync_path = project_root / ".github" / "agents" / "cortex-sync.agent.md"
    work_path = project_root / ".github" / "agents" / "cortex-SDDwork.agent.md"
    mcp_path = project_root / ".vscode" / "mcp.json"

    assert sync_path.exists()
    assert work_path.exists()
    assert mcp_path.exists()
    assert str(sync_path) in files
    assert "handoffs:" in sync_path.read_text(encoding="utf-8")
    assert "agents:" in work_path.read_text(encoding="utf-8")
    assert "cortex" in json.loads(mcp_path.read_text(encoding="utf-8"))["servers"]


def test_claude_code_adapter_writes_project_assets(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    (project_root / ".cortex" / "subagents").mkdir(parents=True)
    for name in ("cortex-code-explorer", "cortex-code-implementer", "cortex-documenter"):
        (project_root / ".cortex" / "subagents" / f"{name}.md").write_text(
            f"---\nname: {name}\ndescription: {name}\n---\n\n{name} body",
            encoding="utf-8",
        )

    adapter = get_adapter("claude_code")
    prompts = {
        "cortex-sync": "---\nname: cortex-sync\n---\n\nSync body",
        "cortex-SDDwork": "---\nname: cortex-SDDwork\n---\n\nWork body",
    }

    files = adapter.inject_profiles(project_root, prompts)
    files.extend(adapter.inject_mcp(project_root))

    assert (project_root / "CLAUDE.md").exists()
    assert (project_root / ".claude" / "skills" / "cortex-sync" / "SKILL.md").exists()
    assert (project_root / ".claude" / "skills" / "cortex-sddwork" / "SKILL.md").exists()
    assert (project_root / ".claude" / "agents" / "cortex-code-explorer.md").exists()
    assert (project_root / ".mcp.json").exists()
    assert (project_root / ".claude" / "settings.json").exists()
    assert str(project_root / ".mcp.json") in files


# ---------------------------------------------------------------------------
# Tripartita Refinada — Plan 03 (Claude Code)
# ---------------------------------------------------------------------------


class TestClaudeCodeTripartitaRefinada:
    """Plan 03 contract — CLAUDE.md mentions the new contracts and the agent
    files inherit the canonical markers from ``.cortex/subagents/``.

    These are the tests that catch silent drift if someone reverts the
    new template lines or if the adapter stops reading the canonical
    prompts from disk.
    """

    def _setup_canonical(self, project_root: Path) -> None:
        """Drop a synthetic canonical bundle that contains all 8 markers
        Plan 01 introduced, so we can assert the adapter copies them
        verbatim into ``.claude/agents/``."""
        subagents = project_root / ".cortex" / "subagents"
        subagents.mkdir(parents=True)
        documenter_body = (
            "---\nname: cortex-documenter\ndescription: documenter\n---\n\n"
            "# HIGH-SIGNAL DOCUMENTATION MODE\n\n"
            "## Criterios para crear un ADR (3 criterios)\n"
            "...\n\n"
            "## VERIFICATION GATE\n"
            "...\n\n"
            "## Modo Handoff\n"
            "...\n\n"
            "## Anti-rationalization\n"
            "...\n\n"
            "## Contrato de Salida\n"
            "```yaml\nagent: cortex-documenter\n```\n"
        )
        explorer_body = (
            "---\nname: cortex-code-explorer\ndescription: explorer\n---\n\n"
            "## Anti-rationalization\n...\n\n## Contrato de Salida\n...\n"
        )
        implementer_body = (
            "---\nname: cortex-code-implementer\ndescription: implementer\n---\n\n"
            "## Anti-rationalization\n...\n\n## Contrato de Salida\n...\n"
        )
        (subagents / "cortex-documenter.md").write_text(documenter_body, encoding="utf-8")
        (subagents / "cortex-code-explorer.md").write_text(explorer_body, encoding="utf-8")
        (subagents / "cortex-code-implementer.md").write_text(implementer_body, encoding="utf-8")

    def test_claude_md_mentions_verification_gate(self, tmp_path: Path) -> None:
        project_root = tmp_path / "project"
        self._setup_canonical(project_root)
        adapter = get_adapter("claude_code")
        adapter.inject_profiles(
            project_root,
            prompts={
                "cortex-sync": "---\nname: cortex-sync\n---\n\nx",
                "cortex-SDDwork": "---\nname: cortex-SDDwork\n---\n\ny",
            },
        )

        claude_md = (project_root / "CLAUDE.md").read_text(encoding="utf-8")
        # All 4 new rules must be present.
        assert "Verification Gate" in claude_md
        assert "cortex_validate_handoff" in claude_md
        assert "cortex_verify_session_claims" in claude_md
        assert "AgentHandoff" in claude_md
        assert "status: handoff" in claude_md.lower() or "`handoff`" in claude_md
        assert "CONTEXT.md" in claude_md

    def test_documenter_agent_inherits_canonical_markers(self, tmp_path: Path) -> None:
        """``.claude/agents/cortex-documenter.md`` must carry every Plan 01
        marker through unchanged. If the adapter starts filtering or
        rewriting the body, this catches it."""
        project_root = tmp_path / "project"
        self._setup_canonical(project_root)
        adapter = get_adapter("claude_code")
        adapter.inject_profiles(
            project_root,
            prompts={
                "cortex-sync": "---\nname: cortex-sync\n---\n\nx",
                "cortex-SDDwork": "---\nname: cortex-SDDwork\n---\n\ny",
            },
        )

        documenter = (
            project_root / ".claude" / "agents" / "cortex-documenter.md"
        ).read_text(encoding="utf-8")
        for marker in (
            "HIGH-SIGNAL DOCUMENTATION MODE",
            "3 criterios",
            "VERIFICATION GATE",
            "Modo Handoff",
            "Anti-rationalization",
            "Contrato de Salida",
        ):
            assert marker in documenter, f"{marker!r} missing from .claude/agents/cortex-documenter.md"

    def test_explorer_and_implementer_inherit_anti_rationalization(self, tmp_path: Path) -> None:
        project_root = tmp_path / "project"
        self._setup_canonical(project_root)
        adapter = get_adapter("claude_code")
        adapter.inject_profiles(
            project_root,
            prompts={
                "cortex-sync": "---\nname: cortex-sync\n---\n\nx",
                "cortex-SDDwork": "---\nname: cortex-SDDwork\n---\n\ny",
            },
        )

        for agent in ("cortex-code-explorer", "cortex-code-implementer"):
            content = (
                project_root / ".claude" / "agents" / f"{agent}.md"
            ).read_text(encoding="utf-8")
            assert "Anti-rationalization" in content, agent
            assert "Contrato de Salida" in content, agent


# ---------------------------------------------------------------------------
# Tripartita Refinada — Plan 05 (Pi)
# ---------------------------------------------------------------------------


class TestPiSyncCanonicalSubagents:
    """Plan 05 §1 contract — Pi must mirror canonical subagents into its
    bundle before injecting the project, otherwise the bundle drifts and
    Pi adopters get yesterday's prompts."""

    def _make_canonical(self, project_root: Path) -> Path:
        """Drop a synthetic canonical bundle with the 3 shared subagents."""
        canonical = project_root / ".cortex" / "subagents"
        canonical.mkdir(parents=True)
        (canonical / "cortex-code-explorer.md").write_text(
            "# canonical explorer (post-Plan 01)\nVERIFICATION GATE marker.",
            encoding="utf-8",
        )
        (canonical / "cortex-code-implementer.md").write_text(
            "# canonical implementer\nAnti-rationalization marker.",
            encoding="utf-8",
        )
        (canonical / "cortex-documenter.md").write_text(
            "# canonical documenter\nHIGH-SIGNAL DOCUMENTATION MODE marker.",
            encoding="utf-8",
        )
        return canonical

    def test_overwrites_bundle_with_canonical_content(self, tmp_path: Path) -> None:
        """When the canonical content is fresher than the bundle, the
        bundle gets updated. We pass a fake ``bundle_dir`` so the real
        repository bundle is not mutated by the test."""
        project_root = tmp_path / "project"
        self._make_canonical(project_root)
        fake_bundle = tmp_path / "fake-bundle"

        adapter = get_adapter("pi")
        overwritten = adapter.sync_canonical_subagents(project_root, bundle_dir=fake_bundle)

        assert len(overwritten) == 3
        documenter = (fake_bundle / ".pi" / "agents" / "cortex-documenter.md").read_text(encoding="utf-8")
        assert "HIGH-SIGNAL DOCUMENTATION MODE" in documenter
        explorer = (fake_bundle / ".pi" / "agents" / "cortex-code-explorer.md").read_text(encoding="utf-8")
        assert "VERIFICATION GATE" in explorer

    def test_no_canonical_directory_returns_empty_list(self, tmp_path: Path) -> None:
        """When the project has no ``.cortex/subagents/`` (e.g. Pi is
        being injected before Cortex setup ran), the sync is a no-op."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        fake_bundle = tmp_path / "fake-bundle"

        adapter = get_adapter("pi")
        overwritten = adapter.sync_canonical_subagents(project_root, bundle_dir=fake_bundle)

        assert overwritten == []
        # Bundle agents directory may exist but must contain none of the shared agents.
        agents_dir = fake_bundle / ".pi" / "agents"
        for name in ("cortex-code-explorer.md", "cortex-code-implementer.md", "cortex-documenter.md"):
            assert not (agents_dir / name).exists()

    def test_partial_canonical_only_copies_what_exists(self, tmp_path: Path) -> None:
        """If only one of the 3 shared agents exists in canonical, only
        that one gets mirrored — the others stay as they were in the bundle."""
        project_root = tmp_path / "project"
        canonical = project_root / ".cortex" / "subagents"
        canonical.mkdir(parents=True)
        (canonical / "cortex-documenter.md").write_text("# only documenter", encoding="utf-8")
        # Pre-seed the fake bundle with stale content for the other two.
        fake_bundle = tmp_path / "fake-bundle"
        agents_dir = fake_bundle / ".pi" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "cortex-code-explorer.md").write_text("STALE explorer", encoding="utf-8")

        adapter = get_adapter("pi")
        overwritten = adapter.sync_canonical_subagents(project_root, bundle_dir=fake_bundle)

        assert len(overwritten) == 1
        assert overwritten[0].name == "cortex-documenter.md"
        # Stale content for the others remains intact.
        assert (agents_dir / "cortex-code-explorer.md").read_text(encoding="utf-8") == "STALE explorer"

    def test_inject_profiles_invokes_sync_by_default(self, tmp_path: Path, monkeypatch) -> None:
        """``inject_profiles(sync_canonical=True)`` (the default) must
        call ``sync_canonical_subagents`` before copying the bundle. We
        patch the method to a no-op spy so the test never touches the
        real bundle on disk."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        adapter = get_adapter("pi")
        calls: list[Path] = []

        def spy(self_: object, root: Path, **_: object) -> list[Path]:
            calls.append(root)
            return []

        monkeypatch.setattr(type(adapter), "sync_canonical_subagents", spy)
        # Also stop inject_profiles from copying the real bundle into tmp_path.
        monkeypatch.setattr("cortex.ide.adapters.pi._default_pi_bundle_dir", lambda: tmp_path / "noop-bundle")
        (tmp_path / "noop-bundle").mkdir()

        adapter.inject_profiles(project_root)

        assert calls == [project_root]

    def test_inject_profiles_skips_sync_when_disabled(self, tmp_path: Path, monkeypatch) -> None:
        """``sync_canonical=False`` reproduces the previous behavior
        (raw bundle copy) — useful for regression / snapshot testing."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        adapter = get_adapter("pi")
        calls: list[Path] = []

        def spy(self_: object, root: Path, **_: object) -> list[Path]:
            calls.append(root)
            return []

        monkeypatch.setattr(type(adapter), "sync_canonical_subagents", spy)
        monkeypatch.setattr("cortex.ide.adapters.pi._default_pi_bundle_dir", lambda: tmp_path / "noop-bundle")
        (tmp_path / "noop-bundle").mkdir()

        adapter.inject_profiles(project_root, sync_canonical=False)

        assert calls == []  # sync was skipped


def test_windsurf_adapter_writes_agents_md(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    monkeypatch.setattr("cortex.ide.adapters.windsurf.Path.home", staticmethod(lambda: tmp_path))

    adapter = get_adapter("windsurf")
    prompts = {"cortex-sync": "sync", "cortex-SDDwork": "work"}
    files = adapter.inject_profiles(project_root, prompts)
    files.extend(adapter.inject_mcp(project_root))

    agents_path = project_root / "AGENTS.md"
    mcp_path = tmp_path / ".codeium" / "windsurf" / "mcp_config.json"

    assert agents_path.exists()
    assert mcp_path.exists()
    assert str(agents_path) in files
    assert "cortex_save_session" in agents_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Tripartita Refinada — Plan 07 §2: smoke cross-IDE
# ---------------------------------------------------------------------------


import pytest


class TestTripartitaCrossIDE:
    """Plan 07 §2 — single parametrized test that asserts the same
    Tripartita Refinada markers reach the materialized files for the
    three IDEs that share the canonical-from-disk pattern (Claude Code,
    OpenCode, Codex). Pi has its own coverage in ``TestPiSyncCanonicalSubagents``
    plus the bundle-content test below, because Pi materializes from a
    bundle instead of straight from ``.cortex/subagents/``.
    """

    # Decision firmada (2026-05-15): Codex NO esta en este parametrizado
    # porque NO genera ``.codex/agents/`` (no soporta subagents). El flujo
    # tripartito en Codex se valida en TestCodexTripartitaRefinada
    # (AGENTS.md en project root con flujo secuencial).
    _MARKERS_PER_IDE = {
        "claude_code": {
            "agents/cortex-documenter.md": [
                "HIGH-SIGNAL DOCUMENTATION MODE",
                "VERIFICATION GATE",
                "Modo Handoff",
                "3 criterios",
                "Anti-rationalization",
                "Contrato de Salida",
            ],
            # CLAUDE.md is at project root, not under .claude/agents/
            "_top_level_governance": [
                "Verification Gate",
                "cortex_validate_handoff",
                "CONTEXT.md",
            ],
        },
    }

    def _setup_canonical(self, project_root: Path) -> None:
        """Synthetic canonical that contains every marker we plan to assert."""
        subagents = project_root / ".cortex" / "subagents"
        subagents.mkdir(parents=True)
        documenter_body = (
            "---\nname: cortex-documenter\ndescription: documenter\n---\n\n"
            "# HIGH-SIGNAL DOCUMENTATION MODE\n\n"
            "## Criterios para crear un ADR (3 criterios)\n...\n\n"
            "## VERIFICATION GATE\n...\n\n"
            "## Modo Handoff\n...\n\n"
            "## Anti-rationalization\n...\n\n"
            "## Contrato de Salida\n```yaml\nagent: cortex-documenter\n```\n"
        )
        for name in ("cortex-code-explorer", "cortex-code-implementer"):
            (subagents / f"{name}.md").write_text(
                f"---\nname: {name}\ndescription: x\n---\n\n## Anti-rationalization\n## Contrato de Salida\n",
                encoding="utf-8",
            )
        (subagents / "cortex-documenter.md").write_text(documenter_body, encoding="utf-8")

    @pytest.mark.parametrize("ide_name", ["claude_code"])
    def test_documenter_inherits_full_marker_set(self, ide_name: str, tmp_path: Path) -> None:
        """The documenter agent must receive ALL Plan 01 markers from
        the canonical, regardless of which IDE adapter is rendering it.

        Decision firmada: codex se removio del parametrizado porque NO
        genera ``.codex/agents/`` (no soporta subagents personalizados).
        """
        project_root = tmp_path / "project"
        self._setup_canonical(project_root)
        adapter = get_adapter(ide_name)
        adapter.inject_profiles(
            project_root,
            prompts={
                "cortex-sync": "---\nname: cortex-sync\n---\n\nx",
                "cortex-SDDwork": "---\nname: cortex-SDDwork\n---\n\ny",
            },
        )

        # Each IDE materializes the documenter under its own directory.
        ide_dir = {"claude_code": ".claude"}[ide_name]
        documenter = (
            project_root / ide_dir / "agents" / "cortex-documenter.md"
        ).read_text(encoding="utf-8")

        for marker in self._MARKERS_PER_IDE[ide_name]["agents/cortex-documenter.md"]:
            assert marker in documenter, (
                f"[{ide_name}] documenter missing marker: {marker!r}"
            )

    @pytest.mark.parametrize("ide_name", ["claude_code"])
    def test_top_level_governance_mentions_tripartita(self, ide_name: str, tmp_path: Path) -> None:
        """CLAUDE.md (Claude Code) must mention the Tripartita Refinada
        contracts. Codex tiene su test propio en TestCodexTripartitaRefinada
        (AGENTS.md en project root).
        """
        project_root = tmp_path / "project"
        self._setup_canonical(project_root)
        adapter = get_adapter(ide_name)
        adapter.inject_profiles(
            project_root,
            prompts={
                "cortex-sync": "---\nname: cortex-sync\n---\n\nx",
                "cortex-SDDwork": "---\nname: cortex-SDDwork\n---\n\ny",
            },
        )

        path_per_ide = {
            "claude_code": project_root / "CLAUDE.md",
        }[ide_name]
        content = path_per_ide.read_text(encoding="utf-8")

        for marker in self._MARKERS_PER_IDE[ide_name]["_top_level_governance"]:
            assert marker in content, (
                f"[{ide_name}] top-level governance missing marker: {marker!r}"
            )


class TestPiBundleHasTripartitaRefinada:
    """Plan 07 §2 (Pi-specific) — the in-tree Pi bundle at
    ``cortex-pi/.pi/`` must already contain the Tripartita Refinada
    markers in its 4 Pi-only agents (sync, SDDwork, security-auditor,
    test-verifier), the agent-chain.yaml validation hooks, the damage
    control rules, and the cortex-vault skill awareness section.

    These markers were added by Plan 05. This test guards against
    accidental rollback that would silently ship adopters with the old
    bundle when they run ``cortex inject --ide pi``.
    """

    @pytest.fixture(scope="class")
    def bundle_dir(self) -> Path:
        # tests/unit/test_ide_adapters.py → repo root is 3 parents up.
        return Path(__file__).resolve().parents[2] / "cortex-pi" / ".pi"

    def test_pi_only_agents_have_contrato_de_salida(self, bundle_dir: Path) -> None:
        """Each of the 4 Pi-only agents must have the Tripartita Refinada
        Contrato de Salida YAML section."""
        for agent in (
            "cortex-sync",
            "cortex-SDDwork",
            "cortex-security-auditor",
            "cortex-test-verifier",
        ):
            content = (bundle_dir / "agents" / f"{agent}.md").read_text(encoding="utf-8")
            assert "Contrato de Salida" in content, agent
            assert "AgentHandoff" in content or "agent: cortex-" in content, agent

    def test_sddwork_has_validation_de_handoffs(self, bundle_dir: Path) -> None:
        content = (bundle_dir / "agents" / "cortex-SDDwork.md").read_text(encoding="utf-8")
        assert "Validación de handoffs" in content
        assert "cortex_validate_handoff" in content
        assert "expected_agent" in content

    def test_sync_has_pre_flight_context_md(self, bundle_dir: Path) -> None:
        content = (bundle_dir / "agents" / "cortex-sync.md").read_text(encoding="utf-8")
        assert "Pre-flight" in content
        assert "CONTEXT.md" in content

    def test_agent_chain_has_validation_hooks(self, bundle_dir: Path) -> None:
        content = (bundle_dir / "agents" / "agent-chain.yaml").read_text(encoding="utf-8")
        assert "validate_handoff:" in content
        assert "expected_input_agent:" in content
        # All 3 chains must declare the keys.
        for chain in ("sddwork:", "hotfix:", "refactor:"):
            assert chain in content

    def test_damage_control_has_handoff_rules(self, bundle_dir: Path) -> None:
        content = (bundle_dir / "damage-control-rules.yaml").read_text(encoding="utf-8")
        assert "handoffRules" in content
        assert "handoff-malformed" in content
        assert "severity: block" in content

    def test_cortex_vault_skill_has_context_awareness(self, bundle_dir: Path) -> None:
        content = (bundle_dir / "skills" / "cortex-vault" / "SKILL.md").read_text(encoding="utf-8")
        assert "CONTEXT.md awareness" in content
        assert "verified" in content.lower() and "asserted" in content.lower()


def test_registry_accepts_common_aliases() -> None:
    assert get_adapter("claude").name == "claude_code"
    assert get_adapter("claude-desktop").name == "claude_desktop"
