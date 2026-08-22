"""Registry y scheduler del ActionEngine (Obra 05 Fase B, plan §3.4).

- ``Registry``: catálogo de acciones registradas por id.
- ``Scheduler``: evalúa precondiciones + preferencias, calcula score
  (impacto × frescura − costo) y devuelve máximo ``max_visible`` propuestas.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cortex.action_engine.models import (
    IMPACTO_BASE,
    COSTO_PENALIZACION,
    ProposedAction,
)
from cortex.action_engine.registry import Registry
from cortex.action_engine.store import PreferencesStore

MAX_VISIBLE_DEFAULT = 5



@dataclass
class Scheduler:
    """Evalúa el registry y propone acciones priorizadas."""

    preferences: PreferencesStore
    max_visible: int = MAX_VISIBLE_DEFAULT
    # frescura: cuántas ejecuciones recientes de la misma acción bajan su
    # prioridad (evita proponer lo mismo recién hecho). v0: fijo.
    frescura: float = 1.0
    extra_reasons: dict[str, list[str]] = field(default_factory=dict)

    def _score(self, action: Action) -> float:
        impacto = IMPACTO_BASE.get(action.category, 2.0)
        penalizacion_costo = COSTO_PENALIZACION.get(action.cost, 1.0)
        multiplicador_aprendido = self.preferences.penalizacion_skips(action.id)
        return (impacto * self.frescura - penalizacion_costo) * multiplicador_aprendido

    def propose(
        self,
        registry: Registry,
        *,
        deep: bool = False,
    ) -> list[ProposedAction]:
        """Acciones ofrecibles ahora mismo.

        ``deep=False`` (on-open): snapshot barato — las acciones pueden
        declarar checks costosos con ``deep_only=True`` en la razón
        (convención: descripción que empieza con "deep:") para omitirlos.
        """
        propuestas: list[ProposedAction] = []
        for action in registry.all():
            if self.preferences.nunca_mas(action.id):
                continue

            fallidas = [
                check.description
                for check in action.preconditions
                if not check.cumple()
            ]
            if fallidas:
                continue

            razones = [f"impacto {action.category}", *self.extra_reasons.get(action.id, [])]
            propuestas.append(
                ProposedAction(action=action, score=round(self._score(action), 3), reasons=razones)
            )

        propuestas.sort(key=lambda p: p.score, reverse=True)
        return propuestas[: self.max_visible]

    def explain_why_not(
        self,
        registry: Registry,
        *,
        deep: bool = False,
    ) -> dict[str, list[str]]:
        """Para cada acción NO propuesta: qué precondiciones fallaron."""
        detalle: dict[str, list[str]] = {}
        for action in registry.all():
            if self.preferences.nunca_mas(action.id):
                detalle[action.id] = ["suprimida por preferencia ('nunca más')"]
                continue
            fallidas = [
                check.description
                for check in action.preconditions
                if not check.cumple()
            ]
            if fallidas:
                detalle[action.id] = fallidas
        return detalle
