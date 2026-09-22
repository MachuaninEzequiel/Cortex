# src/context/mod.rs

## Qué tiene adentro

`ContextEnricher` (P7). Config default: min_score 0.1, domain_confidence 0.5, max_items 8, max_chars 2000, multi_match_boost 1.5, co_occurrence_boost 0.3, flags topic/files/keywords/pr_title/graph/entity/typed/decay/feedback true, half_life 168h, floor 0.10, implicit_boost 0.15.

`enrich(work, embedder, top_k, now)`:
1. Estrategias en orden Python: topic/file/keyword/pr_title vía `search_hybrid` (fetch_k = max_items*2).
2. Entity search sobre function/class/imports/keywords (cotas 5/3/5/3 y max_results 3/2/2/1); dedup por id mayor score; esos hits van `dropped=true` (solo inflan total_raw_hits).
3. Dedup por source_id, multi-match, co-ocurrencia naive y tipada, decay, feedback, DocIntent boost, umbral, presupuesto.
4. `infer_doc_type_from_path`.

Submódulos listados en el archivo.

## Para qué sirve

Construir el bundle de contexto enriquecido para un `WorkContext` (PR/diff/manual).

## Relaciones

### Recibe de

- `NativeEpisodicStore`, `SemanticIndex`, `OnnxEmbedder`, `WorkContext`, reloj `now`.
- Submódulos hybrid/intent/decay/feedback/doc_intent/cooccurrence/models.

### Envía a

- `EnrichedBundle` → presenter/telemetry/CLI `cortex context` / examples `context_check`.

### Notas de implementación observadas en el código

Comentario P7: sin filtros estructurales ni observer en el alcance original; P12A-7 añade filters/observer/telemetry como módulos separados. `matched_chunk_id` None en fixtures sin chunking.
