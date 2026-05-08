"""Tests E2E: setup enterprise non-interactive (TASK 1-4)."""
from __future__ import annotations

import json

import pytest

from tests.e2e.helpers import (
    assert_valid_org_yaml,
    run_cortex,
)


@pytest.mark.e2e
class TestEnterpriseSetup:
    """Valida setup enterprise --preset X --non-interactive."""

    def _setup_base(self, project_dir):
        run_cortex(
            project_dir,
            "setup", "agent", "--git-depth", "5", "--ide", "pi",
        )

    def test_enterprise_setup_small_company(self, e2e_project_dir):
        self._setup_base(e2e_project_dir)
        result = run_cortex(
            e2e_project_dir,
            "setup", "enterprise",
            "--preset", "small-company",
            "--non-interactive",
        )
        assert result.returncode == 0, result.stderr
        assert (e2e_project_dir / ".cortex" / "org.yaml").exists()
        assert_valid_org_yaml(e2e_project_dir / ".cortex" / "org.yaml")
        assert (e2e_project_dir / ".cortex" / "vault-enterprise").is_dir()

    def test_enterprise_setup_multi_project_team(self, e2e_project_dir):
        self._setup_base(e2e_project_dir)
        result = run_cortex(
            e2e_project_dir,
            "setup", "enterprise",
            "--preset", "multi-project-team",
            "--non-interactive",
        )
        assert result.returncode == 0, result.stderr
        org_path = e2e_project_dir / ".cortex" / "org.yaml"
        assert_valid_org_yaml(org_path)
        # Bug 4 corregido: setup enterprise --preset fuerza la escritura del
        # org.yaml con el preset correcto, aunque setup agent haya creado uno
        # previo con small-company.
        import yaml
        org_data = yaml.safe_load(org_path.read_text(encoding="utf-8"))
        assert org_data.get("profile") == "multi-project-team", (
            f"Expected profile 'multi-project-team', got '{org_data.get('profile')}'"
        )

    def test_enterprise_setup_regulated_organization(self, e2e_project_dir):
        self._setup_base(e2e_project_dir)
        result = run_cortex(
            e2e_project_dir,
            "setup", "enterprise",
            "--preset", "regulated-organization",
            "--non-interactive",
        )
        assert result.returncode == 0, result.stderr
        org_path = e2e_project_dir / ".cortex" / "org.yaml"
        assert_valid_org_yaml(org_path)
        # Bug 4 corregido: regulated-organization debe tener branch_isolation_enabled: true
        import yaml
        org_data = yaml.safe_load(org_path.read_text(encoding="utf-8"))
        memory = org_data.get("memory") or {}
        assert memory.get("branch_isolation_enabled") is True, (
            f"Expected branch_isolation_enabled=True for regulated-organization, "
            f"got: {memory.get('branch_isolation_enabled')}"
        )

    def test_memory_report_after_enterprise_setup(self, e2e_project_dir):
        self._setup_base(e2e_project_dir)
        run_cortex(
            e2e_project_dir,
            "setup", "enterprise",
            "--preset", "small-company",
            "--non-interactive",
        )
        result = run_cortex(
            e2e_project_dir,
            "memory-report", "--json",
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert "project_root" in data
        assert "enterprise_enabled" in data
        assert "sources" in data
        assert "promotion" in data

    def test_doctor_enterprise_scope(self, isolated_git_repo):
        self._setup_base(isolated_git_repo)
        run_cortex(
            isolated_git_repo,
            "setup", "enterprise",
            "--preset", "small-company",
            "--non-interactive",
        )
        (isolated_git_repo / ".gitignore").write_text(
            ".memory/\n*.chroma/\nvault/sessions/\n", encoding="utf-8"
        )
        result = run_cortex(
            isolated_git_repo,
            "doctor", "--scope", "enterprise",
        )
        assert result.returncode == 0, result.stderr
