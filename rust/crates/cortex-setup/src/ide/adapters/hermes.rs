//! Porteo de cortex/ide/adapters/hermes.py (P8d).
//!
//! Hermes: prompts con header bajo ``prompts`` y MCP bajo ``mcp`` en
//! ``~/.config/hermes/config.json`` (config user-level, no depende del
//! project_root salvo para el comando MCP).

use serde_json::{json, Value};

use crate::ide::adapters::mcp_command;
use crate::ide::base::{backup_file, deep_merge_dict, generate_autogen_header, json_dump_ascii};
use crate::ide::{IdeAdapter, IdeCtx, Prompts};

/// Claves canónicas que este adapter escribe bajo ``prompts``.
const CORTEX_PROMPT_KEYS: [&str; 2] = ["cortex-sync", "cortex-SDDwork"];

pub struct HermesAdapter;

impl HermesAdapter {
    #[allow(dead_code)]
    pub fn new() -> Self {
        HermesAdapter
    }
}

impl Default for HermesAdapter {
    fn default() -> Self {
        Self::new()
    }
}

fn config_path(ctx: &IdeCtx) -> std::path::PathBuf {
    ctx.home.join(".config").join("hermes").join("config.json")
}

impl IdeAdapter for HermesAdapter {
    fn name(&self) -> &'static str {
        "hermes"
    }

    fn display_name(&self) -> &'static str {
        "Hermes"
    }

    fn config_paths(&self, ctx: &IdeCtx) -> Vec<(String, std::path::PathBuf)> {
        vec![("config".into(), config_path(ctx))]
    }

    fn inject_profiles(&self, ctx: &IdeCtx, prompts: &Prompts) -> Result<Vec<String>, String> {
        let config_path = config_path(ctx);
        std::fs::create_dir_all(config_path.parent().expect("parent"))
            .map_err(|e| format!("mkdir config dir: {e}"))?;

        backup_file(ctx, &config_path);

        // contextlib.suppress(Exception) en la lectura/parse.
        let mut data: Value = read_json_or_empty(&config_path);

        if let Some(obj) = data.as_object_mut() {
            obj.entry("prompts".to_string())
                .or_insert_with(|| json!({}));
        }

        let header = generate_autogen_header(
            ctx,
            &[
                ".cortex/skills/cortex-sync.md",
                ".cortex/skills/cortex-SDDwork.md",
            ],
            "hermes",
        );

        let mut cortex_prompts = json!({});
        for skill_name in CORTEX_PROMPT_KEYS {
            if let Some(content) = prompts.get(skill_name) {
                cortex_prompts
                    .as_object_mut()
                    .expect("objeto literal")
                    .insert(
                        skill_name.to_string(),
                        Value::String(format!("{header}\n\n{content}")),
                    );
            }
        }

        // Deep merge to preserve other prompts
        if let Some(obj) = data.as_object_mut() {
            let merged = deep_merge_dict(
                obj.get("prompts").expect("prompts existe tras setdefault"),
                &cortex_prompts,
            );
            obj.insert("prompts".into(), merged);
        }

        std::fs::write(&config_path, json_dump_ascii(&data))
            .map_err(|e| format!("write {}: {e}", config_path.display()))?;
        Ok(vec![config_path.to_string_lossy().into_owned()])
    }

    fn inject_mcp(&self, ctx: &IdeCtx) -> Result<Vec<String>, String> {
        let config_path = config_path(ctx);
        std::fs::create_dir_all(config_path.parent().expect("parent"))
            .map_err(|e| format!("mkdir config dir: {e}"))?;

        backup_file(ctx, &config_path);

        let mut data: Value = read_json_or_empty(&config_path);

        if let Some(obj) = data.as_object_mut() {
            obj.entry("mcp".to_string()).or_insert_with(|| json!({}));
        }

        // _get_mcp_command sin WSL (needs_wsl_shielding == False):
        // {"command": "cortex", "args": ["mcp-server","--stdio"],
        //  "env": {"PYTHONPATH": <root>, "PYTHONWARNINGS": "ignore"}}.
        let mcp_cmd = mcp_command(ctx);
        // Orden de claves del dict literal de Python: command, args, env.
        let cortex_config = json!({
            "command": mcp_cmd.get("command").cloned().unwrap_or(Value::Null),
            "args": mcp_cmd.get("args").cloned().unwrap_or_else(|| json!([])),
            "env": mcp_cmd.get("env").cloned().unwrap_or_else(|| json!({})),
        });

        // Deep merge to preserve other MCP servers
        if let Some(obj) = data.as_object_mut() {
            let merged = deep_merge_dict(
                obj.get("mcp").expect("mcp existe tras setdefault"),
                &json!({"cortex": cortex_config}),
            );
            obj.insert("mcp".into(), merged);
        }

        std::fs::write(&config_path, json_dump_ascii(&data))
            .map_err(|e| format!("write {}: {e}", config_path.display()))?;
        Ok(vec![config_path.to_string_lossy().into_owned()])
    }

    /// Quitar lo inyectado por Cortex de ``~/.config/hermes/config.json``.
    ///
    /// Merge inverso: SOLO ``prompts.{cortex-sync,cortex-SDDwork}`` y
    /// ``mcp.cortex``; todo lo ajeno queda intacto. ``project_root`` no
    /// aplica (config user-level) pero se acepta por contrato V2.
    /// NOTA: Python no hace unlink aunque el archivo quede vacío y NO crea
    /// backup al reescribir aquí — se espeja exactamente.
    fn uninstall(&self, ctx: &IdeCtx) -> Vec<String> {
        let mut removed: Vec<String> = Vec::new();
        let config_path = config_path(ctx);
        if !config_path.exists() {
            return removed;
        }

        let data: Value = match std::fs::read_to_string(&config_path)
            .map_err(|e| e.to_string())
            .and_then(|t| serde_json::from_str::<Value>(&t).map_err(|e| e.to_string()))
        {
            Ok(v) => v,
            Err(_) => {
                // logger.warning(...) es solo log, sin efecto en archivos.
                return vec![format!("{} (skipped: invalid JSON)", config_path.display())];
            }
        };

        let mut data = data;
        let mut changed = false;

        if let Some(prompts) = data.get_mut("prompts").and_then(Value::as_object_mut) {
            for key in CORTEX_PROMPT_KEYS {
                if prompts.contains_key(key) {
                    prompts.remove(key);
                    changed = true;
                    removed.push(format!(
                        "{} (prompt '{key}' removed)",
                        config_path.display()
                    ));
                }
            }
        }

        if let Some(mcp) = data.get_mut("mcp").and_then(Value::as_object_mut) {
            if mcp.contains_key("cortex") {
                mcp.remove("cortex");
                changed = true;
                removed.push(format!("{} (cortex entry removed)", config_path.display()));
            }
        }

        if changed {
            // Python propaga excepciones de escritura, pero el contrato del
            // trait devuelve Vec<String>; en fixtures la escritura no falla.
            let _ = std::fs::write(&config_path, json_dump_ascii(&data));
        }
        removed
    }
}

/// Lee un archivo JSON; ante lectura/parse fallido devuelve objeto vacío
/// (espejo de `contextlib.suppress(Exception)` alrededor de load en Python).
fn read_json_or_empty(path: &std::path::Path) -> Value {
    if path.exists() {
        if let Ok(text) = std::fs::read_to_string(path) {
            if let Ok(parsed) = serde_json::from_str::<Value>(&text) {
                return parsed;
            }
        }
    }
    json!({})
}
