//! Porteo de cortex/ide/adapters/opencode.py (P8d).
//!
//! OpenCode: skills con header en ``~/.config/opencode/skills/``, copia de
//! subagents canónicos y perfiles agent en ``~/.config/opencode/opencode.json``
//! (campo moderno ``permission`` allow|ask|deny; las tools MCP NO se declaran
//! porque opencode las descubre dinámicamente). MCP bajo la clave ``mcp``.

use std::path::PathBuf;

use serde_json::{json, Value};

use crate::ide::adapters::mcp_command;
use crate::ide::base::{backup_file, deep_merge_dict, generate_autogen_header, json_dump_ascii};
use crate::ide::{IdeAdapter, IdeCtx, Prompts};

pub struct OpenCodeAdapter;

impl OpenCodeAdapter {
    #[allow(dead_code)]
    pub fn new() -> Self {
        OpenCodeAdapter
    }
}

impl Default for OpenCodeAdapter {
    fn default() -> Self {
        Self::new()
    }
}

/// Orden canónico de los anchors triádicos tal como los produce
/// `build_all_prompts` en Python (orden de inserción del dict, NO orden
/// alfabético): sync, SDDwork, documenter. `Prompts` es un BTreeMap que
/// no conserva inserción, así que el orden canónico se declara aquí y se
/// filtra por presencia (comportamiento idéntico cuando `prompts` viene
/// de `build_all_prompts`, su único productor real).
const TRIADIC_ORDER: [&str; 3] = ["cortex-sync", "cortex-SDDwork", "cortex-documenter"];

fn config_dir(ctx: &IdeCtx) -> PathBuf {
    ctx.home.join(".config").join("opencode")
}

