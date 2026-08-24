//! Porteo de cortex/ide/adapters/antigravity.py (P8d).
//!
//! Antigravity (Gemini Code Assist): config user-level en
//! ``~/.gemini/settings.json`` con ``system_instructions`` (profiles) y
//! ``mcp_servers`` (MCP, snake_case). Backups con nombre único
//! microsegundo para evitar colisiones mismo-segundo.

use std::path::{Path, PathBuf};

use serde_json::{json, Value};

use crate::ide::adapters::mcp_command;
use crate::ide::base::{backup_file, deep_merge_dict, generate_autogen_header, json_dump_ascii};
use crate::ide::Prompts;
use crate::ide::{IdeAdapter, IdeCtx};

/// `_unique_backup` de Python: ``_backup_file`` con nombre único.
///
/// El timestamp de ``_backup_file`` tiene granularidad de segundos: dos
/// injects en el mismo segundo (p.ej. profiles + MCP seguidos) colisionan
/// y el segundo backup SOBRESCRIBE al primero, destruyendo el snapshot
/// previo a Cortex que uninstall necesita para restaurar. El rename a un
/// nombre con microsegundos lo mitiga en uso real; en fixtures el reloj
/// está congelado y la semántica POSIX del rename (sobrescribe destino)
/// replica exactamente el comportamiento determinista de Python.
fn unique_backup(ctx: &IdeCtx, file_path: &Path) -> PathBuf {
    let backup = backup_file(ctx, file_path);
    if !backup.exists() {
        return backup;
    }
    // datetime.now().strftime("%Y%m%d_%H%M%S%f") — %f son MICROsegundos
    // (6 dígitos); el %f de chrono es nanosegundos, por eso subsec_micros.
    let stamp = format!(
        "{}{:06}",
        ctx.now.format("%Y%m%d_%H%M%S"),
        ctx.now.timestamp_subsec_micros()
    );
    let renamed = backup.with_file_name(format!(
        "{}.cortex_backup_{stamp}",
        file_path.file_name().unwrap_or_default().to_string_lossy()
    ));
    // Path.rename de Python sobrescribe silenciosamente en POSIX (igual
    // que std::fs::rename sobre Linux).
    let _ = std::fs::rename(&backup, &renamed);
    renamed
}

pub struct AntigravityAdapter;

impl AntigravityAdapter {
    #[allow(dead_code)]
    pub fn new() -> Self {
        AntigravityAdapter
    }
}

