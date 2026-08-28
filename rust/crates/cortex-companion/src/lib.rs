//! cortex-companion — superficie única mouse-first (Obra 08 stream B).
//!
//! Especificación: `docs/transformacion/14-HERDR-COMPANION.md`.
//! Estado por task: B1 engine (Backend + paridad), B2 aprobaciones
//! (run_guarded), B3 app ELM-lite mouse-first, B4 widgets + Home,
//! B5 Menu anti-olvido, B6 Sessions+Actions con modal integrado a la
//! máquina de estados (`app::pending` + `effects::apply`), B7 Search con
//! feedback explícito formato-oráculo (`feedback.rs`), B8 Brain híbrido
//! (`brain_panel.rs`: reads directas por el engine in-process, propuestas
//! de mutación con [Ejecutar] → `run_guarded`, router determinista cero
//! tokens / LLM opcional con protocolo TOOL).

#![forbid(unsafe_code)]

use std::path::PathBuf;

pub mod app;
pub mod approval;
pub mod brain_panel;
pub mod effects;
pub mod engine;
pub mod feedback;
pub mod menu;
pub mod screens;
pub mod widgets;

/// Pantallas del Companion (lo consume la app en B3+).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Screen {
    Home,
    Menu,
    Sessions,
    Actions,
    Search,
    Brain,
}

/// Pedido de UI inyectado por el binario (patrón de cortex-tui).
#[derive(Debug, Clone)]
pub struct UiRequest {
    pub screen: Screen,
    pub project_root: PathBuf,
}
