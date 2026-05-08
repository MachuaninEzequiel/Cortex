"""Tests E2E: setup agent + doctor (TASK 1-2)."""
from __future__ import annotations

import pytest

from tests.e2e.helpers import (
    assert_valid_config_yaml,
    run_cortex,
)


@pytest.mark.e2e
class TestSetupBasic:
    """Valida `cortex setup agent --git-depth 5 --ide pi` en proyecto vacío."""

    def test_agent_setup_creates_workspace(self, e2e_project_dir):
        result = run_cortex(
            e2e_project_dir,
            "setup", "agent", "--git-depth", "5", "--ide", "pi",
        )
        assert result.returncode == 0, result.stderr

        cortex = e2e_project_dir / ".cortex"
        assert cortex.is_dir()
        assert (cortex / "config.yaml").exists()
        assert (cortex / "workspace.yaml").exists()
        assert (cortex / "AGENT.md").exists()
        assert (cortex / "vault").is_dir()
        assert (cortex / "skills").is_dir()
        assert (cortex / "subagents").is_dir()

        # workspace.yaml debe tener layout_version: 2
        ws_yaml = (cortex / "workspace.yaml").read_text(encoding="utf-8")
        assert "layout_version: 2" in ws_yaml

        # config.yaml debe ser Pydantic-válido
        assert_valid_config_yaml(cortex / "config.yaml")

    def test_doctor_passes_after_agent_setup(self, isolated_git_repo):
        run_cortex(
            isolated_git_repo,
            "setup", "agent", "--git-depth", "5", "--ide", "pi",
        )
        # Doctor requiere .gitignore con patrones de Cortex
        (isolated_git_repo / ".gitignore").write_text(
            ".memory/\n*.chroma/\nvault/sessions/\n", encoding="utf-8"
        )
        result = run_cortex(isolated_git_repo, "doctor")
        assert result.returncode == 0, result.stderr
        assert "[OK]" in result.stdout

    def test_doctor_strict_passes_after_agent_setup(self, isolated_git_repo):
        run_cortex(
            isolated_git_repo,
            "setup", "agent", "--git-depth", "5", "--ide", "pi",
        )
        (isolated_git_repo / ".gitignore").write_text(
            ".memory/\n*.chroma/\nvault/sessions/\n", encoding="utf-8"
        )
        result = run_cortex(isolated_git_repo, "doctor", "--strict")
        assert result.returncode == 0, result.stderr

    def test_agent_setup_is_idempotent(self, e2e_project_dir):
        run_cortex(
            e2e_project_dir,
            "setup", "agent", "--git-depth", "5", "--ide", "pi",
        )
        config_before = (e2e_project_dir / ".cortex" / "config.yaml").read_text(
            encoding="utf-8"
        )
        result = run_cortex(
            e2e_project_dir,
            "setup", "agent", "--git-depth", "5", "--ide", "pi",
        )
        assert result.returncode == 0, result.stderr
        config_after = (e2e_project_dir / ".cortex" / "config.yaml").read_text(
            encoding="utf-8"
        )
        assert config_before == config_after, "config.yaml fue sobreescrito"
