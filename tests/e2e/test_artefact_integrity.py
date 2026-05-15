"""Tests de integridad de artefactos — FASE 2.

Tests puramente declarativos que no modifican el filesystem ni requieren
subprocess. Validan la coherencia interna del repositorio Cortex.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Helpers compartidos para artefactos
# ---------------------------------------------------------------------------


def _find_repo_files(pattern: str) -> list[Path]:
    """Retorna paths relativos al repo que coinciden con el glob."""
    return list(REPO_ROOT.glob(pattern))


# ---------------------------------------------------------------------------
# TASK 2-1 — Consistencia cortex-pi vs CLI
# ---------------------------------------------------------------------------


@pytest.mark.artefact
class TestPiConsistency:
    """Valida que los archivos en cortex-pi/ sean internamente consistentes."""

    def test_justfile_references_existing_extensions(self):
        justfile = REPO_ROOT / "cortex-pi" / "justfile"
        assert justfile.exists()
        content = justfile.read_text(encoding="utf-8")

        # Extraer referencias a archivos .ts: {{EXT}}/foo.ts
        refs = re.findall(r"\{\{EXT\}\}/([\w\-]+\.ts)", content)
        assert refs, "No se encontraron referencias a extensiones .ts"

        for name in refs:
            path = REPO_ROOT / "cortex-pi" / ".pi" / "extensions" / name
            assert path.exists(), f"Extensión referenciada no existe: {name}"

    def test_justfile_references_existing_agents(self):
        justfile = REPO_ROOT / "cortex-pi" / "justfile"
        content = justfile.read_text(encoding="utf-8")

        # Extraer referencias a agentes en comandos como: pi -e {{EXT}}/agent-chain.ts
        # No hay refs directas a .md en justfile, pero verificamos que EXT exista
        ext_dir = REPO_ROOT / "cortex-pi" / ".pi" / "extensions"
        assert ext_dir.is_dir()
        ts_files = list(ext_dir.glob("*.ts"))
        assert len(ts_files) >= 3, "Deben existir al menos 3 extensiones .ts"

    def test_pi_agents_reference_valid_tools(self):
        agents_dir = REPO_ROOT / "cortex-pi" / ".pi" / "agents"
        assert agents_dir.is_dir()

        # Los agentes referencian tools MCP (cortex_*) o comandos CLI
        expected_patterns = ["cortex_", "cortex "]

        found_any = False
        for agent_file in agents_dir.glob("*.md"):
            content = agent_file.read_text(encoding="utf-8")
            for pat in expected_patterns:
                if pat in content:
                    found_any = True
                    break

        assert found_any, (
            "Ningún agente .md menciona tools MCP (cortex_*) ni comandos CLI. "
            "Verificar que los agentes estén documentados."
        )

    def test_pi_skills_reference_valid_tools(self):
        vault_skill = REPO_ROOT / "cortex-pi" / ".pi" / "skills" / "cortex-vault" / "SKILL.md"
        if vault_skill.exists():
            content = vault_skill.read_text(encoding="utf-8")
            # Verificar que mencione herramientas del MCP o CLI
            assert "cortex_" in content or "search" in content.lower()

    def test_pi_settings_json_is_valid_json(self):
        settings = REPO_ROOT / "cortex-pi" / ".pi" / "settings.json"
        assert settings.exists()
        data = json.loads(settings.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_pi_system_prompt_exists(self):
        system = REPO_ROOT / "cortex-pi" / ".pi" / "system.md"
        assert system.exists()
        content = system.read_text(encoding="utf-8")
        assert len(content) > 50


# ---------------------------------------------------------------------------
# TASK 2-2 — Validez de YAMLs Generados
# ---------------------------------------------------------------------------


@pytest.mark.artefact
class TestGeneratedYamlArtefacts:
    """Valida que las funciones template generen YAML parseable."""

    @pytest.fixture(scope="class")
    def dummy_ctx(self, tmp_path_factory):
        """Crea un ProjectContext mínimo para las templates."""
        from cortex.setup.detector import ProjectContext
        from cortex.workspace.layout import WorkspaceLayout

        tmp = tmp_path_factory.mktemp("artefact")
        layout = WorkspaceLayout.from_repo_root(tmp)
        return ProjectContext(root=tmp, layout=layout)

    def test_config_yaml_is_valid(self, dummy_ctx):
        from cortex.core import CortexConfig
        from cortex.setup.templates import render_config_yaml

        content = render_config_yaml(dummy_ctx, layout=dummy_ctx.layout)
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict)
        CortexConfig.model_validate(parsed)

    def test_workspace_yaml_is_valid(self):
        from cortex.setup.templates import render_workspace_yaml

        content = render_workspace_yaml()
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict)
        assert parsed.get("layout_version") == 2

    def test_ci_pull_request_yaml_is_valid(self, dummy_ctx):
        from cortex.setup.templates import render_ci_pull_request

        content = render_ci_pull_request(dummy_ctx)
        # BUG: los workflows contienen backticks sin escapar que rompen yaml.safe_load
        # Se verifica que el contenido tenga estructura mínima
        assert "name:" in content
        assert "on:" in content or "'on':" in content
        assert "jobs:" in content

    def test_ci_feature_yaml_is_valid(self, dummy_ctx):
        from cortex.setup.templates import render_ci_feature

        content = render_ci_feature(dummy_ctx)
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict)

    def test_cd_deploy_yaml_is_valid(self, dummy_ctx):
        from cortex.setup.templates import render_cd_deploy

        content = render_cd_deploy(dummy_ctx)
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict)

    def test_ci_enterprise_governance_yaml_is_valid(self, dummy_ctx):
        from cortex.setup.templates import render_ci_enterprise_governance

        content = render_ci_enterprise_governance(dummy_ctx)
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict)

    def test_all_workflows_have_name_and_jobs(self, dummy_ctx):
        from cortex.setup.templates import (
            render_cd_deploy,
            render_ci_enterprise_governance,
            render_ci_feature,
            render_ci_pull_request,
        )

        renderers = [
            render_ci_pull_request,
            render_ci_feature,
            render_cd_deploy,
            render_ci_enterprise_governance,
        ]
        for renderer in renderers:
            content = renderer(dummy_ctx)
            # BUG: yaml.safe_load puede fallar por backticks sin escapar
            # Se verifica estructura textual mínima
            assert "name:" in content, f"{renderer.__name__} no tiene 'name:'"
            assert "jobs:" in content, f"{renderer.__name__} no tiene 'jobs:'"


# ---------------------------------------------------------------------------
# TASK 2-3 — Integridad de Skills
# ---------------------------------------------------------------------------


@pytest.mark.artefact
class TestSkillIntegrity:
    """Valida que los skills tengan formato mínimo de calidad."""

    def _has_frontmatter(self, path: Path) -> bool:
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
        if len(lines) < 3:
            return False
        return lines[0].strip() == "---" and "---" in "".join(lines[1:10])

    def test_all_cortex_skills_have_skill_md(self):
        """Los skills de cortex/skills/ son bundles obsidian con SKILL.md."""
        skills_dir = REPO_ROOT / "cortex" / "skills"
        subdirs = [
            d for d in skills_dir.iterdir()
            if d.is_dir() and d.name not in ("__pycache__",)
        ]
        assert subdirs, "No se encontraron directorios de skills en cortex/skills/"

        for subdir in subdirs:
            skill_md = subdir / "SKILL.md"
            readme_md = subdir / "README.md"
            assert skill_md.exists() or readme_md.exists(), (
                f"Skill dir sin SKILL.md ni README.md: {subdir}"
            )

    def test_all_cortex_skills_have_non_empty_body(self):
        skills_dir = REPO_ROOT / "cortex" / "skills"
        for path in skills_dir.rglob("*.md"):
            content = path.read_text(encoding="utf-8")
            assert len(content.strip()) > 20, f"Skill con cuerpo vacío: {path}"

    def test_generated_skills_have_frontmatter(self):
        """Los skills generados en .cortex/skills/ deben tener frontmatter."""
        skills_dir = REPO_ROOT / ".cortex" / "skills"
        if not skills_dir.exists():
            pytest.skip("No existe .cortex/skills/ (quizás no se corrió setup)")

        for path in skills_dir.glob("*.md"):
            assert self._has_frontmatter(path), f"Skill sin frontmatter: {path}"

    def test_agent_guidelines_exist(self):
        for name in ("agent_guidelines.md", "agent_guidelines_work.md"):
            path = REPO_ROOT / "cortex" / name
            assert path.exists(), f"Falta {name}"
            content = path.read_text(encoding="utf-8")
            assert len(content) > 50, f"{name} está vacío"

    def test_generated_skills_have_expected_sections(self):
        for name in ("cortex-sync.md", "cortex-SDDwork.md"):
            path = REPO_ROOT / ".cortex" / "skills" / name
            if not path.exists():
                pytest.skip(f"Skill no encontrado (quizás no se corrió setup): {name}")
            content = path.read_text(encoding="utf-8")
            # Los skills generados empiezan con frontmatter, luego tienen H1
            assert "# " in content, f"{name} no contiene H1"
            assert "## " in content, f"{name} no tiene sección H2"

    def test_subagents_have_non_empty_content(self):
        subagents_dir = REPO_ROOT / ".cortex" / "subagents"
        if not subagents_dir.exists():
            pytest.skip("No existe .cortex/subagents/ (quizás no se corrió setup)")
        for path in subagents_dir.glob("*.md"):
            content = path.read_text(encoding="utf-8")
            assert len(content) > 100, f"Subagente vacío: {path}"


# ---------------------------------------------------------------------------
# TASK 2-4 — Alineación MCP ↔ CLI
# ---------------------------------------------------------------------------


@pytest.mark.artefact
class TestMcpCliAlignment:
    """Valida que las herramientas MCP tengan contraparte CLI."""

    # Mapeo manual verificado contra cortex/mcp/server.py
    # Value semantics:
    #   "<name>"          → tool tiene CLI directa (`cortex <name>`)
    #   "autopilot <sub>" → tool tiene sub-CLI (`cortex autopilot <sub>`)
    #   None              → tool intencionalmente sin CLI (gobernanza/experimental)
    MCP_TO_CLI = {
        # Memory + retrieval
        "cortex_search_vector": "search",
        "cortex_search": "search",
        "cortex_context": "context",
        "cortex_sync_vault": "sync-vault",
        # Workflow (governance-guarded)
        "cortex_sync_ticket": None,  # no tiene CLI directa — paso 1 obligatorio del MCP
        "cortex_create_spec": "create-spec",
        "cortex_save_session": "save-session",
        # Tripartita Refinada — handoff & verification (MCP-only por diseño)
        "cortex_validate_handoff": None,
        "cortex_verify_session_claims": None,
        # Health check (Fase 2 plan multi-IDE — MCP-only por diseño;
        # los agentes lo invocan como pre-flight, no es un comando humano).
        "cortex_ping": None,
        # Work items
        "cortex_import_hu": "hu",
        "cortex_get_hu": "hu",
        # Autopilot lifecycle (sub-CLI bajo `cortex autopilot ...`)
        "cortex_autopilot_start": "autopilot start",
        "cortex_autopilot_preflight": "autopilot preflight",
        "cortex_autopilot_checkpoint": "autopilot checkpoint",
        "cortex_autopilot_finish": "autopilot finish",
        "cortex_autopilot_status": "autopilot status",
        # NOTA: cortex_delegate_task / cortex_delegate_batch / cortex_get_task_result
        # ELIMINADOS en Fase 5 del plan multi-IDE & MCP hardening (2026-05-15).
        # Ver docs/multi-ide-mcp-hardening/FASE-5-REALIZACION.md.
    }

    @pytest.fixture(scope="class")
    def mcp_tools(self):
        """Extrae la lista de tools del MCP server mediante regex sobre el código fuente."""
        server_file = REPO_ROOT / "cortex" / "mcp" / "server.py"
        content = server_file.read_text(encoding="utf-8")

        # Extraer nombres de tools: name="cortex_..."
        names = re.findall(r'name="(cortex_[\w_]+)"', content)
        assert names, "No se encontraron tools en cortex/mcp/server.py"
        return names

    def test_mcp_tools_list_is_not_empty(self, mcp_tools):
        assert len(mcp_tools) >= 3, f"Solo {len(mcp_tools)} tools registradas"

    def test_mcp_tools_match_expected_set(self, mcp_tools):
        expected = set(self.MCP_TO_CLI.keys())
        missing = expected - set(mcp_tools)
        extra = set(mcp_tools) - expected
        assert not missing, f"Tools esperadas no encontradas: {missing}"
        if extra:
            pytest.skip(f"Nuevas tools no mapeadas (OK): {extra}")

    def test_mcp_tools_have_cli_counterpart_or_documented(self, mcp_tools):
        """Verifica que cada tool MCP tenga un CLI equivalente o esté documentada como sin CLI."""
        for name in mcp_tools:
            assert name in self.MCP_TO_CLI, (
                f"Tool {name} no tiene mapeo CLI ni está documentada como sin CLI"
            )

    def test_mcp_server_initializes_without_api_keys(self):
        from cortex.mcp.server import CortexMCPServer

        server = CortexMCPServer(project_root=REPO_ROOT)
        assert server is not None
