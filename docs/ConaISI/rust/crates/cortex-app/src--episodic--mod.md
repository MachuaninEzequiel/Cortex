# src/episodic/mod.rs

## Qué tiene adentro

Memoria episódica nativa (P3) sobre JSONL neutro `{id, document, meta, embedding}`.

`MemoryEntry { id, content, memory_type, tags, files, timestamp ISO, metadata BTreeMap }`. `EpisodicRow` añade `raw_meta` y `embedding`.

`deserialize_row`: id de meta o fallback; tags/files JSON-string o array; `metadata_json` o extracción `entity_*` bool true.

`NativeEpisodicStore`: `load` (ordena por id), `count`, `vector_search` score=`max(0, coseno)` sort desc, `keyword_search` substring case-sensitive score implícito 1.0, `entity_ids` / `entity_search` (recencia con `now`).

`AppendParams` + append (el archivo continúa; usa extract_entities y embedder — más abajo en el archivo). Helpers públicos: `py_dumps_compact`, `serialize_metadata`, `entity_match_score`, `entity_filter_key`, `cosine_max0`.

## Para qué sirve

Sustituir ChromaDB en ranking/paridad con un export JSONL y escrituras append.

## Relaciones

### Recibe de

- JSONL de `bench/parity` / persistencia nativa; query vectors de OnnxEmbedder; `entities::extract_entities`.

### Envía a

- `context::hybrid`, `ContextEnricher` (entity_search), examples `episodic_check`/`p12a1_check`.

### Notas de implementación observadas en el código

Keyword bypass existe porque `where_document` de chromadb moderno lanzaba ValueError. Orden de `keyword_search` es el de `rows` ya sorted-by-id. Coseno propio `cosine_max0`, no `cortex-core::scoring`.
