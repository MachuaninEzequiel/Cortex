//! Porteo de cortex/ide/adapters/claude_desktop.py (P8d).
//!
//! Claude Desktop solo consume MCP: sin perfiles locales. El config vive
//! bajo HOME (`~/Library/Application Support/Claude/…` en macOS,
//! `~/.config/Claude/…` en Linux/WSL) y pide escudo WSL
//! ([`IdeAdapter::needs_wsl_shielding`] → true; en fixtures `_is_wsl()` es
//! siempre false, así que el comando es el directo de `base::_get_mcp_command`).

use std::path::PathBuf;

use serde_json::{json, Value};

use crate::ide::base::{backup_file, deep_merge_dict, json_dump_ascii};
use crate::ide::{IdeAdapter, IdeCtx};

pub struct ClaudeDesktopAdapter;

impl ClaudeDesktopAdapter {
    #[allow(dead_code)]
    pub fn new() -> Self {
        ClaudeDesktopAdapter
    }
}

impl Default for ClaudeDesktopAdapter {
    fn default() -> Self {
        Self::new()
    }
}

/// Rutas candidatas espejo de `get_config_paths` (orden de evaluación
/// incluido: macOS primero, `.config` como default final).
fn candidate_paths(home: &std::path::Path) -> [PathBuf; 2] {
    [
        home.join("Library")
            .join("Application Support")
            .join("Claude")
            .join("claude_desktop_config.json"),
        home.join(".config")
            .join("Claude")
            .join("claude_desktop_config.json"),
    ]
}

impl IdeAdapter for ClaudeDesktopAdapter {
    fn name(&self) -> &'static str {
        "claude_desktop"
    }

    fn display_name(&self) -> &'static str {
        "Claude Desktop"
    }

    /// Pick the one that exists, or default to `.config` for Linux/WSL.
    fn config_paths(&self, ctx: &IdeCtx) -> Vec<(String, PathBuf)> {
        let candidates = candidate_paths(ctx.home);
        let mut target = candidates[1].clone();
        for p in &candidates {
            if p.exists() || p.parent().map(|d| d.exists()).unwrap_or(false) {
                target = p.clone();
                break;
            }
        }
        vec![("mcp".into(), target)]
    }

    fn needs_wsl_shielding(&self) -> bool {
        true
    }

    /// Claude Desktop only uses MCP, it doesn't have local agent profiles.
    fn inject_profiles(
        &self,
        _ctx: &IdeCtx,
        _prompts: &crate::ide::Prompts,
    ) -> Result<Vec<String>, String> {
        Ok(Vec::new())
    }

    fn inject_mcp(&self, ctx: &IdeCtx) -> Result<Vec<String>, String> {
        let mcp_file = self.config_paths(ctx)[0].1.clone();
        if let Some(parent) = mcp_file.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("mkdir {}: {e}", parent.display()))?;
        }

        backup_file(ctx, &mcp_file);

        let mut data: Value = json!({"mcpServers": {}});
        if mcp_file.exists() {
            if let Ok(text) = std::fs::read_to_string(&mcp_file) {
                if let Ok(parsed) = serde_json::from_str::<Value>(&text) {
                    data = parsed;
                }
            }
        }

        if let Some(obj) = data.as_object_mut() {
            obj.entry("mcpServers".to_string())
                .or_insert_with(|| json!({}));
        }

        let mcp_cmd = super::mcp_command(ctx);
        // Orden de claves del dict de Python: command, args, env, enabled.
        let cortex_config = json!({
            "command": mcp_cmd.get("command").cloned().unwrap_or(Value::Null),
            "args": mcp_cmd.get("args").cloned().unwrap_or(Value::Null),
            "env": mcp_cmd.get("env").cloned().unwrap_or(Value::Null),
            "enabled": true,
        });

        // Deep merge to preserve other MCP servers
        let merged = deep_merge_dict(
            data.get("mcpServers").unwrap_or(&json!({})),
            &json!({"cortex": cortex_config}),
        );
        if let Some(obj) = data.as_object_mut() {
            obj.insert("mcpServers".into(), merged);
        }

        std::fs::write(&mcp_file, json_dump_ascii(&data))
            .map_err(|e| format!("write {}: {e}", mcp_file.display()))?;
        Ok(vec![mcp_file.to_string_lossy().into_owned()])
    }

    /// Remove the Cortex MCP server from claude_desktop_config.json.
    ///
    /// Regla de oro: SOLO se borra lo que Cortex creó. Se remueve la clave
    /// ``mcpServers.cortex`` (deep-merge inverso); cualquier otro server o
    /// clave ajena se preserva. Archivo que queda en ``{}`` → unlink.
    /// Contenido mixto/desconocido (JSON inválido) queda intacto y se
    /// reporta como ``skipped``. Idempotente: segunda pasada devuelve ``[]``.
    fn uninstall(&self, ctx: &IdeCtx) -> Vec<String> {
        let mut report: Vec<String> = Vec::new();
        let mcp_file = self.config_paths(ctx)[0].1.clone();
        if !mcp_file.exists() {
            return report;
        }

        let Ok(text) = std::fs::read_to_string(&mcp_file) else {
            report.push(format!(
                "{} (skipped: invalid JSON, not touched)",
                mcp_file.display()
            ));
            return report;
        };
        let Ok(data) = serde_json::from_str::<Value>(&text) else {
            report.push(format!(
                "{} (skipped: invalid JSON, not touched)",
                mcp_file.display()
            ));
            return report;
        };

        if !data.is_object() {
            report.push(format!(
                "{} (skipped: unexpected JSON shape, not touched)",
                mcp_file.display()
            ));
            return report;
        }

        let mut data = data;
        let mut changed = false;
        if let Some(obj) = data.as_object_mut() {
            if let Some(Value::Object(servers)) = obj.get_mut("mcpServers") {
                if servers.contains_key("cortex") {
                    servers.remove("cortex");
                    changed = true;
                    if servers.is_empty() {
                        obj.remove("mcpServers");
                    }
                }
            }
        }

        if !changed {
            return report;
        }

        if data.as_object().map(|o| o.is_empty()).unwrap_or(false) {
            let _ = std::fs::remove_file(&mcp_file);
            report.push(mcp_file.to_string_lossy().into_owned());
        } else {
            backup_file(ctx, &mcp_file);
            let _ = std::fs::write(&mcp_file, json_dump_ascii(&data));
            report.push(format!("{} (Cortex keys removed)", mcp_file.display()));
        }
        report
    }
}
