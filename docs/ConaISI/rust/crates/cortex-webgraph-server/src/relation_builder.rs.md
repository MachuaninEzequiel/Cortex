# rust/crates/cortex-webgraph-server/src/relation_builder.rs

## Qué tiene adentro

Porteo de `cortex/webgraph/relation_builder.py` — edges explicables del grafo híbrido.  Los kernels O(n²) (vecinos semánticos + escaneo cross-source) se delegan a `cortex-core::webgraph`, gateados bit-idénticos contra los loops Python en G4. Este módulo porta la capa de construcción: wikilinks, spec-links, supersedes tipados, el merge/dedupe de `_add_edge` y el orden de inserción del dict Python (que define el orden del array JSON).
Archivo de 607 líneas.
Símbolos públicos observados:
- `pub fn slug(text: &str) -> String`
- `pub struct RelationBuilder`

## Para qué sirve

Porteo de `cortex/webgraph/relation_builder.py` — edges explicables del grafo híbrido.  Los kernels O(n²) (vecinos semánticos + escaneo cross-source) se delegan a `cortex-core::webgraph`, gateados bit-idénticos contra los loops Python en G4. Este módulo porta la capa de construcción: wikilinks, spec-links, supersedes tipados, el merge/dedupe de `_add_edge` y el orden de inserción del dict Python (que define el orden del array JSON).

## Relaciones

### Recibe de

- `use cortex_core::webgraph::semantic_neighbor_pairs`
- `use crate::config::WebGraphConfig`
- `use crate::contracts::{EpisodicRecord, SemanticRecord, WebGraphEdge}`
- Contexto de crate `cortex-webgraph-server`: cortex-core, cortex-app, cortex-workspace, cortex-setup

### Envía a

- Crate `cortex-webgraph-server` envía hacia: HTTP axum, cortex-cli webgraph, brain webgraph.serve

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-webgraph-server/src/relation_builder.rs`.
El crate/archivo declara `forbid(unsafe_code)`.
