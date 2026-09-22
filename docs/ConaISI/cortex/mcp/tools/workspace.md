# cortex/mcp/tools/workspace.py

## Qué tiene adentro

- **Ruta de código:** `cortex/mcp/tools/workspace.py` (204 líneas).
- **Módulo Python:** `cortex.mcp.tools.workspace`.
- **Docstring del módulo:** Handlers MCP del dominio workspace/docs/HU (mixín de CortexMCPServer).
- **Clases definidas:**
  - `WorkspaceToolsMixin`
    - Mixín: handlers MCP de workspace/docs/HU.
    - Métodos internos: `_write_design_note_text`, `_write_doc_text`, `_import_hu_text`, `_get_hu_text`

## Para qué sirve

Handlers MCP del dominio workspace/docs/HU (mixín de CortexMCPServer).

Extraído del monolito server.py (deuda V1, Obra 01 fase P3). Los métodos
conservan su firma y semántica ``self.`` exactas; el contrato observable
está congelado por tests/unit/mcp/test_golden_contract.py.

## Relaciones

### Recibe de

- `cortex.mcp.vault_adapter` (PathVault)
- Dependencias externas/stdlib: `json`, `__future__`, `typing`

### Envía a

- `cortex.mcp.server`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 204.

---
Fuente: código de `cortex/mcp/tools/workspace.py` (AST + grafo de imports internos). No se usó documentación previa.
