# cortex/context_enricher/filters.py

## Qué tiene adentro

- **Ruta de código:** `cortex/context_enricher/filters.py` (150 líneas).
- **Módulo Python:** `cortex.context_enricher.filters`.
- **Docstring del módulo:** cortex.context_enricher.filters - Structural filters for enrichment.
- **Clases definidas:**
  - `EnrichmentFilters` (BaseModel)
    - Structural filters applied after retrieval but before budget.
    - Métodos públicos/especiales: `is_empty`
- **Funciones de módulo:**
  - `apply_filters(items, filters)` — Apply ``filters`` to ``items``. Returns a new list (never mutates).
  - `_passes(item, f, now)`
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.context_enricher.filters - Structural filters for enrichment.

The motor of retrieval is content-driven (vector similarity + BM25). The
filters in this module sit on top of that result set and remove items that
the caller knows are irrelevant *because of their metadata*:

    - ``doc_types``     keep only items of the given DocType(s).
    - ``statuses_*``    keep items in/out of given statuses.
    - ``tags_*``        AND/OR semantics over frontmatter tags.
    - ``vault_scope``   local-only, enterprise-only, or both.
    - ``max_age_days``  drop items older than the window.
    - ``project_ids``   multi-tenant filter for enterprise.
    - ``strict``        in strict mode, items without ``doc_type`` are
                        excluded when ``doc_types`` is set.

All fields are optional. With every field at its default (``filters=None``
or an empty ``EnrichmentFilters()``), ``apply_filters`` is a no-op.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (DocType)
- `cortex.models` (EnrichedItem)
- Dependencias externas/stdlib: `__future__`, `datetime`, `pydantic`

### Envía a

- `cortex.cli._search_filters`
- `cortex.context_enricher.async_enricher`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 150.
Docstrings de símbolos públicos:
- `EnrichmentFilters.is_empty`: Return ``True`` when every field is at its default.
- `apply_filters`: Apply ``filters`` to ``items``. Returns a new list (never mutates).

---
Fuente: código de `cortex/context_enricher/filters.py` (AST + grafo de imports internos). No se usó documentación previa.
