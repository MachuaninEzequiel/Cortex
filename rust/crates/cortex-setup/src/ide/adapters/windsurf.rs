//! Porteo de cortex/ide/adapters/windsurf.py (P8d).
//!
//! Windsurf (Codeium): ``AGENTS.md`` en el project root SOBRESCRITO con el
//! texto canónico Cortex + MCP user-level en
//! ``~/.codeium/windsurf/mcp_config.json``. Backups con nombre único
//! microsegundo para evitar colisiones mismo-segundo.

use std::path::{Path, PathBuf};

use serde_json::{json, Value};

use crate::ide::base::{
    backup_file, deep_merge_dict, is_content_identical_to_bundle, json_dump_ascii,
};
use crate::ide::Prompts;
use crate::ide::{IdeAdapter, IdeCtx};

/// `_unique_backup` de Python: ``_backup_file`` con nombre único
/// (evita colisiones mismo-segundo entre injects consecutivos). Con reloj
/// congelado la semántica POSIX del rename (sobrescribe destino) replica
/// exactamente el comportamiento determinista de Python.
fn unique_backup(ctx: &IdeCtx, file_path: &Path) -> PathBuf {
    let backup = backup_file(ctx, file_path);
    if !backup.exists() {
        return backup;
    }
    // %f de Python son MICROsegundos (6 dígitos).
    let stamp = format!(
        "{}{:06}",
        ctx.now.format("%Y%m%d_%H%M%S"),
        ctx.now.timestamp_subsec_micros()
    );
    let renamed = backup.with_file_name(format!(
        "{}.cortex_backup_{stamp}",
        file_path.file_name().unwrap_or_default().to_string_lossy()
    ));
    let _ = std::fs::rename(&backup, &renamed);
    renamed
}

/// Texto canónico que este adapter escribe en ``AGENTS.md``. Es la SSoT
/// tanto para install como para uninstall (detección de archivo 100% Cortex).
fn cortex_agents_md() -> String {
    [
        "# Cortex Workflow",
        "",
        "Follow this Cortex workflow for every task in this repository:",
        "",
        "1. Start with pre-flight analysis. Call `cortex_sync_ticket` with the user's request before creating any spec with `cortex_create_spec`.",
        "2. Inspect only the relevant files, then persist the implementation spec.",
        "3. Implement directly for simple changes. For complex changes, do deeper analysis first and then implement with minimal, focused edits.",
        "4. Finish every completed implementation by calling `cortex_save_session` with the changed files, technical decisions, validation results, and next steps.",
        "",
        "Additional Cortex rules:",
        "",
        "- Never call `cortex_create_spec` before `cortex_sync_ticket`.",
        "- Do not over-engineer simple tasks.",
        "- Keep the final session summary concise but complete enough for future retrieval.",
        "- If a Cortex MCP tool fails, stop and report the blocker instead of inventing context.",
    ]
    .join("\n")
        + "\n"
}

pub struct WindsurfAdapter;

impl WindsurfAdapter {
    #[allow(dead_code)]
    pub fn new() -> Self {
        WindsurfAdapter
    }
}

