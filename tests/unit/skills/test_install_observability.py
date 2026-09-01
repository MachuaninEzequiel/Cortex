"""Installs de skills con fallos OBSERVABLES (review 9 #8, auditoría H-3).

Antes las excepciones por skill y por archivo se tragaban con ``pass``:
installs parciales invisibles. Ahora quedan como warnings del logger
``cortex.skills`` sin abortar el resto.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

from cortex.skills import install_skills


def test_skill_fallida_registra_warning_y_continua(tmp_path, caplog) -> None:
    """Un recurso que explota al leerse → warning + sigue con el resto."""
    recurso_roto = MagicMock()
    recurso_roto.joinpath.side_effect = RuntimeError("boom lectura bundle")

    with (
        patch("cortex.skills.SKILL_NAMES", ["buena", "rota"]),
        patch("cortex.skills.importlib.resources.files", return_value=recurso_roto),
        caplog.at_level(logging.WARNING, logger="cortex.skills"),
    ):
        instaladas = install_skills(tmp_path)

    assert instaladas == []  # ambas fallaron (bundle roto) pero NO explotó
    warnings_texto = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("no pudo instalarse" in m for m in warnings_texto), (
        f"installs parciales deben dejar warning: {warnings_texto}"
    )


def test_installs_exitosas_no_emiten_warnings(tmp_path, caplog) -> None:
    recurso = MagicMock()
    archivo = MagicMock()
    archivo.is_dir.return_value = False
    archivo.name = "SKILL.md"
    archivo.read_text.return_value = "---\ntitle: x\n---\n"
    recurso.joinpath.return_value = MagicMock(iterdir=MagicMock(return_value=[archivo]))

    with (
        patch("cortex.skills.SKILL_NAMES", ["buena"]),
        patch("cortex.skills.importlib.resources.files", return_value=recurso),
        caplog.at_level(logging.WARNING, logger="cortex.skills"),
    ):
        instaladas = install_skills(tmp_path)

    assert "buena" in instaladas
    warnings_texto = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert warnings_texto == []
