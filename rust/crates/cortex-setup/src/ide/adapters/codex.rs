//! Porteo de cortex/ide/adapters/codex.py (P8d).
//!
//! Codex CLI (OpenAI): rediseño Fase 4 del plan multi-IDE & MCP hardening.
//!
//! - `AGENTS.md` en el PROJECT ROOT (Codex lo lee ahí con merge layered),
//!   bloque Cortex entre marcadores HTML (coexiste con contenido del adopter).
//! - MCP en TOML: `<proyecto>/.codex/config.toml` con sección
//!   `[mcp_servers.cortex]` + `[mcp_servers.cortex.env]`.
//! - Trust del proyecto en el config GLOBAL (`~/.codex/config.toml`,
//!   respeta `CODEX_HOME`): sin trust, Codex descarta la capa project-local.
//!   Entrada envuelta en marcadores ESPECÍFICOS del path (multi-repo safe).
//! - Sin subagents ni skills personalizados: toda la guidance va inline.
//!
//! NOTA de porteo: el módulo original usa regex DOTALL no-codiciosas para
//! localizar bloques marcados; acá se replican con escaneo manual de spans
//! (el crate no depende de `regex`). `shutil.which` se replica sobre `PATH`.
//! En Linux `os.path.normcase` es identidad; se documenta en la comparación
//! de keys de trust.

use std::path::{Path, PathBuf};

use crate::ide::base::{backup_file, generate_autogen_header};
use crate::ide::{IdeAdapter, IdeCtx};

/// Marcadores para la sección Cortex dentro de AGENTS.md preexistente
/// (idénticos a los defaults de `base.py`; se declaran locales como en
/// Python, que también los repite en este módulo).
const CORTEX_AGENTS_MD_MARKER_OPEN: &str =
    "<!-- BEGIN CORTEX SECTION (auto-generated, do not edit) -->";
const CORTEX_AGENTS_MD_MARKER_CLOSE: &str = "<!-- END CORTEX SECTION -->";

/// Marcador del bloque MCP en config.toml.
const CORTEX_TOML_MARKER_OPEN: &str = "# BEGIN CORTEX MCP (auto-generated, do not edit)";
const CORTEX_TOML_MARKER_CLOSE: &str = "# END CORTEX MCP";

/// Plantillas de los marcadores de trust en el config GLOBAL. El tag es
/// `str(project_root)` para que uninstall remueva solo la entrada de ESTE
/// proyecto (multi-repo safe).
const CORTEX_TRUST_MARKER_OPEN_TPL: &str =
    "# BEGIN CORTEX TRUST [{tag}] (auto-generated, do not edit)";
const CORTEX_TRUST_MARKER_CLOSE_TPL: &str = "# END CORTEX TRUST [{tag}]";

/// Cuerpo estático de la sección Cortex en AGENTS.md (entre el comentario
/// del header autogenerado y el marcador de cierre). Termina con `\n\n`
/// antes del marcador de cierre, igual que el f-string de Python.
const AGENTS_MD_BODY: &str = r#"# Cortex Workflow for Codex (triadic anchors, single-agent sequential)

This project uses **Cortex** governance. Cortex is structured around
three slash-invocable anchors:

| Anchor             | Role            | Mandatory |
|--------------------|-----------------|-----------|
| `/cortex-sync`     | opening anchor  | YES — every Session opens here |
| (middle)           | implementation  | pluggable (SDDwork / BYO / etc.) |
| `/cortex-documenter` | closing anchor | YES — every Session closes here |

Codex has no native `Task` tool nor slash-skill dispatch, so the **single
Codex agent executes the three phases sequentially within the same
session**, guided by the explicit instructions below. The phases mirror
the canonical skill files under `.cortex/skills/`.

## Pre-flight check (mandatory, every session)

Before any operation, call `cortex_ping`. If the response is not
`status: "ok"`, abort the operation with a clear message to the user:

> The Cortex MCP server is unavailable (status: <status>; last_error:
> <error>). Restart the IDE or run `cortex doctor` to diagnose.