impl Default for AntigravityAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl IdeAdapter for AntigravityAdapter {
    fn name(&self) -> &'static str {
        "antigravity"
    }

    fn display_name(&self) -> &'static str {
        "Antigravity (Gemini Code Assist)"
    }

    fn config_paths(&self, ctx: &IdeCtx) -> Vec<(String, PathBuf)> {
        vec![(
            "settings".into(),
            ctx.home.join(".gemini").join("settings.json"),
        )]
    }

    fn inject_profiles(&self, ctx: &IdeCtx, prompts: &Prompts) -> Result<Vec<String>, String> {
        let settings_path = ctx.home.join(".gemini").join("settings.json");
        std::fs::create_dir_all(
            settings_path
                .parent()
                .expect("settings tiene parent (~/.gemini)"),
        )
        .map_err(|e| format!("mkdir ~/.gemini: {e}"))?;

        unique_backup(ctx, &settings_path);

        let mut data: Value = Value::Object(Default::default());
        if settings_path.exists() {
            if let Ok(text) = std::fs::read_to_string(&settings_path) {
                if let Ok(parsed) = serde_json::from_str::<Value>(&text) {
                    data = parsed;
                }
            }
        }
        if let Some(obj) = data.as_object_mut() {
            obj.entry("system_instructions".to_string())
                .or_insert_with(|| Value::String(String::new()));
        }

        let header = generate_autogen_header(
            ctx,
            &[
                ".cortex/skills/cortex-sync.md",
                ".cortex/skills/cortex-SDDwork.md",
            ],
            "antigravity",
        );

        let mut combined_prompt = format!(
            "{header}\n\nYou are working in a Cortex project. Please follow these profiles:\n\n"
        );
        for skill_name in ["cortex-sync", "cortex-SDDwork"] {
            if let Some(body) = prompts.get(skill_name) {
                combined_prompt.push_str(&format!("## {skill_name}\n{body}\n\n"));
            }
        }

        // Replace instructions (not append, since this is JSON).
        if let Some(obj) = data.as_object_mut() {
            obj.insert("system_instructions".into(), Value::String(combined_prompt));
        }

        std::fs::write(&settings_path, json_dump_ascii(&data))
            .map_err(|e| format!("write {}: {e}", settings_path.display()))?;
        Ok(vec![settings_path.to_string_lossy().into_owned()])
    }

    fn inject_mcp(&self, ctx: &IdeCtx) -> Result<Vec<String>, String> {
        let settings_path = ctx.home.join(".gemini").join("settings.json");
        std::fs::create_dir_all(
            settings_path
                .parent()
                .expect("settings tiene parent (~/.gemini)"),
        )
        .map_err(|e| format!("mkdir ~/.gemini: {e}"))?;

        unique_backup(ctx, &settings_path);

        let mut data: Value = Value::Object(Default::default());
        if settings_path.exists() {
            if let Ok(text) = std::fs::read_to_string(&settings_path) {
                if let Ok(parsed) = serde_json::from_str::<Value>(&text) {
                    data = parsed;
                }
            }
        }
        if let Some(obj) = data.as_object_mut() {
            obj.entry("mcp_servers".to_string())
                .or_insert_with(|| json!({}));
        }

        let mcp_cmd = mcp_command(ctx);
        let cortex_config = json!({
            "command": mcp_cmd["command"],
            "args": mcp_cmd["args"],
            "env": mcp_cmd["env"],
        });

        // Deep merge to preserve other MCP servers.
        let merged = deep_merge_dict(
            data.get("mcp_servers")
                .expect("mcp_servers setdefault arriba"),
            &json!({"cortex": cortex_config}),
        );
        if let Some(obj) = data.as_object_mut() {
            obj.insert("mcp_servers".into(), merged);
        }

        std::fs::write(&settings_path, json_dump_ascii(&data))
            .map_err(|e| format!("write {}: {e}", settings_path.display()))?;
        Ok(vec![settings_path.to_string_lossy().into_owned()])
    }

    /// Revertir lo inyectado por Cortex en ``~/.gemini/settings.json``.
    ///
    /// - Si existen backups → se restaura ``system_instructions`` desde el
    ///   backup MAS VIEJO cuyo valor NO sea generado por Cortex y se eliminan
    ///   los backups (artefactos 100% Cortex).
    /// - Sin backup útil, si las instrucciones actuales son generadas por
    ///   Cortex → se resetean a vacío (el default del propio inject).
    /// - Se limpia ``mcp_servers.cortex`` preservando el resto.
    fn uninstall(&self, ctx: &IdeCtx) -> Vec<String> {
        let mut removed: Vec<String> = Vec::new();
        let settings_path = ctx.home.join(".gemini").join("settings.json");
        if !settings_path.exists() {
            return removed;
        }

        let Ok(text) = std::fs::read_to_string(&settings_path) else {
            return vec![format!(
                "{} (skipped: invalid JSON)",
                settings_path.display()
            )];
        };
        let mut data: Value = match serde_json::from_str(&text) {
            Ok(parsed) => parsed,
            Err(_) => {
                // logger.warning de Python no es salida observable de paridad.
                return vec![format!(
                    "{} (skipped: invalid JSON)",
                    settings_path.display()
                )];
            }
        };

        let parent = settings_path.parent().expect("settings tiene parent");
        let backups = sorted_glob(parent, "settings.json.cortex_backup_");
        let mut restored = false;
        // El backup útil es el MAS VIEJO cuyo system_instructions NO sea
        // generado por Cortex (los posteriores ya pueden contener
        // instrucciones Cortex regeneradas por inject_mcp).
        for candidate in &backups {
            let backup_data: Option<Value> = std::fs::read_to_string(candidate)
                .ok()
                .and_then(|t| serde_json::from_str(&t).ok());
            let Some(backup_data) = backup_data else {
                continue;
            };
            let instructions = backup_data.get("system_instructions");
            let is_cortex_text = matches!(instructions, Some(Value::String(s)) if s.contains("AUTOGENERATED BY CORTEX"));
            if is_cortex_text {
                continue;
            }
            // Puede ser str o None (clave ausente → null en el JSON final).
            if let Some(obj) = data.as_object_mut() {
                obj.insert(
                    "system_instructions".into(),
                    instructions.cloned().unwrap_or(Value::Null),
                );
            }
            restored = true;
            removed.push(format!(
                "{} (system_instructions restored from {})",
                settings_path.display(),
                candidate
                    .file_name()
                    .map(|n| n.to_string_lossy())
                    .unwrap_or_default()
            ));
            break;
        }
        let mut cleared = false;
        if !restored {
            let instructions = data.get("system_instructions").cloned();
            if let Some(Value::String(s)) = instructions {
                if s.contains("AUTOGENERATED BY CORTEX") {
                    if let Some(obj) = data.as_object_mut() {
                        obj.insert("system_instructions".into(), Value::String(String::new()));
                    }
                    cleared = true;
                    removed.push(format!(
                        "{} (Cortex system_instructions cleared)",
                        settings_path.display()
                    ));
                }
            }
        }

        for backup in &backups {
            let _ = std::fs::remove_file(backup);
            removed.push(backup.to_string_lossy().into_owned());
        }

        let mut changed = false;
        if let Some(Value::Object(servers)) = data.get_mut("mcp_servers") {
            if servers.contains_key("cortex") {
                servers.remove("cortex");
                changed = true;
                removed.push(format!(
                    "{} (cortex entry removed)",
                    settings_path.display()
                ));
            }
        }

        if changed || restored || cleared {
            let _ = std::fs::write(&settings_path, json_dump_ascii(&data));
        }
        removed
    }
}

/// `sorted(Path.glob(pattern))` de Python: rutas ordenadas lexicográficamente.
fn sorted_glob(dir: &Path, prefix: &str) -> Vec<PathBuf> {
    let mut out: Vec<PathBuf> = std::fs::read_dir(dir)
        .into_iter()
        .flatten()
        .flatten()
        .map(|e| e.path())
        .filter(|p| {
            p.file_name()
                .map(|n| n.to_string_lossy().starts_with(prefix))
                .unwrap_or(false)
        })
        .collect();
    out.sort_by_key(|p| p.to_string_lossy().into_owned());
    out
}
