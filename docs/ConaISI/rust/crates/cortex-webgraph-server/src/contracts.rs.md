# rust/crates/cortex-webgraph-server/src/contracts.rs

## Qué tiene adentro

Modelos del WebGraph — porteo de `cortex/webgraph/contracts.py`.
Archivo de 168 líneas.
Símbolos públicos observados:
- `pub type WebGraphMode = String`
- `pub const WEBGRAPH_MODES: &[&str] = &["semantic", "episodic", "hybrid"]`
- `pub struct WebGraphCapabilities`
- `pub struct WebGraphStats`
- `pub struct WebGraphNode`
- `pub struct WebGraphEdge`
- `pub struct WebGraphSnapshot`
- `pub struct WebGraphNodeDetail`
- `pub struct SemanticRecord`
- `pub struct EpisodicRecord`

## Para qué sirve

Modelos del WebGraph — porteo de `cortex/webgraph/contracts.py`.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-webgraph-server`: cortex-core, cortex-app, cortex-workspace, cortex-setup

### Envía a

- Crate `cortex-webgraph-server` envía hacia: HTTP axum, cortex-cli webgraph, brain webgraph.serve

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-webgraph-server/src/contracts.rs`.
El crate/archivo declara `forbid(unsafe_code)`.
