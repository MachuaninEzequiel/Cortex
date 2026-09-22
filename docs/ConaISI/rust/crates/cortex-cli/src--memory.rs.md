# rust/crates/cortex-cli/src/memory.rs

## Qué tiene adentro

`MemoryOpenError::NoConfig` (mensaje ❌ exactamente como common.py). `EpisodicLoad` (JSONL `episodic_export.jsonl` o `memories.jsonl`). `NativeMemory { layout, semantic, episodic, embedder, vault_path, persist_dir }`. `open` / `open_without_embeddings`. `rrf_fuse`. `RetrievalResultMirror`. `enterprise_topology()`.

## Para qué sirve

Glue de memoria para search/context/stats/remember/docs: WorkspaceLayout + SemanticIndex + NativeEpisodicStore + OnnxEmbedder + RRF.

## Relaciones

### Recibe de

- `config.yaml` vía layout.
- `cortex_workspace` namespace episódico.
- `cortex_app` semantic/episodic/hybrid/intent.
- `cortex_embed::onnx::OnnxEmbedder`.
- `cortex_enterprise::config` para topology.

### Envía a

- `memory_cmds`, `docs_cmd`, `remember_cmd`, `pr_context_cmd`.

### Notas de implementación observadas en el código

`open_without_embeddings` evita ~90MB RSS / ~150ms ONNX (stats, forget). Sin config → error que pide `cortex setup full --non-interactive`.
