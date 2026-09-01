"""Fase E: señales de feedback real alimentan el score del scheduler."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from cortex.action_engine.models import Action, ActionResult
from cortex.action_engine.registry import Registry
from cortex.action_engine.scheduler import Scheduler
from cortex.action_engine.signals import (
    MemorySignals,
    leer_senales,
    multiplicador_categoria,
)
from cortex.action_engine.store import ActionLog, PreferencesStore


def _accion(id_: str, categoria: str) -> Action:
    return Action(
        id=id_,
        title="t",
        category=categoria,  # type: ignore[arg-type]
        effect="e",
        reversible=True,
        undo=lambda: ActionResult(ok=True),
        run=lambda dr: ActionResult(ok=True),
    )


def _escribir_feedback(dot_cortex: Path, eventos: list[tuple[int, str]]) -> None:
    ahora = datetime.now(UTC)
    lineas = []
    for dias_atras, tipo in eventos:
        ts = (ahora - timedelta(days=dias_atras)).isoformat(timespec="seconds")
        lineas.append(json.dumps({"ts": ts, "feedback_type": tipo, "memory_id": "x"}))
    (dot_cortex / "feedback.jsonl").write_text("\n".join(lineas) + "\n", encoding="utf-8")


class TestSenales:
    def test_lee_ventana_y_descarta_fuera_de_ella(self, tmp_path: Path) -> None:
        _escribir_feedback(tmp_path, [(1, "positive"), (2, "positive"), (30, "negative")])
        senales = leer_senales(tmp_path, dias=14)
        assert senales.positivos == 2
        assert senales.negativos == 0

    def test_dominio(self, tmp_path: Path) -> None:
        _escribir_feedback(tmp_path, [(1, "negative"), (1, "negative")])
        assert leer_senales(tmp_path).dominio == "negativo"


class TestMultiplicadores:
    def test_negativo_subre_quality_y_maintenance(self, tmp_path: Path) -> None:
        _escribir_feedback(tmp_path, [(i, "negative") for i in range(3)])
        senales = leer_senales(tmp_path)
        assert multiplicador_categoria("quality", senales) > 1.0
        assert multiplicador_categoria("maintenance", senales) > 1.0
        assert multiplicador_categoria("learning", senales) == 1.0

    def test_positivo_subre_learning_y_knowledge(self, tmp_path: Path) -> None:
        _escribir_feedback(tmp_path, [(i, "positive") for i in range(2)])
        senales = leer_senales(tmp_path)
        assert multiplicador_categoria("learning", senales) > 1.0
        assert multiplicador_categoria("knowledge", senales) > 1.0
        assert multiplicador_categoria("quality", senales) == 1.0

    def test_tope_25_porciento(self, tmp_path: Path) -> None:
        _escribir_feedback(tmp_path, [(i, "negative") for i in range(50)])
        senales = leer_senales(tmp_path)
        assert multiplicador_categoria("quality", senales) == pytest.approx(1.25)

    def test_neutro_es_neutro(self, tmp_path: Path) -> None:
        _escribir_feedback(tmp_path, [(1, "positive"), (2, "negative")])
        senales = leer_senales(tmp_path)
        assert multiplicador_categoria("quality", senales) == 1.0


class TestSchedulerConSenales:
    def test_score_quality_sub_con_dominio_negativo(self, tmp_path: Path) -> None:
        prefs = PreferencesStore(tmp_path)
        registry = Registry()
        registry.register(_accion("qual.y", "quality"))

        sin = Scheduler(preferences=prefs).propose(registry)[0].score
        con = Scheduler(
            preferences=prefs,
            senales=MemorySignals(positivos=0, negativos=10),
        ).propose(registry)[0].score

        assert con == pytest.approx(sin * 1.25)

    def test_learning_no_cambia_con_dominio_negativo(self, tmp_path: Path) -> None:
        prefs = PreferencesStore(tmp_path)
        registry = Registry()
        registry.register(_accion("learn.x", "learning"))

        sin = Scheduler(preferences=prefs).propose(registry)[0].score
        con = Scheduler(
            preferences=prefs,
            senales=MemorySignals(positivos=0, negativos=10),
        ).propose(registry)[0].score

        assert con == sin



class TestMetricasMotor:
    def test_calculo_pct_motor(self, tmp_path: Path) -> None:
        from cortex.action_engine.metrics import calcular_metricas

        log = ActionLog(tmp_path)
        log.append({"id": "a.ok", "dry_run": False, "via": "auto"})
        log.append({"id": "b.ok", "dry_run": False, "via": "auto"})
        log.append({"id": "c.x", "dry_run": False, "via": "user"})
        log.append({"id": "d.dry", "dry_run": True, "via": "auto"})

        m = calcular_metricas(log)
        assert m.total_ejecuciones == 3  # dry-runs no cuentan
        assert m.via_auto == 2 and m.via_usuario == 1
        assert m.pct_motor == pytest.approx(66.7)
        assert m.dias_con_interaccion

    def test_vacio(self, tmp_path: Path) -> None:
        from cortex.action_engine.metrics import calcular_metricas

        m = calcular_metricas(ActionLog(tmp_path))
        assert m.total_ejecuciones == 0 and m.pct_motor == 0.0
