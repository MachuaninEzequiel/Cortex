# rust/crates/cortex-cli/src/memory_cmds.rs

## Qué tiene adentro

Comandos raíz `search`, `context`, `stats`, `reindex`. `default_model_dir()` → `~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx`. `CliSearchAdapter` (para TUI). `write_feedback_useful`. Serialización `retrieval_json`.

## Para qué sirve

Familia memoria del CLI (espejo main.py search/context/stats y embedding.py reindex).

## Relaciones

### Recibe de

- `NativeMemory`, clap args (query, top_k, filtros).
- `cortex_config::NamespaceMode`.

### Envía a

- stdout texto/JSON.
- TUI (`CliSearchAdapter` en Home/next --tui).
- feedback.jsonl vía `write_feedback_useful`.

### Notas de implementación observadas en el código

Salidas texto/--json buscadas byte-parity vs Python.
