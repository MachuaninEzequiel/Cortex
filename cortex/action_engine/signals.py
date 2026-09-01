"""Señales de feedback real para el score del scheduler (Obra 05 Fase E).

La marca [y]=útil de la búsqueda TUI (y cualquier feedback explícito
persistido) alimenta la prioridad: dominio negativo ⇒ suben calidad/
mantenimiento (retrieval malo = problemas de índice/docs); dominio
positivo ⇒ suben aprendizaje/conocimiento (usuario comprometido).
Ventana por defecto: 14 días.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

VENTANA_DIAS_DEFAULT = 14


@dataclass(frozen=True)
class MemorySignals:
    positivos: int
    negativos: int

    @property
    def dominio(self) -> str:
        if self.positivos > self.negativos:
            return "positivo"
        if self.negativos > self.positivos:
            return "negativo"
        return "neutro"


def leer_senales(
    dot_cortex: Path, *, dias: int = VENTANA_DIAS_DEFAULT
) -> MemorySignals:
    """Lee feedback.jsonl (+rotado) filtrando a la ventana temporal."""
    ruta = Path(dot_cortex) / "feedback.jsonl"
    rotado = Path(dot_cortex) / "feedback.1.jsonl"
    corte = datetime.now(UTC) - timedelta(days=dias)

    positivos = negativos = 0
    for archivo in (rotado, ruta):
        if not archivo.exists():
            continue
        try:
            for linea in archivo.read_text(encoding="utf-8").splitlines():
                if not linea.strip():
                    continue
                try:
                    evento = json.loads(linea)
                except json.JSONDecodeError:
                    continue
                ts = _parse_ts(evento.get("ts"))
                if ts is not None and ts < corte:
                    continue
                tipo = str(evento.get("feedback_type", ""))
                if tipo in ("positive", "useful"):
                    positivos += 1
                elif tipo in ("negative", "not_useful"):
                    negativos += 1
        except OSError:
            continue
    return MemorySignals(positivos=positivos, negativos=negativos)


def multiplicador_categoria(categoria: str, senales: MemorySignals | None) -> float:
    """Multiplicador suave (tope ±25%) según dominio del feedback."""
    if senales is None or senales.dominio == "neutro":
        return 1.0
    delta = abs(senales.positivos - senales.negativos)
    factor = min(1.25, 1.0 + 0.05 * delta)
    if senales.dominio == "negativo":
        return factor if categoria in ("quality", "maintenance") else 1.0
    return factor if categoria in ("learning", "knowledge") else 1.0


def _parse_ts(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
