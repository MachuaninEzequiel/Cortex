# rust/crates/cortex-webgraph-server/src/config.rs

## Qué tiene adentro

Porteo de `cortex/webgraph/config.py` — WebGraphConfig.
Archivo de 131 líneas.
Símbolos públicos observados:
- `pub struct WebGraphConfig`

## Para qué sirve

Porteo de `cortex/webgraph/config.py` — WebGraphConfig.

## Relaciones

### Recibe de

- `use cortex_workspace::WorkspaceLayout`
- Contexto de crate `cortex-webgraph-server`: cortex-core, cortex-app, cortex-workspace, cortex-setup

### Envía a

- Crate `cortex-webgraph-server` envía hacia: HTTP axum, cortex-cli webgraph, brain webgraph.serve

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-webgraph-server/src/config.rs`.
El crate/archivo declara `forbid(unsafe_code)`.
