# src/context/hybrid.rs

## Qué tiene adentro

RRF cross-source. `RRF_K = 60`.

`UnifiedHit`: source, score RRF, `doc_score_raw` (coseno semántico crudo — el enricher usa ESTE para items semánticos, no el RRF), `dropped`, entry/doc, matched_chunk_*.

`search_hybrid`: detecta intent; pesos adaptativos o (1,1); embed query una vez; `fetch_k = top_k*3`; vector_search episódico + semantic_search_vec; fusión dict inserción episódica primero; `score += w / (60 + rank + 1)`; sort estable desc; truncate top_k.

## Para qué sirve

Unificar rankings episódico y semántico.

## Relaciones

### Recibe de

- `NativeEpisodicStore`, `SemanticIndex`, `OnnxEmbedder`, `intent::detect`.

### Envía a

- `ContextEnricher::search_hybrid_for`.

### Notas de implementación observadas en el código

Clave `episodic:{id}` / `semantic:{path absoluto}`. Lookup semántico panics si falta (`fail_lookup`).
