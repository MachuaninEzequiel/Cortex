# rust/crates/cortex-mcp/src/backends/search.rs

## Qué tiene adentro

`NativeSearchBackend { semantic: SemanticIndex, episodic, embedder: Option<OnnxEmbedder>, vault }`. `open` lee config, construye índice BM25, carga episódico, intenta ONNX en `~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx`. RRF_K=60.

## Para qué sirve

Search/context/sync_ticket reales. Sin modelo → degrada a keyword como `cortex search`.

## Relaciones

### Recibe de

- Vault + JSONL episódico + cortex-embed.
- `cortex_app::context::hybrid::search_hybrid`.

### Envía a

- Mirrors Retrieval/Enriched a handlers_search.

### Notas de implementación observadas en el código

Comentario: embeddings “completos” en MCP quedan para wiring P12; fixtures del oráculo son keyword.
