"""cortex.brain — asistente local experto del proyecto (Obra 06 BRAIN v1).

Permisos estrictos (dueño, 2026-08-23):
- READ: consulta pura (search/doctor/stats/sesión).
- SAFE_ACTION: side-effects no destructivos whitelisteables (webgraph serve).
- Mutaciones NUNCA: se proponen con el comando CLI exacto ("propone, no ejecuta").

Fases: BRAIN-1 núcleo sin LLM (router determinista) · BRAIN-2 llama.cpp/GGUF ·
BRAIN-3 ventana dedicada + logo. Ver doc 06 §BRAIN v1.
"""

from cortex.brain.tools import Tier, ToolSpec, build_tools

__all__ = ["Tier", "ToolSpec", "build_tools"]
