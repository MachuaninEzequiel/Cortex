//! Puerto de la capa de decisión de `cortex.autopilot` (P12B-5):
//! config, models, session-models mínimos, detectors, policies y lifecycle.
//!
//! Fuera de alcance (fallo explícito hasta motor de sesiones nativo):
//! service/cli/mcp_tools — SessionService/Storage/AgentMemory no porteños.

pub mod config;
pub mod detectors;
pub mod errors;
pub mod lifecycle;
pub mod models;
pub mod policies;
pub mod session_models;
