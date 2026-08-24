//! Porteo de cortex/ide/adapters/claude_code.py (P8d).
//!
//! Claude Code: perfiles como skills slash (`.claude/skills/cortex-*/SKILL.md`),
//! subagents legacy (`.claude/agents/cortex-*.md`) con frontmatter
//! `tools:` traducido al vocabulario nativo (PascalCase y `mcp__cortex__`),
//! workflow en `CLAUDE.md` y MCP en `.mcp.json` + `.claude/settings.json`.
use std::path::{Path, PathBuf};

use serde_json::{json, Value};

use crate::ide::base::{
    backup_file, deep_merge_dict, generate_autogen_header, has_marker_block,
    is_content_identical_to_bundle, json_dump_ascii, strip_marker_blocks,
};
use crate::ide::canonical_tools::translate_list;
use crate::ide::prompts::{get_subagent_prompt, split_markdown_frontmatter};
use crate::ide::{IdeAdapter, IdeCtx, Prompts};

/// `_render_claude_markdown`: frontmatter + header dentro de comentario HTML
/// + cuerpo. `header.strip()` recorta el `\n` inicial y el final del header.
fn render_claude_markdown(frontmatter: &[String], header: &str, body: &str) -> String {
    let frontmatter_block = frontmatter.join("\n");
    format!(
        "---\n{frontmatter_block}\n---\n\n<!--\n{}\n-->\n\n{}\n",
        header.trim(),
        body.trim()
    )
}

/// Parsea el campo ``tools:`` del frontmatter de un prompt canónico
/// (formato comma-separated). Lista vacía si no hay frontmatter ni campo.
fn parse_canonical_tools(frontmatter_text: Option<&String>) -> Vec<String> {
    let Some(text) = frontmatter_text else {
        return Vec::new();
    };
    for line in text.split('\n') {
        let stripped = line.trim();
        if stripped.to_lowercase().starts_with("tools:") {
            let value = stripped
                .split_once(':')
                .map(|(_, v)| v.trim())
                .unwrap_or("");
            return value
                .split(',')
                .map(|t| t.trim().to_string())
                .filter(|t| !t.is_empty())
                .collect();
        }
    }
    Vec::new()
}

