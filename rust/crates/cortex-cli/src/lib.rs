//! cortex-cli — biblioteca del CLI nativo (P12B-8).
//!
//! El binario (`main.rs`) hace el dispatch; este módulo expone los
//! comandos y utilidades para tests/examples.

pub mod commands;
pub mod memory;
pub mod memory_cmds;
pub mod paths;
pub mod pyjson;
pub mod rich_panel;
