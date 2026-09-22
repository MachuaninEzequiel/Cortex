# cortex/context_enricher/async_enricher.py

## Qué tiene adentro

- **Ruta de código:** `cortex/context_enricher/async_enricher.py` (290 líneas).
- **Módulo Python:** `cortex.context_enricher.async_enricher`.
- **Docstring del módulo:** cortex.context_enricher.async_enricher ---------------------------------------- AsyncContextEnricher — parallel multi-strategy search using asyncio.
- **Clases definidas:**
  - `AsyncContextEnricher` (ContextEnricher)
    - Parallel multi-strategy context enrichment engine.
    - Métodos públicos/especiales: `__init__`, `enrich`, `enrich_async`
    - Métodos internos: `_build_strategy_tasks`, `_run_entity_search`, `_process_results`

## Para qué sirve

cortex.context_enricher.async_enricher
----------------------------------------
AsyncContextEnricher — parallel multi-strategy search using asyncio.

The existing ContextEnricher runs all 4+ search strategies sequentially.
For a memory store with N memories, each strategy call is an independent
ChromaDB vector search — there is no shared state between them and no
reason to wait for strategy 1 to finish before starting strategy 2.

This module wraps the synchronous strategies in an asyncio executor pool,
running them concurrently. For 4 strategies with ~100ms latency each, this
reduces wall-clock time from ~400ms to ~100ms (4× speedup).

Architecture
------------
``AsyncContextEnricher`` does NOT replace ``ContextEnricher``. It inherits
from it and overrides only the ``enrich`` method (public API), delegating
all business logic (dedup, boost, threshold, budget) to the parent class.
The parent's phase 2-6 processing runs on the results aggregated from
the parallel phase 1.

Backward compatibility
----------------------
All existing code using ``ContextEnricher`` continues to work unchanged.
To opt-in to async execution:

    enricher = AsyncContextEnricher(episodic, semantic, config)
    result = await enricher.enrich_async(work)

Or run synchronously (using the same thread pool under the hood):

    result = enricher.enrich(work)  # blocks, runs strategies in parallel

## Relaciones

### Recibe de

- `cortex.context_enricher.config` (ContextEnricherConfig)
- `cortex.context_enricher.filters` (EnrichmentFilters)
- `cortex.context_enricher.enricher` (ContextEnricher)
- `cortex.models` (EnrichedContext)
- Dependencias externas/stdlib: `asyncio`, `logging`, `__future__`, `collections.abc`, `concurrent.futures`, `typing`

### Envía a

- `cortex.context_enricher`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 290.
Docstrings de símbolos públicos:
- `AsyncContextEnricher.enrich`: Synchronous entry point — runs parallel strategies and blocks.
- `AsyncContextEnricher.enrich_async`: Async entry point — run strategies in parallel, then process results.

---
Fuente: código de `cortex/context_enricher/async_enricher.py` (AST + grafo de imports internos). No se usó documentación previa.
