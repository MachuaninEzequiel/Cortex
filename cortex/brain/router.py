"""Router determinista del brain (BRAIN-1): intents → herramientas sin LLM.

Fallback degradado y red de seguridad: cubre lo rutinario con 0 tokens.
El LLM (BRAIN-2) se agrega ENCIMA, no en lugar de esto.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Intent:
    tool: str | None = None          # None ⇒ no es una consulta mapeable
    args: dict[str, str] = field(default_factory=dict)
    slash: str | None = None         # comando slash detectado (/help, /quit…)
    razon: str = ""


_PATRONES: list[tuple[str, re.Pattern[str], dict[str, str]]] = [
    ("cortex.health", re.compile(r"cómo está|como esta|estado|salud|health|doctor", re.I), {}),
    ("vault.stats", re.compile(r"cuántas notas|cuantas notas|stats|estadística|estadistica", re.I), {}),
    ("session.current", re.compile(r"sesión|sesion|checkpoint|session", re.I), {}),
    ("webgraph.serve", re.compile(r"webgraph|grafo|abrí el grafo|abri el grafo", re.I), {}),
    ("actions.propose", re.compile(r"acciones|pendiente|sugerí|sugiere|qué hago|que hago", re.I), {}),
]

_SLASHES = {"help", "doctor", "stats", "session", "webgraph", "actions", "quit", "search"}


def route_intent(texto: str) -> Intent:
    """Mapea texto libre → intent determinista. Slash commands tienen prioridad."""
    texto_limpio = texto.strip()
    if texto_limpio.startswith("/"):
        partes = texto_limpio[1:].split(maxsplit=1)
        cmd = partes[0].lower()
        if cmd in _SLASHES:
            return Intent(slash=cmd, args={"resto": partes[1] if len(partes) > 1 else ""})
        return Intent(razon=f"slash desconocido: /{cmd}")

    for tool_name, patron, args_fijos in _PATRONES:
        if patron.search(texto_limpio):
            return Intent(tool=tool_name, args=dict(args_fijos),
                          razon="match de keywords")

    # search semántico: cualquier frase imperativa de búsqueda
    if re.search(r"busca|buscá|search|encontrá|encontrar|relacionad", texto_limpio, re.I):
        query = re.sub(r"^(busca|buscá|search|encontrá)\s+(me\s+)?(docs?\s+(sobre|de)\s+)?",
                       "", texto_limpio, flags=re.I).strip() or texto_limpio
        return Intent(tool="memory.search", args={"query": query}, razon="búsqueda libre")

    # pregunta de relación sin keyword explícita → docs.related pide engine
    if len(texto_limpio.split()) >= 3 and texto_limpio.endswith("?"):
        return Intent(tool="docs.related", args={"tema": texto_limpio.rstrip("?").strip()},
                      razon="pregunta abierta → related con opt-in de engine")

    return Intent(razon="sin match — el brain lista qué sabe hacer")
