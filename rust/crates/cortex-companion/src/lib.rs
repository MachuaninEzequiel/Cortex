//! cortex-companion — superficie única mouse-first (Obra 08 stream B).
//!
//! Especificación: `docs/transformacion/14-HERDR-COMPANION.md`.
//! G-B1 (esta etapa): scaffolding del crate + `Backend` trait +
//! `InProcessBackend` (servicios nativos in-proceso). Las pantallas,
//! aprobaciones y el panel Brain llegan en tasks posteriores del plan.

#![forbid(unsafe_code)]

use std::path::PathBuf;

pub mod app;
pub mod approval;
pub mod engine;

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
