# cortex/retrieval/hybrid_search.py

## Qué tiene adentro

- Clase `HybridSearch` y constante `_RRF_K = 60`.
- Singleton de módulo `_intent_detector = QueryIntentDetector()`.
- `search(query, top_k, use_embeddings)`: over-fetch `k*3` de cada fuente, ajusta pesos, fusiona.
- `_rrf_fuse`: `score += weight / (60 + rank)` por fuente; claves `episodic:{id}` y `semantic:{path}`.
- `detect_intent` público para tests/observabilidad.

Pesos adaptativos (si `adaptive_weights=True`, default):
- Intent episódico → `episodic_weight × intent.episodic_weight` (típicamente ×2 / ×0.6).
- Intent semántico → inverso.
- Mixed → 1.0 / 1.0.

## Para qué sirve

Único motor de retrieval híbrido de la fachada local: une Chroma (episódico) y vault (semántico) en una lista `unified_hits`.

## Relaciones

### Recibe de

- `EpisodicMemoryStore.search` y `VaultReader.search` (inyectados; TYPE_CHECKING).
- `QueryIntentDetector` (`cortex.retrieval.intent`).
- Modelos `EpisodicHit`, `SemanticDocument`, `UnifiedHit`, `RetrievalResult`.

### Envía a

- `AgentMemory.retrieve` (scope local).
- Reexportado por `cortex.retrieval` y `cortex.__init__`.
- El resultado alimenta CLI `search`, MCP `cortex_search` / `cortex_search_vector`, enricher (indirecto vía stores).

### Notas de implementación observadas en el código

- Over-fetch ×3 para que el RRF tenga candidatos.
- `result.intent` queda en el `RetrievalResult` (campo `exclude=True` en serialización Pydantic).
- No habla con enterprise: ese camino es `EnterpriseRetrievalService` en `core.retrieve`.

---
Fuente: lectura de `cortex/retrieval/hybrid_search.py`. No se usó documentación previa.
