# cortex/mcp/tools/documenter.py

## Qué tiene adentro

- **Ruta de código:** `cortex/mcp/tools/documenter.py` (415 líneas).
- **Módulo Python:** `cortex.mcp.tools.documenter`.
- **Docstring del módulo:** Handlers MCP del dominio spec/proposal/documenter (mixín de CortexMCPServer).
- **Clases definidas:**
  - `DocumenterToolsMixin`
    - Mixín: handlers MCP de spec/proposal/documenter.
    - Métodos internos: `_create_spec_text`, `_validate_proposal_gap`, `_emit_proposal_text`, `_self_review_note_text`, `_finish_session_text`, `_documenter_briefing_text`
- **Funciones de módulo:**
  - `_serialize_reconstruction(out)` — Serialize a :class:`ReconstructionOutput` to JSON-safe dict.

## Para qué sirve

Handlers MCP del dominio spec/proposal/documenter (mixín de CortexMCPServer).

Extraído del monolito server.py (deuda V1, Obra 01 fase P3). Los métodos
conservan su firma y semántica ``self.`` exactas; el contrato observable
está congelado por tests/unit/mcp/test_golden_contract.py.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `json`, `logging`, `__future__`, `datetime`, `typing`

### Envía a

- `cortex.mcp.server`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 415.

---
Fuente: código de `cortex/mcp/tools/documenter.py` (AST + grafo de imports internos). No se usó documentación previa.
