//! Adaptador nativo para Google Antigravity (Gemini Code Assist & Gemini CLI / `agy`).
//!
//! Soporta tanto la interfaz de proyecto moderna de Gemini CLI / Antigravity:
//! - Reglas del proyecto en `GEMINI.md` (leído por Antigravity en la raíz).
//! - Skills nativas con progressive disclosure en `.agents/skills/<skill>/SKILL.md`.
//! - MCP server global en `~/.gemini/config/mcp_config.json` (`mcpServers`, camelCase).
//! Como la configuración heredada de la extensión IDE:
//! - `~/.gemini/settings.json` con `system_instructions` y `mcp_servers`.

use std::path::{Path, PathBuf};

use serde_json::{json, Value};

use crate::ide::adapters::mcp_command;
use crate::ide::base::{backup_file, deep_merge_dict, generate_autogen_header, json_dump_ascii};
use crate::ide::Prompts;
use crate::ide::{IdeAdapter, IdeCtx};

/// Sources del header del workflow de Antigravity.
const WORKFLOW_SOURCES: [&str; 3] = [
    ".cortex/skills/cortex-sync.md",
    ".cortex/skills/cortex-SDDwork.md",
    ".cortex/skills/cortex-documenter.md",
];

/// Spec declarativa de un skill a inyectar en `.agents/skills/`.
struct SkillSpec<'a> {
    directory_name: &'a str,
    frontmatter_name: &'a str,
    description: &'a str,
    source_path: &'a str,
    prompt_key: &'a str,
}

const SKILL_SPECS: [SkillSpec<'static>; 3] = [
    SkillSpec {
        directory_name: "cortex-sync",
        frontmatter_name: "cortex-sync",
        description: "Create a Cortex spec before any implementation work.",
        source_path: ".cortex/skills/cortex-sync.md",
        prompt_key: "cortex-sync",
    },
    SkillSpec {
        directory_name: "cortex-sddwork",
        frontmatter_name: "cortex-sddwork",
        description: "Implement a persisted Cortex spec using the Cortex workflow.",
        source_path: ".cortex/skills/cortex-SDDwork.md",
        prompt_key: "cortex-SDDwork",
    },
    SkillSpec {
        directory_name: "cortex-documenter",
        frontmatter_name: "cortex-documenter",
        description: "Close a Cortex Session with editorial criterion (anchor de cierre).",
        source_path: ".cortex/skills/cortex-documenter.md",
        prompt_key: "cortex-documenter",
    },
];

fn render_antigravity_skill(frontmatter: &[String], header: &str, body: &str) -> String {
    let frontmatter_block = frontmatter.join("\n");
    format!(
        "---\n{frontmatter_block}\n---\n\n<!--\n{}\n-->\n\n{}\n",
        header.trim(),
        body.trim()
    )
}

fn strip_frontmatter_or_empty(prompt: Option<&String>) -> String {
    let content = prompt.cloned().unwrap_or_default();
    crate::ide::prompts::strip_markdown_frontmatter(&content)
}

fn gemini_workflow_doc(header: &str) -> String {
    [
        "<!--",
        header.trim(),
        "-->",
        "",
        "# Cortex Governance & Workflow Guide (Gemini CLI / Antigravity)",
        "",
        "This project is governed by **Cortex** (hybrid cognitive memory & SDD workflows for AI agents).",
        "",
        "## 1. Triadic Anchors",
        "",
        "Cortex operates with three primary invocable skills:",
        "- `/cortex-sync` — Pre-flight alignment, ticket sync, spec creation. Mandatory opening anchor.",
        "- `/cortex-sddwork` — Managed implementation via SDDwork. Follows TDD and spec milestones.",
        "- `/cortex-documenter` — Editorial session close, briefing, vault documentation. Mandatory closing anchor.",
        "",
        "## 2. Governance Rules",
        "",
        "- Always call `cortex_sync_ticket` before creating specs.",
        "- Emit phase checkpoints via `cortex session checkpoint` / `cortex_session_checkpoint`.",
        "- Direct execution for brief informational queries; structured SDD mode for multi-file changes.",
        "- Never close a session with broken tests or failing verification gates.",
    ]
    .join("\n")
        + "\n"
}