/// Contenido EXACTO que ``inject_profiles`` escribe en ``CLAUDE.md``.
///
/// Único punto de verdad para install y uninstall: uninstall compara el
/// contenido on-disk contra esta plantilla (normalizando el timestamp del
/// header) para decidir si el archivo es 100% Cortex y puede eliminarse.
fn claude_workflow_doc(header: &str) -> String {
    [
        "<!--",
        header.trim(),
        "-->",
        "",
        "# Cortex Workflow — Triadic Anchors (Phase 09.A+ / May 2026)",
        "",
        "Cortex se ejecuta con TRES skills invocables con `/`. El medio es",
        "pluggable; los anchors de inicio y cierre son **obligatorios**.",
        "",
        "1. **`/cortex-sync`** (anchor inicio, obligatorio) — carga contexto",
        "   histórico via ONNX/RRF, emite propuesta interactiva, persiste la",
        "   spec en el vault, abre la Session.",
        "2. **Middle (pluggable)** — uno de los siguientes:",
        "   - **`/cortex-SDDwork`** (Managed): Fast Track edits directos o Deep",
        "     Track con delegación a los subagents canónicos.",
        "   - Subagents directos via Task tool: `cortex-code-explorer`,",
        "     `cortex-code-designer`, `cortex-code-implementer` (Deep Track).",
        "   - **BYO**: trabajás manualmente o con cualquier otro agente. Cortex",
        "     reconstruye desde el diff al cierre.",
        "3. **`/cortex-documenter`** (anchor cierre, obligatorio) — invoca",
        "   `cortex_documenter_briefing`, decide qué doc types persistir",
        "   (session / handoff / adr / decision / runbook / etc.), escribe la",
        "   nota a mano con criterio editorial, llama `cortex_self_review_note`,",
        "   persiste vía `cortex_write_doc` y cierra con `cortex_close_session`.",
        "",
        "## Hard rules",
        "",
        "- NUNCA llames `cortex_create_spec` antes de `cortex_sync_ticket` (el MCP",
        "  server rechaza con violación de gobernanza).",
        "- NUNCA omitas `/cortex-documenter` al final — sin el cierre con criterio",
        "  editorial, la sesión queda con documentación de baja señal y la memoria",
        "  organizacional se erosiona.",
        "- El status `handoff` es un outcome de primera clase. Si los verification",
        "  hooks fallan o quedan archivos unimplemented, cerrar como `handoff`",
        "  (NO `closed`) para que el próximo `/cortex-sync` lo priorice.",
        "- Si `CONTEXT.md` existe, los términos del dominio son canónicos.",
        "  `/cortex-documenter` puede agregar nuevos términos vía `cortex_write_doc`",
        "  con `doc_type=glossary`.",
        "",
        "## Subagents canónicos (Task tool)",
        "",
        "Disponibles para que `/cortex-SDDwork` delegue trabajo en Deep Track:",
        "",
        "- `cortex-code-explorer` — análisis de arquitectura read-only.",
        "- `cortex-code-designer` — produce design doc antes de implementar.",
        "- `cortex-code-implementer` — implementa siguiendo el design doc.",
        "- `cortex-documenter` (DEPRECATED) — solo para compatibilidad con flujos",
        "  antiguos; el flujo canónico de cierre es `/cortex-documenter`.",
    ]
    .join("\n")
        + "\n"
}

/// Sources del header del workflow (usado por install y uninstall).
const WORKFLOW_SOURCES: [&str; 7] = [
    ".cortex/skills/cortex-sync.md",
    ".cortex/skills/cortex-SDDwork.md",
    ".cortex/skills/cortex-documenter.md",
    ".cortex/subagents/cortex-code-explorer.md",
    ".cortex/subagents/cortex-code-implementer.md",
    ".cortex/subagents/cortex-code-designer.md",
    ".cortex/subagents/cortex-documenter.md",
];

pub struct ClaudeCodeAdapter;

impl ClaudeCodeAdapter {
    #[allow(dead_code)]
    pub fn new() -> Self {
        ClaudeCodeAdapter
    }
}

impl Default for ClaudeCodeAdapter {
    fn default() -> Self {
        Self::new()
    }
}

/// Spec declarativa de un skill slash a inyectar (entrada del dict
/// ``skill_specs`` de Python; el nombre de directorio puede diferir del
/// nombre en frontmatter, ej. ``cortex-sddwork`` vs prompt ``cortex-SDDwork``).
struct SkillSpec<'a> {
    directory_name: &'a str,
    frontmatter_name: &'a str,
    description: &'a str,
    source_path: &'a str,
    prompt_key: &'a str,
}

