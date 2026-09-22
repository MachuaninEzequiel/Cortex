# rust/crates/cortex-mcp/src/handlers_search.rs

## Qué tiene adentro

Mirrors de retrieval (`REntry`, `RDoc`, `RHit`, `RetrievalMirror`, `Enriched*`). Trait `SearchBackend`. `extract_query_keywords`, `normalize_string_list`, `extract_candidate_files`. Handlers: `search_vector_text`, `search_text_dispatch` (si hay filtros estructurales → ContextEnricher path), `context_text`, `enrich_context`, `build_sync_ticket_context`.

## Para qué sirve

Tools `cortex_search`, `cortex_search_vector`, `cortex_context`, `cortex_sync_ticket`.

## Relaciones

### Recibe de

- Query/limit/filtros del tool.
- `SearchBackend` (prod: `NativeSearchBackend` sobre SemanticIndex + episódico + ONNX opcional).

### Envía a

- Texto/JSON de hits al agente.

### Notas de implementación observadas en el código

Si `doc_type`/status/tags/etc. vienen informados, `search` no usa RRF crudo: usa enricher (mismo backend que `cortex docs search`).
