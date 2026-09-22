# cortex/mcp/schemas.py

## Qué tiene adentro

- **Ruta de código:** `cortex/mcp/schemas.py` (1079 líneas).
- **Módulo Python:** `cortex.mcp.schemas`.
- **Docstring del módulo:** Definiciones (schemas) de las tools MCP — fuente única.
- **Funciones de módulo:**
  - `build_tool_definitions()` — Definiciones exactas de las 32 tools anunciadas por list_tools.
- **Constantes / símbolos de módulo:** `_CHECKPOINT_SOURCE_VALUES`

## Para qué sirve

Definiciones (schemas) de las tools MCP — fuente única.

Extraído del monolito ``server.py`` (deuda V1, Obra 01 fase P3). El
contrato completo está congelado por
``tests/unit/mcp/test_golden_contract.py`` contra
``golden/list_tools.json``: cualquier cambio acá en nombres,
descriptions o inputSchema DEBE reflejarse en ese snapshot y estar
documentado en docs/transformacion/.

## Relaciones

### Recibe de

- `cortex.session.models` (CheckpointSource)
- Dependencias externas/stdlib: `mcp.types`, `__future__`

### Envía a

- `cortex.mcp.server`
- `cortex.mcp.tools.sessions`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 1079.
Docstrings de símbolos públicos:
- `build_tool_definitions`: Definiciones exactas de las 32 tools anunciadas por list_tools.

---
Fuente: código de `cortex/mcp/schemas.py` (AST + grafo de imports internos). No se usó documentación previa.
