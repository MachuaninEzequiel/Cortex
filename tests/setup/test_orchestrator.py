"""
tests.setup.test_orchestrator
-----------------------------
Tests for the setup orchestration system.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cortex.setup.orchestrator import SetupOrchestrator, format_summary

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

        assert (orchestrator_no_memory.root / ".memory").is_dir()
        assert (orchestrator_no_memory.root / "vault").is_dir()

    def test_creates_config_yaml(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        orchestrator_no_memory.run()

        config = orchestrator_no_memory.root / "config.yaml"
        assert config.exists()

    def test_creates_vault_docs(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        orchestrator_no_memory.run()

        assert (orchestrator_no_memory.root / "vault" / "architecture.md").exists()
        assert (orchestrator_no_memory.root / "vault" / "decisions.md").exists()
        assert (orchestrator_no_memory.root / "vault" / "runbooks.md").exists()

    def test_creates_workflows(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        orchestrator_no_memory.run()

        workflows = orchestrator_no_memory.root / ".github" / "workflows"
        assert (workflows / "ci-pull-request.yml").exists()
        assert (workflows / "ci-feature.yml").exists()
        assert (workflows / "cd-deploy.yml").exists()

    def test_creates_devsecdocops_script(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        orchestrator_no_memory.run()

        script = orchestrator_no_memory.root / "scripts" / "devsecdocops.sh"
        assert script.exists()
        # Check executable permission (POSIX only)
        import os
        if os.name != "nt":
            assert script.stat().st_mode & 0o111

    def test_creates_agent_guidelines(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        orchestrator_no_memory.run()

        guidelines = orchestrator_no_memory.root / ".cortex" / "AGENT.md"
        assert guidelines.exists()
        content = guidelines.read_text(encoding="utf-8")
        assert "Governance Rules" in content or "Cortex Agent" in content
        assert "document" in content.lower()

    def test_installs_skills(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        orchestrator_no_memory.run()

        skills_dir = orchestrator_no_memory.root / ".qwen" / "skills"
        assert (skills_dir / "obsidian-markdown").exists()
        assert (skills_dir / "obsidian-markdown" / "SKILL.md").exists()
        assert (skills_dir / "obsidian-markdown" / "references").exists()
        assert (skills_dir / "json-canvas").exists()
        assert (skills_dir / "obsidian-bases").exists()
        assert (skills_dir / "defuddle").exists()
        assert (skills_dir / "obsidian-cli").exists()

    def test_skips_existing_skills(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        root = orchestrator_no_memory.root
        existing = root / ".qwen" / "skills" / "obsidian-markdown"
        existing.mkdir(parents=True)
        (existing / "SKILL.md").write_text("existing", encoding="utf-8")

        summary = orchestrator_no_memory.run()

        assert any("obsidian-markdown" in s and "already exists" in s for s in summary["skipped"])
        # The existing file should not be overwritten
        assert (existing / "SKILL.md").read_text(encoding="utf-8") == "existing"

    def test_skips_existing_files(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        root = orchestrator_no_memory.root
        # Create existing files
        (root / "config.yaml").write_text("existing: true", encoding="utf-8")
        (root / "vault").mkdir()
        (root / "vault" / "architecture.md").write_text("existing", encoding="utf-8")

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

        assert "config.yaml" in summary["created"]
        assert "vault/architecture.md" in summary["created"]
        assert "scripts/devsecdocops.sh" in summary["created"]

    def test_summary_has_project_info(self, orchestrator_no_memory: SetupOrchestrator) -> None:
        summary = orchestrator_no_memory.run()

        assert "project_name" in summary
        assert "language" in summary
        assert "created" in summary


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
        assert (tmp_path / "config.yaml").exists()
        assert (tmp_path / "vault" / "architecture.md").exists()

    def test_config_reflects_node_project(self, tmp_path: Path) -> None:
        pkg = {"name": "test-app"}
        (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")

        with patch("cortex.core.AgentMemory") as mock_mem:
            mock_instance = MagicMock()
            mock_instance.sync_vault.return_value = 3
            mock_mem.return_value = mock_instance

            orchestrator = SetupOrchestrator(tmp_path)
            orchestrator.run()

        config = tmp_path / "config.yaml"
        content = config.read_text(encoding="utf-8")
        # Config should exist and be valid
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
            "created": ["config.yaml", "vault/architecture.md"],
            "skipped": [],
            "warnings": [],
        }
        output = format_summary(summary)

        assert "config.yaml" in output
        assert "vault/architecture.md" in output
        assert "✅ Created" in output

    def test_contains_skipped_files(self) -> None:
        summary = {
            "project_name": "test",
            "language": "python",
            "package_manager": "pip",
            "frameworks": [],
            "ci_detected": "none",
            "created": [],
            "skipped": ["config.yaml (already exists)"],
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
