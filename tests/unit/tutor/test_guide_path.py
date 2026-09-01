"""guide_path consumido por el TutorEngine (Obra 05 Fase A, tarea 4).

Antes era un campo muerto: los 7 topics lo definían y nadie lo leía.
Ahora show_topic/show_topic_by_slug muestran la referencia a la guía
extendida cuando existe.
"""

from __future__ import annotations

import io
from pathlib import Path

from rich.console import Console

from cortex.tutor.engine import TutorEngine
from cortex.tutor.topics import (
    commands,
    enterprise,
    getting_started,
    ide_integration,
    pipeline,
    vault,
    workflow,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _console() -> Console:
    return Console(record=True, width=120, file=io.StringIO())


class TestGuidePathRevivido:
    def test_show_topic_muestra_guia_extendida(self) -> None:
        topic = getting_started.GettingStartedTopic()
        console = _console()
        engine = TutorEngine(console=console, topics=[topic])

        engine.show_topic(0)

        texto = console.export_text()
        assert "docs/guides/getting-started.md" in texto
        assert "Guía extendida" in texto

    def test_topic_sin_guia_no_muestra_linea(self) -> None:
        console = _console()
        engine = TutorEngine(console=console, topics=[commands.CommandsTopic()])

        engine.show_topic_by_slug("commands")

        assert "Guía extendida" not in console.export_text()

    def test_todos_los_paths_apuntan_a_archivos_existentes(self) -> None:
        """Los guide_path definidos deben apuntar a archivos reales del repo."""
        modulos = [enterprise, getting_started, ide_integration, pipeline, vault, workflow]
        revisados = 0
        for mod in modulos:
            for nombre in vars(mod):
                cls = getattr(mod, nombre)
                if not (isinstance(cls, type) and hasattr(cls, "guide_path")):
                    continue
                if cls.__module__ != mod.__name__:
                    continue
                path = cls().guide_path
                if path is None:
                    continue
                assert (REPO_ROOT / path).exists(), f"{path} no existe"
                revisados += 1
        assert revisados >= 4, f"solo {revisados} topics con guía — se esperaban más"
