//! Porteo de cortex/ide/adapters/zed.py (P8d).
//!
//! Zed: los prompts canónicos se escriben DIRECTO en `~/.zed/agents.json`
//! (user-level) como agents con `system_prompt`. Sin MCP injection
//! (stub en Python también). Uninstall = merge inverso por clave.

use std::path::PathBuf;

use serde_json::{json, Value};

use crate::ide::base::{backup_file, deep_merge_dict, generate_autogen_header, json_dump_ascii};
use crate::ide::{IdeAdapter, IdeCtx};

/// Claves canónicas que este adapter escribe en ``agents.json``.
const CORTEX_AGENT_KEYS: [&str; 2] = ["cortex-sync", "cortex-SDDwork"];

pub struct ZedAdapter;

impl ZedAdapter {
    #[allow(dead_code)]
    pub fn new() -> Self {
        ZedAdapter
    }
}

impl Default for ZedAdapter {
    fn default() -> Self {
        Self::new()
    }
}

fn agents_json_path(ctx: &IdeCtx) -> PathBuf {
    // Python: Path.home() / ".zed" / "agents.json".
    ctx.home.join(".zed").join("agents.json")
}

impl IdeAdapter for ZedAdapter {
    fn name(&self) -> &'static str {
        "zed"
    }

    fn display_name(&self) -> &'static str {
        "Zed"
    }

    fn config_paths(&self, ctx: &IdeCtx) -> Vec<(String, PathBuf)> {
        vec![("agents".into(), agents_json_path(ctx))]
    }

    fn inject_profiles(
        &self,
        ctx: &IdeCtx,
        prompts: &crate::ide::Prompts,
    ) -> Result<Vec<String>, String> {
        let agents_path = agents_json_path(ctx);
        std::fs::create_dir_all(agents_path.parent().expect("agents.json tiene parent"))
            .map_err(|e| format!("mkdir {}: {e}", agents_path.parent().unwrap().display()))?;

        backup_file(ctx, &agents_path);

        let header = generate_autogen_header(
            ctx,
            &[
                ".cortex/skills/cortex-sync.md",
                ".cortex/skills/cortex-SDDwork.md",
            ],
            "zed",
        );

        // En Zed los prompts se escriben dentro de agents.json directamente.
        // NOTA de paridad: el prompt se usa RAW (sin strip de frontmatter),
        // igual que el dict-comp de Python.
        let mut data: Value = json!({ "agents": {} });
        if agents_path.exists() {
            if let Ok(text) = std::fs::read_to_string(&agents_path) {
                if let Ok(parsed) = serde_json::from_str::<Value>(&text) {
                    data = parsed;
                }
            }
        }
        // Python: data.setdefault("agents", {}). Si el JSON parseado no es
        // un objeto, Python crashearía (AttributeError); aquí se normaliza a
        // objeto fresco — caso fuera del contrato de fixtures.
        if let Some(obj) = data.as_object_mut() {
            obj.entry("agents".to_string()).or_insert_with(|| json!({}));
        }

        let mut cortex_agents = serde_json::Map::new();
        if let Some(prompt) = prompts.get("cortex-sync") {
            cortex_agents.insert(
                "cortex-sync".into(),
                json!({
                    "name": "Cortex Sync",
                    "description": "Pre-flight analysis with context injection",
                    "system_prompt": format!("{header}\n\n{prompt}"),
                }),
            );
        }
        if let Some(prompt) = prompts.get("cortex-SDDwork") {
            cortex_agents.insert(
                "cortex-SDDwork".into(),
                json!({
                    "name": "Cortex SDDwork",
                    "description": "Implementation orchestrator",
                    "system_prompt": format!("{header}\n\n{prompt}"),
                }),
            );
        }

        // Deep merge para preservar otros agents.
        let merged = deep_merge_dict(
            data.get("agents").expect("agents setdefault"),
            &Value::Object(cortex_agents),
        );
        if let Some(obj) = data.as_object_mut() {
            obj.insert("agents".into(), merged);
        }

        std::fs::write(&agents_path, json_dump_ascii(&data))
            .map_err(|e| format!("write {}: {e}", agents_path.display()))?;
        Ok(vec![agents_path.to_string_lossy().into_owned()])
    }

    fn inject_mcp(&self, _ctx: &IdeCtx) -> Result<Vec<String>, String> {
        // Zed soporta MCP vía extensions/settings pero requiere config manual;
        // el adapter de Python también devuelve [] acá.
        Ok(Vec::new())
    }

    /// Quitar los agents canónicos de Cortex de ``~/.zed/agents.json``.
    ///
    /// Merge inverso: se eliminan SOLO las claves ``agents.cortex-sync`` y
    /// ``agents.cortex-SDDwork``; cualquier otro agent o clave queda intacto.
    /// ``project_root`` no aplica (config user-level).
    fn uninstall(&self, ctx: &IdeCtx) -> Vec<String> {
        let mut removed: Vec<String> = Vec::new();
        let agents_path = agents_json_path(ctx);
        if !agents_path.exists() {
            return removed;
        }

        let data: Value = match std::fs::read_to_string(&agents_path)
            .map_err(|e| e.to_string())
            .and_then(|t| serde_json::from_str::<Value>(&t).map_err(|e| e.to_string()))
        {
            Ok(v) => v,
            Err(_) => {
                // Python: logger.warning + report skip.
                return vec![format!("{} (skipped: invalid JSON)", agents_path.display())];
            }
        };

        let mut changed = false;
        if let Some(obj) = data.as_object() {
            if let Some(Value::Object(agents)) = obj.get("agents") {
                let mut cleaned = agents.clone();
                for key in CORTEX_AGENT_KEYS {
                    if cleaned.remove(key).is_some() {
                        changed = true;
                        removed.push(format!("{} (agent '{key}' removed)", agents_path.display()));
                    }
                }
                if changed {
                    let mut new_data = data.clone();
                    if let Some(new_obj) = new_data.as_object_mut() {
                        new_obj.insert("agents".into(), Value::Object(cleaned));
                    }
                    let _ = std::fs::write(&agents_path, json_dump_ascii(&new_data));
                }
            }
            // agents existe pero no es dict → Python: isinstance false,
            // sin cambios (mismo resultado silencioso).
        }
        // data no-objeto válido: Python crashearía en .get(); acá termina
        // sin cambios — comportamiento fuera del contrato de fixtures.
        removed
    }
}
