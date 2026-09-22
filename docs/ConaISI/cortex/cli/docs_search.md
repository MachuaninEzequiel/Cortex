# cortex/cli/docs_search.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/docs_search.py` (125 líneas).
- **Módulo Python:** `cortex.cli.docs_search`.
- **Docstring del módulo:** cortex.cli.docs_search - ``cortex docs search`` with structural filters (Fase 13).
- **Funciones de módulo:**
  - `search(query, project_root, top_k, doc_type, exclude_doc_type, status, tag, tag_any, scope, max_age_days, project_id, strict, output_format)` — Search the canonical vault honouring structural filters.
  - `_build_enricher(project_root)` — Construct a ``ContextEnricher`` with the project's episodic + semantic stores.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.cli.docs_search - ``cortex docs search`` with structural filters (Fase 13).

The legacy ``cortex search`` exposes the raw hybrid-RRF retrieval over both
memory layers. This new subcommand sits on top of ``ContextEnricher.enrich()``
and exposes the structural filters (``doc_types``, ``vault_scope``,
``max_age_days``, ``tags_required``) plus DocIntent boost introduced in Fase 08.

Output formats:

    - text (default): human-readable, grouped by DocType.
    - json:           full ``EnrichedContext`` payload.
    - compact:        single-line per item, LLM-friendly.

## Relaciones

### Recibe de

- `cortex.cli._search_filters` (build_enrichment_filters_from_cli)
- `cortex.context_enricher.config` (ContextEnricherConfig)
- `cortex.context_enricher.enricher` (ContextEnricher)
- `cortex.context_enricher.presenter` (ContextPresenter)
- Dependencias externas/stdlib: `typer`, `__future__`, `pathlib`

### Envía a

- `cortex.cli.docs_subcommand`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 125.
Docstrings de símbolos públicos:
- `search`: Search the canonical vault honouring structural filters.

---
Fuente: código de `cortex/cli/docs_search.py` (AST + grafo de imports internos). No se usó documentación previa.
