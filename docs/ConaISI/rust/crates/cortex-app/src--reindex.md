# src/reindex.rs

## Qué tiene adentro

Reindex nativo del vault (Obra 18 / C1).

- `CACHE_SCHEMA_VERSION = "2"`.
- `cache_fingerprint(model_name, embedding_text)`: sha256 de `model\x00schema\x00text` en hex.
- `ReindexOutcome { n_chunks, dim, vectors_dir, backup_dir }`.
- `ReindexError`: UnsupportedModel, ModelMissing, Config, Semantic, Embed, Store.
- `vectors_dir(dot_cortex) = dot_cortex/vectors`.
- `resolve_reindex_model(config_path)`: lee YAML → `CortexConfig::resolve_embedder(None)`.
- `reindex_vault(vault, vectors_dir, model, model_dir)`:
  1. Solo admite `all-MiniLM-L6-v2`.
  2. Exige `model_dir` (si falta, hint `$HOME/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx/model.onnx`).
  3. `SemanticIndex::build` + `attach_embeddings_with(OnnxEmbedder)`.
  4. Si hay cache, rename a `vectors.backup-{UTC %Y%m%d-%H%M%S}`.
  5. `VectorStore::open` + `put_many` (fps, chunk_ids, f32 flat) + `compact`.
  6. Fallo de store restaura el backup.

## Para qué sirve

Rebuild del cache vectorial nativo con rollback.

## Relaciones

### Recibe de

- Vault path, `.cortex/vectors`, `config.yaml` (modelo), directorio ONNX.
- `cortex_config::CortexConfig`, `cortex_embed::OnnxEmbedder`, `cortex_core::VectorStore`, `semantic::SemanticIndex`.

### Envía a

- CLI de reindex (`cortex-cli`) y cualquier caller de `reindex_vault`.
- Fingerprints usados también por `SemanticIndex::attach_embeddings_from_store`.

### Notas de implementación observadas en el código

0 chunks → outcome dim=0 sin escribir store. Embeddings se castean f64→f32 al persistir.
