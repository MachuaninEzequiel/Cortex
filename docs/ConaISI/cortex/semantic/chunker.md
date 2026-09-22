# cortex/semantic/chunker.py

## Qué tiene adentro

- **Ruta de código:** `cortex/semantic/chunker.py` (306 líneas).
- **Módulo Python:** `cortex.semantic.chunker`.
- **Docstring del módulo:** cortex.semantic.chunker - Split markdown documents into embedding-sized chunks.
- **Clases definidas:**
  - `Chunk`
    - One indexable slice of a document.
    - Métodos públicos/especiales: `word_count`, `embedding_text`
- **Funciones de módulo:**
  - `chunk_document(title, content, doc_type, tags)` — Split ``content`` into indexable chunks.
  - `_word_count(text)`
  - `_single_chunk()`
  - `_make_chunk()` — Build a Chunk with a collision-safe ``chunk_id`` (Fix A4).
  - `_split_with_pattern(content, pattern, fallback_title, doc_type, tags, parent_path, overlap_words)`
  - `_split_paragraphs(content, fallback_title, doc_type, tags, parent_path, overlap_words)`
  - `_combined_h2_h3()` — Pattern matching both H2 and H3 headers.
- **Constantes / símbolos de módulo:** `_H2_RE`, `_H3_RE`, `__all__`

## Para qué sirve

cortex.semantic.chunker - Split markdown documents into embedding-sized chunks.

Long notes (e.g. runbooks, postmortems, ADRs > 1000 words) lose information
when embedded as a single vector because the underlying model truncates
inputs past ~512 tokens. Chunking by H2/H3 boundaries preserves recall by
producing one vector per logical section.

The chunker is content-agnostic; it accepts a ``doc_type`` and ``tags`` so
the structural signal can be injected into the embedding text:

    embedding_text = "<doc_type> <tags> <section_title> <text>"

Routing decides whether a document is chunked at all (``chunking_enabled``,
``chunking_min_words``, ``chunking_boundary`` in ``RouteSpec``). The
``VaultReader`` calls this module on every ``index_file`` invocation.

## Relaciones

### Recibe de

- `cortex.documentation.common` (slugify)
- `cortex.documentation.doc_type` (DocType)
- Dependencias externas/stdlib: `re`, `__future__`, `collections.abc`, `dataclasses`

### Envía a

- `cortex.semantic.vault_reader`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 306.
Docstrings de símbolos públicos:
- `Chunk.embedding_text`: Text that should be fed to the embedder.
- `chunk_document`: Split ``content`` into indexable chunks.

---
Fuente: código de `cortex/semantic/chunker.py` (AST + grafo de imports internos). No se usó documentación previa.
