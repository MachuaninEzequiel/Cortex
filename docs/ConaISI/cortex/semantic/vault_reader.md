# cortex/semantic/vault_reader.py

## Qué tiene adentro

- **916 líneas.** `VaultReader`: índice in-memory de un directorio Markdown (vault Obsidian-compatible).
- Parsea con `MarkdownParser`, chunkea con `chunk_document`, embebe con `Embedder` (mismo stack que lo episódico).
- Índice persistido: `.cortex_index.json` junto al vault.
- Cache de vectores: `VectorCache` opcional (fingerprint del texto a embeber).
- BM25 a nivel documento (`_compute_idf`, `_doc_lengths`, `_avgdl`) como señal keyword.
- Ruta nativa: si `CORTEX_NATIVE=1` y existe `cortex_core._native`, usa matriz f64 batch (G1 cosine) e índice BM25 Rust (G3). Se invalida en cada mutación.
- `search`: híbrido vector + BM25, scores a nivel chunk, agrega al doc padre por max; rellena `matched_chunk_id` / `matched_section_title`.
- CRUD de notas: `create_note`, `index_file`, `sync`.
- Paths validados con `cortex.security.paths`.

## Para qué sirve

Capa semántica: el “cerebro documental”. Todo retrieve de vault (CLI, MCP, webgraph semantic source, enterprise sources) pasa por aquí o por un `VaultReader` gemelo.

## Relaciones

### Recibe de

- Disco: `vault_path/**/*.md`.
- `MarkdownParser`, `chunker`, `VectorCache`.
- `Embedder` (`cortex.episodic.embedder` → factory).
- `DocType` / `classify_path` (documentation) para decidir chunking.
- `resolve_safe` / `validate_under_root`.
- Opcional: `cortex_core._native` (PyO3).

### Envía a

- `AgentMemory.semantic`, `HybridSearch.semantic`.
- `cortex.enterprise.sources`, `cortex.webgraph.semantic_source`.
- Reexport `cortex.semantic`, `cortex.__init__`.

### Notas de implementación observadas en el código

- BM25 keyword queda a nivel **doc**, embeddings a nivel **chunk**.
- `sync()` embebe en un solo `embed_batch` (cache hits primero).
- Dimensión de vectores no está hardcodeada en este archivo; la da el embedder / store nativo.

---
Fuente: lectura de `cortex/semantic/vault_reader.py`. No se usó documentación previa.