impl Default for WindsurfAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl IdeAdapter for WindsurfAdapter {
    fn name(&self) -> &'static str {
        "windsurf"
    }

    fn display_name(&self) -> &'static str {
        "Windsurf"
    }

    fn config_paths(&self, ctx: &IdeCtx) -> Vec<(String, PathBuf)> {
        vec![(
            "mcp".into(),
            ctx.home
                .join(".codeium")
                .join("windsurf")
                .join("mcp_config.json"),
        )]
    }

    fn inject_profiles(&self, ctx: &IdeCtx, _prompts: &Prompts) -> Result<Vec<String>, String> {
        let agents_path = ctx.project_root.join("AGENTS.md");
        std::fs::create_dir_all(agents_path.parent().expect("AGENTS.md tiene parent"))
            .map_err(|e| format!("mkdir root: {e}"))?;
        unique_backup(ctx, &agents_path);
        std::fs::write(&agents_path, cortex_agents_md())
            .map_err(|e| format!("write AGENTS.md: {e}"))?;
        Ok(vec![agents_path.to_string_lossy().into_owned()])
    }

    fn inject_mcp(&self, ctx: &IdeCtx) -> Result<Vec<String>, String> {
        let mcp_file = ctx
            .home
            .join(".codeium")
            .join("windsurf")
            .join("mcp_config.json");
        std::fs::create_dir_all(
            mcp_file
                .parent()
                .expect("mcp_config tiene parent (~/.codeium/windsurf)"),
        )
        .map_err(|e| format!("mkdir ~/.codeium/windsurf: {e}"))?;

        unique_backup(ctx, &mcp_file);

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

        let cortex_config = json!({
            "command": "cortex",
            "args": ["mcp-server", "--stdio", "--project-root",
                     ctx.project_root.to_string_lossy()],
            "env": {"PYTHONWARNINGS": "ignore"},
        });

        let merged = deep_merge_dict(
            data.get("mcpServers")
                .expect("mcpServers setdefault arriba"),
            &json!({"cortex": cortex_config}),
        );
        if let Some(obj) = data.as_object_mut() {
            obj.insert("mcpServers".into(), merged);
        }

        std::fs::write(&mcp_file, json_dump_ascii(&data))
            .map_err(|e| format!("write {}: {e}", mcp_file.display()))?;
        Ok(vec![mcp_file.to_string_lossy().into_owned()])
    }

    /// Eliminar lo inyectado por Cortex en Windsurf.
    ///
    /// ``AGENTS.md`` fue SOBRESCRITO por inject_profiles (no mergeado):
    /// - Backups existentes → se restaura el contenido del backup MAS VIEJO
    ///   y se eliminan los backups (artefactos 100% Cortex).
    /// - Sin backup y contenido idéntico al canónico → unlink.
    /// - Cualquier otro caso → intacto, reportado como skipped.
    ///
    /// Además limpia ``mcpServers.cortex`` del MCP config user-level.
    /// El cleanup de MCP está envuelto en suppress: JSON inválido se salta
    /// SIN línea de reporte (a diferencia de antigravity).
    fn uninstall(&self, ctx: &IdeCtx) -> Vec<String> {
        let mut removed: Vec<String> = Vec::new();

        // En Rust el contrato IdeAdapter siempre provee ctx.project_root
        // (equivalente a project_root != None de Python).
        let root = ctx.project_root;
        let agents_path = root.join("AGENTS.md");
        let backups = sorted_glob(root, "AGENTS.md.cortex_backup_");
        if !backups.is_empty() {
            // El backup más viejo es el estado previo a la primera escritura
            // de Cortex; los siguientes ya pueden contener contenido
            // Cortex regenerado.
            let oldest = &backups[0];
            let content = std::fs::read_to_string(oldest).unwrap_or_default();
            let _ = std::fs::write(&agents_path, content);
            removed.push(format!(
                "{} (restored from {})",
                agents_path.display(),
                oldest
                    .file_name()
                    .map(|n| n.to_string_lossy())
                    .unwrap_or_default()
            ));
            for backup in &backups {
                let _ = std::fs::remove_file(backup);
                removed.push(backup.to_string_lossy().into_owned());
            }
        } else if agents_path.exists() {
            let existing = std::fs::read_to_string(&agents_path).unwrap_or_default();
            if is_content_identical_to_bundle(&existing, &cortex_agents_md()) {
                let _ = std::fs::remove_file(&agents_path);
                removed.push(agents_path.to_string_lossy().into_owned());
            } else {
                removed.push(format!(
                    "{} (skipped: mixed/unknown content)",
                    agents_path.display()
                ));
            }
        }

        // Limpiar entrada cortex del MCP config user-level. TODO el bloque
        // está dentro de contextlib.suppress(Exception): ante cualquier
        // error NO se reporta nada.
        let mcp_file = ctx
            .home
            .join(".codeium")
            .join("windsurf")
            .join("mcp_config.json");
        if mcp_file.exists() {
            let cleaned = (|| -> Option<()> {
                let text = std::fs::read_to_string(&mcp_file).ok()?;
                let mut data: Value = serde_json::from_str(&text).ok()?;
                let obj = data.as_object_mut()?;
                {
                    let servers = match obj.get_mut("mcpServers") {
                        Some(Value::Object(s)) => s,
                        _ => return None,
                    };
                    if !servers.contains_key("cortex") {
                        return None;
                    }
                    servers.remove("cortex");
                }
                std::fs::write(&mcp_file, json_dump_ascii(&data)).ok()?;
                Some(())
            })();
            if cleaned.is_some() {
                removed.push(format!("{} (cortex entry removed)", mcp_file.display()));
            }
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
