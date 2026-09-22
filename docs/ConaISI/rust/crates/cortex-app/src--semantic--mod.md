# src/semantic/mod.rs

## Qué tiene adentro

Pipeline semántico (P2). Submódulos `chunker`, `parser`, `routing`.

Tipos:
- `EmbedBatchFn`: `&mut dyn FnMut(&[String]) -> Result<Vec<Vec<f64>>, String>`.
- `IndexedChunk { info: Chunk, embedding }`.
- `SemDoc { path absoluto posix, rel, title, content, tags, links }`.
- `SemanticIndex { docs (orden inserción), chunks, by_rel, doc_lengths, idf, avgdl }`.

Métodos:
- `build(vault)`: recolecta `.md` recursivo, sort de paths, parse, `recompute_stats`.
- `recompute_stats`: doc_len = whitespace tokens de `title + " " + content`; IDF `ln((N-df+0.5)/(df+0.5)+1)` sobre palabras unique lowercased; avgdl.
- `attach_embeddings` / `attach_embeddings_with(OnnxEmbedder)`: `chunks_for_doc` + `embed_batch`.
- `attach_embeddings_from_store`: fingerprints `reindex::cache_fingerprint`; hit completo o false.
- `index_file(vault, rel, embed_batch)`: `resolve_safe`; upsert conservando posición; purga chunks del padre; re-embebe; recompute_stats. Archivo inexistente → Ok(false).
- `semantic_search` / `semantic_search_vec`: coseno naive (suma `.sum()`, NO Neumaier); score>0; max por padre (primer máximo gana); sort desc.
- `bm25_search`: k1=1.5 b=0.75; tf = `text.matches(term)`; solo score>0.

`chunks_for_doc`: `doc_type_from_rel` o Glossary; si chunking off → single chunk.

Tests: incremental `index_file` vs rebuild BM25; missing file; archivo nuevo al final.

## Para qué sirve

Índice del vault markdown: BM25 + vectores por chunk, espejo de `VaultReader`.

## Relaciones

### Recibe de

- Filesystem vault, `parser`, `chunker`, `routing`, `security::resolve_safe`, `cortex-embed`, `cortex-core::VectorStore`, `reindex::cache_fingerprint`.

### Envía a

- `context::hybrid::search_hybrid`, `context::ContextEnricher`, `reindex_vault`, examples `bm25_search`/`semantic_search`.

### Notas de implementación observadas en el código

Coseno semántico es suma ingenua, distinto del Neumaier de `cortex-core::scoring`. Rel paths usan `/` aunque el OS sea `\`.
