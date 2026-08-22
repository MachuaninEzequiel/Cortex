"""Runner del ActionEngine (Obra 05 Fase B).

Ejecuta acciones aplicando las reglas duras del contrato:
- dry-run nativo (pasa ``dry_run=True`` al run de la acción);
- irreversible ⇒ exige ``approved=True`` explícito;
- toda ejecución (incluidos dry-runs y fallos) queda en action_log.jsonl;
- deshacer: ``undo_last()`` sobre la última ejecución reversible con éxito.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from cortex.action_engine.models import Action, ActionResult, Trigger, ahora_iso
from cortex.action_engine.store import ActionLog

logger = logging.getLogger(__name__)


@dataclass
class ExecutionRecord:
    action: Action
    result: ActionResult
    duration_ms: int
    dry_run: bool


@dataclass
class Runner:
    log: ActionLog
    trigger: Trigger = "on-open"
    _historial: list[ExecutionRecord] = field(default_factory=list, repr=False)

    def __init__(
        self,
        directory: Path,
        trigger: Trigger = "on-open",
    ) -> None:
        self.log = ActionLog(directory)
        self.trigger = trigger
        self._historial = []

    # ── ejecución ──────────────────────────────────────────────────────

    def execute(
        self,
        action: Action,
        *,
        dry_run: bool = False,
        approved: bool = False,
    ) -> ActionResult:
        """Ejecuta (o simula) una acción y la registra.

        Reglas:
        - irreversible exige ``approved=True`` salvo en dry-run;
        - el resultado SIEMPRE se registra en action_log.
        """
        if not dry_run and not action.reversible and not approved:
            return self._registrar(
                action,
                ActionResult.fail(
                    f"{action.id} es irreversible — requiere aprobación explícita"
                ),
                0,
                dry_run=True,
            )

        t0 = time.perf_counter()
        try:
            result = action.run(dry_run)
        except Exception as exc:  # noqa: BLE001 — el runner nunca revienta
            logger.exception("Acción %s falló", action.id)
            result = ActionResult.fail(f"{action.id}: {exc}")
        duration = int((time.perf_counter() - t0) * 1000)
        return self._registrar(action, result, duration, dry_run)

    def undo_last(self) -> ActionResult | None:
        """Deshace la última ejecución real y reversible. None si no hay."""
        for record in reversed(self._historial):
            if record.dry_run or not record.action.reversible or not record.result.ok:
                continue
            undo_fn = record.action.undo
            if undo_fn is None:
                continue
            resultado = undo_fn()
            self.log.append(
                {
                    "id": record.action.id,
                    "ts": ahora_iso(),
                    "trigger": self.trigger,
                    "dry_run": False,
                    "ok": resultado.ok,
                    "message": f"UNDO: {resultado.message}",
                    "duration_ms": 0,
                }
            )
            self._historial.remove(record)
            return resultado
        return None

    # ── registro interno ───────────────────────────────────────────────

    def _registrar(
        self,
        action: Action,
        result: ActionResult,
        duration_ms: int,
        dry_run: bool,
    ) -> ActionResult:
        self.log.append(
            {
                "id": action.id,
                "ts": ahora_iso(),
                "trigger": self.trigger,
                "dry_run": dry_run,
                "ok": result.ok,
                "message": result.message,
                "duration_ms": duration_ms,
            }
        )
        if not dry_run:
            self._historial.append(
                ExecutionRecord(action=action, result=result, duration_ms=duration_ms, dry_run=False)
            )
        return result
