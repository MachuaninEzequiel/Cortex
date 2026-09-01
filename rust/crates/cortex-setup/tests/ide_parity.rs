//! Paridad P8d: los 11 IDE adapters byte-a-byte contra el oráculo Python
//! (`bench/parity/archive/p8_ide_golden.py` +
//! `bench/parity/archive/golden_setup/ide/`).
//!
//! Para cada IDE × escenario (fresh / existing / uninstall) se reconstruye
//! el mismo fixture (proyecto con SSoT `.cortex/` + HOME redirigido con
//! configs ajenas pre-sembradas), se corre el adapter REAL con
//! `IdeCtx { home, now congelado }` y se compara el árbol resultante
//! (project + home) más los reports normalizados contra el manifiesto
//! capturado por Python.
//!
//! Normalizaciones pactadas: `{{ROOT}}` / `{{HOME}}`; los reports se
//! ordenan en ambos lados (el glob de subagents de opencode.py NO es
//! determinista y solo afecta el ORDEN de la lista, no los archivos).

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use chrono::TimeZone;
use serde_json::Value;

use cortex_setup::ide::adapters::all_adapters;
use cortex_setup::ide::prompts::build_all_prompts;
use cortex_setup::ide::{IdeCtx, Prompts};

const GOLDEN: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../bench/parity/archive/golden_setup/ide"
);

const FROZEN_SECS: (i32, u32, u32, u32, u32, u32) = (2026, 8, 24, 12, 34, 56);

// ---------------------------------------------------------------------------
// Fixture SSoT — DEBE ser idéntico a p8_ide_golden.py
// ---------------------------------------------------------------------------

const SKILL_SYNC: &str = "---\nname: cortex-sync\ndescription: Cortex PRE-FLIGHT (Spec Creation Only). NO WRITE PERMISSIONS.\n---\n\n# Cortex Sync - Gobernanza de Analisis\n\nAnchor de inicio. Llama a `cortex_sync_ticket` antes que nada.\nAcentos de prueba: áéíóú. Emoji: ⚠️.\n";

const SKILL_SDDWORK: &str = "---\nname: cortex-SDDwork\ndescription: Implementación orquestada de la spec persistida.\n---\n\n# Cortex SDDwork\n\nMiddle pluggable. Fast Track para edits directos; Deep Track con\ndelegación a los subagents canónicos (explorer / designer / implementer).\n";

const SKILL_DOCUMENTER: &str = "---\nname: cortex-documenter\ndescription: Anchor de cierre con criterio editorial.\n---\n\n# Cortex Documenter\n\nCierra la Session: decide doc types, escribe nota a mano, llama\n`cortex_self_review_note`, persiste vía `cortex_write_doc` y cierra con\n`cortex_close_session`.\n";

const SUBAGENT_DESIGNER: &str = "---\nname: cortex-code-designer\ndescription: Produce design doc antes de implementar.\ntools: read_file, cortex_context, cortex_create_spec\n---\n\n# Cortex Code Designer\n\nDiseña antes de tocar código. Salida: design note revisable.\n";

const SUBAGENT_EXPLORER: &str = "---\nname: cortex-code-explorer\ndescription: Análisis read-only de arquitectura.\ntools: read_file, execute_command, cortex_search, cortex_ping\n---\n\n# Cortex Code Explorer\n\nExplora el repositorio sin mutar estado. Emite checkpoint al terminar.\n";

const SUBAGENT_IMPLEMENTER: &str = "---\nname: cortex-code-implementer\ndescription: Implementa siguiendo el design doc.\ntools: read_file, write_file, edit_file, execute_command, cortex_session_checkpoint\n---\n\n# Cortex Code Implementer\n\nDeep Track. Implementa la spec con edits quirúrgicos.\n";

const SUBAGENT_DOCUMENTER: &str = "---\nname: cortex-documenter\ndescription: DEPRECATED - usar /cortex-documenter skill.\ntools: read_file, cortex_documenter_briefing, cortex_self_review_note, cortex_write_doc, cortex_close_session\n---\n\n# Cortex Documenter (subagent legacy)\n\nFlujo antiguo de reconstrucción. Mantenido por compatibilidad.\n";

