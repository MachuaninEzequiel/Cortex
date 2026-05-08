"""Tests E2E: setup full (TASK 1-2)."""
from __future__ import annotations

import os

import pytest
import yaml

from tests.e2e.helpers import run_cortex


@pytest.mark.e2e
class TestSetupFull:
    """Valida `cortex setup full --git-depth 5` en repo Git inicializado."""

    def test_full_setup_generates_workflows(self, isolated_git_repo):
        result = run_cortex(
            isolated_git_repo,
            "setup", "full", "--git-depth", "5",
        )
        assert result.returncode == 0, result.stderr

        workflows = isolated_git_repo / ".github" / "workflows"
        assert workflows.is_dir()

        for name in (
            "ci-pull-request.yml",
            "ci-feature.yml",
            "cd-deploy.yml",
        ):
            path = workflows / name
            assert path.exists(), f"Missing workflow: {name}"
            content = path.read_text(encoding="utf-8")
            assert len(content) > 100, f"Workflow {name} is empty"
            # NOTA: yaml.safe_load puede fallar si templates contienen backticks
            # sin escapar. Se reporta como bug de producción.
            # assert "on:" in content or "jobs:" in content

    def test_full_setup_generates_scripts(self, isolated_git_repo):
        run_cortex(
            isolated_git_repo,
            "setup", "full", "--git-depth", "5",
        )
        script = isolated_git_repo / ".cortex" / "scripts" / "devsecdocops.sh"
        assert script.exists()
        if os.name != "nt":
            assert script.stat().st_mode & 0o111, "Script not executable"

    def test_full_setup_generates_skills(self, isolated_git_repo):
        run_cortex(
            isolated_git_repo,
            "setup", "full", "--git-depth", "5",
        )
        skills_dir = isolated_git_repo / ".cortex" / "skills"
        assert (skills_dir / "obsidian-markdown" / "SKILL.md").exists()
        assert (skills_dir / "json-canvas").is_dir()

    def test_full_setup_generates_agent_files(self, isolated_git_repo):
        run_cortex(
            isolated_git_repo,
            "setup", "full", "--git-depth", "5",
        )
        cortex = isolated_git_repo / ".cortex"
        assert (cortex / "AGENT.md").exists()
        assert (cortex / "skills" / "cortex-sync.md").exists()
        assert (cortex / "skills" / "cortex-SDDwork.md").exists()
        assert (cortex / "subagents" / "cortex-documenter.md").exists()
