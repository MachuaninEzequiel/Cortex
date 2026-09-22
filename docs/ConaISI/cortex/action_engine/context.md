# cortex/action_engine/context.py

## Qué tiene adentro

- **Ruta de código:** `cortex/action_engine/context.py` (69 líneas).
- **Módulo Python:** `cortex.action_engine.context`.
- **Docstring del módulo:** Contexto de servicios para las acciones del catálogo (Obra 05 Fase B).
- **Clases definidas:**
  - `ActionContext`
    - Métodos públicos/especiales: `from_project_root`, `dot_cortex`, `vault_path`, `config_existe`, `mem`, `sessions`

## Para qué sirve

Contexto de servicios para las acciones del catálogo (Obra 05 Fase B).

Regla dura #1 del contrato: toda acción delega en su servicio. El
``ActionContext`` agrupa esas dependencias con carga PEREZOSA — el gate
de ``cortex next`` es <2s en repo mediano, así que nada pesado (ChromaDB,
ONNX) se construye salvo que una acción lo necesite realmente.

## Relaciones

### Recibe de

- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `__future__`, `dataclasses`, `pathlib`

### Envía a

- `cortex.action_engine.actions`
- `cortex.action_engine.actions.catalog`
- `cortex.brain.chat`
- `cortex.brain.tools`
- `cortex.cli.next`
- `cortex.tui.core`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 69.
Docstrings de símbolos públicos:
- `ActionContext.dot_cortex`: Directorio ``.cortex`` real (workspace_root ya lo es en layout nuevo;

---
Fuente: código de `cortex/action_engine/context.py` (AST + grafo de imports internos). No se usó documentación previa.
