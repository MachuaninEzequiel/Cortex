# cortex/mcp/tools/sessions.py

## Qué tiene adentro

- **Ruta de código:** `cortex/mcp/tools/sessions.py` (523 líneas).
- **Módulo Python:** `cortex.mcp.tools.sessions`.
- **Docstring del módulo:** Handlers MCP del dominio sesiones/checkpoints/tasks (mixín de CortexMCPServer).
- **Clases definidas:**
  - `SessionToolsMixin`
    - Mixín: handlers MCP de sesiones/checkpoints/tasks.
    - Métodos internos: `_save_session_text`, `_session_open_text`, `_session_checkpoint_text`, `_session_close_text`, `_session_status_text`, `_session_task_list_text`, `_session_task_update_text`, `_session_review_checkpoint_text`, `_close_session_text`, `_session_list_text`, `_validate_handoff_text`, `_verify_session_claims_text`

## Para qué sirve

Handlers MCP del dominio sesiones/checkpoints/tasks (mixín de CortexMCPServer).

Extraído del monolito server.py (deuda V1, Obra 01 fase P3). Los métodos
conservan su firma y semántica ``self.`` exactas; el contrato observable
está congelado por tests/unit/mcp/test_golden_contract.py.

## Relaciones

### Recibe de

- `cortex.mcp.schemas` (_CHECKPOINT_SOURCE_VALUES)
- Dependencias externas/stdlib: `json`, `logging`, `__future__`, `typing`

### Envía a

- `cortex.mcp.server`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 523.

---
Fuente: código de `cortex/mcp/tools/sessions.py` (AST + grafo de imports internos). No se usó documentación previa.
