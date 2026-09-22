# src/semantic/chunker.rs

## Qué tiene adentro

Chunking H2/H3.

`Chunk { parent_path, chunk_id, section_title, position, text, doc_type, tags }`. `embedding_text()` concatena no-vacíos: `doc_type.value`, tags, section_title, body.

`slugify`: NFKD→ascii, lower implícito vía filter ascii, quita no `[A-Za-z0-9_\s-]`, colapsa whitespace/`_`/`-` a un `-`, trim `-`.

`chunk_document`: si contenido vacío o `word_count < route.min_words` o sin headers → single chunk (`chunk_id = parent_path`). Prefijo antes del primer header = sección `(prefix)` pos 0. IDs `parent#h2-{slug}` y colisiones `-2`, `-3`. Header end = fin del título SIN `\n` (como `match.end()` Python).

`single_chunk_public` para el índice.

No porta `_split_paragraphs` (boundary paragraph inalcanzable en la tabla).

## Para qué sirve

Dividir docs largos en secciones indexables.

## Relaciones

### Recibe de

- `routing::{DocType, Route}` y campos del `SemDoc`.

### Envía a

- `chunks_for_doc` en `semantic/mod.rs`; fingerprints usan `embedding_text()`.

### Notas de implementación observadas en el código

`###` no matchea `##` si `boundary_h3` es false. Slug vacío → `"section"`.