NEVER fall back to manual markdown writing. NEVER degrade Cortex features
when the MCP is down.

---

## Phase 1 — Opening anchor (acts as `/cortex-sync`)

Mandatory first step. See `.cortex/skills/cortex-sync.md` for the full
canonical skill.

1. Call `cortex_sync_ticket` with the user's request. The MCP server
   rejects any later `cortex_create_spec` if this step is skipped.
2. Read `CONTEXT.md` if it exists; its terms are canonical and the spec
   must not invent synonyms.
3. Explore the repo with `glob` + `read` (NOT modify) to ground the spec
   in real code.
4. Emit a proposal with `cortex_emit_proposal` (summary + 2-5
   alternatives + recommendation + risks). In `proposal_mode="required"`,
   end the turn after emitting — wait for the user's confirmation in a
   later message before continuing.
5. After confirmation, call `cortex_create_spec` (passing
   `proposal_mode` / `proposal_confirmed` as appropriate). This persists
   the spec to `vault/specs/` AND opens the Session.

---

## Phase 2 — Middle (acts as `/cortex-SDDwork`)

Implement the persisted spec. The full canonical skill lives at
`.cortex/skills/cortex-SDDwork.md`.

1. Verify the active Session with `cortex_session_status`. Abort if no
   active session exists.
2. Decide between **Fast Track** (1-2 files, cosmetic / bugfix / simple
   logic) and **Deep Track** (refactors, new architecture).
3. Make the changes following existing repo conventions. Run tests if
   declared in the spec's `verification_hooks`. Codex cannot delegate to
   subagents — for Deep Track, perform the explorer / designer /
   implementer steps sequentially in your own context.
4. Emit ONE `cortex_session_checkpoint` with `source="cortex-SDDwork"`,
   carrying `verified_claims`, `unverified_claims`, `artifacts_touched`,
   and a brief `note`. Do NOT close the session here — that's Phase 3.

---

## Phase 3 — Closing anchor (acts as `/cortex-documenter`)

Mandatory final step. The full canonical skill lives at
`.cortex/skills/cortex-documenter.md`. The documenter writes the session
note **by hand with editorial criterion** — NOT a template fill.

1. Call `cortex_documenter_briefing` (no args = active session). Receive
   JSON with: spec, diff_text, diff_entries, files_verified_by_git (✓),
   files_declared_only (◌), in_scope / out_of_scope / unimplemented
   files, verification_results, contradictions, suggested_adrs,
   raw_checkpoints, gitless flag.
2. Apply the canonical decision table to decide what doc types to emit
   (1 mandatory main note: `session` or `handoff`; 0..N optional:
   `adr`, `decision`, `incident`, `postmortem`, `runbook`,
   `architecture`, `changelog`, `glossary`, `hu`). See the skill file
   for the objective criteria per doc type.
3. Write the main note body in your own prose — reference, don't
   duplicate. Mention files with provenance: ``✓ path`` for git-verified,
   ``◌ path`` for declared-only (uncommitted).
4. **Recommended**: call `cortex_self_review_note(body=<draft>,
   verification_hooks_passed=<bool>)`. Surfaces placeholder tokens and
   hollow success claims. Revise or proceed.
5. Persist the main note with `cortex_write_doc(doc_type=...,
   payload=...)`. Persist any secondary notes the same way.
6. Close the Session with `cortex_close_session(status=...,
   session_note_path=..., adrs_created=[...])`. `status` MUST be one of
   `closed` / `handoff` / `abandoned`. Use `handoff` (not `closed`) when
   required verification hooks failed OR unimplemented files remain.

---

## Hard rules

- NEVER call `cortex_create_spec` before `cortex_sync_ticket`. The MCP
  server rejects it with a governance violation.
- NEVER skip Phase 3 (closing anchor). A session without the documenter
  closing step erodes the organizational memory.
- NEVER write Markdown to the vault by hand with `write_file` — the
  canonical routing depends on `cortex_write_doc` and `cortex_create_spec`.
