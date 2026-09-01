//! Porteo de cortex/ide/canonical_tools.py (P8d).
//!
//! Vocabulario canónico de tools de Cortex y matriz de traducción por IDE.
//! Los prompts canónicos referencian tools por su nombre canónico; cada
//! adapter traduce esos nombres al formato del IDE SOLO en el frontmatter
//! `tools:` (nunca se reescribe el cuerpo del prompt).
//!
//! Decisiones firmadas 2026-05-15 (MATRIZ-NATIVA-IDES.md §4):
//! - `claude_code`: PascalCase nativo (`Read`, `Write`) + prefijo
//!   `mcp__cortex__` para tools MCP.
//! - `opencode`: lowercase nativo (`read`, `write`); los tools MCP se
//!   descubren dinámicamente al conectarse al server → su traducción es
//!   `None` y el adapter los OMITE del frontmatter.
//! - `codex`/`pi` y los community/experimental NO están validados contra
//!   docs oficiales: pedir su traducción devuelve
//!   [`TranslateError::UnvalidatedIde`] (intencional, según lo firmado).

/// Error espejo de `UnknownCanonicalToolError` / `UnvalidatedIDEError`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TranslateError {
    /// Tool canónico desconocido (espejo de `UnknownCanonicalToolError`).
    UnknownCanonicalTool(String),
    /// IDE no validado contra docs oficiales (espejo de `UnvalidatedIDEError`).
    UnvalidatedIde(String),
}

impl std::fmt::Display for TranslateError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            TranslateError::UnknownCanonicalTool(c) => write!(
                f,
                "Canonical tool '{c}' is not in the canonical vocabulary. \
                 Known tools: {}",
                format_sorted_known_tools()
            ),
            TranslateError::UnvalidatedIde(ide) => write!(
                f,
                "IDE '{ide}' is not validated against official docs in this \
                 plan. Validated IDEs: {}. See \
                 docs/multi-ide-mcp-hardening/MATRIZ-NATIVA-IDES.md section 4.",
                format_validated_ides()
            ),
        }
    }
}

impl std::error::Error for TranslateError {}

/// Vocabulario canónico completo, en el orden de declaración del Literal de
/// Python (`CanonicalTool`). `cortex_delegate_task` fue eliminado en Fase 5
/// del plan multi-IDE (la delegación a subagents es responsabilidad nativa
/// del IDE, no del MCP server).
pub const CANONICAL_TOOLS: &[&str] = &[
    // Filesystem operations
    "read_file",
    "write_file",
    "edit_file",
    // Shell
    "execute_command",
    // Cortex MCP tools
    "cortex_search",
    "cortex_context",
    "cortex_save_session",
    "cortex_validate_handoff",
    "cortex_verify_session_claims",
    "cortex_sync_ticket",
    "cortex_create_spec",
    "cortex_emit_proposal",
    "cortex_documenter_briefing",
    "cortex_close_session",
    "cortex_write_doc",
    "cortex_self_review_note",
    "cortex_ping",
    // Pluggable Middle (Phase 00/01) — Session primitive tools.
    "cortex_session_open",
    "cortex_session_checkpoint",
    "cortex_session_close",
    "cortex_session_status",
    "cortex_session_list",
    "cortex_finish_session",
    // Pluggable Middle (Phase 08 / T8.2) — Managed quality gates.
    "cortex_review_checkpoint",
    // Pluggable Middle (Phase 09.B) — Design step (cortex-code-designer).
    "write_design_note_canonical",
    // Pluggable Middle (Phase 09.C) — Tasks granulares.
    "cortex_session_task_list",
    "cortex_session_task_update",
];

/// IDEs con traducción VALIDADA contra documentación oficial 2026 y que
/// inyectan frontmatter `tools:` traducible (orden del Literal de Python).
pub const VALIDATED_IDES: &[&str] = &["claude_code", "opencode"];

/// Índice del IDE en la fila interna ([0] = claude_code, [1] = opencode).
fn ide_index(ide: &str) -> Option<usize> {
    match ide {
        "claude_code" => Some(0),
        "opencode" => Some(1),
        _ => None,
    }
}

