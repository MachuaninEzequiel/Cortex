# cortex/tutor/hint.py

## Qué tiene adentro

- **Ruta de código:** `cortex/tutor/hint.py` (218 líneas).
- **Módulo Python:** `cortex.tutor.hint`.
- **Docstring del módulo:** cortex.tutor.hint ----------------- Contextual hint engine that inspects the current project state and suggests the most relevant next action. Zero tokens consumed.
- **Clases definidas:**
  - `Hint`
    - A single contextual tip.
    - Métodos públicos/especiales: `render`
  - `ProjectState`
    - Detected state of the current project directory.
    - Métodos públicos/especiales: `detect`
  - `HintEngine`
    - Generates contextual tips based on project state.
    - Métodos públicos/especiales: `get_hint`

## Para qué sirve

cortex.tutor.hint
-----------------
Contextual hint engine that inspects the current project state
and suggests the most relevant next action. Zero tokens consumed.

EPIC 6: Uses WorkspaceLayout for path detection so both new
and legacy layouts work correctly.

## Relaciones

### Recibe de

- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `__future__`, `dataclasses`, `pathlib`, `rich.console`, `rich.panel`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 218.
Docstrings de símbolos públicos:
- `Hint.render`: Render the hint as a rich panel.
- `ProjectState.detect`: Inspect the filesystem at project_root and build state.
- `HintEngine.get_hint`: Return the most relevant hint for the current state.

---
Fuente: código de `cortex/tutor/hint.py` (AST + grafo de imports internos). No se usó documentación previa.
