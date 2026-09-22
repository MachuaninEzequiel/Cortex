# rust/crates/cortex-cli/src/commands/webgraph.rs

## Qué tiene adentro

`export` (mode semantic|episodic|hybrid, --output, --no-cache, --workspace-file), `serve` (host/port, --no-open no-op documentado), `doctor`. Federación: si hay workspace federado el comando **falla explícito** (sin passthrough). `Other` → rechazo rc 2.

## Para qué sirve

Snapshots y UI WebGraph nativa (axum de cortex-webgraph-server).

## Relaciones

### Recibe de

- `cortex_webgraph_server`, WorkspaceLayout, NativeMemory/embeddings según modo.

### Envía a

- JSON snapshot / servidor HTTP.

### Notas de implementación observadas en el código

Paridad live honesta: vault sin markdown y sin store episódico (embedder no se invoca).
