# cortex/cli/_search_filters.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/_search_filters.py` (104 líneas).
- **Módulo Python:** `cortex.cli._search_filters`.
- **Docstring del módulo:** Shared helper to build ``EnrichmentFilters`` from CLI/MCP flags.
- **Funciones de módulo:**
  - `_to_doc_types(slugs)`
  - `build_enrichment_filters_from_cli()` — Build ``EnrichmentFilters`` from CLI flag values.
  - `has_any_filter()` — Return True when at least one structural flag is engaged.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

Shared helper to build ``EnrichmentFilters`` from CLI/MCP flags.

Used by both ``cortex search`` (top-level command) and ``cortex docs search``
(canonical subcommand) so the parsing of ``--doc-type`` / ``--scope`` /
``--tag`` / ``--max-age-days`` / ``--strict`` stays in one place.

Extracted as part of Item #7 (deuda residual canonical-documentation).

## Relaciones

### Recibe de

- `cortex.context_enricher.filters` (EnrichmentFilters)
- `cortex.documentation.doc_type` (DocType)
- Dependencias externas/stdlib: `__future__`, `collections.abc`

### Envía a

- `cortex.cli.docs_search`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 104.
Docstrings de símbolos públicos:
- `build_enrichment_filters_from_cli`: Build ``EnrichmentFilters`` from CLI flag values.
- `has_any_filter`: Return True when at least one structural flag is engaged.

---
Fuente: código de `cortex/cli/_search_filters.py` (AST + grafo de imports internos). No se usó documentación previa.
