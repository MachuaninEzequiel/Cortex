# rust/crates/cortex-cli/src/commands/remember_cmd.rs

## Qué tiene adentro

`remember` (content, --type, --tag, --file, branch/repo/commit, --summarize) persiste en JSONL nativo con ONNX. `forget` borra `mem_*`. Warning si `--summarize` y llm.provider == none.

## Para qué sirve

CRUD episódico raíz.

## Relaciones

### Recibe de

- `NativeMemory` + `NativeEpisodicStore::append/delete`.
- config.yaml llm.provider.

### Envía a

- JSONL episódico + stdout.

### Notas de implementación observadas en el código

forget abre sin embeddings (B7).
