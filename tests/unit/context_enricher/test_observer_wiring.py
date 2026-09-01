"""Wiring del PersistentObserver (Obra 05 Fase A, tarea 2).

1. Rotación JSONL: al superar _MAX_BYTES, events file rota a .1.jsonl.
2. make_observer resuelve la ruta canónica <workspace>/.cortex/.
3. Los 4 puntos de construcción de ContextEnricher pasan observer=
   (guardia estática: cada sitio referencia make_observer).
"""

from __future__ import annotations

from pathlib import Path

from cortex.context_enricher.telemetry import (
    PersistentObserver,
    make_observer,
)
from cortex.models import EnrichedContext, WorkContext


def _observer(tmp_path: Path, max_bytes: int | None = None) -> PersistentObserver:
    obs = PersistentObserver(tmp_path / ".cortex" / "enrichment-events.jsonl")
    if max_bytes is not None:
        obs._MAX_BYTES = max_bytes
    return obs


def _ctx() -> EnrichedContext:
    return EnrichedContext(
        work=WorkContext(source="manual", changed_files=[], keywords=[], search_queries=[]),
        items=[],
        total_searches=0,
        total_raw_hits=0,
        total_items=0,
        total_chars=0,
        within_budget=True,
    )


class TestRotacion:
    def test_rota_al_superar_max_bytes(self, tmp_path: Path) -> None:
        # ~230B por evento: 1000B dispara exactamente UNA rotación en el evento 6
        obs = _observer(tmp_path, max_bytes=1000)
        for i in range(6):
            run_id = obs.record_enrichment(_ctx(), latency_ms=1 + i)
            assert run_id

        rotado = tmp_path / ".cortex" / "enrichment-events.1.jsonl"
        assert rotado.exists(), "debe existir generación histórica tras rotar"
        vivo = tmp_path / ".cortex" / "enrichment-events.jsonl"
        assert vivo.stat().st_size < 6 * 400  # el vivo quedó acotado
        # todos los eventos siguen consultables (vivo + rotado)
        assert len(obs.iter_events()) >= 6


class TestMakeObserver:
    def test_ruta_canonica_bajo_workspace(self, tmp_path: Path) -> None:
        obs = make_observer(project_root=tmp_path)
        assert obs.enabled
        assert obs.path == tmp_path / ".cortex" / "enrichment-events.jsonl"

    def test_config_puede_deshabilitar(self, tmp_path: Path) -> None:
        obs = make_observer(project_root=tmp_path, enabled=False)
        assert not obs.enabled
        assert obs.record_enrichment(_ctx()) == ""


class TestGuardiaEstaticaWiring:
    def test_los_4_sitios_referencian_make_observer(self) -> None:
        sitios = [
            "cortex/core.py",
            "cortex/mcp/tools/search.py",
            "cortex/cli/main.py",
            "cortex/cli/docs_search.py",
        ]
        root = Path(__file__).resolve().parents[3]
        faltantes = []
        for rel in sitios:
            texto = (root / rel).read_text(encoding="utf-8")
            ok = "make_observer(" in texto and "observer=make_observer" in texto
            if not ok:
                faltantes.append(rel)
        assert not faltantes, f"Sitios sin wiring de telemetría: {faltantes}"
