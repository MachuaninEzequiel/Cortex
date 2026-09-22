# cortex/cli/_setup_helpers.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/_setup_helpers.py` (66 líneas).
- **Módulo Python:** `cortex.cli._setup_helpers`.
- **Docstring del módulo:** cortex.cli._setup_helpers ------------------------- Helpers compartidos por los comandos ``cortex setup *``.
- **Funciones de módulo:**
  - `select_ide_interactive(provided_ide, non_interactive)` — Resolve the target IDE for setup.

## Para qué sirve

cortex.cli._setup_helpers
-------------------------
Helpers compartidos por los comandos ``cortex setup *``.

Fase 6 del plan multi-IDE & MCP hardening (2026-05-15):
Centraliza la seleccion de IDE para que ``cortex setup full`` y
``cortex setup agent`` compartan la misma logica. Antes, ``setup_agent``
tenia un bloque interactivo de ~20 lineas y ``setup_full`` no tenia
prompt en absoluto — obligando al adopter a correr dos comandos para
configurar IDE + pipeline + webgraph.

## Relaciones

### Recibe de

- `cortex.ide`
- Dependencias externas/stdlib: `typer`, `__future__`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 66.
Docstrings de símbolos públicos:
- `select_ide_interactive`: Resolve the target IDE for setup.

---
Fuente: código de `cortex/cli/_setup_helpers.py` (AST + grafo de imports internos). No se usó documentación previa.