const PRESEED_CLAUDE_MD: &str = "# Mi proyecto\n\nNotas propias del humano.\n";
const PRESEED_AGENTS_MD: &str = "# Agentes del proyecto\n\nConvenciones locales.\n";
const PRESEED_MCP_JSON: &str = "{\n  \"mcpServers\": {\n    \"local-dev\": {\n      \"command\": \"npx\",\n      \"args\": [\n        \"-y\",\n        \"thing\"\n      ]\n    }\n  }\n}\n";
const PRESEED_SETTINGS_JSON: &str = "{\n  \"enabledMcpjsonServers\": [\n    \"other\"\n  ],\n  \"permissions\": {\n    \"allow\": [\n      \"Bash\"\n    ]\n  }\n}\n";
const PRESEED_CURSOR_MCP: &str = "{\n  \"mcpServers\": {\n    \"other-server\": {\n      \"command\": \"other\"\n    }\n  }\n}\n";
const PRESEED_CODEX_TOML: &str =
    "model = \"gpt-5-codex\"\n\n[mcp_servers.other]\ncommand = \"other\"\n";
const PRESEED_WINDSURF_MCP: &str =
    "{\n  \"mcpServers\": {\n    \"existing\": {\n      \"command\": \"x\"\n    }\n  }\n}\n";
const PRESEED_OPENCODE_JSON: &str = "{\n  \"theme\": \"dark\"\n}\n";
const PRESEED_HERMES_CONFIG: &str = "{\n  \"model\": \"hermes-3\",\n  \"temperature\": 0.7\n}\n";
const PRESEED_GEMINI_SETTINGS: &str = "{\n  \"theme\": \"dark\"\n}\n";
const PRESEED_ZED_AGENTS: &str = "{\n  \"existing\": {\n    \"command\": \"z\"\n  }\n}\n";
const PRESEED_CLAUDE_DESKTOP: &str =
    "{\n  \"mcpServers\": {\n    \"global-server\": {\n      \"command\": \"g\"\n    }\n  }\n}\n";

fn write_rel(base: &Path, rel: &str, content: &str) {
    let p = base.join(rel);
    if let Some(parent) = p.parent() {
        std::fs::create_dir_all(parent).expect("mkdir fixture");
    }
    std::fs::write(p, content).expect("write fixture");
}

fn build_fixture_project(root: &Path) {
    write_rel(
        root,
        "config.yaml",
        "semantic:\n  vault_path: vault\nretrieval:\n  top_k: 5\n",
    );
    write_rel(
        root,
        "vault/nota-a.md",
        "# Nota A\n\nContenido determinista del fixture.\n",
    );
    write_rel(root, ".cortex/skills/cortex-sync.md", SKILL_SYNC);
    write_rel(root, ".cortex/skills/cortex-SDDwork.md", SKILL_SDDWORK);
    write_rel(
        root,
        ".cortex/skills/cortex-documenter.md",
        SKILL_DOCUMENTER,
    );
    write_rel(
        root,
        ".cortex/subagents/cortex-code-designer.md",
        SUBAGENT_DESIGNER,
    );
    write_rel(
        root,
        ".cortex/subagents/cortex-code-explorer.md",
        SUBAGENT_EXPLORER,
    );
    write_rel(
        root,
        ".cortex/subagents/cortex-code-implementer.md",
        SUBAGENT_IMPLEMENTER,
    );
    write_rel(
        root,
        ".cortex/subagents/cortex-documenter.md",
        SUBAGENT_DOCUMENTER,
    );
}

fn preseed(root: &Path, home: &Path) {
    write_rel(root, "CLAUDE.md", PRESEED_CLAUDE_MD);
    write_rel(root, "AGENTS.md", PRESEED_AGENTS_MD);
    write_rel(root, ".mcp.json", PRESEED_MCP_JSON);
    write_rel(root, ".claude/settings.json", PRESEED_SETTINGS_JSON);
    write_rel(home, ".cursor/mcp.json", PRESEED_CURSOR_MCP);
    write_rel(home, ".codex/config.toml", PRESEED_CODEX_TOML);
    write_rel(
        home,
        ".codeium/windsurf/mcp_config.json",
        PRESEED_WINDSURF_MCP,
    );
    write_rel(
        home,
        ".config/opencode/opencode.json",
        PRESEED_OPENCODE_JSON,
    );
    write_rel(home, ".config/hermes/config.json", PRESEED_HERMES_CONFIG);
    write_rel(home, ".gemini/settings.json", PRESEED_GEMINI_SETTINGS);
    write_rel(home, ".zed/agents.json", PRESEED_ZED_AGENTS);
    write_rel(
        home,
        ".config/Claude/claude_desktop_config.json",
        PRESEED_CLAUDE_DESKTOP,
    );
}

// ---------------------------------------------------------------------------
// Snapshot + normalización
// ---------------------------------------------------------------------------