- The status `handoff` is a first-class outcome. If hooks fail or
  unimplemented files remain, close with `handoff` (NOT `closed`).
- If `CONTEXT.md` exists at project root or under `.cortex/CONTEXT.md`,
  treat its terms as canonical. Add new canonical terms via
  `cortex_write_doc(doc_type="glossary", ...)`.

"#;

// ---------------------------------------------------------------------------
// Helpers de bloques marcados (réplica de las regex DOTALL no-codiciosas)
// ---------------------------------------------------------------------------

/// Span de UNA coincidencia `open .*? close`: primer `open`, luego el
/// `close` más cercano posterior (semántica no-greedy de Python).
/// `eat_newline` replica el sufijo `r"\n?"` del patrón de uninstall/merge.
struct BlockSpan {
    start: usize,
    /// Fin exclusivo (incluye el `\n` opcional si `eat_newline` y existe).
    end: usize,
}

/// Todas las coincidencias no solapadas, de izquierda a derecha.
fn find_block_spans(haystack: &str, open: &str, close: &str, eat_newline: bool) -> Vec<BlockSpan> {
    let mut spans = Vec::new();
    let bytes = haystack.as_bytes();
    let mut from = 0usize;
    while from <= bytes.len() {
        let Some(rel_open) = find_sub(&bytes[from..], open.as_bytes()) else {
            break;
        };
        let open_start = from + rel_open;
        let after_open = open_start + open.len();
        if after_open > bytes.len() {
            break;
        }
        let Some(rel_close) = find_sub(&bytes[after_open..], close.as_bytes()) else {
            break;
        };
        let mut end = after_open + rel_close + close.len();
        if eat_newline && end < bytes.len() && bytes[end] == b'\n' {
            end += 1;
        }
        spans.push(BlockSpan {
            start: open_start,
            end,
        });
        from = end;
    }
    spans
}

fn find_sub(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    if needle.is_empty() || haystack.len() < needle.len() {
        return None;
    }
    haystack.windows(needle.len()).position(|w| w == needle)
}

/// `pattern.sub("", existing)` con patrón `open .*? close \n?`:
/// elimina todos los bloques marcados (incluyendo un `\n` final opcional
/// de cada uno) preservando el resto byte-a-byte.
fn strip_marked_blocks(existing: &str, open_m: &str, close_m: &str) -> String {
    let spans = find_block_spans(existing, open_m, close_m, true);
    if spans.is_empty() {
        return existing.to_string();
    }
    let mut out = String::with_capacity(existing.len());
    let mut last = 0usize;
    for span in &spans {
        out.push_str(&existing[last..span.start]);
        last = span.end;
    }
    out.push_str(&existing[last..]);
    out
}

/// `_replace_or_append_cortex_section`: reemplaza cada bloque Cortex por
/// `block.strip()` o appendea al final. Append: separador solo si hay
/// contenido previo (sin `\n` final → `\n\n`; con él → `\n`). El bloque se
/// agrega VERBATIM (sin strip ni `\n` extra — distinto de upsert_marker_block
/// de base.py, que es la semántica de otro adapter).
fn replace_or_append_cortex_section(existing: &str, cortex_block: &str) -> String {
    let spans = find_block_spans(
        existing,
        CORTEX_AGENTS_MD_MARKER_OPEN,
        CORTEX_AGENTS_MD_MARKER_CLOSE,
        false,
    );
    if !spans.is_empty() {
        let mut out = String::with_capacity(existing.len());
        let mut last = 0usize;
        for span in &spans {
            out.push_str(&existing[last..span.start]);
            out.push_str(cortex_block.trim());
            last = span.end;
        }
        out.push_str(&existing[last..]);
        return out;
    }
    let sep = if existing.is_empty() {
        ""
    } else if existing.ends_with('\n') {
        "\n"
    } else {
        "\n\n"
    };
    format!("{existing}{sep}{cortex_block}")
}

