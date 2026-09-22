# rust/crates/cortex-webgraph-server/src/service.rs

## Qué tiene adentro

Porteo de `cortex/webgraph/service.py` — orquestación de snapshots.  GAP explícito (P12B-3): `_append_enterprise_nodes` depende de `cortex.enterprise.config` (crate cortex-enterprise, tarea P12B-3). Mientras ese crate no exista, si el proyecto TIENE org.yaml se emite warning por stderr y el snapshot queda SIN nodos enterprise (jamás se finge paridad: el gate cubre proyectos sin org.yaml, que es el caso donde Python tampoco agrega nada).
Archivo de 320 líneas.
Símbolos públicos observados:
- `pub struct WebGraphService`

## Para qué sirve

Porteo de `cortex/webgraph/service.py` — orquestación de snapshots.  GAP explícito (P12B-3): `_append_enterprise_nodes` depende de `cortex.enterprise.config` (crate cortex-enterprise, tarea P12B-3). Mientras ese crate no exista, si el proyecto TIENE org.yaml se emite warning por stderr y el snapshot queda SIN nodos enterprise (jamás se finge paridad: el gate cubre proyectos sin org.yaml, que es el caso donde Python tampoco agrega nada).

## Relaciones

### Recibe de

- `use crate::cache::WebGraphCache`
- `use crate::config::WebGraphConfig`
- `use crate::contracts::{`
- `use crate::graph_builder::GraphBuilder`
- `use crate::sources::{EmbedFn, EpisodicSource, SemanticSource}`
- `use cortex_workspace::WorkspaceLayout`
- Contexto de crate `cortex-webgraph-server`: cortex-core, cortex-app, cortex-workspace, cortex-setup

### Envía a

- Crate `cortex-webgraph-server` envía hacia: HTTP axum, cortex-cli webgraph, brain webgraph.serve

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-webgraph-server/src/service.rs`.
El crate/archivo declara `forbid(unsafe_code)`.
