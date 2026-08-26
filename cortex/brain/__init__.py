"""cortex.brain — DEPRECATED (dueño, 2026-08-25 — doc 12 §4.2).

Duplicado legacy del brain oficial `cortex-brain` (Rust + llama.cpp, Obra 06
fase final). Solo se mantiene como oráculo hasta la baja definitiva de
Python; el subcomando nativo ya no pasa por acá.

Permisos históricos (dueño, 2026-08-23):
- READ: consulta pura (search/doctor/stats/sesión).
- SAFE_ACTION: side-effects no destructivos whitelisteables (webgraph serve).
- Mutaciones NUNCA: se proponen con el comando CLI exacto ("propone, no ejecuta").

Fases: BRAIN-1 núcleo sin LLM (router determinista) · BRAIN-2 llama.cpp/GGUF ·
BRAIN-3 ventana dedicada + logo. Ver doc 06 §BRAIN v1.
"""

from cortex.brain.tools import Tier, ToolSpec, build_tools

__all__ = ["Tier", "ToolSpec", "build_tools"]
