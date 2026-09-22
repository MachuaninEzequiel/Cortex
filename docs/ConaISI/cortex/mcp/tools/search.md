# cortex/mcp/tools/search.py

## Qué tiene adentro

- **Ruta de código:** `cortex/mcp/tools/search.py` (239 líneas).
- **Módulo Python:** `cortex.mcp.tools.search`.
- **Docstring del módulo:** Handlers MCP del dominio búsqueda/contexto (mixín de CortexMCPServer).
- **Clases definidas:**
  - `SearchToolsMixin`
    - Mixín: handlers MCP de búsqueda/contexto.
    - Métodos internos: `_extract_query_keywords`, `_enrich_context`, `_normalize_string_list`, `_extract_candidate_files`, `_build_sync_ticket_context`, `_search_text`, `_search_vector_text`, `_search_text_dispatch`, `_context_text`

## Para qué sirve

Handlers MCP del dominio búsqueda/contexto (mixín de CortexMCPServer).

Extraído del monolito server.py (deuda V1, Obra 01 fase P3). Los métodos
conservan su firma y semántica ``self.`` exactas; el contrato observable
está congelado por tests/unit/mcp/test_golden_contract.py.

## Relaciones

### Recibe de

- `cortex.models` (EnrichedContext)
- `cortex.security.paths` (PathSecurityError, resolve_safe)
- Dependencias externas/stdlib: `re`, `__future__`, `typing`

### Envía a

- `cortex.mcp.server`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 239.

---
Fuente: código de `cortex/mcp/tools/search.py` (AST + grafo de imports internos). No se usó documentación previa.
