//! Servidor WebGraph nativo — porteo de `cortex/webgraph/*` (fase P12B-2).
//!
//! El CÓMPUTO del grafo ya es nativo y gateado (cortex-core::webgraph,
//! Gate G4: vecinos semánticos + escaneo cross-source bit-idénticos). Este
//! crate porta la capa de orquestación y exposición:
//!
//! - [`contracts`] — modelos `WebGraphNode/Edge/Snapshot/Detail` (pydantic).
//! - [`style`] — colores/formas por DocType, tabla de edges y legend
//!   (+ inferencia de DocType por ruta, doc 13).
//! - [`config`] — `WebGraphConfig` load/save.
//! - [`sources`] — proyección de vault semántico + memoria episódica a
//!   records (embedder inyectable para determinismo del gate).
//! - [`relation_builder`] — wikilinks/spec-links/supersedes/cross-source/
//!   semantic-neighbors con los kernels de cortex-core.
//! - [`graph_builder`] — nodos + degree + snapshot.
//! - [`cache`] — fingerprint sha256 + caché de snapshots.
//! - [`service`] — `WebGraphService` (build/detail/subgraph/scope/enterprise).
//! - [`federation`] — workspace.yaml multi-proyecto + servicio federado.
//! - [`openers`] — resolución segura de rutas del vault + apertura.
//! - [`server`] — router axum equivalente al Flask de Python.
//! - [`pyjson`] — serializador JSON compatible byte-a-byte con
//!   `json.dumps`/`jsonify` de Flask (sort_keys, ensure_ascii, separadores),
//!   necesario porque el contrato del gate es paridad de BYTES.
//!
//! Gate P12B-2: `bench/parity/webgraph_golden_p12b.py` levanta el server
//! Flask REAL sobre un fixture determinista; el checker Rust
//! (`examples/webgraph_check.rs`) levanta este router axum sobre el mismo
//! fixture y compara status+cuerpo de cada endpoint tras normalizar
//! {{ROOT}}/{{TS}}/{{FP}}.

#![forbid(unsafe_code)]

pub mod cache;
pub mod config;
pub mod contracts;
pub mod federation;
pub mod graph_builder;
pub mod openers;
pub mod pyjson;
pub mod relation_builder;
pub mod server;
pub mod service;
pub mod sources;
pub mod style;

pub use config::WebGraphConfig;
pub use contracts::{
    EpisodicRecord, SemanticRecord, WebGraphCapabilities, WebGraphEdge, WebGraphMode, WebGraphNode,
    WebGraphNodeDetail, WebGraphSnapshot, WebGraphStats,
};
pub use federation::{
    default_workspace_file, load_workspace_projects, resolve_workspace_file, write_workspace_file,
    FederatedWebGraphService, WorkspaceProject,
};
pub use service::WebGraphService;
