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

/// Binario que los IDEs deben ejecutar para el MCP.
///
/// Orden: `CORTEX_CLI_BIN` (Brain / tests) → sibling de `current_exe`
/// (`cortex-cli` o `cortex-cli-<triple>`, sidecar Tauri) → PATH → nombre
/// pelado `cortex-cli` (paridad con el oráculo cuando no hay binario).
pub fn cortex_cli_command() -> String {
    if let Ok(p) = std::env::var("CORTEX_CLI_BIN") {
        let p = p.trim();
        if !p.is_empty() {
            return p.to_string();
        }
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let direct = dir.join("cortex-cli");
            if direct.is_file() {
                return direct.to_string_lossy().into_owned();
            }
            if let Ok(entries) = std::fs::read_dir(dir) {
                for entry in entries.flatten() {
                    let name = entry.file_name();
                    let s = name.to_string_lossy();
                    if s == "cortex-cli" || s.starts_with("cortex-cli-") {
                        return entry.path().to_string_lossy().into_owned();
                    }
                }
            }
        }
    }
    if let Some(path_env) = std::env::var_os("PATH") {
        for dir in std::env::split_paths(&path_env) {
            let candidate = dir.join("cortex-cli");
            if candidate.is_file() {
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    if let Ok(md) = std::fs::metadata(&candidate) {
                        if md.permissions().mode() & 0o111 != 0 {
                            return candidate.to_string_lossy().into_owned();
                        }
                    }
                }
                #[cfg(not(unix))]
                {
                    return candidate.to_string_lossy().into_owned();
                }
            }
        }
    }
    "cortex-cli".to_string()
}

/// Helper común `_get_mcp_command` de base.py (sin WSL en fixtures).
pub fn mcp_command(ctx: &IdeCtx) -> serde_json::Value {
    serde_json::json!({
        "command": cortex_cli_command(),
        "args": ["mcp-server", "--stdio"],
        "env": {
            "PYTHONPATH": ctx.project_root.to_string_lossy(),
            "PYTHONWARNINGS": "ignore"
        }
    })
}

#[allow(unused)]
fn _ctx_used(_: &IdeCtx) {}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;
    use std::path::Path;
    use std::sync::Mutex;

    static ENV: Mutex<()> = Mutex::new(());

    #[test]
    fn cortex_cli_command_honra_env() {
        let _g = ENV.lock().unwrap_or_else(|e| e.into_inner());
        std::env::set_var("CORTEX_CLI_BIN", "/opt/CortexBrain/cortex-cli");
        assert_eq!(cortex_cli_command(), "/opt/CortexBrain/cortex-cli");
        let ctx = IdeCtx {
            project_root: Path::new("/tmp/proj"),
            home: Path::new("/tmp/home"),
            now: Utc::now(),
        };
        let v = mcp_command(&ctx);
        assert_eq!(v["command"], "/opt/CortexBrain/cortex-cli");
        std::env::remove_var("CORTEX_CLI_BIN");
    }
}
