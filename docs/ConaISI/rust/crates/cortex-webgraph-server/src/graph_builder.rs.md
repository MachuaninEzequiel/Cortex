# rust/crates/cortex-webgraph-server/src/graph_builder.rs

## Qué tiene adentro

Porteo de `cortex/webgraph/graph_builder.py`.
Archivo de 123 líneas.
Símbolos públicos observados:
- `pub struct GraphBuilder`

## Para qué sirve

Porteo de `cortex/webgraph/graph_builder.py`.

## Relaciones

### Recibe de

- `use crate::config::WebGraphConfig`
- `use crate::contracts::{`
- `use crate::relation_builder::RelationBuilder`
- Contexto de crate `cortex-webgraph-server`: cortex-core, cortex-app, cortex-workspace, cortex-setup

### Envía a

- Crate `cortex-webgraph-server` envía hacia: HTTP axum, cortex-cli webgraph, brain webgraph.serve

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-webgraph-server/src/graph_builder.rs`.
El crate/archivo declara `forbid(unsafe_code)`.