impl IdeAdapter for ClaudeCodeAdapter {
    fn name(&self) -> &'static str {
        "claude_code"
    }

    fn display_name(&self) -> &'static str {
        "Claude Code"
    }

    fn config_paths(&self, _ctx: &IdeCtx) -> Vec<(String, PathBuf)> {
        vec![
            ("claude_md".into(), PathBuf::from("CLAUDE.md")),
            ("agents_dir".into(), Path::new(".claude").join("agents")),
            ("skills_dir".into(), Path::new(".claude").join("skills")),
            (
                "settings".into(),
                Path::new(".claude").join("settings.json"),
            ),
            ("mcp".into(), PathBuf::from(".mcp.json")),
        ]
    }

    fn inject_profiles(&self, ctx: &IdeCtx, prompts: &Prompts) -> Result<Vec<String>, String> {
        let root = ctx.project_root;
        let claude_md_path = root.join("CLAUDE.md");
        let agents_dir = root.join(".claude").join("agents");
        let skills_dir = root.join(".claude").join("skills");
        std::fs::create_dir_all(&agents_dir)
            .map_err(|e| format!("mkdir {}: {e}", agents_dir.display()))?;
        std::fs::create_dir_all(&skills_dir)
            .map_err(|e| format!("mkdir {}: {e}", skills_dir.display()))?;

        let header = generate_autogen_header(ctx, &WORKFLOW_SOURCES, "claude_code");

        let mut files_written: Vec<String> = Vec::new();

        backup_file(ctx, &claude_md_path);
        std::fs::write(&claude_md_path, claude_workflow_doc(&header))
            .map_err(|e| format!("write CLAUDE.md: {e}"))?;
        files_written.push(claude_md_path.to_string_lossy().into_owned());

        // Phase 09.A+ / May 2026: los tres anchors triádicos se instalan
        // como skills slash-invocables. ``cortex-documenter`` se suma como
        // tercer skill; el subagent legacy queda para backward compat.
        // Orden de inserción del dict de Python: sync, sddwork, documenter.
        let skill_specs = [
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
        for spec in &skill_specs {
            let skill_dir = skills_dir.join(spec.directory_name);
            std::fs::create_dir_all(&skill_dir)
                .map_err(|e| format!("mkdir {}: {e}", skill_dir.display()))?;
            let skill_path = skill_dir.join("SKILL.md");
            backup_file(ctx, &skill_path);
            let body = strip_frontmatter_or_empty(prompts.get(spec.prompt_key));
            let content = render_claude_markdown(
                &[
                    format!("name: {}", spec.frontmatter_name),
                    format!("description: {}", spec.description),
                ],
                &generate_autogen_header(ctx, &[spec.source_path], "claude_code"),
                &body,
            );
            std::fs::write(&skill_path, content)
                .map_err(|e| format!("write {}: {e}", skill_path.display()))?;
            files_written.push(skill_path.to_string_lossy().into_owned());
        }

        // Orden de inserción del dict de Python: explorer, implementer,
        // documenter (DEPRECATED).
        let agent_specs: [(&str, &str); 3] = [
            (
                "cortex-code-explorer",
                "Read-only architecture analysis for complex changes.",
            ),
            (
                "cortex-code-implementer",
                "Deep-track implementation specialist for complex changes.",
            ),
            (
                "cortex-documenter",
                "DEPRECATED — use /cortex-documenter skill instead. Persist sessions via the legacy Reconstruction flow.",
            ),
        ];
        for (agent_name, description) in &agent_specs {
            let agent_path = agents_dir.join(format!("{agent_name}.md"));
            backup_file(ctx, &agent_path);

            // Leer el prompt canónico y separar frontmatter del body. El
            // frontmatter declara los tools en vocabulario canónico; se
            // traducen al formato nativo via translate_list (falla ante un
            // tool desconocido, igual que la excepción de Python).
            let canonical_md = get_subagent_prompt(ctx, agent_name);
            let (canonical_frontmatter, canonical_body) = split_markdown_frontmatter(&canonical_md);
            let canonical_tools = parse_canonical_tools(canonical_frontmatter.as_ref());
            let translated_tools =
                translate_list(&canonical_tools, "claude_code").map_err(|e| e.to_string())?;

            let mut frontmatter_lines = vec![
                format!("name: {agent_name}"),
                format!("description: {description}"),
            ];
            // Solo inyectar ``tools:`` si el canonico declara tools. Sin la
            // línea, Claude Code hereda TODAS las tools del padre — eso
            // viola la restricción declarada por el prompt canónico.
            if !translated_tools.is_empty() {
                frontmatter_lines.push(format!("tools: {}", translated_tools.join(", ")));
            }

            let content = render_claude_markdown(
                &frontmatter_lines,
                &generate_autogen_header(
                    ctx,
                    &[&format!(".cortex/subagents/{agent_name}.md")],
                    "claude_code",
                ),
                &canonical_body,
            );
            std::fs::write(&agent_path, content)
                .map_err(|e| format!("write {}: {e}", agent_path.display()))?;
            files_written.push(agent_path.to_string_lossy().into_owned());
        }

        Ok(files_written)
    }

    fn inject_mcp(&self, ctx: &IdeCtx) -> Result<Vec<String>, String> {
        let root = ctx.project_root;
        let settings_path = root.join(".claude").join("settings.json");
        let mcp_file = root.join(".mcp.json");
        std::fs::create_dir_all(settings_path.parent().expect("settings parent"))
            .map_err(|e| format!("mkdir .claude: {e}"))?;
        std::fs::create_dir_all(mcp_file.parent().expect("mcp parent"))
            .map_err(|e| format!("mkdir root: {e}"))?;

        backup_file(ctx, &settings_path);
        backup_file(ctx, &mcp_file);

        let mut settings_data: Value = Value::Object(Default::default());
        if settings_path.exists() {
            if let Ok(text) = std::fs::read_to_string(&settings_path) {
                if let Ok(parsed) = serde_json::from_str::<Value>(&text) {
                    settings_data = parsed;
                }
            }
        }

        let obj = settings_data.as_object_mut().expect("settings es objeto");
        let mut enabled_servers = match obj.get("enabledMcpjsonServers") {
            Some(Value::Array(a)) => a.clone(),
            _ => Vec::new(),
        };
        if !enabled_servers.iter().any(|v| v == "cortex") {
            enabled_servers.push(Value::String("cortex".into()));
        }
        obj.insert(
            "enabledMcpjsonServers".into(),
            Value::Array(enabled_servers),
        );

        let mut data: Value = json!({"mcpServers": {}});
        if mcp_file.exists() {
            if let Ok(text) = std::fs::read_to_string(&mcp_file) {
                if let Ok(parsed) = serde_json::from_str::<Value>(&text) {
                    data = parsed;
                }
            }
        }
        if !data.is_object() || data.get("mcpServers").is_none() {
            if let Some(o) = data.as_object_mut() {
                o.entry("mcpServers".to_string())
                    .or_insert_with(|| json!({}));
            }
        }

        // Ruta absoluta del project_root para que Claude Code localice el
        // workspace sin importar desde qué directorio abre el IDE.
        let cortex_config = json!({
            "type": "stdio",
            "command": "cortex",
            "args": ["mcp-server", "--stdio", "--project-root",
                     ctx.project_root.to_string_lossy()],
            "env": {"PYTHONWARNINGS": "ignore"},
        });

        let merged = deep_merge_dict(
            data.get("mcpServers").expect("mcpServers"),
            &json!({"cortex": cortex_config}),
        );
        if let Some(o) = data.as_object_mut() {
            o.insert("mcpServers".into(), merged);
        }

        std::fs::write(&settings_path, json_dump_ascii(&settings_data))
            .map_err(|e| format!("write settings: {e}"))?;
        std::fs::write(&mcp_file, json_dump_ascii(&data))
            .map_err(|e| format!("write .mcp.json: {e}"))?;
        Ok(vec![
            settings_path.to_string_lossy().into_owned(),
            mcp_file.to_string_lossy().into_owned(),
        ])
    }

    /// Remove Cortex artifacts (Fase 2). Regla de oro: SOLO se borra lo que
    /// Cortex creó. Idempotente: segunda pasada devuelve ``[]``.
    fn uninstall(&self, ctx: &IdeCtx) -> Vec<String> {
        let mut report: Vec<String> = Vec::new();
        let root = ctx.project_root;

        // ── 1. CLAUDE.md ─────────────────────────────────────────────
        let claude_md = root.join("CLAUDE.md");
        if claude_md.exists() {
            let backups = sorted_glob(root, "CLAUDE.md.cortex_backup_*");
            if let Some(latest) = backups.last() {
                let content = std::fs::read_to_string(latest).unwrap_or_default();
                let _ = std::fs::write(&claude_md, content);
                for backup in &backups {
                    let _ = std::fs::remove_file(backup);
                }
                report.push(format!(
                    "{} (restored from {})",
                    claude_md.display(),
                    latest
                        .file_name()
                        .map(|n| n.to_string_lossy())
                        .unwrap_or_default()
                ));
            } else {
                let content = std::fs::read_to_string(&claude_md).unwrap_or_default();
                let header = generate_autogen_header(ctx, &WORKFLOW_SOURCES, "claude_code");
                if has_marker_block(&content) {
                    let cleaned = strip_marker_blocks(&content);
                    if !cleaned.trim().is_empty() {
                        let _ = std::fs::write(&claude_md, &cleaned);
                        report.push(format!("{} (Cortex sections removed)", claude_md.display()));
                    } else {
                        let _ = std::fs::remove_file(&claude_md);
                        report.push(claude_md.to_string_lossy().into_owned());
                    }
                } else if is_content_identical_to_bundle(&content, &claude_workflow_doc(&header)) {
                    // Contenido 100% Cortex (solo difiere el timestamp).
                    let _ = std::fs::remove_file(&claude_md);
                    report.push(claude_md.to_string_lossy().into_owned());
                } else {
                    report.push(format!(
                        "{} (skipped: mixed content without Cortex markers or backup)",
                        claude_md.display()
                    ));
                }
            }
        }

        // ── 2. Skills (.claude/skills/cortex-*/) ────────────────────
        let skills_dir = root.join(".claude").join("skills");
        if skills_dir.is_dir() {
            for skill_dir in sorted_glob(&skills_dir, "cortex-*") {
                if !skill_dir.is_dir() {
                    continue;
                }
                // Solo borrar archivos creados por Cortex; si queda algo
                // ajeno dentro, el directorio se preserva.
                if let Ok(entries) = std::fs::read_dir(&skill_dir) {
                    for entry in entries.flatten() {
                        let f = entry.path();
                        if f.is_file() {
                            let name = entry.file_name().to_string_lossy().into_owned();
                            if name == "SKILL.md" || name.contains(".cortex_backup_") {
                                let _ = std::fs::remove_file(&f);
                            }
                        }
                    }
                }
                let remaining = std::fs::read_dir(&skill_dir)
                    .map(|d| d.count())
                    .unwrap_or(1);
                if remaining == 0 {
                    let _ = std::fs::remove_dir(&skill_dir);
                    report.push(format!("{}/SKILL.md", skill_dir.display()));
                } else {
                    report.push(format!(
                        "{} (skipped: foreign files inside)",
                        skill_dir.display()
                    ));
                }
            }
        }

        // ── 3. Agents (.claude/agents/cortex-*.md) ──────────────────
        let agents_dir = root.join(".claude").join("agents");
        for agent_name in [
            "cortex-code-explorer",
            "cortex-code-implementer",
            "cortex-documenter",
        ] {
            let agent_path = agents_dir.join(format!("{agent_name}.md"));
            if agent_path.is_file() {
                let _ = std::fs::remove_file(&agent_path);
                report.push(agent_path.to_string_lossy().into_owned());
            }
        }

        // ── 4. settings.json: enabledMcpjsonServers 'cortex' ────────
        let settings_path = root.join(".claude").join("settings.json");
        if settings_path.exists() {
            match std::fs::read_to_string(&settings_path)
                .map_err(|e| e.to_string())
                .and_then(|t| serde_json::from_str::<Value>(&t).map_err(|e| e.to_string()))
            {
                Err(_) => {
                    report.push(format!(
                        "{} (skipped: invalid JSON, not touched)",
                        settings_path.display()
                    ));
                }
                Ok(mut settings_data) if settings_data.is_object() => {
                    let mut changed = false;
                    if let Some(obj) = settings_data.as_object_mut() {
                        let should_remove = matches!(
                            obj.get("enabledMcpjsonServers"),
                            Some(Value::Array(a))
                                if a.iter().any(|v| v == "cortex")
                        );
                        if should_remove {
                            if let Some(Value::Array(enabled)) =
                                obj.get_mut("enabledMcpjsonServers")
                            {
                                enabled.retain(|v| v != "cortex");
                                if enabled.is_empty() {
                                    obj.remove("enabledMcpjsonServers");
                                }
                            }
                            changed = true;
                        }
                    }
                    if changed {
                        if settings_data
                            .as_object()
                            .map(|o| o.is_empty())
                            .unwrap_or(false)
                        {
                            // Python: ``if not settings_data`` → unlink.
                            let _ = std::fs::remove_file(&settings_path);
                            report.push(settings_path.to_string_lossy().into_owned());
                        } else {
                            backup_file(ctx, &settings_path);
                            let _ = std::fs::write(&settings_path, json_dump_ascii(&settings_data));
                            report
                                .push(format!("{} (Cortex keys removed)", settings_path.display()));
                        }
                    }
                }
                Ok(_non_dict) => {}
            }
        }

        // ── 5. .mcp.json: mcpServers.cortex ─────────────────────────
        let mcp_file = root.join(".mcp.json");
        if mcp_file.exists() {
            match std::fs::read_to_string(&mcp_file)
                .map_err(|e| e.to_string())
                .and_then(|t| serde_json::from_str::<Value>(&t).map_err(|e| e.to_string()))
            {
                Err(_) => {
                    report.push(format!(
                        "{} (skipped: invalid JSON, not touched)",
                        mcp_file.display()
                    ));
                }
                Ok(mut data) if data.is_object() => {
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
                    if changed {
                        if data.as_object().map(|o| o.is_empty()).unwrap_or(false) {
                            let _ = std::fs::remove_file(&mcp_file);
                            report.push(mcp_file.to_string_lossy().into_owned());
                        } else {
                            backup_file(ctx, &mcp_file);
                            let _ = std::fs::write(&mcp_file, json_dump_ascii(&data));
                            report.push(format!("{} (Cortex keys removed)", mcp_file.display()));
                        }
                    }
                }
                Ok(_non_dict) => {}
            }
        }

        report
    }
}

