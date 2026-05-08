"""Autouse fixture para verificar instalación de cortex en tests de escenarios.

Este conftest.py se limita al subdirectorio scenarios/; por eso,
test_artefact_integrity.py (que vive en tests/e2e/ directamente) no es
afectado por este autouse.
"""
from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def _require_cortex_installed(cortex_install) -> None:
    """Auto-activa la verificación de cortex para todos los tests de scenarios/.

    Los tests de artefactos (tests/e2e/test_artefact_integrity.py) no están
    bajo scenarios/ y no son afectados por este autouse.
    """
    # cortex_install ya hace el skip si no está instalado
