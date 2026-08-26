//! Puerto de `cortex.autopilot` — Cierre Obra 07 T3.
//!
//! - Capa de decisión (P12B-5): config, models, session-models mínimos,
//!   detectors, policies y lifecycle.
//! - [`service`] (T3): orquestación sobre el SessionService NATIVO
//!   (`cortex-app::session`) — start/preflight/checkpoint/finish/status.
//!   El cierre vía documenter (`finish(auto=True)`) requiere un backend
//!   [`service::DocumenterFinalize`] inyectado; sin él ⇒ fallo explícito
//!   con el mensaje exacto del oráculo (patrón P6/P9).

pub mod config;
pub mod detectors;
pub mod errors;
pub mod lifecycle;
pub mod models;
pub mod policies;
pub mod service;
pub mod session_models;