fn gemini_composed_workflow_doc(header: &str) -> String {
    [
        "<!--",
        header.trim(),
        "-->",
        "",
        "# Cortex Governance & Workflow Guide (Gemini CLI / Antigravity)",
        "",
        "This project is governed by **Cortex** (hybrid cognitive memory & SDD workflows for AI agents).",
        "Project-wide agent conventions and composed lifecycle guidelines are defined in [AGENTS.md](AGENTS.md).",
        "",
        "## 1. Composed Lifecycle Anchors",
        "",
        "Follow the active composed workflow installed in `.agents/skills/`:",
        "- `grill` — Socratic refinement and clarification before specification.",
        "- `to-spec` / `spec` — Specification authoring.",
        "- `to-tickets` / `plan` — Task and implementation breakdown.",
        "- `implement` / `tdd` — TDD execution and gate validation.",
        "- `review` — Pre-close verification and QA.",
        "- `/cortex-documenter` / `cortex autopilot finish` — Session archival and documentation.",
        "",
        "## 2. Governance Rules",
        "",
        "- Emit phase checkpoints via `cortex session checkpoint` / `cortex_session_checkpoint`.",
        "- Follow the agent skills contract defined in AGENTS.md.",
        "- Direct execution for brief informational queries; structured SDD mode for multi-file changes.",
        "- Never close a session with broken tests or failing verification gates.",
    ]
    .join("\n")
        + "\n"
}

/// Copia recursiva de un directorio respetando archivos existentes.
fn copy_dir_all(src: &Path, dst: &Path) -> std::io::Result<()> {
    std::fs::create_dir_all(dst)?;
    for entry in std::fs::read_dir(src)? {
        let entry = entry?;
        let ty = entry.file_type()?;
        if ty.is_dir() {
            copy_dir_all(&entry.path(), &dst.join(entry.file_name()))?;
        } else {
            let target_file = dst.join(entry.file_name());
            if !target_file.exists() {
                std::fs::copy(entry.path(), target_file)?;
            }
        }
    }
    Ok(())
}

fn is_dir_empty(dir: &Path) -> bool {
    std::fs::read_dir(dir)
        .map(|mut i| i.next().is_none())
        .unwrap_or(false)
}