/// `_replace_or_append_cortex_toml_block`: ídem, con los marcadores TOML.
fn replace_or_append_cortex_toml_block(existing: &str, cortex_toml: &str) -> String {
    let spans = find_block_spans(
        existing,
        CORTEX_TOML_MARKER_OPEN,
        CORTEX_TOML_MARKER_CLOSE,
        false,
    );
    if !spans.is_empty() {
        let mut out = String::with_capacity(existing.len());
        let mut last = 0usize;
        for span in &spans {
            out.push_str(&existing[last..span.start]);
            out.push_str(cortex_toml.trim());
            last = span.end;
        }
        out.push_str(&existing[last..]);
        return out;
    }
    let sep = if existing.is_empty() {
        ""
    } else if existing.ends_with('\n') {
        "\n"
    } else {
        "\n\n"
    };
    format!("{existing}{sep}{cortex_toml}")
}

// ---------------------------------------------------------------------------
// Comando cortex y bloque TOML del MCP
// ---------------------------------------------------------------------------

/// Réplica de `shutil.which("cortex")`: busca `cmd` en cada dir de `PATH`
/// como archivo ejecutable. Devuelve la ruta absoluta o el nombre pelado.
fn resolve_cortex_command() -> String {
    if let Some(path_env) = std::env::var_os("PATH") {
        for dir in std::env::split_paths(&path_env) {
            let candidate = dir.join("cortex");
            if candidate.is_file() {
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    if let Ok(md) = std::fs::metadata(&candidate) {
                        if md.permissions().mode() & 0o111 != 0 {
                            return candidate.to_string_lossy().into_owned();
                        }
                    }
                }
                #[cfg(not(unix))]
                {
                    return candidate.to_string_lossy().into_owned();
                }
            }
        }
    }
    "cortex".to_string()
}

/// `_build_cortex_toml_block`: bloque TOML del MCP server Cortex.
///
/// Hardening 2026-05-30: `command` resuelto a ruta absoluta,
/// `startup_timeout_sec = 60` (el default de 10 s mata el server Python en
/// frío) y env vars que protegen el stdio JSON-RPC. Backslashes escapados
/// para Windows (no-op en POSIX).
fn build_cortex_toml_block(project_root: &Path) -> String {
    let project_str = project_root.to_string_lossy().replace('\\', "\\\\");
    let command_str = resolve_cortex_command().replace('\\', "\\\\");
    format!(
        "{CORTEX_TOML_MARKER_OPEN}\n\
         [mcp_servers.cortex]\n\
         command = \"{command_str}\"\n\
         args = [\"mcp-server\", \"--stdio\", \"--project-root\", \"{project_str}\"]\n\
         startup_timeout_sec = 60\n\
         enabled = true\n\
         \n\
         [mcp_servers.cortex.env]\n\
         PYTHONWARNINGS = \"ignore\"\n\
         PYTHONIOENCODING = \"utf-8\"\n\
         PYTHONUNBUFFERED = \"1\"\n\
         {CORTEX_TOML_MARKER_CLOSE}\n"
    )
}

// ---------------------------------------------------------------------------
// Trust del proyecto en el config GLOBAL (~/.codex/config.toml)
// ---------------------------------------------------------------------------

/// `_codex_global_config_path`: respeta `CODEX_HOME`; default
/// `Path.home()/.codex/config.toml` (acá `ctx.home`).
fn codex_global_config_path(ctx: &IdeCtx) -> PathBuf {
    match std::env::var("CODEX_HOME") {
        Ok(home) if !home.is_empty() => PathBuf::from(home).join("config.toml"),
        _ => ctx.home.join(".codex").join("config.toml"),
    }
}

/// `_trust_markers`: par BEGIN/END específico del path del proyecto.
fn trust_markers(project_root: &Path) -> (String, String) {
    let tag = project_root.to_string_lossy();
    (
        CORTEX_TRUST_MARKER_OPEN_TPL.replace("{tag}", &tag),
        CORTEX_TRUST_MARKER_CLOSE_TPL.replace("{tag}", &tag),
    )
}

