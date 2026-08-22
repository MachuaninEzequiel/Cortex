"""Tests del núcleo ActionEngine (Obra 05 Fase B).

Cubren el contrato duro §3.2: auto_ok solo reversible+instant,
reversible exige undo, irreversible exige aprobación, todo se registra
en action_log.jsonl, dry-run no escribe y las preferencias aprenden.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.action_engine import (
    Action,
    ActionResult,
    Check,
    PreferencesStore,
    Registry,
    Runner,
    Scheduler,
)
from cortex.action_engine.learning import Learner


def _accion_ok(id_: str = "test.accion", **kwargs) -> Action:
    base = dict(
        id=id_,
        title="Acción de prueba",
        category="maintenance",
        effect="no cambia nada real",
        reversible=True,
        undo=lambda: ActionResult(ok=True, message="deshecho"),
        cost="instant",
        auto_ok=True,
        run=lambda dry_run: ActionResult(
            ok=True, message="[dry-run] simulado" if dry_run else "hecho"
        ),
    )
    base.update(kwargs)
    return Action(**base)


class TestContrato:
    def test_auto_ok_exige_reversible_e_instant(self) -> None:
        with pytest.raises(ValueError, match="auto_ok"):
            _accion_ok(reversible=False, auto_ok=True)
        with pytest.raises(ValueError, match="auto_ok"):
            _accion_ok(cost="minutes", auto_ok=True)

    def test_reversible_exige_undo(self) -> None:
        with pytest.raises(ValueError, match="undo"):
            _accion_ok(undo=None)

    def test_id_formato_dominio_accion(self) -> None:
        with pytest.raises(ValueError, match="id inválido"):
            _accion_ok(id_="sinpunto")


class TestActionLog:
    def test_toda_ejecucion_se_registra(self, tmp_path: Path) -> None:
        runner = Runner(directory=tmp_path)
        accion = _accion_ok()
        runner.execute(accion)
        runner.execute(accion, dry_run=True)

        entradas = runner.log.load()
        assert len(entradas) == 2
        assert all(e["id"] == "test.accion" for e in entradas)
        assert [e["dry_run"] for e in entradas] == [False, True]
        assert entradas[0]["trigger"] == "on-open"
        assert "duration_ms" in entradas[0]

    def test_irreversible_sin_aprobacion_no_ejecuta(self, tmp_path: Path) -> None:
        ejecutado = []

        def correr(dry_run: bool) -> ActionResult:
            ejecutado.append(dry_run)
            return ActionResult(ok=True, message="cambio destructivo")

        accion = _accion_ok(
            id_="danger.drop", reversible=False, undo=None, auto_ok=False, run=correr
        )
        runner = Runner(directory=tmp_path)

        resultado = runner.execute(accion)  # sin approved
        assert not resultado.ok
        assert not ejecutado  # NUNCA corrió

        # con approved sí corre
        resultado2 = runner.execute(accion, approved=True)
        assert resultado2.ok and ejecutado == [False]

    def test_undo_last_deshace_solo_reales_y_reversibles(self, tmp_path: Path) -> None:
        deshechos: list[str] = []
        accion = _accion_ok(undo=lambda: ActionResult(ok=True, message="back"))
        irreversible = _accion_ok(
            id_="danger.x", reversible=False, undo=None, auto_ok=False,
            run=lambda dr: ActionResult(ok=True, message="boom"),
        )
        runner = Runner(directory=tmp_path)
        runner.execute(accion, dry_run=True)
        runner.execute(accion)
        runner.execute(irreversible, approved=True)

        resultado = runner.undo_last()
        # la última real es la irreversible (sin undo) → deshace la anterior
        assert resultado is not None and resultado.message == "back"


class TestSchedulerYPreferencias:
    def test_precondicion_falla_no_ofrece(self, tmp_path: Path) -> None:
        registry = Registry()
        registry.register(_accion_ok(preconditions=(Check("nunca", lambda: False),)))
        sched = Scheduler(preferences=PreferencesStore(tmp_path))

        assert sched.propose(registry) == []
        detalle = sched.explain_why_not(registry)
        assert "nunca" in detalle["test.accion"][0]

    def test_nunca_mas_suprime(self, tmp_path: Path) -> None:
        registry = Registry()
        registry.register(_accion_ok())
        prefs = PreferencesStore(tmp_path)
        sched = Scheduler(preferences=prefs)

        assert len(sched.propose(registry)) == 1
        prefs.registrar("test.accion", "never")
        assert sched.propose(registry) == []
        detalle = sched.explain_why_not(registry)
        assert "preferencia" in detalle["test.accion"][0]

    def test_skips_bajan_score_y_accepts_compensan(self, tmp_path: Path) -> None:
        registry = Registry()
        registry.register(_accion_ok())
        learner = Learner(PreferencesStore(tmp_path))

        base = Scheduler(preferences=learner._prefs).propose(registry)[0].score

        learner.registrar_decision("test.accion", "skip")
        tras_skip = Scheduler(preferences=learner._prefs).propose(registry)[0].score
        assert tras_skip < base

        learner.registrar_decision("test.accion", "accept")
        learner.registrar_decision("test.accion", "accept")
        tras_accepts = Scheduler(preferences=learner._prefs).propose(registry)[0].score
        assert tras_accepts == base

    def test_max_visible(self, tmp_path: Path) -> None:
        registry = Registry()
        for i in range(8):
            registry.register(_accion_ok(id_=f"test.a{i}"))
        sched = Scheduler(preferences=PreferencesStore(tmp_path), max_visible=5)
        assert len(sched.propose(registry)) == 5


class TestRegistry:
    def test_duplicados_rechazados(self, tmp_path: Path) -> None:
        registry = Registry()
        registry.register(_accion_ok())
        with pytest.raises(ValueError, match="duplicada"):
            registry.register(_accion_ok())