fn normalize(text: &str, root: &Path, home: &Path) -> String {
    text.replace(&root.to_string_lossy().to_string(), "{{ROOT}}")
        .replace(&home.to_string_lossy().to_string(), "{{HOME}}")
}

fn walk_files(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let p = entry.path();
        if p.is_dir() {
            walk_files(&p, out);
        } else if p.is_file() {
            out.push(p);
        }
    }
}

fn snapshot(base: &Path, scope: &str, root: &Path, home: &Path) -> BTreeMap<String, String> {
    let mut files = BTreeMap::new();
    let mut paths = Vec::new();
    walk_files(base, &mut paths);
    for full in paths {
        let rel = full
            .strip_prefix(base)
            .expect("path bajo base")
            .to_string_lossy()
            .replace('\\', "/");
        let content = std::fs::read_to_string(&full)
            .unwrap_or_else(|e| panic!("no UTF-8 en {}: {e}", full.display()));
        files.insert(format!("{scope}:{rel}"), normalize(&content, root, home));
    }
    files
}

// ---------------------------------------------------------------------------
// El gate: 11 IDEs × 3 escenarios
// ---------------------------------------------------------------------------

#[test]
fn ide_adapters_byte_parity() {
    // Un solo #[test] secuencial: CODEX_HOME es una env var global del
    // proceso y las scenarios de un mismo IDE comparten el runner.
    let ides = [
        "claude_code",
        "opencode",
        "pi",
        "codex",
        "cursor",
        "claude_desktop",
        "vscode",
        "windsurf",
        "zed",
        "antigravity",
        "hermes",
    ];
    let scenarios = ["fresh", "existing", "uninstall"];
    for ide in ides {
        for scenario in scenarios {
            run_one(ide, scenario);
        }
    }
}

