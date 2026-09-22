# cortex/semantic/vector_cache.py

## Qué tiene adentro

- **Ruta de código:** `cortex/semantic/vector_cache.py` (502 líneas).
- **Módulo Python:** `cortex.semantic.vector_cache`.
- **Docstring del módulo:** cortex.semantic.vector_cache - Persistent cache for embedding vectors.
- **Clases definidas:**
  - `CacheEntry`
    - A single vector entry persisted in the cache.
  - `CacheStats`
    - Operational metrics of the cache.
    - Métodos públicos/especiales: `hit_rate`
  - `VectorCache`
    - Persistent cache for sentence-transformer-style embeddings.
    - Métodos públicos/especiales: `__init__`, `get`, `put`, `batch_get`, `batch_put`, `invalidate`, `get_chunk_fingerprints`, `invalidate_chunks`, `invalidate_by_chunk_id`, `compact`, `clear`, `stats`
    - Métodos internos: `_maybe_auto_compact`, `_load`, `_reset_corrupt`, `_save_index`, `__len__`, `__contains__`, `_read_vector_at`
- **Funciones de módulo:**
  - `cache_fingerprint(model_name, embedding_text)` — Content fingerprint salted with model identity (Fix A3).
- **Constantes / símbolos de módulo:** `CACHE_SCHEMA_VERSION`, `VECTOR_DTYPE`, `DEFAULT_MODEL_NAME`, `__all__`

## Para qué sirve

cortex.semantic.vector_cache - Persistent cache for embedding vectors.

Eliminates the cold-start cost of re-embedding the entire semantic vault on
each process restart. Vectors are stored in a single binary file
(``chunks.bin``) keyed by SHA-256 fingerprint of the embedding text; an
``index.json`` companion file maps fingerprints to (offset, dim) byte
positions.

Layout::

    .cortex/vectors/
        index.json     - { schema_version, entries: {fp: CacheEntry}, invalidated: [fp...] }
        chunks.bin     - contiguous array of float32 vectors

Invalidation triggers:
    1. Fingerprint mismatch (content changed in the file).
    2. ``schema_version`` bump (cache layout changed).
    3. Explicit ``invalidate(fp)`` or ``invalidate_by_chunk_id(prefix)``.

4. Model identity mismatch (``model_name`` in header differs from the
   configured model) or dimension change — vectors of another model are
   never reused.

The cache is thread-safe (single-process, RLock). It is **not** safe for
concurrent processes; that's a deliberate trade-off for MVP simplicity.

When invalidations accumulate, call ``compact()`` to reclaim space. The
``CacheStats.invalidated_entries`` field surfaces when compaction is worth it.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `hashlib`, `json`, `logging`, `threading`, `numpy`, `__future__`, `dataclasses`, `pathlib`

### Envía a

- `cortex.cli.docs_vectorization`
- `cortex.semantic.native_vector_cache`
- `cortex.semantic.vault_reader`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 502.
Docstrings de símbolos públicos:
- `VectorCache.get`: Return vector for ``fingerprint`` or ``None`` on miss/invalidated.
- `VectorCache.put`: Store ``vector`` under ``fingerprint`` / ``chunk_id``.
- `VectorCache.batch_get`: Bulk get. Returns only hits.
- `VectorCache.batch_put`: Bulk put. items = list of (fingerprint, chunk_id, vector).
- `VectorCache.invalidate`: Mark an entry as invalidated. Returns ``True`` if it existed.
- `VectorCache.get_chunk_fingerprints`: Return ``{chunk_id: fingerprint}`` for every chunk under ``parent_path``.
- `VectorCache.invalidate_chunks`: Invalidate cache entries by exact ``chunk_id`` match.
- `VectorCache.invalidate_by_chunk_id`: Invalidate every entry whose ``chunk_id`` starts with ``chunk_id_prefix``.
- `VectorCache.compact`: Rebuild ``chunks.bin`` keeping only non-invalidated entries.
- `VectorCache.clear`: Remove all entries and delete the binary file.
- `cache_fingerprint`: Content fingerprint salted with model identity (Fix A3).

---
Fuente: código de `cortex/semantic/vector_cache.py` (AST + grafo de imports internos). No se usó documentación previa.
