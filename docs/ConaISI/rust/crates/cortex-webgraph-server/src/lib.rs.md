# rust/crates/cortex-webgraph-server/src/lib.rs

## Qué tiene adentro

Servidor WebGraph nativo — porteo de `cortex/webgraph/*` (fase P12B-2).  El CÓMPUTO del grafo ya es nativo y gateado (cortex-core::webgraph, Gate G4: vecinos semánticos + escaneo cross-source bit-idénticos). Este crate porta la capa de orquestación y exposición:  - [`contracts`] — modelos `WebGraphNode/Edge/Snapshot/Detail` (pydantic). - [`style`] — colores/formas por DocType, tabla de edges y legend (+ inferencia de DocType por ruta, doc 13). - [`config`] — `WebGraphConfig` load/save. - [`sources`] — proyección de vault semántico + memoria episódica a records (embedder inyectable para determinismo del gate).
Archivo de 55 líneas.
Símbolos públicos observados:
- `pub mod cache`
- `pub mod config`
- `pub mod contracts`
- `pub mod federation`
- `pub mod graph_builder`
- `pub mod openers`
- `pub mod pyjson`
- `pub mod relation_builder`
- `pub mod server`
- `pub mod service`
- `pub mod sources`
- `pub mod style`
- `pub use config::WebGraphConfig`
- `pub use contracts::`
- `pub use federation::`
- `pub use service::WebGraphService`

## Para qué sirve

Servidor WebGraph nativo — porteo de `cortex/webgraph/*` (fase P12B-2).  El CÓMPUTO del grafo ya es nativo y gateado (cortex-core::webgraph, Gate G4: vecinos semánticos + escaneo cross-source bit-idénticos). Este crate porta la capa de orquestación y exposición:  - [`contracts`] — modelos `WebGraphNode/Edge/Snapshot/Detail` (pydantic). - [`style`] — colores/formas por DocType, tabla de edges y legend (+ inferencia de DocType por ruta, doc 13). - [`config`] — `WebGraphConfig` load/save. - [`sources`] — proyección de vault semántico + memoria episódica a records (embedder inyectable para determinismo del gate).

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-webgraph-server`: cortex-core, cortex-app, cortex-workspace, cortex-setup

### Envía a

- Crate `cortex-webgraph-server` envía hacia: HTTP axum, cortex-cli webgraph, brain webgraph.serve

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-webgraph-server/src/lib.rs`.
El crate/archivo declara `forbid(unsafe_code)`.
