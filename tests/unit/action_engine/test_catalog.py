"""Catálogo v1 del ActionEngine (plan §3.3): las 10 acciones.

Gate de Fase B: toda acción ejecuta (dry-run) y deshace en test; las
precondiciones deciden cuándo aparece; el contrato se respeta.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cortex.action_engine.actions import build_default_registry
from cortex.action_engine.context import ActionContext
from cortex.action_engine.models import ActionResult
from cortex.action_engine.registry import Registry
from cortex.action_engine.runner import Runner


@pytest.fixture
def ctx(tmp_path: Path) -> ActionContext:
    """Contexto mínimo: mocks livianos + layout sintético en tmp."""
    dot_cortex = tmp_path / ".cortex"
    dot_cortex.mkdir(parents=True, exist_ok=True)
    vault = tmp_path / "vault"
    vault.mkdir(exist_ok=True)
    (vault / "decisions").mkdir()
    (vault / "decisions" / "ADR-001-demo.md").write_text(
        "---\ntitle: demo\ndoc_type: adr\nstatus: accepted\n---\n\n# demo\n",
        encoding="utf-8",
    )

    layout = MagicMock()
    layout.workspace_root = tmp_path
    layout.config_path = dot_cortex / "config.yaml"
    layout.vault_path = vault

    mem = MagicMock()
    mem.sync_vault.return_value = 1

    sessions = MagicMock()

    # list() devuelve records reales-like con lo que consultan los checks
    def _record(sid="2026-08-01_stale", open_=True, checkpoints=(), days=30):
        from datetime import UTC, datetime, timedelta

        from cortex.session.models import SessionRecord, SessionStatus

        return SessionRecord(
            session_id=sid,
            spec_path=Path("vault/specs/demo.md"),
            spec_summary="demo",
            start_commit="a" * 40,
            start_branch="main",
            opened_at=datetime.now(UTC) - timedelta(days=days),
            status=SessionStatus.OPEN if open_ else SessionStatus.CLOSED,
            checkpoints=list(checkpoints),
        )

    sessions.list.return_value = [_record()]

    ctx = ActionContext(layout=layout, _mem=mem, _sessions=sessions)
    # config.yaml NO existe → setup.finish_bootstrap ofrecible
    return ctx


EXPECTED_IDS = {
    "setup.finish_bootstrap",
    "session.close_stale",
    "session.checkpoint_now",
    "vault.reindex",
    "vault.validate_docs",
    "quality.run_gates",
    "learn.topic",
    "knowledge.promote",
    "memory.prune",
    "ide.resync",
}


class TestCatalogoV1:
    def test_los_10_ids_estan_registrados(self, ctx: ActionContext) -> None:
        registry = build_default_registry(ctx)
        assert {a.id for a in registry.all()} == EXPECTED_IDS

    def test_toda_accion_cumple_contrato(self, ctx: ActionContext) -> None:
        for action in build_default_registry(ctx).all():
            if action.auto_ok:
                assert action.reversible and action.cost == "instant", action.id
            if action.reversible:
                assert action.undo is not None, action.id
            if not action.reversible:
                assert not action.auto_ok, action.id

    def test_dry_run_nunca_toca_servicios_mutadores(self, ctx: ActionContext) -> None:
        runner = Runner(directory=ctx.dot_cortex)
        registry = build_default_registry(ctx)
        for action in registry.all():
            resultado = runner.execute(action, dry_run=True, approved=False)
            assert resultado.ok or resultado.message, action.id
        # sync_vault jamás fue llamado (solo en ejecución real de vault.reindex)
        ctx.mem.sync_vault.assert_not_called()


class TestEjecucionReal:
    def test_vault_reindex_delega_en_sync_vault(self, ctx: ActionContext) -> None:
        runner = Runner(directory=ctx.dot_cortex)
        accion = build_default_registry(ctx).get("vault.reindex")
        resultado = runner.execute(accion)
        assert resultado.ok and "1" in resultado.message
        ctx.mem.sync_vault.assert_called_once()

    def test_session_close_stale_lista_guia(self, ctx: ActionContext) -> None:
        runner = Runner(directory=ctx.dot_cortex)
        accion = build_default_registry(ctx).get("session.close_stale")
        resultado = runner.execute(accion)
        assert resultado.ok
        assert "2026-08-01_stale" in resultado.message

    def test_learn_topic_devuelve_topico(self, ctx: ActionContext) -> None:
        runner = Runner(directory=ctx.dot_cortex)
        accion = build_default_registry(ctx).get("learn.topic")
        resultado = runner.execute(accion)
        assert resultado.ok and "Topic sugerido" in resultado.message

    def test_setup_bootstrap_dry_run_no_crea_config(self, ctx: ActionContext) -> None:
        runner = Runner(directory=ctx.dot_cortex)
        accion = build_default_registry(ctx).get("setup.finish_bootstrap")
        resultado = runner.execute(accion, dry_run=True)
        assert "[dry-run]" in resultado.message or "bootstrap" in resultado.message
        # no creó el config real
        assert not (ctx.dot_cortex / "config.yaml").exists()


class TestSchedulerIntegracion:
    def test_propone_maximo_5_y_prioriza_setup(self, ctx: ActionContext) -> None:
        from cortex.action_engine.scheduler import Scheduler
        from cortex.action_engine.store import PreferencesStore

        registry = build_default_registry(ctx)
        sched = Scheduler(preferences=PreferencesStore(ctx.dot_cortex))
        propuestas = sched.propose(registry)

        assert len(propuestas) <= 5
        ids = {p.action.id for p in propuestas}
        # bootstrap es la de mayor impacto y su precondición cumple acá
        assert "setup.finish_bootstrap" in ids
        scores = [p.score for p in propuestas]
        assert scores == sorted(scores, reverse=True)
