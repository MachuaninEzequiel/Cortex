# src/bm25.rs

## Qué tiene adentro

Índice BM25 in-memory (Gate G3). Replica `VaultReader._bm25_search` + `_compute_idf`.

`Bm25Index`: `texts` (ya en minúsculas), `paths`, `doc_lens`, `idf: HashMap<String,f64>`, `avgdl`.

API:
- `set_stats(idf_keys, idf_vals, avgdl)` — longitudes alineadas o error.
- `add_batch(paths, texts, doc_lens)` — lote.
- `remove_batch(paths)` — por ruta exacta.
- `clear`, `len`, `is_empty`.
- `search(terms, k1, b) -> Vec<f64>` — un score por documento, orden de inserción, rayon por documento.
- `top_k` — scores > 0, sort estable desc, empate gana índice menor.

`count_nonoverlap` = `str.count` de Python (`match_indices`). Término ausente o `idf==0.0` se salta. Fórmula: `score += idf * (tf*(k1+1) / (tf + k1*(1-b+b*doc_len/avgdl)))`.

Tests: count substring/UTF-8, paridad bit exacta vs loop Python, skip de términos, rebuild.

## Para qué sirve

Ranking léxico nativo con la misma aritmética que Python. El comentario rechaza tantivy porque tokeniza y cambiaría el ranking (tf es substring, no token).

## Relaciones

### Recibe de

- Python/`cortex-app`: textos ya `.lower()`, IDF y avgdl precomputados, `k1`/`b`.
- `rayon` para el map por documento.

### Envía a

- `cortex-py::NativeBm25Index` (`search` → numpy, `top_k` → `Vec<(f64,u32)>`).
- Tests internos. `cortex-app::semantic` implementa BM25 propio sobre `SemanticIndex` (no llama este tipo directamente en el código leído de semantic/mod.rs).

### Notas de implementación observadas en el código

Needle vacío → 0 (defensa). `collect` de rayon preserva orden. Scores se asumen finitos; `total_cmp` ordena NaN de forma determinista.
