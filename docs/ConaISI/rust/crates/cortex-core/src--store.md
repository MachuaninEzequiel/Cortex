# src/store.rs

## Qué tiene adentro

Store vectorial append-only (Gate G2). Archivo único `vectors.v3.bin` (`STORE_FILENAME`).

Formato:
- Header: magic 8 bytes `CCTXV3\0\0` + `model_len u32LE` + `model_name` UTF-8.
- PUT (`tag=1`): klen + fingerprint + clen + chunk_id + vlen + `dim × f32 LE`.
- TOMBSTONE (`tag=2`): klen + fingerprint.

Tipos:
- `StoreError`: `Io`, `Corrupted`, `DimMismatch`, `LengthMismatch`.
- `VectorStore`: arena `Vec<f32>` + `chunk_ids` alineados + `HashMap` fingerprint→fila + `truncated_tail`.
- API: `open(dir, model_name)`, `dim/len/is_empty`, `get_many`, `fps_for_chunk_ids`, `fps_with_chunk_prefix`, `entries_export`, `put_many` (todo-o-nada), `invalidate_many`, `compact` (tmp + rename atómico).

Carga: una lectura secuencial. Header roto o `model_name` distinto → reset del archivo. Cola truncada: conserva prefijo válido y marca `truncated_tail`.

Tests cubren round-trip dim 3/384/1024, misses en store vacío, tombstone+compact, reput del mismo fp, reset por modelo distinto, cola truncada, consultas por chunk_id.

## Para qué sirve

Reemplazar el cache Python `chunks.bin` + `index.json` (open/seek por vector y re-serialización O(N) del índice). Persistencia nativa de embeddings con invalidación granular.

## Relaciones

### Recibe de

- Directorio destino y `model_name` del caller.
- Fingerprints opacos calculados fuera (Python `cache_fingerprint` / `cortex-app::reindex::cache_fingerprint`).
- Vectores `f32` y `chunk_id`.

### Envía a

- `cortex-py::NativeVectorStore` (Mutex + pymethods).
- `cortex-app::semantic::SemanticIndex::attach_embeddings_from_store`.
- `cortex-app::reindex::reindex_vault` (put_many + compact).

### Notas de implementación observadas en el código

`dim` se infiere del primer vector y se valida después. Re-PUT deja la fila vieja como basura hasta `compact()`. Mensajes de error en español. Magic v3 (no v2).
