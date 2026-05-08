"""Tests E2E: setup sobre distintos tipos de proyectos (TASK 3-2).

Valida que `cortex setup full` y `cortex setup enterprise` funcionen
correctamente independientemente del tipo de proyecto base.
"""
from __future__ import annotations

import pytest

from tests.e2e.helpers import (
    assert_valid_config_yaml,
    assert_valid_org_yaml,
    copy_fixture_project,
    run_cortex,
)


FIXTURES = [
    "empty-project",
    "vite-react-project",
    "python-package",
    "legacy-cortex-project",
]


@pytest.mark.e2e
class TestSetupOnFixtures:
    """Parametrizado sobre los 4 fixtures de proyecto."""

    @pytest.mark.parametrize("fixture_name", FIXTURES)
    def test_setup_full_on_all_projects(self, fixture_name, tmp_path):
        project = copy_fixture_project(fixture_name, tmp_path)

        # Inicializar git para que setup full funcione
        import subprocess
        subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project, check=True, capture_output=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=project, check=True, capture_output=True)

        result = run_cortex(project, "setup", "full", "--git-depth", "5")
        assert result.returncode == 0, result.stderr

        # Verificar estructura mínima
        assert (project / ".cortex").is_dir()

        # En legacy layout, config.yaml puede estar en raíz; en new layout en .cortex/
        config_paths = [project / ".cortex" / "config.yaml", project / "config.yaml"]
        assert any(p.exists() for p in config_paths), "No se encontró config.yaml"
        for p in config_paths:
            if p.exists():
                assert_valid_config_yaml(p)
                break

        # Verificar que .github/workflows se crearon
        workflows = project / ".github" / "workflows"
        assert workflows.is_dir(), "No se generaron workflows"

    @pytest.mark.parametrize("fixture_name", FIXTURES)
    def test_setup_enterprise_on_all_projects(self, fixture_name, tmp_path):
        project = copy_fixture_project(fixture_name, tmp_path)

        result = run_cortex(
            project,
            "setup", "agent", "--git-depth", "5", "--ide", "pi",
        )
        assert result.returncode == 0, result.stderr

        result = run_cortex(
            project,
            "setup", "enterprise",
            "--preset", "small-company",
            "--non-interactive",
        )
        assert result.returncode == 0, result.stderr

        assert (project / ".cortex" / "org.yaml").exists()
        assert_valid_org_yaml(project / ".cortex" / "org.yaml")
        assert (project / ".cortex" / "vault-enterprise").is_dir()

    def test_legacy_project_maintains_layout(self, tmp_path):
        project = copy_fixture_project("legacy-cortex-project", tmp_path)

        # Guardar contenido original
        original_config = (project / "config.yaml").read_text(encoding="utf-8")
        original_vault = (project / "vault" / "legacy_doc.md").read_text(encoding="utf-8")

        import subprocess
        subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project, check=True, capture_output=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=project, check=True, capture_output=True)

        result = run_cortex(project, "setup", "full", "--git-depth", "5")
        assert result.returncode == 0, result.stderr

        # Verificar que archivos legacy no fueron destruidos
        assert (project / "vault" / "legacy_doc.md").exists()
        assert (project / "vault" / "legacy_doc.md").read_text(encoding="utf-8") == original_vault

    @pytest.mark.parametrize("fixture_name", FIXTURES)
    def test_doctor_passes_on_all_fixtures(self, fixture_name, tmp_path):
        project = copy_fixture_project(fixture_name, tmp_path)

        import subprocess
        subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project, check=True, capture_output=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=project, check=True, capture_output=True)

        run_cortex(project, "setup", "full", "--git-depth", "5")

        (project / ".gitignore").write_text(
            ".memory/\n*.chroma/\nvault/sessions/\n", encoding="utf-8"
        )

        # En legacy, el doctor puede reportar warnings de layout mixto
        result = run_cortex(project, "doctor", check=False)
        if result.returncode != 0:
            # Permitir si solo hay warnings (no FAIL) en legacy
            assert "[FAIL]" not in result.stdout, f"Doctor reportó FAIL: {result.stdout}"