/// Nombre nativo claude_code para un tool MCP (`mcp__cortex__<tool>`).
/// El harness de Claude Code prefija `mcp__<server>__` cuando el frontmatter
/// restringe tools; con restricción deben listarse explícitamente.
fn claude_mcp_native(canonical: &str) -> Option<&'static str> {
    match canonical {
        "cortex_search" => Some("mcp__cortex__cortex_search"),
        "cortex_context" => Some("mcp__cortex__cortex_context"),
        "cortex_save_session" => Some("mcp__cortex__cortex_save_session"),
        "cortex_validate_handoff" => Some("mcp__cortex__cortex_validate_handoff"),
        "cortex_verify_session_claims" => Some("mcp__cortex__cortex_verify_session_claims"),
        "cortex_sync_ticket" => Some("mcp__cortex__cortex_sync_ticket"),
        "cortex_create_spec" => Some("mcp__cortex__cortex_create_spec"),
        "cortex_emit_proposal" => Some("mcp__cortex__cortex_emit_proposal"),
        "cortex_documenter_briefing" => Some("mcp__cortex__cortex_documenter_briefing"),
        "cortex_close_session" => Some("mcp__cortex__cortex_close_session"),
        "cortex_write_doc" => Some("mcp__cortex__cortex_write_doc"),
        "cortex_self_review_note" => Some("mcp__cortex__cortex_self_review_note"),
        "cortex_ping" => Some("mcp__cortex__cortex_ping"),
        "cortex_session_open" => Some("mcp__cortex__cortex_session_open"),
        "cortex_session_checkpoint" => Some("mcp__cortex__cortex_session_checkpoint"),
        "cortex_session_close" => Some("mcp__cortex__cortex_session_close"),
        "cortex_session_status" => Some("mcp__cortex__cortex_session_status"),
        "cortex_session_list" => Some("mcp__cortex__cortex_session_list"),
        "cortex_finish_session" => Some("mcp__cortex__cortex_finish_session"),
        "cortex_review_checkpoint" => Some("mcp__cortex__cortex_review_checkpoint"),
        "write_design_note_canonical" => Some("mcp__cortex__write_design_note_canonical"),
        "cortex_session_task_list" => Some("mcp__cortex__cortex_session_task_list"),
        "cortex_session_task_update" => Some("mcp__cortex__cortex_session_task_update"),
        _ => None,
    }
}

/// Fila de la matriz `_TOOL_NAME_BY_IDE`: traducción por IDE validado.
/// `[claude_code, opencode]`; `None` = omitir del frontmatter.
fn row(canonical: &str) -> Option<[Option<&'static str>; 2]> {
    match canonical {
        // ---------------- Filesystem ----------------
        "read_file" => Some([Some("Read"), Some("read")]),
        "write_file" => Some([Some("Write"), Some("write")]),
        "edit_file" => Some([Some("Edit"), Some("edit")]),
        "execute_command" => Some([Some("Bash"), Some("bash")]),
        // ---------------- Cortex MCP ----------------
        // opencode: siempre None — los MCP tools se descubren dinámicamente
        // y declararlos en frontmatter es error (MATRIZ-NATIVA-IDES.md §1.2).
        other => claude_mcp_native(other).map(|n| [Some(n), None]),
    }
}

/// Traduce un tool canónico al nombre nativo del IDE.
///
/// Devuelve `Ok(None)` cuando el IDE acepta el tool pero NO lo declara en
/// frontmatter (caso clásico: MCP tools en opencode).
///
/// Errores (espejo exacto de las excepciones de Python): tool no canónico →
/// [`TranslateError::UnknownCanonicalTool`]; IDE no validado →
/// [`TranslateError::UnvalidatedIde`].
pub fn translate(canonical: &str, ide: &str) -> Result<Option<String>, TranslateError> {
    // Python valida primero la existencia del tool, después el IDE.
    if !CANONICAL_TOOLS.contains(&canonical) {
        return Err(TranslateError::UnknownCanonicalTool(canonical.to_string()));
    }
    let idx = ide_index(ide).ok_or_else(|| TranslateError::UnvalidatedIde(ide.to_string()))?;
    let natives = row(canonical).expect("tool canónico siempre tiene fila en la matriz");
    Ok(natives[idx].map(str::to_string))
}

/// Traduce una lista de tools canónicos al formato del IDE.
///
/// Omite los tools cuya traducción es `None`. Falla ante un tool no canónico
/// o un IDE no validado (espejo de las excepciones de Python).
pub fn translate_list(tools: &[String], ide: &str) -> Result<Vec<String>, TranslateError> {
    let mut out = Vec::new();
    for t in tools {
        if let Some(name) = translate(t, ide)? {
            out.push(name);
        }
    }
    Ok(out)
}

/// Devuelve la lista de IDEs validados contra docs oficiales 2026.
pub fn get_validated_ides() -> Vec<String> {
    VALIDATED_IDES.iter().map(|s| (*s).to_string()).collect()
}

/// Devuelve la lista completa de tools canónicos (orden de declaración).
pub fn get_canonical_tools() -> Vec<String> {
    CANONICAL_TOOLS.iter().map(|s| (*s).to_string()).collect()
}

/// `[...]` estilo repr de lista ordenada de Python para el mensaje de error.
fn format_sorted_known_tools() -> String {
    let mut names: Vec<&str> = CANONICAL_TOOLS.to_vec();
    names.sort_unstable();
    let items: Vec<String> = names.iter().map(|n| format!("'{n}'")).collect();
    format!("[{}]", items.join(", "))
}

/// `['claude_code', 'opencode']` estilo Python para el mensaje de error.
fn format_validated_ides() -> String {
    let items: Vec<String> = VALIDATED_IDES.iter().map(|n| format!("'{n}'")).collect();
    format!("[{}]", items.join(", "))
}
