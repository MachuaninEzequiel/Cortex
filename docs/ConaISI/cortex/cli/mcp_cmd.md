# cortex/cli/mcp_cmd.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/mcp_cmd.py` (49 líneas).
- **Módulo Python:** `cortex.cli.mcp_cmd`.
- **Docstring del módulo:** ``cortex mcp-server`` — servidor MCP sobre stdio.
- **Funciones de módulo:**
  - `register(app)` — Registra ``mcp-server`` y el alias oculto ``mcp-serve``.

## Para qué sirve

``cortex mcp-server`` — servidor MCP sobre stdio.

Extraído del monolito cli/main.py (deuda V2, Obra 01 fase P4).

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `asyncio`, `sys`, `typer`, `__future__`, `pathlib`

### Envía a

- `cortex.cli.main`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 49.
Docstrings de símbolos públicos:
- `register`: Registra ``mcp-server`` y el alias oculto ``mcp-serve``.

---
Fuente: código de `cortex/cli/mcp_cmd.py` (AST + grafo de imports internos). No se usó documentación previa.