/// `sorted(Path.glob(pattern))` de Python: rutas ordenadas lexicográficamente
/// por su representación en string.
fn sorted_glob(dir: &Path, pattern: &str) -> Vec<PathBuf> {
    let mut out: Vec<PathBuf> = std::fs::read_dir(dir)
        .into_iter()
        .flatten()
        .flatten()
        .map(|e| e.path())
        .filter(|p| {
            p.file_name()
                .map(|n| glob_match(&n.to_string_lossy(), pattern))
                .unwrap_or(false)
        })
        .collect();
    out.sort_by_key(|p| p.to_string_lossy().into_owned());
    out
}

/// Matching estilo glob para los patrones de un solo `*` que usa este
/// adapter (`CLAUDE.md.cortex_backup_*`, `cortex-*`).
fn glob_match(name: &str, pattern: &str) -> bool {
    match pattern.split_once('*') {
        None => name == pattern,
        Some((prefix, suffix)) => {
            name.len() >= prefix.len() + suffix.len()
                && name.starts_with(prefix)
                && name.ends_with(suffix)
        }
    }
}

/// `strip_markdown_frontmatter(...)` tolerando prompt ausente (dict.get → "").
fn strip_frontmatter_or_empty(prompt: Option<&String>) -> String {
    let content = prompt.cloned().unwrap_or_default();
    crate::ide::prompts::strip_markdown_frontmatter(&content)
}
