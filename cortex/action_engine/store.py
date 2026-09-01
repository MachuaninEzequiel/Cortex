"""Persistencia del ActionEngine (Obra 05 Fase B).

- ``ActionLog``: registro append-only de ejecuciones en
  ``.cortex/action_log.jsonl`` — insumo del paso APRENDER.
- ``PreferencesStore``: supresiones y contadores aceptar/saltar/nunca por
  id en ``.cortex/actions.yaml`` — el motor aprende preferencias negativas
  y positivas (plan §3.5/§3.6).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_LOG_ROTADO = "action_log.1.jsonl"


class ActionLog:
    """JSONL append-only: {id, ts, trigger, dry_run, ok, message, duration_ms}."""

    def __init__(self, directory: Path, max_bytes: int = 5 * 1024 * 1024) -> None:
        self._dir = Path(directory)
        self._path = self._dir / "action_log.jsonl"
        self._max_bytes = max_bytes

    @property
    def path(self) -> Path:
        return self._path

    def append(self, entry: dict[str, object]) -> None:
        from cortex.action_engine.models import ahora_iso

        entry = {**entry, "ts": entry.get("ts") or ahora_iso()}
        self._dir.mkdir(parents=True, exist_ok=True)
        self._rotar_si_corresponde()
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    def _rotar_si_corresponde(self) -> None:
        if not self._path.exists() or self._path.stat().st_size < self._max_bytes:
            return
        rotado = self._dir / _LOG_ROTADO
        if rotado.exists():
            rotado.unlink()
        self._path.rename(rotado)

    def load(self) -> list[dict[str, object]]:
        eventos: list[dict[str, object]] = []
        for ruta in (self._dir / _LOG_ROTADO, self._path):
            if not ruta.exists():
                continue
            for linea in ruta.read_text(encoding="utf-8").splitlines():
                if not linea.strip():
                    continue
                try:
                    eventos.append(json.loads(linea))
                except json.JSONDecodeError:
                    logger.warning("Línea corrupta en %s", ruta.name)
        return eventos


class PreferencesStore:
    """Preferencias por acción en YAML::

        acciones:
          vault.reindex:
            never: false
            skips: 2
            accepts: 7

    Reglas v0 (aprendizaje): ``never`` suprime la acción para siempre;
    cada ``skip`` resta score; los ``accepts`` lo devuelven.
    """

    def __init__(self, directory: Path) -> None:
        self._dir = Path(directory)
        self._path = self._dir / "actions.yaml"

    @property
    def path(self) -> Path:
        return self._path

    def _load(self) -> dict[str, dict[str, int | bool]]:
        if not self._path.exists():
            return {}
        try:
            data = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
            acciones = data.get("acciones") or {}
            return acciones if isinstance(acciones, dict) else {}
        except Exception:  # noqa: BLE001 — YAML roto no debe tumbar el motor
            logger.warning("actions.yaml ilegible; se ignora", exc_info=True)
            return {}

    def _guardar(self, acciones: dict[str, dict[str, int | bool]]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            yaml.safe_dump({"acciones": acciones}, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    def registrar(self, action_id: str, eleccion: str) -> None:
        """Registra 'accept' | 'skip' | 'never' para una acción."""
        acciones = self._load()
        entrada = acciones.get(action_id) or {"never": False, "skips": 0, "accepts": 0}
        if eleccion == "never":
            entrada["never"] = True
        elif eleccion == "skip":
            entrada["skips"] = int(entrada.get("skips", 0)) + 1
        elif eleccion == "accept":
            entrada["accepts"] = int(entrada.get("accepts", 0)) + 1
            # un accept compensa hasta dos skips (v0 simple)
            if entrada["skips"] >= 2:
                entrada["skips"] = int(entrada["skips"]) - 2
            else:
                entrada["skips"] = 0
        else:
            raise ValueError(f"elección inválida: {eleccion!r}")
        acciones[action_id] = entrada
        self._guardar(acciones)

    def nunca_mas(self, action_id: str) -> bool:
        entrada = self._load().get(action_id) or {}
        return bool(entrada.get("never", False))

    def penalizacion_skips(self, action_id: str) -> float:
        """Score multiplier v0: -15% por skip consecutivo (mínimo 0.4)."""
        entrada = self._load().get(action_id) or {}
        skips = int(entrada.get("skips", 0))
        return max(0.4, 1.0 - 0.15 * skips)