fn run_one(ide: &str, scenario: &str) {
    let tmp = std::env::temp_dir().join(format!(
        "cortex-ide-parity-{ide}-{scenario}-{}",
        std::process::id()
    ));
    let _ = std::fs::remove_dir_all(&tmp);
    let project = tmp.join("project");
    let home = tmp.join("home");
    std::fs::create_dir_all(&home).expect("mkdir home");
    build_fixture_project(&project);
    if scenario != "fresh" {
        preseed(&project, &home);
    }

    let prev_codex_home = std::env::var("CODEX_HOME").ok();
    std::env::set_var("CODEX_HOME", home.join(".codex"));

    let now = chrono::Utc
        .with_ymd_and_hms(
            FROZEN_SECS.0,
            FROZEN_SECS.1,
            FROZEN_SECS.2,
            FROZEN_SECS.3,
            FROZEN_SECS.4,
            FROZEN_SECS.5,
        )
        .unwrap();
    let ctx = IdeCtx {
        project_root: &project,
        home: &home,
        now,
    };

    let mut adapters = all_adapters();
    let adapter = adapters
        .iter_mut()
        .find(|a| a.name() == ide)
        .unwrap_or_else(|| panic!("adapter no registrado: {ide}"));

    // ESPEJO EXACTO del oráculo: el escenario uninstall corre inject con
    // prompts VACÍOS ({}) DESCARTANDO sus returns, y solo captura lo que
    // devuelve uninstall.
    let mut reports: Vec<String> = Vec::new();
    if scenario == "uninstall" {
        let empty = Prompts::new();
        adapter
            .inject_profiles(&ctx, &empty)
            .unwrap_or_else(|e| panic!("{ide}__{scenario}: inject_profiles: {e}"));
        adapter
            .inject_mcp(&ctx)
            .unwrap_or_else(|e| panic!("{ide}__{scenario}: inject_mcp: {e}"));
        reports.extend(adapter.uninstall(&ctx));
    } else {
        let prompts = build_all_prompts(&ctx);
        reports.extend(
            adapter
                .inject_profiles(&ctx, &prompts)
                .unwrap_or_else(|e| panic!("{ide}__{scenario}: inject_profiles: {e}")),
        );
        reports.extend(
            adapter
                .inject_mcp(&ctx)
                .unwrap_or_else(|e| panic!("{ide}__{scenario}: inject_mcp: {e}")),
        );
    }

    restore_codex_home(prev_codex_home.as_deref());

    let mut files = snapshot(&project, "project", &project, &home);
    files.extend(snapshot(&home, "home", &project, &home));

    // Normalización N-mcp-command (delta INTENCIONAL del port nativo,
    // ver plan §15): el binario nativo se instala como `cortex-cli` (no
    // existe `cortex`); los ARGS inyectados ya son compatibles con el
    // nativo (mcp-server --stdio --project-root). Byte-parity para todo
    // lo demás se mantiene contra el golden del oráculo. No aplica a pi:
    // su mcp.json viene del bundle (paridad copia == bundle).
    if ide != "pi" {
        for v in files.values_mut() {
            *v = normalize_bin_command(v);
        }
    }
    let mut reports_sorted: Vec<String> = reports
        .into_iter()
        .map(|r| normalize(&r, &project, &home))
        .collect();
    reports_sorted.sort();

    // ── Comparación contra el golden ────────────────────────────────
    let golden_path = format!("{GOLDEN}/{ide}__{scenario}/manifest.json");
    let raw = std::fs::read_to_string(&golden_path)
        .unwrap_or_else(|e| panic!("falta golden {golden_path}: {e}"));
    let golden: Value = serde_json::from_str(&raw).expect("manifest JSON inválido");

    let golden_reports: Vec<String> = golden["reports"]
        .as_array()
        .expect("reports array")
        .iter()
        .map(|v| v.as_str().expect("report str").to_string())
        .collect();
    assert_eq!(
        reports_sorted, golden_reports,
        "{ide}__{scenario}: listas de reports difieren"
    );

    let mut golden_files = golden["files"].as_object().cloned().expect("files map");

    // Normalización N-pi-bundle: el adaptador pi copia `cortex-pi/`
    // VERBATIM al proyecto (adapters/pi.rs: "el bundle es la única fuente
    // de verdad de Pi"). El golden del oráculo congelaba una versión vieja
    // del bundle (resolver pipx); la paridad REAL es copia == bundle actual.
    if ide == "pi" {
        let bundle = PathBuf::from(concat!(env!("CARGO_MANIFEST_DIR"), "/../../../cortex-pi"));
        for (key, expected) in golden_files.iter_mut() {
            // Todo archivo que el bundle aporta (raíz o .pi/) se compara
            // contra la fuente REAL del bundle, no contra el golden.
            if let Some(rel) = key.strip_prefix("project:") {
                let src = bundle.join(rel);
                if src.is_file() {
                    let content = std::fs::read_to_string(&src)
                        .unwrap_or_else(|e| panic!("bundle faltante {src:?}: {e}"));
                    *expected = Value::String(content);
                }
            }
        }
    }
    let mut problems: Vec<String> = Vec::new();
    for (key, expected) in &golden_files {
        let expected_str = expected.as_str().expect("file content str");
        match files.get(key) {
            Some(actual) if actual == expected_str => {}
            Some(actual) => {
                problems.push(format!(
                    "{key}: contenido difiere\n<<< golden\n{}\n=== ours\n{}\n>>>",
                    truncate(expected_str),
                    truncate(actual)
                ));
            }
            None => problems.push(format!("{key}: falta en Rust")),
        }
    }
    for key in files.keys() {
        if !golden_files.contains_key(key) {
            problems.push(format!("{key}: extra en Rust"));
        }
    }
    assert!(
        problems.is_empty(),
        "{ide}__{scenario}: {} diferencias de archivos\n{}",
        problems.len(),
        problems.join("\n")
    );

    let _ = std::fs::remove_dir_all(&tmp);
}

fn restore_codex_home(prev: Option<&str>) {
    match prev {
        Some(v) => std::env::set_var("CODEX_HOME", v),
        None => std::env::remove_var("CODEX_HOME"),
    }
}

fn truncate(s: &str) -> String {
    const MAX: usize = 600;
    if s.len() <= MAX {
        s.to_string()
    } else {
        format!("{}…[+{} bytes]", &s[..MAX], s.len() - MAX)
    }
}

/// Normalización N-mcp-command: el binario NATIVO se llama `cortex-cli`
/// (nombre pelado o ruta absoluta que resuelve el PATH); el golden del
/// oráculo esperaba el nombre del producto Python (`cortex`). Reemplaza
/// el valor del `command` del server MCP en TOML y JSON inyectados.
fn normalize_bin_command(v: &str) -> String {
    let mut out = v.to_string();
    // Iterar TODOS los servers MCP del archivo (el preseed puede tener
    // otros commands antes del de cortex).
    for marker in ["\"command\": \"", "command = \""] {
        let mut pos = 0usize;
        while let Some(rel) = out[pos..].find(marker) {
            let start = pos + rel + marker.len();
            let Some(end_rel) = out[start..].find('"') else {
                break;
            };
            let cmd = &out[start..start + end_rel];
            if cmd.contains("cortex-cli") {
                out.replace_range(start..start + end_rel, "cortex");
            }
            pos = start + end_rel + 1;
        }
    }
    out
}
