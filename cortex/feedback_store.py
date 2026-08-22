"""Persistencia de feedback en ``.cortex/feedback.jsonl`` (Obra 05 Fase A).

Hasta ahora ``FeedbackCollector`` era puramente en memoria: cada proceso
arrancaba sin historia y el paso APRENDER del ActionEngine no tenía
materia prima. Este store añade persistencia append-only con rotación,
sin cambiar el comportamiento de ningún consumidor existente.

Formato: una línea JSON por evento::

    {"ts": "...", "type": "explicit", "memory_id": "...",
     "feedback_type": "useful", "source": "tui"}

Rotación: cuando el archivo supera ``max_bytes`` se renombra a
``<nombre>.1.jsonl`` (se descarta la generación previa). Simple,
crash-safe (append atómico por línea) y suficiente para v1.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_FEEDBACK_FILE = "feedback.jsonl"


class FeedbackStore:
    """Append-only JSONL store con rotación de una generación."""

    def __init__(
        self,
        directory: Path,
        filename: str = DEFAULT_FEEDBACK_FILE,
        max_bytes: int = 5 * 1024 * 1024,
    ) -> None:
        self._dir = Path(directory)
        self._path = self._dir / filename
        self._max_bytes = max_bytes

    @property
    def path(self) -> Path:
        return self._path

    def append(self, event: dict[str, object]) -> None:
        """Agrega un evento; completa ``ts`` si falta. Nunca explota."""
        evento = dict(event)
        evento.setdefault("ts", datetime.now(UTC).isoformat(timespec="milliseconds"))
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            self._rotar_si_corresponde()
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(evento, ensure_ascii=False, default=str) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        except OSError:
            logger.warning("No se pudo persistir feedback en %s", self._path, exc_info=True)

    def _rotar_si_corresponde(self) -> None:
        if not self._path.exists() or self._path.stat().st_size < self._max_bytes:
            return
        rotado = self._path.with_suffix(".1.jsonl")
        if rotado.exists():
            rotado.unlink()  # v1: una sola generación histórica
        self._path.rename(rotado)
        logger.info("Feedback rotado a %s", rotado.name)

    def load(self) -> list[dict[str, object]]:
        """Lee todos los eventos válidos (los corruptos se saltan con warning)."""
        eventos: list[dict[str, object]] = []
        for ruta in (self._path, self._path.with_suffix(".1.jsonl")):
            if not ruta.exists():
                continue
            for linea in ruta.read_text(encoding="utf-8").splitlines():
                if not linea.strip():
                    continue
                try:
                    eventos.append(json.loads(linea))
                except json.JSONDecodeError:
                    logger.warning("Línea corrupta en %s: %r", ruta.name, linea[:80])
        return eventos
