//! Porteo de cortex/ide/adapters/vscode.py (P8d).
//!
//! VS Code: agents top-level nativos en `.github/agents/*.agent.md` (con
//! frontmatter tools/handoffs) + subagents en `.claude/agents/*.md` +
//! MCP en `.vscode/mcp.json` bajo la clave `servers` con
//! `${workspaceFolder}` como project-root.

use std::path::PathBuf;

use serde_json::{json, Value};

use crate::ide::base::{backup_file, deep_merge_dict, generate_autogen_header, json_dump_ascii};
use crate::ide::prompts::{get_subagent_prompt, strip_markdown_frontmatter};
use crate::ide::{IdeAdapter, IdeCtx, Prompts};

/// Agents canónicos top-level que este adapter escribe (SSoT install/uninstall).
const VSCODE_TOP_AGENTS: [&str; 2] = ["cortex-sync", "cortex-SDDwork"];
const CLAUDE_SUBAGENTS: [&str; 3] = [
    "cortex-code-explorer",
    "cortex-code-implementer",
    "cortex-documenter",
];

fn render_vscode_agent(frontmatter: &[&str], header: &str, body: &str) -> String {
    let frontmatter_block = frontmatter.join("\n");
    format!(
        "---\n{frontmatter_block}\n---\n\n<!--\n{}\n-->\n\n{}\n",
        header.trim(),
        body.trim()
    )
}

fn render_claude_agent(name: &str, description: &str, header: &str, body: &str) -> String {
    format!(
        "---\nname: {name}\ndescription: {description}\n---\n\n<!--\n{}\n-->\n\n{}\n",
        header.trim(),
        body.trim()
    )
}

pub struct VSCodeAdapter;

impl VSCodeAdapter {
    #[allow(dead_code)]
    pub fn new() -> Self {
        VSCodeAdapter
    }
}

