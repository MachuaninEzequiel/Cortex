"""E2E pytest fixtures — neutrales, sin autouse de instalación.

Las fixtures definidas aquí son útiles para TODOS los tests de tests/e2e/,
incluyendo los tests de artefactos (FASE 2) que NO necesitan que cortex
esté instalado. Por eso, `cortex_install` es NO-autouse.

Para activar la verificación de instalación automáticamente en los tests de
escenarios, ver tests/e2e/scenarios/conftest.py.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import MockEmbedder

# ---------------------------------------------------------------------------
# Mock embedder (reutilizado desde tests.conftest para evitar divergencia)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mock_embedder_session() -> MockEmbedder:
    """Reutiliza el MockEmbedder determinista de tests/conftest.py."""
    return MockEmbedder()


# ---------------------------------------------------------------------------
# Directorio de proyecto E2E aislado
# ---------------------------------------------------------------------------


@pytest.fixture
def e2e_project_dir(tmp_path: Path, monkeypatch) -> Path:
    """Crea un directorio de proyecto temporal para tests E2E.

    - Setea CORTEX_ENV=sandbox para evitar que Cortex descubiera
      configuraciones del repo padre.
    - Cambia el working dir al proyecto.
    """
    project = tmp_path / "project"
    project.mkdir(parents=True)
    monkeypatch.setenv("CORTEX_ENV", "sandbox")
    monkeypatch.chdir(project)
    return project


# ---------------------------------------------------------------------------
# Repo Git aislado
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_git_repo(e2e_project_dir: Path) -> Path:
    """Inicializa un repo Git en el directorio de proyecto E2E.

    Crea un commit vacío inicial para que --git-depth N no falle.
    """
    subprocess.run(
        ["git", "init"],
        cwd=e2e_project_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=e2e_project_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=e2e_project_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=e2e_project_dir,
        check=True,
        capture_output=True,
    )
    return e2e_project_dir


# ---------------------------------------------------------------------------
# Verificación de instalación de cortex (NON-AUTOUSE)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def cortex_install() -> None:
    """Verifica que `cortex` esté instalado y funcione.

    Es NON-AUTOUSE porque los tests de artefactos (FASE 2) no necesitan
    cortex instalado. Los tests que ejecuten subprocess deben declararla
    explícitamente o heredar el autouse de scenarios/conftest.py.

    Si cortex no está disponible, saltea el test limpiamente.
    """
    for cmd in (
        ["cortex", "--help"],
        [sys.executable, "-m", "cortex.cli.main", "--help"],
    ):
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=10)
            return  # instalación confirmada
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    pytest.skip("cortex not installed (neither binary nor module)")
