# cortex/cli/common.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/common.py` (97 líneas).
- **Módulo Python:** `cortex.cli.common`.
- **Docstring del módulo:** Plomería compartida entre los submódulos de ``cortex.cli``.
- **Funciones de módulo:**
  - `_load_memory(project_root)` — Return an ``AgentMemory`` rooted at *project_root* (or CWD if None).
  - `_get_staged_files()` — Get list of staged (and modified) files from git.
- **Constantes / símbolos de módulo:** `_DEFAULT_CONFIG`

## Para qué sirve

Plomería compartida entre los submódulos de ``cortex.cli``.

Extraída de cli/main.py (deuda V2, Obra 01 fase P4) para que los
subapps importen de acá sin ciclos: main.py también importa de este
módulo, nunca al revés.

## Relaciones

### Recibe de

- `cortex.core` (AgentMemory)
- Dependencias externas/stdlib: `subprocess`, `sys`, `typer`, `__future__`, `pathlib`

### Envía a

- `cortex.cli.documenting`
- `cortex.cli.embedding`
- `cortex.cli.hu`
- `cortex.cli.main`
- `cortex.cli.pr_context`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 97.

---
Fuente: código de `cortex/cli/common.py` (AST + grafo de imports internos). No se usó documentación previa.
