# cortex/brain/chat.py

## Qué tiene adentro

- **Ruta de código:** `cortex/brain/chat.py` (147 líneas).
- **Módulo Python:** `cortex.brain.chat`.
- **Docstring del módulo:** DEPRECATED (2026-08-25, doc 12 §4.2): ver cortex/brain/__init__.py.
- **Clases definidas:**
  - `BrainSession`
    - Métodos públicos/especiales: `abrir`, `banner`, `help_texto`, `dispatch`
    - Métodos internos: `__post_init__`
- **Funciones de módulo:**
  - `run_brain(project_root)` — Entry point del comando `cortex brain`.
- **Constantes / símbolos de módulo:** `_BANNER`

## Para qué sirve

DEPRECATED (2026-08-25, doc 12 §4.2): ver cortex/brain/__init__.py.

Loop de chat del brain (BRAIN-1, sin LLM).

``ChatSession`` es inyectable (input_fn/console) para testear sin TTY y
sin modelo. BRAIN-2 agrega el backend llama.cpp ENCIMA de este loop vía
el mismo ``route_intent`` + tool-calling.

## Relaciones

### Recibe de

- `cortex.action_engine.context` (ActionContext)
- `cortex.brain.router` (route_intent)
- `cortex.brain.tools` (Tier, build_tools)
- Dependencias externas/stdlib: `sys`, `__future__`, `dataclasses`, `pathlib`, `rich.console`, `rich.panel`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 147.
Docstrings de símbolos públicos:
- `BrainSession.abrir`: Descubre el proyecto; False si no está inicializado.
- `BrainSession.dispatch`: Procesa una entrada y devuelve la respuesta (puro → testeable).
- `run_brain`: Entry point del comando `cortex brain`.

---
Fuente: código de `cortex/brain/chat.py` (AST + grafo de imports internos). No se usó documentación previa.
