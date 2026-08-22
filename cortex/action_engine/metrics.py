"""Métrica de éxito del dueño (Obra 05 Fase E, plan §3.6).

Definición registrada para la medición de adopción:

- ``pct_motor`` = ejecuciones decididas por el motor (auto-ok, ``via=auto``)
  sobre el total de ejecuciones reales (no dry-run).
- Target declarado por el dueño: abrir el menú de acciones <1 vez por día
  de trabajo activo ⇒ proxy medible hoy: ``pct_motor`` alto con volumen
  estable de ejecuciones y ``dias_con_interaccion`` bajo.

La ventana de observación se abre con la adopción; el cierre se registra
en ESTADO-ACTUAL.md tras ≥2 semanas de uso real.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cortex.action_engine.store import ActionLog


@dataclass(frozen=True)
class MetricasMotor:
    total_ejecuciones: int
    via_auto: int
    via_usuario: int
    dry_runs: int
    pct_motor: float
    acciones_por_id: dict[str, int] = field(default_factory=dict)
    dias_con_interaccion: tuple[str, ...] = field(default_factory=tuple)


def calcular_metricas(log: ActionLog) -> MetricasMotor:
    total = auto = usuario = dry = 0
    por_id: dict[str, int] = {}
    dias: set[str] = set()
    for entry in log.load():
        if entry.get("dry_run"):
            dry += 1
            continue
        total += 1
        if entry.get("via") == "auto":
            auto += 1
        else:
            usuario += 1
        accion_id = str(entry.get("id", "?"))
        por_id[accion_id] = por_id.get(accion_id, 0) + 1
        ts = str(entry.get("ts", ""))[:10]
        if ts:
            dias.add(ts)

    pct = round(auto / total * 100, 1) if total else 0.0
    return MetricasMotor(
        total_ejecuciones=total,
        via_auto=auto,
        via_usuario=usuario,
        dry_runs=dry,
        pct_motor=pct,
        acciones_por_id=dict(sorted(por_id.items(), key=lambda kv: -kv[1])),
        dias_con_interaccion=tuple(sorted(dias)),
    )
