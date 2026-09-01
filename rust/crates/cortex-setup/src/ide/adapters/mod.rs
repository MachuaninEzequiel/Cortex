//! Los 11 adapters IDE (porteo 1:1 de cortex/ide/adapters/*.py).
//!
//! Orden del registry de Python (`registry._build_registry`):
//! target primero (claude_code, opencode, pi, codex), luego community
//! (cursor, claude_desktop, vscode, windsurf) y experimentales
//! (zed, antigravity, hermes).

pub mod antigravity;
pub mod claude_code;
pub mod claude_desktop;
pub mod codex;
pub mod cursor;
pub mod hermes;
pub mod opencode;
pub mod pi;
pub mod vscode;
pub mod windsurf;
pub mod zed;

use super::{IdeAdapter, IdeCtx};

/// Registry completo en el orden canónico de Python.
pub fn all_adapters() -> Vec<Box<dyn IdeAdapter>> {
    vec![
        Box::new(claude_code::ClaudeCodeAdapter),
        Box::new(opencode::OpenCodeAdapter),
        Box::new(pi::PiAdapter),
        Box::new(codex::CodexAdapter),
        Box::new(cursor::CursorAdapter),
        Box::new(claude_desktop::ClaudeDesktopAdapter),
        Box::new(vscode::VSCodeAdapter),
        Box::new(windsurf::WindsurfAdapter),
        Box::new(zed::ZedAdapter),
        Box::new(antigravity::AntigravityAdapter),
        Box::new(hermes::HermesAdapter),
    ]
}

/// Helper común `_get_mcp_command` de base.py (sin WSL en fixtures).
pub fn mcp_command(ctx: &IdeCtx) -> serde_json::Value {
    // Binario NATIVO: el port Rust 100% nativo se instala como `cortex-cli`
    // (los flags `mcp-server --stdio` los acepta el nativo, compat legacy).
    serde_json::json!({
        "command": "cortex-cli",
        "args": ["mcp-server", "--stdio"],
        "env": {
            "PYTHONPATH": ctx.project_root.to_string_lossy(),
            "PYTHONWARNINGS": "ignore"
        }
    })
}

#[allow(unused)]
fn _ctx_used(_: &IdeCtx) {}
