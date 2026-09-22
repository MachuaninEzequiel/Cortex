# cortex/documenter/contradiction_detector.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documenter/contradiction_detector.py` (93 líneas).
- **Módulo Python:** `cortex.documenter.contradiction_detector`.
- **Docstring del módulo:** cortex.documenter.contradiction_detector — Pluggable memory-search.
- **Clases definidas:**
  - `ContradictionFinding`
    - A potential conflict between current work and prior decisions.
  - `ContradictionDetector` (Protocol)
    - Interface for memory-search-based contradiction detection.
    - Métodos públicos/especiales: `find_contradictions`
  - `NoOpContradictionDetector`
    - Default detector: returns an empty list.
    - Métodos públicos/especiales: `find_contradictions`
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.documenter.contradiction_detector — Pluggable memory-search.

The reconstruction algorithm (§7.2 step 5) checks for contradictions
between the current diff and prior decisions stored in Cortex memory.
That check requires the full :class:`cortex.core.AgentMemory` façade
(ChromaDB, ONNX embeddings, vault reader) which is too heavy for the
CLI ``cortex finish-session`` path.

To keep the reconstructor lightweight and testable, contradiction
detection is **pluggable** via the :class:`ContradictionDetector`
Protocol. The CLI passes :class:`NoOpContradictionDetector` (returns no
findings); the MCP-invoked documenter subagent — which already holds an
``AgentMemory`` — can provide a real implementation backed by
``cortex_search``.

Phase 02+ may promote a default implementation here as soon as a
lightweight semantic search becomes available without loading the full
memory stack.

## Relaciones

### Recibe de

- `cortex.session.models` (Checkpoint)
- Dependencias externas/stdlib: `__future__`, `collections.abc`, `dataclasses`, `typing`

### Envía a

- `cortex.documenter`
- `cortex.documenter.reconstruction`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 93.
Docstrings de símbolos públicos:
- `ContradictionDetector.find_contradictions`: Return contradictions between the current work and past records.

---
Fuente: código de `cortex/documenter/contradiction_detector.py` (AST + grafo de imports internos). No se usó documentación previa.
