"""Modelos del ActionEngine (Obra 05 Fase B, §3.2 del plan).

Contrato duro:
1. Toda acción delega en su servicio — nunca reimplementa lógica.
2. Las precondiciones se evalúan ANTES de ofrecer la acción.
3. ``reversible=False`` ⇒ requiere aprobación SIEMPRE (sin modo auto).
4. Toda ejecución se registra en ``.cortex/action_log.jsonl``.
5. Dry-run nativo: ``run(dry_run=True)`` devuelve el efecto sin escribir.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

Categoria = Literal["setup", "quality", "maintenance", "knowledge", "learning"]
Costo = Literal["instant", "seconds", "minutes"]
Trigger = Literal["on-open", "on-event", "on-schedule"]

# Tabla estática de impacto por categoría (plan §3.4): setup > calidad >
# mantenimiento > conocimiento > aprendizaje. Refinada luego por aprendizaje.
IMPACTO_BASE: dict[str, float] = {
    "setup": 10.0,
    "quality": 8.0,
    "maintenance": 6.0,
    "knowledge": 4.0,
    "learning": 3.0,
}

COSTO_PENALIZACION: dict[str, float] = {
    "instant": 0.0,
    "seconds": 1.0,
    "minutes": 3.0,
}


def _ahora() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class Check:
    """Precondición pura: predicado sin efectos + razón legible si falla.

    ``deep_only=True``: el check es costoso (escaneos completos) y SOLO se
    evalúa en modo deep (``cortex next --all`` / on-schedule). En snapshot
    on-open se asume cumplido y no bloquea la propuesta.
    """

    description: str
    predicate: Callable[[], bool]
    deep_only: bool = False

    def cumple(self, *, deep: bool = False) -> bool:
        if self.deep_only and not deep:
            return True
        try:
            return bool(self.predicate())
        except Exception:  # noqa: BLE001 — un check roto nunca ofrece la acción
            return False


@dataclass(frozen=True)
class ActionResult:
    """Resultado de ejecutar una acción."""

    ok: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def dry(cls, effect: str) -> "ActionResult":
        return cls(ok=True, message=f"[dry-run] {effect}")

    @classmethod
    def fail(cls, message: str) -> "ActionResult":
        return cls(ok=False, message=message)


@dataclass(frozen=True)
class Action:
    id: str
    title: str
    category: Categoria
    effect: str
    preconditions: tuple[Check, ...] = ()
    reversible: bool = False
    undo: Callable[[], ActionResult] | None = None
    cost: Costo = "seconds"
    auto_ok: bool = False
    run: Callable[[bool], ActionResult] = lambda dry_run: ActionResult(
        ok=False, message="acción sin implementar"
    )

    def __post_init__(self) -> None:
        if self.auto_ok and not (self.reversible and self.cost == "instant"):
            raise ValueError(
                f"{self.id}: auto_ok requiere reversible=True y cost='instant' "
                "(regla dura #3 del contrato)"
            )
        if self.reversible and self.undo is None:
            raise ValueError(f"{self.id}: reversible=True exige undo (contrato)")
        if not self.id or "." not in self.id:
            raise ValueError(f"id inválido: {self.id!r} — formato 'dominio.accion'")


@dataclass
class ProposedAction:
    """Una acción que el scheduler ofrece tras evaluar precondiciones."""

    action: Action
    score: float
    reasons: list[str] = field(default_factory=list)  # por qué se propone


@dataclass(frozen=True)
class Decision:
    """Decisión del usuario/aprendizaje sobre una acción propuesta."""

    action_id: str
    eleccion: Literal["accept", "skip", "never"]
    ts: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))


def ahora_iso() -> str:
    return _ahora().isoformat(timespec="seconds")
