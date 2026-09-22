# src/context/cooccurrence.rs

## Qué tiene adentro

Grafo naive: `build_co_occurrence(entries_files)` cuenta pares de files co-mencionados. `co_occurrence_score` consulta ese conteo.

Grafo tipado: `RELATIONSHIP_WEIGHTS` 6 pares; `TypedCooccurrenceGraph`.

## Para qué sirve

Expandir/boostear items que comparten archivos o relaciones semánticas con el work.

## Relaciones

### Recibe de

- Listas de files por entrada episódica; grafo tipado construido desde el corpus.

### Envía a

- `ContextEnricher` (config `graph_expansion` / `typed_graph`).

### Notas de implementación observadas en el código

Naive es conteo, no embeddings.
