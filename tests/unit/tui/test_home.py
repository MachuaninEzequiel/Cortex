"""TUI Home (Obra 05 Fase D): snapshot <300ms, renderers puros, decisiones."""

from __future__ import annotations

import io
import time
from pathlib import Path

from rich.console import Console

from cortex.tui.core import render_actions_screen, render_home, snapshot_home


def _repo(tmp_path: Path) -> Path:
    dot = tmp_path / ".cortex"
    dot.mkdir(parents=True)
    (dot / "config.yaml").write_text(
        "episodic:\n  persist_dir: .memory/chroma\n"
        "  collection_name: cortex_episodic\n"
        "  embedding_model: all-MiniLM-L6-v2\n  embedding_backend: onnx\n"
        "semantic:\n  vault_path: vault\n",
        encoding="utf-8",
    )
    vault = dot / "vault" / "decisions"
    vault.mkdir(parents=True)
    for i in range(1, 6):
        (vault / f"ADR-{i:03d}.md").write_text(
            f"---\ntitle: A{i}\ndoc_type: adr\nstatus: accepted\n---\n\n#c\n",
            encoding="utf-8",
        )
    (tmp_path / ".git").mkdir()
    return tmp_path


def _console() -> Console:
    return Console(record=True, width=100, file=io.StringIO())


class TestSnapshotHome:
    def test_gate_snapshot_menos_de_300ms(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        t0 = time.perf_counter()
        state = snapshot_home(repo)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 300, f"snapshot tardó {elapsed_ms:.0f}ms — gate <300ms"
        assert state.vault_notas == 5

    def test_proyecto_sin_inicializar_no_revienta(self, tmp_path: Path) -> None:
        vacio = tmp_path / "vacio"
        vacio.mkdir()
        state = snapshot_home(vacio)
        assert any("init" in k for k, _ in state.doctor_items)


class TestRenderHome:
    def test_render_contiene_secciones(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        state = snapshot_home(repo)
        console = _console()
        console.print(render_home(state))
        texto = console.export_text()

        for seccion in ("SESIÓN", "PENDIENTE", "VAULT", "SALUD"):
            assert seccion in texto, f"falta sección {seccion}"

    def test_render_80x24_sin_desborde(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path)
        state = snapshot_home(repo)
        console = Console(record=True, width=80, file=io.StringIO())
        console.print(render_home(state))
        lineas = console.export_text().splitlines()
        assert len(lineas) <= 24, f"{len(lineas)} líneas — no entra en 80x24"
        for linea in lineas:
            assert len(linea) <= 80


class TestPantallaAcciones:
    def test_render_lista_costo_y_seguridad(self, tmp_path: Path) -> None:
        from unittest.mock import MagicMock

        from cortex.action_engine.actions import build_default_registry
        from cortex.action_engine.scheduler import Scheduler
        from cortex.action_engine.store import PreferencesStore

        ctx = MagicMock()
        ctx.dot_cortex = Path("/tmp")
        registry = build_default_registry(ctx)
        propuestas = Scheduler(preferences=PreferencesStore(Path("/tmp"))).propose(
            registry
        )

        console = _console()
        console.print(render_actions_screen(propuestas))
        texto = console.export_text()
        assert "Acciones sugeridas" in texto
        assert (
            "auto-ok" in texto or "reversible" in texto or "irreversible" in texto
        )
