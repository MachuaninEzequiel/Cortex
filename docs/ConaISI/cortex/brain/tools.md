# cortex/brain/tools.py

## Qué tiene adentro

- **Ruta de código:** `cortex/brain/tools.py` (176 líneas).
- **Módulo Python:** `cortex.brain.tools`.
- **Docstring del módulo:** DEPRECATED (2026-08-25, doc 12 §4.2): ver cortex/brain/__init__.py.
- **Clases definidas:**
  - `Tier` (str, Enum)
  - `ToolSpec`
- **Funciones de módulo:**
  - `build_tools(ctx)` — Construye el registro de herramientas anclado al proyecto de *ctx*.

## Para qué sirve

DEPRECATED (2026-08-25, doc 12 §4.2): ver cortex/brain/__init__.py.

Herramientas del brain — read-only + safe-action, sobre servicios existentes.

Contrato (doc 06 §BRAIN v1):
- ``Tier.READ``: consulta pura, sin side-effects.
- ``Tier.SAFE_ACTION``: side-effect externo no destructivo whitelisteado
  (único permitido hoy: webgraph.serve).
- Las MUTACIONES no son herramientas: ``actions_propose`` devuelve el
  comando CLI exacto para que el usuario las ejecute ("propone, no ejecuta").

## Relaciones

### Recibe de

- `cortex.action_engine.context` (ActionContext)
- Dependencias externas/stdlib: `subprocess`, `sys`, `__future__`, `collections.abc`, `dataclasses`, `enum`, `pathlib`

### Envía a

- `cortex.brain`
- `cortex.brain.chat`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 176.
Docstrings de símbolos públicos:
- `build_tools`: Construye el registro de herramientas anclado al proyecto de *ctx*.

---
Fuente: código de `cortex/brain/tools.py` (AST + grafo de imports internos). No se usó documentación previa.
