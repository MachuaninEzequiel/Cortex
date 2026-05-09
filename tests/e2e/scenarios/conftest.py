"""Autouse fixture para verificar instalación de cortex en tests de escenarios.

Este conftest.py se limita al subdirectorio scenarios/; por eso,
test_artefact_integrity.py (que vive en tests/e2e/ directamente) no es
afectado por este autouse.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _require_cortex_installed(cortex_install) -> None:
    """Auto-activa la verificación de cortex para todos los tests de scenarios/.

    Los tests de artefactos (tests/e2e/test_artefact_integrity.py) no están
    bajo scenarios/ y no son afectados por este autouse.
    """
    # cortex_install ya hace el skip si no está instalado


@pytest.fixture
def autopilot_workspace(tmp_path: Path) -> Path:
    """Crea un workspace Cortex temporal con layout v2 para tests de Autopilot.

    El workspace incluye lo mínimo necesario para que ``WorkspaceLayout.discover``
    lo reconozca y ``StateStore`` pueda persistir estado sin tocar el repo real.
    """
    cortex = tmp_path / ".cortex"
    cortex.mkdir(parents=True, exist_ok=True)
    (cortex / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")
    (cortex / "config.yaml").write_text(
        "llm:\n  provider: openai\n  model: gpt-4o\n", encoding="utf-8"
    )
    return tmp_path