impl IdeAdapter for OpenCodeAdapter {
    fn name(&self) -> &'static str {
        "opencode"
    }

    fn display_name(&self) -> &'static str {
        "OpenCode"
    }

    fn config_paths(&self, ctx: &IdeCtx) -> Vec<(String, PathBuf)> {
        let dir = config_dir(ctx);
        vec![
            ("main".into(), dir.join("opencode.json")),
            ("skills_dir".into(), dir.join("skills")),
            ("subagents_dir".into(), dir.join("subagents")),
        ]
    }

    fn needs_wsl_shielding(&self) -> bool {
        true
    }

    fn inject_profiles(&self, ctx: &IdeCtx, prompts: &Prompts) -> Result<Vec<String>, String> {
        let config_file = config_dir(ctx).join("opencode.json");
        let skills_dir = config_dir(ctx).join("skills");
        let subagents_dir = config_dir(ctx).join("subagents");

        std::fs::create_dir_all(&skills_dir)
            .map_err(|e| format!("mkdir {}: {e}", skills_dir.display()))?;
        std::fs::create_dir_all(&subagents_dir)
            .map_err(|e| format!("mkdir {}: {e}", subagents_dir.display()))?;
        let mut files_written: Vec<String> = Vec::new();

        let header = generate_autogen_header(
            ctx,
            &[
                ".cortex/skills/cortex-sync.md",
                ".cortex/skills/cortex-SDDwork.md",
                ".cortex/skills/cortex-documenter.md",
            ],
            "opencode",
        );

        // Write core skills with header (orden canónico triádico).
        for skill_name in TRIADIC_ORDER {
            let Some(content) = prompts.get(skill_name) else {
                continue;
            };
            let skill_file = skills_dir.join(format!("{skill_name}.md"));
            backup_file(ctx, &skill_file);
            std::fs::write(&skill_file, format!("{header}\n\n{content}"))
                .map_err(|e| format!("write {}: {e}", skill_file.display()))?;
            files_written.push(skill_file.to_string_lossy().into_owned());
        }

        // Copy subagents with header — resueltos vía WorkspaceLayout
        // (en Rust: ctx.subagents_dir() == project_root/.cortex/subagents).
        // NOTA determinismo: el glob de Python no garantiza orden; aquí se
        // recorre ordenado para que la lista escrita sea reproducible.
        let cortex_subagents_dir = ctx.subagents_dir();
        if cortex_subagents_dir.is_dir() {
            let mut names: Vec<String> = std::fs::read_dir(&cortex_subagents_dir)
                .map_err(|e| format!("readdir {}: {e}", cortex_subagents_dir.display()))?
                .flatten()
                .filter(|e| e.path().is_file() && e.file_name().to_string_lossy().ends_with(".md"))
                .map(|e| e.file_name().to_string_lossy().into_owned())
                .collect();
            names.sort();
            for name in names {
                let dest = subagents_dir.join(&name);
                backup_file(ctx, &dest);
                let body = std::fs::read_to_string(cortex_subagents_dir.join(&name))
                    .map_err(|e| format!("read {}: {e}", name))?;
                let subagent_header = generate_autogen_header(
                    ctx,
                    &[&format!(".cortex/subagents/{name}")],
                    "opencode",
                );
                std::fs::write(&dest, format!("{subagent_header}\n\n{body}"))
                    .map_err(|e| format!("write {}: {e}", dest.display()))?;
                files_written.push(dest.to_string_lossy().into_owned());
            }
        }

        // Read existing config (errores de lectura/parse → {} como en
        // contextlib.suppress de Python).
        let mut data: Value = read_json_or_empty(&config_file);

        backup_file(ctx, &config_file);

        if let Some(obj) = data.as_object_mut() {
            obj.entry("agent".to_string()).or_insert_with(|| json!({}));
        }

        // Perfiles agente de Cortex (Fase 4 plan multi-IDE: campo moderno
        // ``permission``, sin tools MCP — se descubren dinámicamente).
        let cortex_profiles = json!({
            "cortex-sync": {
                "mode": "primary",
                "description": "PRE-FLIGHT: Context gathering and spec preparation.",
                "prompt": format!(
                    "{{file:{}}}",
                    skills_dir.join("cortex-sync.md").display()
                ),
                "permission": {
                    "read": "allow",
                    "write": "deny",
                    "edit": "deny",
                    "bash": "deny",
                },
            },
            "cortex-SDDwork": {
                "mode": "primary",
                "description":
                    "ORCHESTRATOR: Fast Track direct edits or Deep Track delegation.",
                "prompt": format!(
                    "{{file:{}}}",
                    skills_dir.join("cortex-SDDwork.md").display()
                ),
                "permission": {
                    "read": "allow",
                    "write": "allow",
                    "edit": "allow",
                    "bash": "ask",
                    "task": "allow",
                },
            },
            "cortex-documenter": {
                "mode": "primary",
                "description":
                    "CLOSING ANCHOR: Editorial documentation + Session close (Phase 09.A+).",
                "prompt": format!(
                    "{{file:{}}}",
                    skills_dir.join("cortex-documenter.md").display()
                ),
                "permission": {
                    "read": "allow",
                    "write": "allow",
                    "edit": "allow",
                    "bash": "deny",
                    "task": "deny",
                },
            },
        });

        // Deep merge to preserve other agent profiles
        if let Some(obj) = data.as_object_mut() {
            let merged = deep_merge_dict(
                obj.get("agent").expect("agent existe tras setdefault"),
                &cortex_profiles,
            );
            obj.insert("agent".into(), merged);
        }

        std::fs::write(&config_file, json_dump_ascii(&data))
            .map_err(|e| format!("write {}: {e}", config_file.display()))?;
        files_written.push(config_file.to_string_lossy().into_owned());
        Ok(files_written)
    }

    fn inject_mcp(&self, ctx: &IdeCtx) -> Result<Vec<String>, String> {
        let config_file = config_dir(ctx).join("opencode.json");
        std::fs::create_dir_all(config_file.parent().expect("parent"))
            .map_err(|e| format!("mkdir config dir: {e}"))?;

        backup_file(ctx, &config_file);

        let mut data: Value = read_json_or_empty(&config_file);

        if let Some(obj) = data.as_object_mut() {
            obj.entry("mcp".to_string()).or_insert_with(|| json!({}));
        }

        let (command, environment) = if self.needs_wsl_shielding() && crate::ide::base::is_wsl() {
            // Rama WSL real (inaccesible en fixtures: is_wsl() es false).
            let cmd = mcp_command(ctx);
            let args: Vec<String> = cmd
                .get("args")
                .and_then(Value::as_array)
                .map(|a| {
                    a.iter()
                        .map(|v| v.as_str().unwrap_or_default().to_string())
                        .collect()
                })
                .unwrap_or_default();
            (
                {
                    let mut v = vec![cmd
                        .get("command")
                        .and_then(Value::as_str)
                        .unwrap_or_default()
                        .to_string()];
                    v.extend(args);
                    v
                },
                cmd.get("env").cloned().unwrap_or_else(|| json!({})),
            )
        } else {
            (
                vec![
                    "cortex".to_string(),
                    "mcp-server".to_string(),
                    "--stdio".to_string(),
                    "--project-root".to_string(),
                    ctx.project_root.to_string_lossy().into_owned(),
                ],
                json!({"PYTHONWARNINGS": "ignore"}),
            )
        };

        // Orden de claves del dict literal de Python: type, command, enabled,
        // y ``environment`` solo si hay env.
        let mut cortex_config = json!({
            "type": "local",
            "command": command,
            "enabled": true,
        });
        let env_non_empty = environment
            .as_object()
            .map(|o| !o.is_empty())
            .unwrap_or(true);
        if env_non_empty {
            cortex_config
                .as_object_mut()
                .expect("objeto literal")
                .insert("environment".into(), environment);
        }

        // Deep merge to preserve other MCP servers
        if let Some(obj) = data.as_object_mut() {
            let merged = deep_merge_dict(
                obj.get("mcp").expect("mcp existe tras setdefault"),
                &json!({"cortex": cortex_config}),
            );
            obj.insert("mcp".into(), merged);
        }

        std::fs::write(&config_file, json_dump_ascii(&data))
            .map_err(|e| format!("write {}: {e}", config_file.display()))?;
        Ok(vec![config_file.to_string_lossy().into_owned()])
    }

    /// Remove Cortex artifacts (Obra 02 Fase 2). Regla de oro: SOLO se borra
    /// lo que Cortex creó. Idempotente: segunda pasada devuelve ``[]``.
    fn uninstall(&self, ctx: &IdeCtx) -> Vec<String> {
        let mut report: Vec<String> = Vec::new();
        let skills_dir = config_dir(ctx).join("skills");
        let subagents_dir = config_dir(ctx).join("subagents");

        // 1. Skills escritas por inject_profiles (cortex-*.md).
        if skills_dir.is_dir() {
            for skill_file in sorted_md_glob_starting_with(&skills_dir, "cortex-") {
                if skill_file.is_file() {
                    let _ = std::fs::remove_file(&skill_file);
                    report.push(skill_file.to_string_lossy().into_owned());
                }
            }
        }

        // 2. Subagents copiados por inject_profiles: solo los que trae el
        // bundle actual (.cortex/subagents/*.md del proyecto).
        let mut bundle_names: Vec<String> = Vec::new();
        let layout_subagents = ctx.subagents_dir();
        if layout_subagents.is_dir() {
            if let Ok(entries) = std::fs::read_dir(&layout_subagents) {
                bundle_names = entries
                    .flatten()
                    .filter(|e| e.path().is_file())
                    .map(|e| e.file_name().to_string_lossy().into_owned())
                    .filter(|n| n.ends_with(".md"))
                    .collect();
            }
        }
        if subagents_dir.is_dir() {
            let mut candidates: Vec<String> = std::fs::read_dir(&subagents_dir)
                .into_iter()
                .flatten()
                .flatten()
                .map(|e| e.file_name().to_string_lossy().into_owned())
                .filter(|n| {
                    n.ends_with(".md") && (n.starts_with("cortex-") || bundle_names.contains(n))
                })
                .collect();
            candidates.sort();
            candidates.dedup();
            for name in candidates {
                let dest = subagents_dir.join(&name);
                if dest.is_file() {
                    let _ = std::fs::remove_file(&dest);
                    report.push(dest.to_string_lossy().into_owned());
                }
            }
        }

        // 3. opencode.json: quitar agent.cortex-* y mcp.cortex por clave,
        // preservando todo lo ajeno. Archivo que queda en ``{}`` → unlink.
        let config_file = config_dir(ctx).join("opencode.json");
        if config_file.exists() {
            match std::fs::read_to_string(&config_file)
                .map_err(|e| e.to_string())
                .and_then(|t| serde_json::from_str::<Value>(&t).map_err(|e| e.to_string()))
            {
                Err(_) => {
                    report.push(format!(
                        "{} (skipped: invalid JSON, not touched)",
                        config_file.display()
                    ));
                }
                Ok(mut data) if data.is_object() => {
                    let mut changed = false;

                    if let Some(agent_cfg) = data.get_mut("agent").and_then(Value::as_object_mut) {
                        let cortex_keys: Vec<String> = agent_cfg
                            .keys()
                            .filter(|k| k.starts_with("cortex-"))
                            .cloned()
                            .collect();
                        for key in cortex_keys {
                            agent_cfg.remove(&key);
                            changed = true;
                        }
                        if agent_cfg.is_empty() && data.get("agent").is_some() {
                            data.as_object_mut()
                                .expect("data es objeto")
                                .remove("agent");
                        }
                    }

                    if let Some(mcp_cfg) = data.get_mut("mcp").and_then(Value::as_object_mut) {
                        if mcp_cfg.contains_key("cortex") {
                            mcp_cfg.remove("cortex");
                            changed = true;
                            if mcp_cfg.is_empty() && data.get("mcp").is_some() {
                                data.as_object_mut().expect("data es objeto").remove("mcp");
                            }
                        }
                    }

                    if changed {
                        let is_empty = data.as_object().map(|o| o.is_empty()).unwrap_or(false);
                        if is_empty {
                            let _ = std::fs::remove_file(&config_file);
                            report.push(config_file.to_string_lossy().into_owned());
                        } else {
                            backup_file(ctx, &config_file);
                            let _ = std::fs::write(&config_file, json_dump_ascii(&data));
                            report.push(format!("{} (Cortex keys removed)", config_file.display()));
                        }
                    }
                }
                Ok(_non_dict) => {}
            }
        }

        report
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

/// `sorted(dir.glob(pattern))`: rutas ordenadas por representación string,
/// filtrando por prefijo de nombre (equivalente al patrón glob usado).
fn sorted_md_glob_starting_with(dir: &std::path::Path, prefix: &str) -> Vec<PathBuf> {
    let mut out: Vec<PathBuf> = std::fs::read_dir(dir)
        .into_iter()
        .flatten()
        .flatten()
        .map(|e| e.path())
        .filter(|p| {
            p.file_name()
                .map(|n| {
                    let n = n.to_string_lossy();
                    n.starts_with(prefix) && n.ends_with(".md")
                })
                .unwrap_or(false)
        })
        .collect();
    out.sort_by_key(|p| p.to_string_lossy().into_owned());
    out
}
