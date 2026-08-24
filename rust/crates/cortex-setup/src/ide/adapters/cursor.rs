//! Porteo de cortex/ide/adapters/cursor.py (P8d).
//!
//! Cursor IDE (rediseño Fase 4 del plan multi-IDE, validado contra docs
//! oficiales de Cursor 2.4+):
//!
//! - Subagents canónicos en ``.cursor/agents/`` (project-level).
//! - Slash skills triádicos en ``.cursor/skills/<n>/SKILL.md`` (Phase 09.A+).
//! - MCP registration en ``~/.cursor/mcp.json`` (user-level).
//!
//! Frontmatter Cursor: name, description, model (inherit), readonly.
//! NO se declara ``tools:`` — los subagents heredan TODAS las tools del
//! padre (comportamiento documentado oficialmente).

use std::path::PathBuf;

use serde_json::{json, Value};

use crate::ide::base::{backup_file, deep_merge_dict, generate_autogen_header, json_dump_ascii};
use crate::ide::prompts::{get_skill_prompt, get_subagent_prompt};
use crate::ide::{IdeAdapter, IdeCtx, Prompts};

/// Spec declarativa de un subagent canónico (dict `_CORTEX_SUBAGENTS`).
struct SubagentSpec {
    name: &'static str,
    description: &'static str,
    readonly: bool,
}

/// Subagents canónicos en orden de inserción del dict de Python (define el
/// orden de escritura y de reporte). Coincide con la lista de claude_code
/// y otros adapters validados, más `cortex-code-designer` (Deep Track).
const CORTEX_SUBAGENTS: [SubagentSpec; 4] = [
    SubagentSpec {
        name: "cortex-code-explorer",
        description: "Read-only architecture analysis for complex changes.",
        readonly: true,
    },
    SubagentSpec {
        name: "cortex-code-implementer",
        description: "Deep-track implementation specialist for complex changes.",
        readonly: false,
    },
    SubagentSpec {
        name: "cortex-code-designer",
        description:
            "Produce a design doc between explorer and implementer (Deep Track).",
        readonly: false,
    },
    SubagentSpec {
        // Kept for backward compat with the legacy Reconstruction flow.
        // The canonical closing anchor is the /cortex-documenter SLASH SKILL;
        // the subagent stays accessible via Task tool con banner DEPRECATED.
        name: "cortex-documenter",
        description: "DEPRECATED — use the /cortex-documenter slash skill instead. Legacy Reconstruction persistence.",
        readonly: false,
    },
];

/// Spec declarativa de un slash skill (dict `_CORTEX_SLASH_SKILLS`).
/// La clave del dict de Python es el nombre canónico del prompt
/// (`source_skill_name`); `skill_name` es el nombre del DIRECTORIO.
struct SlashSkillSpec {
    /// Clave del dict / nombre para `get_skill_prompt` (casing canónico).
    source_skill_name: &'static str,
    /// Nombre del directorio y valor `name:` del frontmatter.
    skill_name: &'static str,
    description: &'static str,
    /// Archivo fuente bajo `.cortex/skills/` para el header autogen.
    source_file: &'static str,
}

/// Orden de inserción del dict de Python: sync, SDDwork, documenter.
const CORTEX_SLASH_SKILLS: [SlashSkillSpec; 3] = [
    SlashSkillSpec {
        source_skill_name: "cortex-sync",
        skill_name: "cortex-sync",
        description: "Create a Cortex spec before any implementation work.",
        source_file: "cortex-sync.md",
    },
    SlashSkillSpec {
        // Directory must match the skill name; Cursor + Claude both use a
        // lowercased convention so we keep the canonical casing for the
        // source file and use ``cortex-sddwork`` for the directory.
        source_skill_name: "cortex-SDDwork",
        skill_name: "cortex-sddwork",
        description: "Implement a persisted Cortex spec using the Cortex workflow.",
        source_file: "cortex-SDDwork.md",
    },
    SlashSkillSpec {
        source_skill_name: "cortex-documenter",
        skill_name: "cortex-documenter",
        description: "Close a Cortex Session with editorial criterion (anchor de cierre).",
        source_file: "cortex-documenter.md",
    },
];