/// `_build_cortex_trust_block`: entrada `[projects."<path>"]` con
/// `trust_level = "trusted"`, envuelta en los marcadores del path.
fn build_cortex_trust_block(project_root: &Path) -> String {
    let (open_m, close_m) = trust_markers(project_root);
    let project_str = project_root.to_string_lossy().replace('\\', "\\\\");
    format!(
        "{open_m}\n\
         [projects.\"{project_str}\"]\n\
         trust_level = \"trusted\"\n\
         {close_m}\n"
    )
}

/// `os.path.normpath` POSIX simplificado: colapsa slashes duplicados,
/// resuelve `.` y `..` internos, preserva el slash inicial.
fn posix_normpath(path: &str) -> String {
    let absolute = path.starts_with('/');
    let mut parts: Vec<&str> = Vec::new();
    for seg in path.split('/') {
        match seg {
            "" | "." => {}
            ".." => {
                if let Some(last) = parts.last() {
                    if *last != ".." {
                        parts.pop();
                        continue;
                    }
                }
                if !absolute {
                    parts.push("..");
                }
            }
            other => parts.push(other),
        }
    }
    let joined = parts.join("/");
    if absolute {
        format!("/{joined}")
    } else if joined.is_empty() {
        ".".to_string()
    } else {
        joined
    }
}

/// Normalización de comparación: `normcase(normpath(x))`. En Linux
/// `normcase` es identidad (documentado en el docstring de Python).
fn normalize_key(path: &str) -> String {
    posix_normpath(path)
}

/// `_global_has_foreign_trust`: ¿existe ya `[projects."este path"]` FUERA de
/// nuestros marcadores? Replica la regex
/// `(?mi)^\s*\[projects\.(?:"([^"]*)"|'([^']*)')\]\s*$` con parsing por línea.
fn global_has_foreign_trust(content: &str, project_root: &Path) -> bool {
    let target = normalize_key(&project_root.to_string_lossy());
    for line in content.split('\n') {
        let trimmed = line.trim();
        if !trimmed.to_lowercase().starts_with("[projects.") {
            continue;
        }
        let Some(rest) = trimmed.get("[projects.".len()..) else {
            continue;
        };
        // Debe terminar en ']' tras el key citado.
        let Some(inner) = rest.strip_suffix(']') else {
            continue;
        };
        let key: Option<&str> = if let Some(k) = inner.strip_prefix('"') {
            // [^"]*: sin comillas dobles dentro.
            if k.contains('"') {
                None
            } else {
                Some(k)
            }
        } else if let Some(k) = inner.strip_prefix('\'') {
            if k.contains('\'') {
                None
            } else {
                Some(k)
            }
        } else {
            None
        };
        let Some(key) = key else { continue };
        // Basic strings escapan backslashes (\\ -> \); los literales no.
        let key_unescaped = key.replace("\\\\", "\\");
        if normalize_key(&key_unescaped) == target {
            return true;
        }
    }
    false
}

/// `_merge_trust_into_global`: merge no-destructivo del trust de ESTE
/// proyecto. Reemplaza SOLO el bloque entre nuestros marcadores (que según
/// el patrón incluye un `\n` final opcional); si ya hay trust externo del
/// mismo path, no duplica la tabla TOML.
fn merge_trust_into_global(existing: &str, project_root: &Path) -> String {
    let (open_m, close_m) = trust_markers(project_root);
    let spans = find_block_spans(existing, &open_m, &close_m, true);
    let ours_present = !spans.is_empty();

    // without_ours = pattern.sub("", existing)
    let mut without_ours = String::with_capacity(existing.len());
    let mut last = 0usize;
    for span in &spans {
        without_ours.push_str(&existing[last..span.start]);
        last = span.end;
    }
    without_ours.push_str(&existing[last..]);

    if global_has_foreign_trust(&without_ours, project_root) {
        // Ya confiado por el usuario/Codex: no duplicar.
        return if ours_present {
            without_ours
        } else {
            existing.to_string()
        };
    }

    let trust_block = build_cortex_trust_block(project_root);
    if ours_present {
        // pattern.sub(lambda _: trust_block.trim() + "\n", existing)
        let replacement = format!("{}\n", trust_block.trim());
        let mut out = String::with_capacity(existing.len());
        let mut last = 0usize;
        for span in &spans {
            out.push_str(&existing[last..span.start]);
            out.push_str(&replacement);
            last = span.end;
        }
        out.push_str(&existing[last..]);
        return out;
    }
    let sep = if existing.is_empty() {
        ""
    } else if existing.ends_with('\n') {
        "\n"
    } else {
        "\n\n"
    };
    format!("{existing}{sep}{trust_block}")
}

