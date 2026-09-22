# cortex/brain/router.py

## Qué tiene adentro

- **Ruta de código:** `cortex/brain/router.py` (61 líneas).
- **Módulo Python:** `cortex.brain.router`.
- **Docstring del módulo:** DEPRECATED (2026-08-25, doc 12 §4.2): ver cortex/brain/__init__.py.
- **Clases definidas:**
  - `Intent`
- **Funciones de módulo:**
  - `route_intent(texto)` — Mapea texto libre → intent determinista. Slash commands tienen prioridad.
- **Constantes / símbolos de módulo:** `_PATRONES`, `_SLASHES`

## Para qué sirve

DEPRECATED (2026-08-25, doc 12 §4.2): ver cortex/brain/__init__.py.

Router determinista del brain (BRAIN-1): intents → herramientas sin LLM.

Fallback degradado y red de seguridad: cubre lo rutinario con 0 tokens.
El LLM (BRAIN-2) se agrega ENCIMA, no en lugar de esto.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `re`, `__future__`, `dataclasses`

### Envía a

- `cortex.brain.chat`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 61.
Docstrings de símbolos públicos:
- `route_intent`: Mapea texto libre → intent determinista. Slash commands tienen prioridad.

---
Fuente: código de `cortex/brain/router.py` (AST + grafo de imports internos). No se usó documentación previa.