/// `_unique_backup` con granularidad de microsegundos para evitar colisiones.
fn unique_backup(ctx: &IdeCtx, file_path: &Path) -> PathBuf {
    let backup = backup_file(ctx, file_path);
    if !backup.exists() {
        return backup;
    }
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
        "Antigravity (Gemini Code Assist / CLI)"
    }

    fn config_paths(&self, ctx: &IdeCtx) -> Vec<(String, PathBuf)> {
        vec![
            ("gemini_md".into(), PathBuf::from("GEMINI.md")),
            (
                "skills_dir".into(),
                Path::new(".agents").join("skills"),
            ),
            (
                "settings".into(),
                ctx.home.join(".gemini").join("settings.json"),
            ),
            (
                "mcp_config".into(),
                ctx.home.join(".gemini").join("config").join("mcp_config.json"),
            ),
        ]
    }

    fn inject_profiles(&self, ctx: &IdeCtx, prompts: &Prompts) -> Result<Vec<String>, String> {
        let mut files_written: Vec<String> = Vec::new();
        let root = ctx.project_root;

        // 1. GEMINI.md en la raíz del proyecto (leído nativamente por Antigravity CLI)
        let gemini_md_path = root.join("GEMINI.md");
        let header = generate_autogen_header(ctx, &WORKFLOW_SOURCES, "antigravity");
        backup_file(ctx, &gemini_md_path);
        let has_composed = root.join(".cortex").join("skills").join("composed").is_dir()
            || root.join(".agents").join("skills").join("grill").is_dir()
            || (root.join("AGENTS.md").is_file()
                && std::fs::read_to_string(root.join("AGENTS.md"))
                    .map(|c| c.contains("## Agent skills"))
                    .unwrap_or(false));
        let workflow_content = if has_composed {
            gemini_composed_workflow_doc(&header)
        } else {
            gemini_workflow_doc(&header)
        };
        std::fs::write(&gemini_md_path, workflow_content)
            .map_err(|e| format!("write GEMINI.md: {e}"))?;
        files_written.push(gemini_md_path.to_string_lossy().into_owned());

        // 2. Skills nativas bajo .agents/skills/<skill>/SKILL.md
        let skills_dir = root.join(".agents").join("skills");
        std::fs::create_dir_all(&skills_dir)
            .map_err(|e| format!("mkdir {}: {e}", skills_dir.display()))?;

        for spec in &SKILL_SPECS {
            let skill_dir = skills_dir.join(spec.directory_name);
            std::fs::create_dir_all(&skill_dir)
                .map_err(|e| format!("mkdir {}: {e}", skill_dir.display()))?;
            let skill_path = skill_dir.join("SKILL.md");
            backup_file(ctx, &skill_path);
            let body = strip_frontmatter_or_empty(prompts.get(spec.prompt_key));
            let content = render_antigravity_skill(
                &[
                    format!("name: {}", spec.frontmatter_name),
                    format!("description: {}", spec.description),
                ],
                &generate_autogen_header(ctx, &[spec.source_path], "antigravity"),
                &body,
            );
            std::fs::write(&skill_path, content)
                .map_err(|e| format!("write {}: {e}", skill_path.display()))?;
            files_written.push(skill_path.to_string_lossy().into_owned());
        }

        // Si existen skills compuestas en .cortex/skills/composed, espejarlas a .agents/skills/
        let composed_dir = root.join(".cortex").join("skills").join("composed");
        if composed_dir.is_dir() {
            if let Ok(entries) = std::fs::read_dir(&composed_dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.is_dir() {
                        let name = entry.file_name();
                        let target_sub = skills_dir.join(&name);
                        let _ = copy_dir_all(&path, &target_sub);
                    }
                }
            }
        }

        // 3. User-level legacy: ~/.gemini/settings.json (retrocompatibilidad IDE extension)
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

        let legacy_header = generate_autogen_header(
            ctx,
            &[
                ".cortex/skills/cortex-sync.md",
                ".cortex/skills/cortex-SDDwork.md",
            ],
            "antigravity",
        );

        let mut combined_prompt = format!(
            "{legacy_header}\n\nYou are working in a Cortex project. Please follow these profiles:\n\n"
        );
        for skill_name in ["cortex-sync", "cortex-SDDwork"] {
            if let Some(body) = prompts.get(skill_name) {
                combined_prompt.push_str(&format!("## {skill_name}\n{body}\n\n"));
            }
        }

        if let Some(obj) = data.as_object_mut() {
            obj.insert("system_instructions".into(), Value::String(combined_prompt));
        }

        std::fs::write(&settings_path, json_dump_ascii(&data))
            .map_err(|e| format!("write {}: {e}", settings_path.display()))?;
        files_written.push(settings_path.to_string_lossy().into_owned());

        Ok(files_written)
    }

    fn inject_mcp(&self, ctx: &IdeCtx) -> Result<Vec<String>, String> {
        let mut files_written: Vec<String> = Vec::new();
        let mcp_cmd = mcp_command(ctx);
        let cortex_config = json!({
            "command": mcp_cmd["command"],
            "args": mcp_cmd["args"],
            "env": mcp_cmd["env"],
        });

        // 1. User-level Antigravity CLI: ~/.gemini/config/mcp_config.json
        let mcp_config_path = ctx.home.join(".gemini").join("config").join("mcp_config.json");
        std::fs::create_dir_all(
            mcp_config_path
                .parent()
                .expect("mcp_config tiene parent (~/.gemini/config)"),
        )
        .map_err(|e| format!("mkdir ~/.gemini/config: {e}"))?;

        unique_backup(ctx, &mcp_config_path);

        let mut mcp_data: Value = json!({"mcpServers": {}});
        if mcp_config_path.exists() {
            if let Ok(text) = std::fs::read_to_string(&mcp_config_path) {
                if let Ok(parsed) = serde_json::from_str::<Value>(&text) {
                    if parsed.is_object() {
                        mcp_data = parsed;
                    }
                }
            }
        }
        if let Some(obj) = mcp_data.as_object_mut() {
            obj.entry("mcpServers".to_string())
                .or_insert_with(|| json!({}));
        }

        let merged_mcp = deep_merge_dict(
            mcp_data.get("mcpServers").expect("mcpServers setdefault arriba"),
            &json!({"cortex": cortex_config}),
        );
        if let Some(obj) = mcp_data.as_object_mut() {
            obj.insert("mcpServers".into(), merged_mcp);
        }

        std::fs::write(&mcp_config_path, json_dump_ascii(&mcp_data))
            .map_err(|e| format!("write {}: {e}", mcp_config_path.display()))?;
        files_written.push(mcp_config_path.to_string_lossy().into_owned());

        // 2. User-level legacy: ~/.gemini/settings.json
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
        files_written.push(settings_path.to_string_lossy().into_owned());

        Ok(files_written)
    }

    /// Revertir lo inyectado por Cortex en el proyecto y en las configs globales de Gemini.
    fn uninstall(&self, ctx: &IdeCtx) -> Vec<String> {
        let mut removed: Vec<String> = Vec::new();

        // 1. GEMINI.md en la raíz del proyecto
        let gemini_md_path = ctx.project_root.join("GEMINI.md");
        if gemini_md_path.exists() {
            let backups = sorted_glob(ctx.project_root, "GEMINI.md.cortex_backup_");
            let mut restored = false;
            for candidate in &backups {
                if let Ok(text) = std::fs::read_to_string(candidate) {
                    if !text.contains("AUTOGENERATED BY CORTEX") {
                        let _ = std::fs::write(&gemini_md_path, &text);
                        removed.push(format!(
                            "{} (restored from {})",
                            gemini_md_path.display(),
                            candidate.file_name().unwrap_or_default().to_string_lossy()
                        ));
                        restored = true;
                        break;
                    }
                }
            }
            if !restored {
                if let Ok(text) = std::fs::read_to_string(&gemini_md_path) {
                    if text.contains("AUTOGENERATED BY CORTEX") {
                        let _ = std::fs::remove_file(&gemini_md_path);
                        removed.push(gemini_md_path.to_string_lossy().into_owned());
                    }
                }
            }
            for b in &backups {
                let _ = std::fs::remove_file(b);
                removed.push(b.to_string_lossy().into_owned());
            }
        }

        // 2. Skills en .agents/skills/
        let skills_dir = ctx.project_root.join(".agents").join("skills");
        for spec in &SKILL_SPECS {
            let skill_dir = skills_dir.join(spec.directory_name);
            if skill_dir.exists() {
                let _ = std::fs::remove_dir_all(&skill_dir);
                removed.push(skill_dir.to_string_lossy().into_owned());
            }
        }
        if skills_dir.exists() && is_dir_empty(&skills_dir) {
            let _ = std::fs::remove_dir(&skills_dir);
        }
        let agents_dir = ctx.project_root.join(".agents");
        if agents_dir.exists() && is_dir_empty(&agents_dir) {
            let _ = std::fs::remove_dir(&agents_dir);
        }

        // 3. ~/.gemini/config/mcp_config.json
        let mcp_config_path = ctx.home.join(".gemini").join("config").join("mcp_config.json");
        if mcp_config_path.exists() {
            if let Ok(text) = std::fs::read_to_string(&mcp_config_path) {
                if let Ok(mut data) = serde_json::from_str::<Value>(&text) {
                    let mut changed = false;
                    if let Some(Value::Object(servers)) = data.get_mut("mcpServers") {
                        if servers.contains_key("cortex") {
                            servers.remove("cortex");
                            changed = true;
                            removed.push(format!(
                                "{} (cortex entry removed)",
                                mcp_config_path.display()
                            ));
                        }
                    }
                    if changed {
                        let _ = std::fs::write(&mcp_config_path, json_dump_ascii(&data));
                    }
                }
            }
            if let Some(parent) = mcp_config_path.parent() {
                let backups = sorted_glob(parent, "mcp_config.json.cortex_backup_");
                for b in &backups {
                    let _ = std::fs::remove_file(b);
                    removed.push(b.to_string_lossy().into_owned());
                }
            }
        }

        // 4. ~/.gemini/settings.json (legacy)
        let settings_path = ctx.home.join(".gemini").join("settings.json");
        if settings_path.exists() {
            if let Ok(text) = std::fs::read_to_string(&settings_path) {
                if let Ok(mut data) = serde_json::from_str::<Value>(&text) {
                    let parent = settings_path.parent().expect("settings tiene parent");
                    let backups = sorted_glob(parent, "settings.json.cortex_backup_");
                    let mut restored = false;
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
                }
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