/// `Path.resolve()` de Python (best-effort): canonicaliza si existe.
fn resolve_path(p: &Path) -> PathBuf {
    std::fs::canonicalize(p).unwrap_or_else(|_| p.to_path_buf())
}

pub struct CodexAdapter;

impl CodexAdapter {
    #[allow(dead_code)]
    pub fn new() -> Self {
        CodexAdapter
    }

    /// `detect_installation` override de Python: ¿binario `codex` en PATH?
    pub fn detect_installation(&self) -> bool {
        which_codex()
    }
}

fn which_codex() -> bool {
    if let Some(path_env) = std::env::var_os("PATH") {
        for dir in std::env::split_paths(&path_env) {
            let candidate = dir.join("codex");
            if candidate.is_file() {
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    if let Ok(md) = std::fs::metadata(&candidate) {
                        if md.permissions().mode() & 0o111 != 0 {
                            return true;
                        }
                    }
                }
                #[cfg(not(unix))]
                {
                    return true;
                }
            }
        }
    }
    false
}

impl Default for CodexAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl IdeAdapter for CodexAdapter {
    fn name(&self) -> &'static str {
        "codex"
    }

    fn display_name(&self) -> &'static str {
        "Codex"
    }

    fn config_paths(&self, _ctx: &IdeCtx) -> Vec<(String, PathBuf)> {
        vec![
            ("agents_md".into(), PathBuf::from("AGENTS.md")), // project root, NOT .codex/
            (
                "config_toml".into(),
                Path::new(".codex").join("config.toml"),
            ),
        ]
    }

    /// Inyecta AGENTS.md en project root con las instrucciones del flujo
    /// Cortex. ``prompts`` se acepta por uniformidad pero NO se usa: Codex
    /// no soporta subagents ni skills personalizados (del prompts, nada).
    fn inject_profiles(
        &self,
        ctx: &IdeCtx,
        _prompts: &crate::ide::Prompts,
    ) -> Result<Vec<String>, String> {
        let agents_md_path = ctx.project_root.join("AGENTS.md");
        if let Some(parent) = agents_md_path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("mkdir {}: {e}", parent.display()))?;
        }

        let autogen_header = generate_autogen_header(
            ctx,
            &[
                ".cortex/skills/cortex-sync.md",
                ".cortex/skills/cortex-SDDwork.md",
                ".cortex/skills/cortex-documenter.md",
                ".cortex/subagents/cortex-code-explorer.md",
                ".cortex/subagents/cortex-code-implementer.md",
                ".cortex/subagents/cortex-code-designer.md",
                ".cortex/subagents/cortex-documenter.md",
            ],
            "codex",
        );
        let cortex_block = build_cortex_agents_section(&autogen_header);

        let mut existing = String::new();
        if agents_md_path.exists() {
            backup_file(ctx, &agents_md_path);
            existing = std::fs::read_to_string(&agents_md_path)
                .map_err(|e| format!("read {}: {e}", agents_md_path.display()))?;
        }

        let new_content = replace_or_append_cortex_section(&existing, &cortex_block);
        std::fs::write(&agents_md_path, new_content)
            .map_err(|e| format!("write {}: {e}", agents_md_path.display()))?;
        Ok(vec![agents_md_path.to_string_lossy().into_owned()])
    }

    /// Dos escrituras, ambas merge no-destructivo:
    /// 1. `<proyecto>/.codex/config.toml` — registro project-scoped del MCP.
    /// 2. `~/.codex/config.toml` (global) — marca el proyecto como trusted
    ///    (sin esto Codex descarta en silencio la capa project-local).
    fn inject_mcp(&self, ctx: &IdeCtx) -> Result<Vec<String>, String> {
        let mut written: Vec<String> = Vec::new();

        // 1. Registro project-scoped del MCP (mono-repo).
        let config_path = ctx.project_root.join(".codex").join("config.toml");
        std::fs::create_dir_all(config_path.parent().expect("config parent"))
            .map_err(|e| format!("mkdir .codex: {e}"))?;
        let cortex_toml = build_cortex_toml_block(ctx.project_root);
        let mut existing = String::new();
        if config_path.exists() {
            backup_file(ctx, &config_path);
            existing = std::fs::read_to_string(&config_path)
                .map_err(|e| format!("read {}: {e}", config_path.display()))?;
        }
        std::fs::write(
            &config_path,
            replace_or_append_cortex_toml_block(&existing, &cortex_toml),
        )
        .map_err(|e| format!("write {}: {e}", config_path.display()))?;
        written.push(config_path.to_string_lossy().into_owned());

        // 2. Trust del proyecto en el config global.
        let global_path = codex_global_config_path(ctx);
        let global_existing = if global_path.exists() {
            std::fs::read_to_string(&global_path)
                .map_err(|e| format!("read {}: {e}", global_path.display()))?
        } else {
            String::new()
        };
        let new_global = merge_trust_into_global(&global_existing, ctx.project_root);
        if new_global != global_existing {
            std::fs::create_dir_all(global_path.parent().expect("global parent"))
                .map_err(|e| format!("mkdir ~/.codex: {e}"))?;
            if global_path.exists() {
                backup_file(ctx, &global_path);
            }
            std::fs::write(&global_path, new_global)
                .map_err(|e| format!("write {}: {e}", global_path.display()))?;
            written.push(global_path.to_string_lossy().into_owned());
            print_trust_notice(ctx.project_root, &global_path);
        }

        Ok(written)
    }

    /// Remueve los bloques Cortex marcados (conservador: nunca borra archivos
    /// completos con contenido ajeno), revierte la entrada de trust de ESTE
    /// proyecto en el config global y limpia artefactos legacy pre-Fase 4.
    /// Idempotente.
    fn uninstall(&self, ctx: &IdeCtx) -> Vec<String> {
        let mut removed: Vec<String> = Vec::new();
        let cwd = resolve_path(ctx.project_root);

        // 1. Limpiar bloque Cortex de AGENTS.md en project root.
        // OJO paridad: Python computa ``pattern.sub("")`` SIN condicionar a
        // que existan bloques — con un archivo sin bloques pero sin `\n`
        // final igual lo reescribe normalizado (rstrip + "\n").
        let agents_md = cwd.join("AGENTS.md");
        if agents_md.exists() {
            if let Ok(existing) = std::fs::read_to_string(&agents_md) {
                let cleaned = strip_marked_blocks(
                    &existing,
                    CORTEX_AGENTS_MD_MARKER_OPEN,
                    CORTEX_AGENTS_MD_MARKER_CLOSE,
                );
                let cleaned = format!("{}\n", cleaned.trim_end());
                if cleaned != existing {
                    if !cleaned.trim().is_empty() {
                        let _ = std::fs::write(&agents_md, cleaned);
                        removed.push(format!("{} (Cortex section removed)", agents_md.display()));
                    } else {
                        let _ = std::fs::remove_file(&agents_md);
                        removed.push(agents_md.to_string_lossy().into_owned());
                    }
                }
            }
        }

        // 2. Limpiar bloque Cortex de .codex/config.toml (ídem nota 1).
        let config_toml = cwd.join(".codex").join("config.toml");
        if config_toml.exists() {
            if let Ok(existing) = std::fs::read_to_string(&config_toml) {
                let cleaned = strip_marked_blocks(
                    &existing,
                    CORTEX_TOML_MARKER_OPEN,
                    CORTEX_TOML_MARKER_CLOSE,
                );
                let cleaned = format!("{}\n", cleaned.trim_end());
                if cleaned != existing {
                    if !cleaned.trim().is_empty() {
                        let _ = std::fs::write(&config_toml, cleaned);
                        removed.push(format!(
                            "{} (Cortex MCP block removed)",
                            config_toml.display()
                        ));
                    } else {
                        let _ = std::fs::remove_file(&config_toml);
                        removed.push(config_toml.to_string_lossy().into_owned());
                    }
                }
            }
        }

        // 2b. Revertir la entrada de trust de ESTE proyecto en el config
        // global (ownership-aware: solo el bloque entre NUESTROS marcadores
        // para este path). Backup antes de reescribir, como en Python.
        let global_path = codex_global_config_path(ctx);
        if global_path.exists() {
            if let Ok(existing) = std::fs::read_to_string(&global_path) {
                let (open_m, close_m) = trust_markers(&cwd);
                let cleaned = strip_marked_blocks(&existing, &open_m, &close_m);
                if cleaned != existing {
                    let _ = backup_file(ctx, &global_path);
                    let _ = std::fs::write(&global_path, format!("{}\n", cleaned.trim_end()));
                    removed.push(format!(
                        "{} (Cortex trust entry removed)",
                        global_path.display()
                    ));
                }
            }
        }

        // 3. Limpieza de artefactos legacy del adapter pre-Fase 4 (Codex
        // nunca los leyó, pero pueden quedar de instalaciones viejas).
        let legacy_paths = [
            cwd.join(".codex").join("AGENTS.md"),
            cwd.join(".codex").join("mcp.json"),
            cwd.join(".codex")
                .join("agents")
                .join("cortex-code-explorer.md"),
            cwd.join(".codex")
                .join("agents")
                .join("cortex-code-implementer.md"),
            cwd.join(".codex")
                .join("agents")
                .join("cortex-documenter.md"),
            cwd.join(".codex").join("skills").join("cortex-sync.md"),
            cwd.join(".codex").join("skills").join("cortex-sddwork.md"),
        ];
        for legacy in legacy_paths {
            if legacy.exists() {
                let _ = std::fs::remove_file(&legacy);
                removed.push(legacy.to_string_lossy().into_owned());
            }
        }

        // Drop empty Cortex-managed subdirectories.
        for subdir in [
            cwd.join(".codex").join("agents"),
            cwd.join(".codex").join("skills"),
        ] {
            if subdir.exists() {
                let empty = std::fs::read_dir(&subdir).map(|d| d.count()).unwrap_or(1) == 0;
                if empty {
                    let _ = std::fs::remove_dir(&subdir);
                    removed.push(subdir.to_string_lossy().into_owned());
                }
            }
        }

        removed
    }
}

/// `_build_cortex_agents_section`: bloque Cortex completo para AGENTS.md
/// (modelo triádico de anchors, single-agent sequential).
fn build_cortex_agents_section(autogen_header: &str) -> String {
    let mut s = String::with_capacity(8192);
    s.push_str(CORTEX_AGENTS_MD_MARKER_OPEN);
    s.push('\n');
    s.push_str("<!--\n");
    s.push_str(autogen_header.trim());
    s.push_str("\n-->\n\n");
    s.push_str(AGENTS_MD_BODY);
    s.push_str(CORTEX_AGENTS_MD_MARKER_CLOSE);
    s.push('\n');
    s
}

/// `_print_trust_notice`: aviso explícito y auditable en stdout.
fn print_trust_notice(project_root: &Path, global_path: &Path) {
    println!(
        "\n[Cortex][Codex] Proyecto marcado como 'trusted' en Codex:\n    {}\n  escrito en: {}\n  Necesario para que Codex cargue el MCP server (sin trust, Codex\n  ignora la capa project-local .codex/). Esto habilita la capa\n  project-local (config/hooks/exec policies) SOLO para este\n  proyecto. Se revierte con 'cortex uninstall --ide codex'.\n",
        project_root.display(),
        global_path.display()
    );
}