/// Renderiza un SKILL.md de Cursor 2.4+: frontmatter YAML con `name`
/// (lowercase, coincide con la carpeta padre) y `description`.
fn render_cursor_skill(
    skill_name: &str,
    description: &str,
    autogen_header: &str,
    body: &str,
) -> String {
    let fm_block = format!("name: {skill_name}\ndescription: {description}");
    format!(
        "---\n{fm_block}\n---\n\n<!--\n{}\n-->\n\n{}\n",
        autogen_header.trim(),
        body.trim()
    )
}

/// Renderiza un archivo de subagent en formato Cursor 2.4+.
/// Frontmatter: name, description, model, readonly. Sin ``tools:``.
fn render_cursor_subagent(
    name: &str,
    description: &str,
    readonly: bool,
    autogen_header: &str,
    body: &str,
) -> String {
    let fm_block = format!(
        "name: {name}\ndescription: {description}\nmodel: inherit\nreadonly: {}",
        if readonly { "true" } else { "false" }
    );
    format!(
        "---\n{fm_block}\n---\n\n<!--\n{}\n-->\n\n{}\n",
        autogen_header.trim(),
        body.trim()
    )
}

pub struct CursorAdapter;

impl CursorAdapter {
    #[allow(dead_code)]
    pub fn new() -> Self {
        CursorAdapter
    }
}

