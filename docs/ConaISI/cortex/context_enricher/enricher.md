# cortex/context_enricher/enricher.py

## Qué tiene adentro

- **Ruta de código:** `cortex/context_enricher/enricher.py` (658 líneas).
- **Módulo Python:** `cortex.context_enricher.enricher`.
- **Docstring del módulo:** cortex.context_enricher.enricher --------------------------------- Multi-strategy search engine for the Context Enricher.
- **Clases definidas:**
  - `ContextEnricher`
    - Multi-strategy context enrichment engine.
    - Métodos públicos/especiales: `__init__`, `enrich`
    - Métodos internos: `_finalize_items`, `_search_hybrid`, `_hit_to_enriched_item`, `_unified_hit_to_enriched`, `_episodic_hit_to_enriched`, `_semantic_hit_to_enriched`, `_build_co_occurrence`, `_build_typed_graph`, `_graph_entries`, `_store_cache_token`, `_co_occurrence_score`
- **Funciones de módulo:**
  - `_doc_type_from_doc(doc)` — Best-effort DocType slug for a SemanticDocument.
  - `_status_from_doc(doc)` — Status from frontmatter when available.
- **Constantes / símbolos de módulo:** `_SUBFOLDER_TO_TYPE_SLUG`

## Para qué sirve

cortex.context_enricher.enricher
---------------------------------
Multi-strategy search engine for the Context Enricher.

Takes a WorkContext, executes parallel searches across multiple
strategies (topic, files, keywords, pr_title), deduplicates results
by ID, applies multi-match boost and co-occurrence boost, enforces
threshold and budget, and returns an EnrichedContext.

## Relaciones

### Recibe de

- `cortex.context_enricher.config` (ContextEnricherConfig)
- `cortex.models` (EnrichedContext, EnrichedItem, EpisodicHit)
- Dependencias externas/stdlib: `logging`, `__future__`, `collections`, `typing`

### Envía a

- `cortex.cli.docs_search`
- `cortex.context_enricher`
- `cortex.context_enricher.async_enricher`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 658.
Docstrings de símbolos públicos:
- `ContextEnricher.enrich`: Execute multi-strategy search and return enriched context.

---
Fuente: código de `cortex/context_enricher/enricher.py` (AST + grafo de imports internos). No se usó documentación previa.
