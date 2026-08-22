"""Paso APRENDER v0 del ActionEngine (plan §3.6).

Bucle mínimo: cada decisión (accept/skip/never) se persiste en
``.cortex/actions.yaml`` y ajusta el score futuro vía
``PreferencesStore.penalizacion_skips``. El registro crudo de ejecuciones
vive en action_log.jsonl; el agregado mensual llega en fases posteriores.
"""

from __future__ import annotations

from cortex.action_engine.store import PreferencesStore


class Learner:
    def __init__(self, preferences: PreferencesStore) -> None:
        self._prefs = preferences

    def registrar_decision(self, action_id: str, eleccion: str) -> None:
        """accept | skip | never — persiste y ajusta prioridad futura."""
        self._prefs.registrar(action_id, eleccion)

    def suprimida(self, action_id: str) -> bool:
        return self._prefs.nunca_mas(action_id)

    def multiplicador(self, action_id: str) -> float:
        return self._prefs.penalizacion_skips(action_id)