impl Default for VSCodeAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl IdeAdapter for VSCodeAdapter {
    fn name(&self) -> &'static str {
        "vscode"
    }

    fn display_name(&self) -> &'static str {
        "VS Code"
    }

    /// Rutas RELATIVAS al proyecto (Python devuelve Paths relativos; los
    /// call-sites hacen el join con project_root).
    fn config_paths(&self, _ctx: &IdeCtx) -> Vec<(String, PathBuf)> {
        vec![
            ("mcp".into(), PathBuf::from(".vscode").join("mcp.json")),
            ("agents_dir".into(), PathBuf::from(".github").join("agents")),
            (
                "claude_agents_dir".into(),
                PathBuf::from(".claude").join("agents"),
            ),
        ]
    }

    fn inject_profiles(&self, ctx: &IdeCtx, prompts: &Prompts) -> Result<Vec<String>, String> {
        let root = ctx.project_root;
        let agents_dir = root.join(".github").join("agents");
        let claude_agents_dir = root.join(".claude").join("agents");
        std::fs::create_dir_all(&agents_dir)
            .map_err(|e| format!("mkdir {}: {e}", agents_dir.display()))?;
        std::fs::create_dir_all(&claude_agents_dir)
            .map_err(|e| format!("mkdir {}: {e}", claude_agents_dir.display()))?;

        let sync_body = strip_markdown_frontmatter(
            prompts.get("cortex-sync").map(|s| s.as_str()).unwrap_or(""),
        );
        let work_body = strip_markdown_frontmatter(
            prompts
                .get("cortex-SDDwork")
                .map(|s| s.as_str())
                .unwrap_or(""),
        );

        let top_level_header = generate_autogen_header(
            ctx,
            &[
                ".cortex/skills/cortex-sync.md",
                ".cortex/skills/cortex-SDDwork.md",
            ],
            "vscode",
        );

        // Orden de inserción del dict de Python: explorer, implementer,
        // documenter. (La description del documenter difiere de la del
        // adapter claude_code — así está en la fuente vscode.py.)
        let subagent_sources: [(&str, &str, &str); 3] = [
            (
                "cortex-code-explorer",
                "Read-only architecture analysis for complex changes.",
                ".cortex/subagents/cortex-code-explorer.md",
            ),
            (
                "cortex-code-implementer",
                "Deep-track implementation specialist for complex changes.",
                ".cortex/subagents/cortex-code-implementer.md",
            ),
            (
                "cortex-documenter",
                "Session documentation and vault persistence specialist.",
                ".cortex/subagents/cortex-documenter.md",
            ),
        ];

        let mut files_written: Vec<String> = Vec::new();

        let sync_path = agents_dir.join("cortex-sync.agent.md");
        backup_file(ctx, &sync_path);
        let content = render_vscode_agent(
            &[
                "name: cortex-sync",
                "description: Create Cortex specs before implementation.",
                "tools: ['search/codebase', 'search/usages', 'cortex/*']",
                "handoffs:",
                "  - label: Continue with cortex-SDDwork",
                "    agent: cortex-SDDwork",
                "    prompt: Continue from the persisted Cortex spec and execute the implementation workflow.",
                "    send: false",
            ],
            &top_level_header,
            &sync_body,
        );
        std::fs::write(&sync_path, content)
            .map_err(|e| format!("write {}: {e}", sync_path.display()))?;
        files_written.push(sync_path.to_string_lossy().into_owned());

        let work_path = agents_dir.join("cortex-SDDwork.agent.md");
        backup_file(ctx, &work_path);
        let content = render_vscode_agent(
            &[
                "name: cortex-SDDwork",
                "description: Implement Cortex specs with fast-track or deep-track routing.",
                "tools: ['agent', 'edit', 'search/codebase', 'search/usages', 'cortex/*']",
                "agents: ['cortex-code-explorer', 'cortex-code-implementer', 'cortex-documenter']",
            ],
            &top_level_header,
            &work_body,
        );
        std::fs::write(&work_path, content)
            .map_err(|e| format!("write {}: {e}", work_path.display()))?;
        files_written.push(work_path.to_string_lossy().into_owned());

        for (agent_name, description, source) in &subagent_sources {
            let agent_header = generate_autogen_header(ctx, &[source], "vscode");
            let agent_path = claude_agents_dir.join(format!("{agent_name}.md"));
            backup_file(ctx, &agent_path);
            let canonical = get_subagent_prompt(ctx, agent_name);
            let content = render_claude_agent(
                agent_name,
                description,
                &agent_header,
                &strip_markdown_frontmatter(&canonical),
            );
            std::fs::write(&agent_path, content)
                .map_err(|e| format!("write {}: {e}", agent_path.display()))?;
            files_written.push(agent_path.to_string_lossy().into_owned());
        }

        Ok(files_written)
    }

    fn inject_mcp(&self, ctx: &IdeCtx) -> Result<Vec<String>, String> {
        let mcp_path = ctx.project_root.join(".vscode").join("mcp.json");
        std::fs::create_dir_all(mcp_path.parent().expect("mcp.json tiene parent"))
            .map_err(|e| format!("mkdir .vscode: {e}"))?;
        backup_file(ctx, &mcp_path);

        let mut data: Value = json!({});
        if mcp_path.exists() {
            if let Ok(text) = std::fs::read_to_string(&mcp_path) {
                if let Ok(parsed) = serde_json::from_str::<Value>(&text) {
                    data = parsed;
                }
            }
        }

        // VS Code usa ${workspaceFolder} (no ruta absoluta) para que el
        // workspace resuelva relativo al proyecto abierto.
        let cortex_config = json!({
            "type": "stdio",
            "command": "cortex-cli",
            "args": ["mcp-server", "--stdio", "--project-root", "${workspaceFolder}"],
            "env": {"PYTHONWARNINGS": "ignore"},
        });

        if let Some(obj) = data.as_object_mut() {
            obj.entry("servers".to_string())
                .or_insert_with(|| json!({}));
        }

        let merged = deep_merge_dict(
            data.get("servers").expect("servers setdefault"),
            &json!({"cortex": cortex_config}),
        );
        if let Some(obj) = data.as_object_mut() {
            obj.insert("servers".into(), merged);
        }

        std::fs::write(&mcp_path, json_dump_ascii(&data))
            .map_err(|e| format!("write {}: {e}", mcp_path.display()))?;
        Ok(vec![mcp_path.to_string_lossy().into_owned()])
    }

    /// Eliminar lo inyectado por Cortex en VS Code:
    ///
    /// - `.github/agents/{cortex-sync,cortex-SDDwork}.agent.md`.
    /// - `.claude/agents/{explorer,implementer,documenter}.md`.
    /// - Entrada `servers.cortex` de `<project>/.vscode/mcp.json`.
    ///
    /// SOLO se borra lo que Cortex creó (archivos por nombre canónico); los
    /// directorios solo se eliminan si quedan vacíos.
    fn uninstall(&self, ctx: &IdeCtx) -> Vec<String> {
        let mut removed: Vec<String> = Vec::new();
        let root = ctx.project_root;

        // (dir, sufijo, nombres canónicos) — orden del tuple-loop de Python.
        for (agents_dir, suffix, names) in [
            (
                root.join(".github").join("agents"),
                ".agent.md",
                &VSCODE_TOP_AGENTS[..],
            ),
            (
                root.join(".claude").join("agents"),
                ".md",
                &CLAUDE_SUBAGENTS[..],
            ),
        ] {
            for agent_name in names {
                let agent_path = agents_dir.join(format!("{agent_name}{suffix}"));
                if agent_path.exists() {
                    let _ = std::fs::remove_file(&agent_path);
                    removed.push(agent_path.to_string_lossy().into_owned());
                }
            }
            let is_empty = std::fs::read_dir(&agents_dir)
                .map(|mut d| d.next().is_none())
                .unwrap_or(false);
            if agents_dir.exists() && is_empty {
                let _ = std::fs::remove_dir(&agents_dir);
                removed.push(agents_dir.to_string_lossy().into_owned());
            }
        }

        // Entrada cortex de .vscode/mcp.json (merge inverso, preservando
        // otros servers del adopter). QUIRK de Python replicado: todo el
        // bloque vive dentro de contextlib.suppress(Exception), así que un
        // JSON inválido se salta SILENCIOSAMENTE (sin línea de reporte).
        let mcp_path = root.join(".vscode").join("mcp.json");
        if mcp_path.exists() {
            if let Ok(text) = std::fs::read_to_string(&mcp_path) {
                if let Ok(mut data) = serde_json::from_str::<Value>(&text) {
                    let mut should_write = false;
                    if let Some(obj) = data.as_object_mut() {
                        if let Some(Value::Object(servers)) = obj.get_mut("servers") {
                            // La remoción muta en lugar el map ya insertado
                            // en `data` (mismo efecto que el `del` de Python).
                            if servers.remove("cortex").is_some() {
                                should_write = true;
                            }
                        }
                    }
                    if should_write {
                        let _ = std::fs::write(&mcp_path, json_dump_ascii(&data));
                        removed.push(format!("{} (cortex entry removed)", mcp_path.display()));
                    }
                }
            }
        }

        removed
    }
}
