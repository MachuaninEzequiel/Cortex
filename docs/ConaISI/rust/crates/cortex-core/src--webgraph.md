# src/webgraph.rs

## Qué tiene adentro

Vecinos semánticos y edges cross-source (Gate G4). Réplica de `RelationBuilder._add_semantic_neighbors` y `_add_cross_source_edges`.

Funciones/tipos:
- `sum_neumaier` y `cosine_truncated` (dot a `min(len)`, normas completas, 0.0 si falta/vacío/norma cero). Duplicados respecto de `scoring.rs` para no acoplar módulos.
- `semantic_neighbor_pairs(ids, embeddings, threshold, max_edges_per_node) -> Vec<(i,j,score)>` con `ids[i] < ids[j]`. Pasada 1 rayon i<j; ranking por nodo score DESC + id DESC; `allowed_pairs`; pasada 2 loops anidados Python.
- `BuiltEdge { id, source, target, edge_type, weight, evidence }`.
- `EdgeAccumulator`: clave direccional `(type,source,target)` para `wikilink|supersedes|superseded_by`; resto `(type, min, max)` lexicográfico. Primera inserción fija id/source/target; evidence dedup; weight = max.
- `cross_source_build(...)`: por cada episódico, contra cada semántico: `shared_tag` (peso 1.0, hasta 3 tags), `shared_entity` (1.1, hasta 4), `same_spec_reference` si `sem_is_spec` y overlap ≥3 tokens (1.2). Merge secuencial: primero `same_file_reference` (1.3) por `epi_files_targets`, luego el resto. Evidence se une con `\u{1}` en la fase paralela.

Tests: umbral inclusivo `>=`, embeddings vacíos, desempate id DESC, orden de emisión, paridad vs referencia Python en n=60.

## Para qué sirve

Construir aristas del webgraph con orden y pesos idénticos al builder Python, paralelizando el O(n²).

## Relaciones

### Recibe de

- IDs, embeddings opcionales, tags/entities/tokens ya ordenados, flags `sem_is_spec`, pares (file_ref, target_id) ya resueltos.
- `rayon`.

### Envía a

- `cortex-py::semantic_neighbor_pairs` y `cross_source_build` (tuplas hacia Python).
- `cortex-webgraph-server` (crate hermano; este módulo es la pieza de dominio).

### Notas de implementación observadas en el código

Self-loops (`source==target`) se descartan. Intersección de listas ordenadas es merge-style. `debug_assert` de longitudes alineadas.
