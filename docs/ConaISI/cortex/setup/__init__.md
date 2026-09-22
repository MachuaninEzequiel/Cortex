# cortex/setup/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/setup/__init__.py` (14 líneas).
- **Módulo Python:** `cortex.setup`.
- **Docstring del módulo:** cortex.setup ------------ Project setup and auto-detection utilities for the ``cortex setup`` command.

## Para qué sirve

cortex.setup
------------
Project setup and auto-detection utilities for the ``cortex setup`` command.

## Relaciones

### Recibe de

- `cortex.setup.cortex_workspace` (ensure_cortex_workspace)
- `cortex.setup.detector` (ProjectContext)
- `cortex.setup.detector` (ProjectDetector)
- `cortex.setup.orchestrator` (SetupOrchestrator)
- `cortex.setup.orchestrator` (format_summary)
- Dependencias externas/stdlib: `__future__`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 14.
Reexportes observados:
- cortex.setup.cortex_workspace: ensure_cortex_workspace
- cortex.setup.detector: ProjectContext
- cortex.setup.detector: ProjectDetector
- cortex.setup.orchestrator: SetupOrchestrator
- cortex.setup.orchestrator: format_summary

---
Fuente: código de `cortex/setup/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