impl Default for CursorAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl IdeAdapter for CursorAdapter {
    fn name(&self) -> &'static str {
        "cursor"
    }

    fn display_name(&self) -> &'static str {
        "Cursor"
    }

    /// Project-level por default (docs Cursor 2.4+: ``.cursor/agents/``);
    /// user-level (``~/.cursor/``) sigue soportado para MCP.
    fn config_paths(&self, ctx: &IdeCtx) -> Vec<(String, PathBuf)> {
        let base_dir = ctx.home.join(".cursor");
        vec![
            ("mcp".into(), base_dir.join("mcp.json")),
            ("user_agents_dir".into(), base_dir.join("agents")),
            (
                "project_agents_dir_relative".into(),
                PathBuf::from(".cursor").join("agents"),
            ),
        ]
    }

    /// Inyecta los subagents canónicos en ``.cursor/agents/`` y los 3
    /// slash skills (anchors triádicos) en ``.cursor/skills/<n>/SKILL.md``.
    ///
    /// ``prompts`` se acepta por uniformidad con el contrato pero NO se usa
    /// (espejo de ``del prompts`` de Python): el contenido se lee directo
    /// de ``.cortex/{skills,subagents}/*.md``, la SSoT canónica.
    fn inject_profiles(&self, ctx: &IdeCtx, _prompts: &Prompts) -> Result<Vec<String>, String> {
        let root = ctx.project_root;
        let mut files_written: Vec<String> = Vec::new();

        // ── Subagents (.cursor/agents/) ───────────────────────────────
        let agents_dir = root.join(".cursor").join("agents");
        std::fs::create_dir_all(&agents_dir)
            .map_err(|e| format!("mkdir {}: {e}", agents_dir.display()))?;

        for spec in &CORTEX_SUBAGENTS {
            let agent_path = agents_dir.join(format!("{}.md", spec.name));
            backup_file(ctx, &agent_path);

            let autogen_header = generate_autogen_header(
                ctx,
                &[&format!(".cortex/subagents/{}.md", spec.name)],
                "cursor",
            );
            let canonical_md = get_subagent_prompt(ctx, spec.name);
            let (_, canonical_body) =
                crate::ide::prompts::split_markdown_frontmatter(&canonical_md);

            let content = render_cursor_subagent(
                spec.name,
                spec.description,
                spec.readonly,
                &autogen_header,
                &canonical_body,
            );
            std::fs::write(&agent_path, content)
                .map_err(|e| format!("write {}: {e}", agent_path.display()))?;
            files_written.push(agent_path.to_string_lossy().into_owned());
        }

        // ── Slash skills (.cursor/skills/) — Phase 09.A+ anchors ──────
        let skills_dir = root.join(".cursor").join("skills");
        std::fs::create_dir_all(&skills_dir)
            .map_err(|e| format!("mkdir {}: {e}", skills_dir.display()))?;

        for spec in &CORTEX_SLASH_SKILLS {
            let skill_subdir = skills_dir.join(spec.skill_name);
            std::fs::create_dir_all(&skill_subdir)
                .map_err(|e| format!("mkdir {}: {e}", skill_subdir.display()))?;
            let skill_path = skill_subdir.join("SKILL.md");
            backup_file(ctx, &skill_path);

            let autogen_header = generate_autogen_header(
                ctx,
                &[&format!(".cortex/skills/{}", spec.source_file)],
                "cursor",
            );
            let canonical_md = get_skill_prompt(ctx, spec.source_skill_name);
            let (_, canonical_body) =
                crate::ide::prompts::split_markdown_frontmatter(&canonical_md);

            let content = render_cursor_skill(
                spec.skill_name,
                spec.description,
                &autogen_header,
                &canonical_body,
            );
            std::fs::write(&skill_path, content)
                .map_err(|e| format!("write {}: {e}", skill_path.display()))?;
            files_written.push(skill_path.to_string_lossy().into_owned());
        }

        Ok(files_written)
    }

    /// MCP config de Cursor va en ``~/.cursor/mcp.json`` (user-level según
    /// docs oficiales), con --project-root absoluto para que Cortex localice
    /// la workspace independientemente del cwd de Cursor al arrancar.
    fn inject_mcp(&self, ctx: &IdeCtx) -> Result<Vec<String>, String> {
        let mcp_file = ctx.home.join(".cursor").join("mcp.json");
        std::fs::create_dir_all(mcp_file.parent().expect("mcp parent"))
            .map_err(|e| format!("mkdir ~/.cursor: {e}"))?;

        backup_file(ctx, &mcp_file);

        let mut data: Value = json!({"mcpServers": {}});
        if mcp_file.exists() {
            if let Ok(text) = std::fs::read_to_string(&mcp_file) {
                if let Ok(parsed) = serde_json::from_str::<Value>(&text) {
                    // Nota: Python crashea con AttributeError si el JSON
                    // válido no es un objeto (setdefault sobre no-dict);
                    // aquí ese camino inalcanzable por fixtures se trata
                    // como contenido inválido y se conserva el default.
                    if parsed.is_object() {
                        data = parsed;
                    }
                }
            }
        }
        if !data.is_object() || data.get("mcpServers").is_none() {
            if let Some(o) = data.as_object_mut() {
                o.entry("mcpServers".to_string())
                    .or_insert_with(|| json!({}));
            }
        }

        let cortex_config = json!({
            "command": "cortex",
            "args": [
                "mcp-server",
                "--stdio",
                "--project-root",
                ctx.project_root.to_string_lossy(),
            ],
            "env": {
                "PYTHONWARNINGS": "ignore",
            },
        });

        // Deep merge para preservar otros MCP servers.
        let merged = deep_merge_dict(
            data.get("mcpServers").expect("mcpServers"),
            &json!({"cortex": cortex_config}),
        );
        if let Some(o) = data.as_object_mut() {
            o.insert("mcpServers".into(), merged);
        }

        std::fs::write(&mcp_file, json_dump_ascii(&data))
            .map_err(|e| format!("write mcp.json: {e}"))?;
        Ok(vec![mcp_file.to_string_lossy().into_owned()])
    }

    /// Elimina lo inyectado por Cortex en Cursor. Regla de oro: SOLO se
    /// borra lo que Cortex creó (nombres canónicos namespaced); directorios
    /// solo se eliminan si quedan vacíos. Idempotente.
    ///
    /// Nota de porteos: la rama ``project_root=None`` de Python (warning de
    /// log + solo limpieza user-level) no existe en el contrato Rust —
    /// [`IdeCtx`] siempre trae project_root explícito, nunca Path.cwd().
    fn uninstall(&self, ctx: &IdeCtx) -> Vec<String> {
        let mut removed: Vec<String> = Vec::new();
        let root = ctx.project_root;

        // 1. Project-level subagents
        let project_agents_dir = root.join(".cursor").join("agents");
        for spec in &CORTEX_SUBAGENTS {
            let agent_path = project_agents_dir.join(format!("{}.md", spec.name));
            if agent_path.exists() {
                let _ = std::fs::remove_file(&agent_path);
                removed.push(agent_path.to_string_lossy().into_owned());
            }
        }
        // Drop empty .cursor/agents/ directory
        if dir_exists_empty(&project_agents_dir) {
            let _ = std::fs::remove_dir(&project_agents_dir);
            removed.push(project_agents_dir.to_string_lossy().into_owned());
        }

        // 2. Project-level slash skills (Phase 09.A+)
        let skills_dir = root.join(".cursor").join("skills");
        for spec in &CORTEX_SLASH_SKILLS {
            let skill_subdir = skills_dir.join(spec.skill_name);
            let skill_path = skill_subdir.join("SKILL.md");
            if skill_path.exists() {
                let _ = std::fs::remove_file(&skill_path);
                removed.push(skill_path.to_string_lossy().into_owned());
            }
            if dir_exists_empty(&skill_subdir) {
                let _ = std::fs::remove_dir(&skill_subdir);
                removed.push(skill_subdir.to_string_lossy().into_owned());
            }
        }
        if dir_exists_empty(&skills_dir) {
            let _ = std::fs::remove_dir(&skills_dir);
            removed.push(skills_dir.to_string_lossy().into_owned());
        }

        // Drop .cursor/ itself si quedó completamente vacío.
        let cursor_dir = root.join(".cursor");
        if dir_exists_empty(&cursor_dir) {
            let _ = std::fs::remove_dir(&cursor_dir);
            removed.push(cursor_dir.to_string_lossy().into_owned());
        }

        // 3. Limpiar entrada Cortex de MCP config (user-level). En Python
        // todo este bloque corre dentro de contextlib.suppress(Exception):
        // ante cualquier fallo se continúa silenciosamente.
        let mcp_file = ctx.home.join(".cursor").join("mcp.json");
        if mcp_file.exists() {
            let result = (|| -> Result<(), String> {
                let text = std::fs::read_to_string(&mcp_file).map_err(|e| e.to_string())?;
                let mut data: Value = serde_json::from_str(&text).map_err(|e| e.to_string())?;
                let obj = match data.as_object_mut() {
                    Some(o) => o,
                    None => return Ok(()),
                };
                if let Some(Value::Object(servers)) = obj.get_mut("mcpServers") {
                    if servers.contains_key("cortex") {
                        servers.remove("cortex");
                        std::fs::write(&mcp_file, json_dump_ascii(&data))
                            .map_err(|e| e.to_string())?;
                        removed.push(format!("{} (cortex entry removed)", mcp_file.display()));
                    }
                }
                Ok(())
            })();
            let _ = result; // suprimido igual que contextlib.suppress
        }

        removed
    }
}

/// Espejo de ``dir.exists() and not any(dir.iterdir())`` de Python.
fn dir_exists_empty(dir: &std::path::Path) -> bool {
    dir.is_dir()
        && std::fs::read_dir(dir)
            .map(|mut d| d.next().is_none())
            .unwrap_or(false)
}
