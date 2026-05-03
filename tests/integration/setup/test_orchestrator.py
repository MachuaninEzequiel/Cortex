"""
tests.setup.test_orchestrator
-----------------------------
Tests for the setup orchestration system.

EPIC 4: Tests are now layout-aware.  For a brand-new project
the orchestrator writes exclusively inside ``.cortex/`` (new layout).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cortex.setup.orchestrator import SetupOrchestrator, format_summary
from cortex.workspace.layout import WorkspaceLayout


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _new_layout_root(tmp_path: Path) -> Path:
    """Return the expected repo root for a brand-new project.

    Since SetupOrchestrator calls ``WorkspaceLayout.discover()``,
    a brand-new tmp_path (no .cortex/, no config.yaml) will be
    treated as a new-layout project (bootstrap mode in discover).
    """
    return tmp_path


# ------------------------------------------------------------------
# Orchestrator tests (with mocked memory)
# ------------------------------------------------------------------

@pytest.fixture
def orchestrator_no_memory(tmp_path: Path):
    """Create an orchestrator with memory init mocked out."""
    with patch("cortex.core.AgentMemory") as mock_mem:
        mock_instance = MagicMock()
        mock_instance.sync_vault.return_value = 3
        mock_instance.remember.return_value = MagicMock(id="mem_test")
        mock_mem.return_value = mock_instance
        yield SetupOrchestrator(tmp_path)


class TestSetupOrchestrator:
    def test_creates_directories(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        orchestrator_no_memory.run()
        layout = orchestrator_no_memory.layout

        # In new layout, directories live inside .cortex/
        assert layout.is_new_layout
        assert layout.episodic_memory_path.is_dir()
        assert layout.vault_path.is_dir()
        # Subdirectories inside vault
        assert (layout.vault_path / "sessions").is_dir()
        assert (layout.vault_path / "decisions").is_dir()
        assert (layout.vault_path / "runbooks").is_dir()
        assert (layout.vault_path / "hu").is_dir()

    def test_creates_config_yaml(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        orchestrator_no_memory.run()

        layout = orchestrator_no_memory.layout
        config = layout.config_path
        assert config.exists()
        # Content should use new-layout paths
        content = config.read_text(encoding="utf-8")
        assert "persist_dir: memory" in content
        assert "vault_path: vault" in content

    def test_creates_vault_docs(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        orchestrator_no_memory.run()

        layout = orchestrator_no_memory.layout
        assert (layout.vault_path / "architecture.md").exists()
        assert (layout.vault_path / "decisions.md").exists()
        assert (layout.vault_path / "runbooks.md").exists()

    def test_creates_workflows(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        orchestrator_no_memory.run()

        layout = orchestrator_no_memory.layout
        workflows = layout.workflows_dir
        assert (workflows / "ci-pull-request.yml").exists()
        assert (workflows / "ci-feature.yml").exists()
        assert (workflows / "cd-deploy.yml").exists()

    def test_creates_devsecdocops_script(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        orchestrator_no_memory.run()

        layout = orchestrator_no_memory.layout
        script = layout.scripts_dir / "devsecdocops.sh"
        assert script.exists()
        # Check executable permission (POSIX only)
        import os
        if os.name != "nt":
            assert script.stat().st_mode & 0o111

    def test_creates_agent_guidelines(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        orchestrator_no_memory.run()

        guidelines = orchestrator_no_memory.layout.agent_guidelines_path
        assert guidelines.exists()
        content = guidelines.read_text(encoding="utf-8")
        assert "Governance Rules" in content or "Cortex" in content
        assert "document" in content.lower()

    def test_creates_workspace_yaml(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        """EPIC 4: workspace.yaml with layout_version: 2 must be created."""
        orchestrator_no_memory.run()

        layout = orchestrator_no_memory.layout
        ws_yaml = layout.workspace_yaml_path
        assert ws_yaml.exists()
        content = ws_yaml.read_text(encoding="utf-8")
        assert "layout_version: 2" in content

    def test_creates_release2_cortex_workspace(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        orchestrator_no_memory.run()

        root = orchestrator_no_memory.root
        assert (root / ".cortex" / "system-prompt.md").exists()
        assert (root / ".cortex" / "skills" / "cortex-sync.md").exists()
        assert (root / ".cortex" / "skills" / "cortex-SDDwork.md").exists()
        assert (root / ".cortex" / "subagents" / "cortex-documenter.md").exists()

    def test_installs_skills(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        orchestrator_no_memory.run()

        skills_dir = orchestrator_no_memory.layout.skills_dir
        assert (skills_dir / "obsidian-markdown").exists()
        assert (skills_dir / "obsidian-markdown" / "SKILL.md").exists()
        assert (skills_dir / "obsidian-markdown" / "references").exists()
        assert (skills_dir / "json-canvas").exists()
        assert (skills_dir / "obsidian-bases").exists()
        assert (skills_dir / "defuddle").exists()
        assert (skills_dir / "obsidian-cli").exists()

    def test_skips_existing_skills(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        root = orchestrator_no_memory.root
        existing = root / ".cortex" / "skills" / "obsidian-markdown"
        existing.mkdir(parents=True)
        (existing / "SKILL.md").write_text("existing", encoding="utf-8")

        summary = orchestrator_no_memory.run()

        assert any("obsidian-markdown" in s and "already exists" in s for s in summary["skipped"])
        # The existing file should not be overwritten
        assert (existing / "SKILL.md").read_text(encoding="utf-8") == "existing"

    def test_skips_existing_files(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        root = orchestrator_no_memory.root
        # Create layout manually to get paths for pre-creation
        layout = WorkspaceLayout.discover(root)

        # Pre-create .cortex/config.yaml and vault/architecture.md
        config_path = layout.config_path
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("existing: true", encoding="utf-8")

        vault_path = layout.vault_path
        vault_path.mkdir(parents=True, exist_ok=True)
        (vault_path / "architecture.md").write_text("existing", encoding="utf-8")

        summary = orchestrator_no_memory.run()

        assert any("config.yaml" in s and "already exists" in s for s in summary["skipped"])
        assert any("architecture.md" in s and "already exists" in s for s in summary["skipped"])

    def test_does_not_overwrite_existing_workflows(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        root = orchestrator_no_memory.root
        workflows = root / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci-pull-request.yml").write_text("existing", encoding="utf-8")

        summary = orchestrator_no_memory.run()

        assert any("ci-pull-request.yml" in s and "already exists" in s for s in summary["skipped"])

    def test_summary_contains_created_files(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        summary = orchestrator_no_memory.run()

        # In new layout, paths contain .cortex/
        created_str = " ".join(summary["created"])
        assert "config.yaml" in created_str
        assert "architecture.md" in created_str
        assert "devsecdocops.sh" in created_str
        assert "cortex-SDDwork.md" in created_str
        assert "workspace.yaml" in created_str

    def test_summary_has_project_info(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        summary = orchestrator_no_memory.run()

        assert "project_name" in summary
        assert "language" in summary
        assert "created" in summary

    def test_new_layout_structure(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        """EPIC 4: Verify new-layout directory structure."""
        orchestrator_no_memory.run()
        root = orchestrator_no_memory.root

        # All these should live inside .cortex/ in new layout
        assert (root / ".cortex" / "config.yaml").exists()
        assert (root / ".cortex" / "vault").is_dir()
        assert (root / ".cortex" / "memory").is_dir()
        assert (root / ".cortex" / "workspace.yaml").exists()
        assert (root / ".cortex" / "org.yaml").exists()

        # Workflows are ALWAYS at .github/workflows (not inside .cortex/)
        assert (root / ".github" / "workflows" / "ci-pull-request.yml").exists()

        # Scripts inside .cortex/scripts in new layout
        assert (root / ".cortex" / "scripts" / "devsecdocops.sh").exists()


# ------------------------------------------------------------------
# Node.js project setup
# ------------------------------------------------------------------

class TestNodeProjectSetup:
    def test_full_setup_for_node_project(self, tmp_path: Path) -> None:
        # Create a Node.js project
        pkg = {
            "name": "my-node-app",
            "scripts": {"test": "jest", "lint": "eslint ."},
            "dependencies": {"express": "^4.18"},
        }
        (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")

        with patch("cortex.core.AgentMemory") as mock_mem:
            mock_instance = MagicMock()
            mock_instance.sync_vault.return_value = 3
            mock_mem.return_value = mock_instance

            orchestrator = SetupOrchestrator(tmp_path)
            summary = orchestrator.run()

        assert summary["language"] == "javascript"
        assert summary["project_name"] == "my-node-app"
        # In new layout, config lives inside .cortex/
        layout = WorkspaceLayout.discover(tmp_path)
        assert layout.config_path.exists()
        assert layout.vault_path.is_dir() or layout.vault_path.exists()

    def test_config_reflects_node_project(self, tmp_path: Path) -> None:
        pkg = {"name": "test-app"}
        (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")

        with patch("cortex.core.AgentMemory") as mock_mem:
            mock_instance = MagicMock()
            mock_instance.sync_vault.return_value = 3
            mock_mem.return_value = mock_instance

            orchestrator = SetupOrchestrator(tmp_path)
            orchestrator.run()

        layout = WorkspaceLayout.discover(tmp_path)
        config = layout.config_path
        content = config.read_text(encoding="utf-8")
        # Config should exist and contain episodic section
        assert "episodic" in content


# ------------------------------------------------------------------
# format_summary tests (no memory needed)
# ------------------------------------------------------------------

class TestFormatSummary:
    def test_contains_created_files(self) -> None:
        summary = {
            "project_name": "test",
            "language": "python",
            "package_manager": "pip",
            "frameworks": [],
            "ci_detected": "none",
            "created": [".cortex/config.yaml", ".cortex/vault/architecture.md"],
            "skipped": [],
            "warnings": [],
        }
        output = format_summary(summary)

        assert "config.yaml" in output
        assert "architecture.md" in output
        assert "✅ Created" in output

    def test_contains_skipped_files(self) -> None:
        summary = {
            "project_name": "test",
            "language": "python",
            "package_manager": "pip",
            "frameworks": [],
            "ci_detected": "none",
            "created": [],
            "skipped": [".cortex/config.yaml (already exists)"],
            "warnings": [],
        }
        output = format_summary(summary)

        assert "⏭ Skipped" in output
        assert "already exists" in output

    def test_contains_warnings(self) -> None:
        summary = {
            "project_name": "test",
            "language": "python",
            "package_manager": "pip",
            "frameworks": [],
            "ci_detected": "none",
            "created": [],
            "skipped": [],
            "warnings": ["Something went wrong"],
        }
        output = format_summary(summary)

        assert "⚠ Warnings" in output
        assert "Something went wrong" in output

    def test_contains_next_steps(self) -> None:
        summary = {
            "project_name": "test",
            "language": "python",
            "package_manager": "pip",
            "frameworks": [],
            "ci_detected": "none",
            "created": [],
            "skipped": [],
            "warnings": [],
        }
        output = format_summary(summary)

        assert "Next steps" in output
        assert "VS Code" in output