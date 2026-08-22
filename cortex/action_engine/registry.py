"""Registry del ActionEngine (plan §3.2)."""

from __future__ import annotations

from cortex.action_engine.models import Action


class Registry:
    """Catálogo de acciones registradas por id (sin duplicados)."""

    def __init__(self) -> None:
        self._acciones: dict[str, Action] = {}

    def register(self, action: Action) -> None:
        if action.id in self._acciones:
            raise ValueError(f"acción duplicada: {action.id}")
        self._acciones[action.id] = action

    def get(self, action_id: str) -> Action:
        return self._acciones[action_id]

    def all(self) -> list[Action]:
        return list(self._acciones.values())

    def __len__(self) -> int:
        return len(self._acciones)

    def __contains__(self, action_id: str) -> bool:
        return action_id in self._acciones
