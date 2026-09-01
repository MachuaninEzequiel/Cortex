//! Handlers MCP in-process de la familia autopilot — porte de
//! `cortex/autopilot/mcp_tools.py` (Cierre Obra 07 T3, diferidos por T1).
//!
//! Tools: `cortex_autopilot_{start,preflight,checkpoint,finish,status}`.
//!
//! El backend ([`AutopilotBackend`]) reproduce el servicio real
//! (producción: cortex-autopilot::service sobre SessionService nativo;
//! gates: stubs deterministas). El FORMATEO de texto vive acá porque es
//! parte del wire-format byte-a-byte del tool: mismos literales, mismo
//! orden de líneas y `_format_error` por tipo de excepción del oráculo.

use serde_json::Value;

/// Espejo de las excepciones relevantes para `_format_error`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AutopilotToolError {
    /// `NoActiveSessionError`.
    NoActiveSession(String),
    /// `cortex.session.errors.SessionNotFound`.
    SessionNotFound(String),
    /// `AutopilotError` genérico.
    Autopilot(String),
    /// Cualquier otra excepción: `{type}: {message}`.
    Other { kind: String, message: String },
}

impl std::fmt::Display for AutopilotToolError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NoActiveSession(m) | Self::SessionNotFound(m) | Self::Autopilot(m) => {
                f.write_str(m)
            }
            Self::Other { kind, message } => write!(f, "{kind}: {message}"),
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct StartData {
    pub session_id: String,
    pub mode: String,
    pub status: String,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, Default)]
pub struct PreflightData {
    pub task_type: String,
    pub confidence: f64,
    pub reason: String,
    pub suggested_complexity: String,
}

#[derive(Debug, Clone, Default)]
pub struct CheckpointData {
    pub session_id: String,
    pub total_checkpoints: usize,
    pub status: String,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, Default)]
pub struct FinishData {
    pub session_id: String,
    pub status: String,
    pub documented: bool,
    pub blocked: bool,
    pub blocked_reason: String,
    pub session_note_path: Option<String>,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, Default)]
pub struct StatusData {
    pub active: bool,
    pub session_id: String,
    pub status: String,
    /// None ⇒ línea "Mode: unknown".
    pub mode: Option<String>,
    pub inferred_mode: String,
    pub checkpoint_count: usize,
    pub start_branch: String,
}

/// Backend in-process de la familia autopilot.
pub trait AutopilotBackend {
    fn start(&mut self, mode: Option<&str>) -> Result<StartData, AutopilotToolError>;
    fn preflight(
        &mut self,
        user_request: Option<&str>,
        changed_files: &[String],
        git_diff_stat: Option<&str>,
    ) -> Result<PreflightData, AutopilotToolError>;
    #[allow(clippy::too_many_arguments)]
    fn checkpoint(
        &mut self,
        source: &str,
        verified_claims: Vec<String>,
        unverified_claims: Vec<String>,
        artifacts_touched: Vec<String>,
        note: &str,
        files_in_scope: Option<Vec<String>>,
    ) -> Result<CheckpointData, AutopilotToolError>;
    fn finish(
        &mut self,
        session_id: Option<&str>,
        auto: bool,
        intent: &str,
        reason: &str,
    ) -> Result<FinishData, AutopilotToolError>;
    fn status(&mut self, session_id: Option<&str>) -> Result<StatusData, AutopilotToolError>;
}

// ── Extracción de argumentos (espejo de _opt/_str_list/_parse_mode) ─────────

fn opt<'a>(args: &'a Value, key: &str) -> Option<&'a Value> {
    args.get(key)
}

fn opt_str_default(args: &Value, key: &str, default: &str) -> String {
    match opt(args, key) {
        None | Some(Value::Null) => default.to_string(),
        Some(v) => py_str(v),
    }
}

fn opt_bool(args: &Value, key: &str) -> bool {
    match opt(args, key) {
        None => false,
        Some(v) => py_truthy(v),
    }
}

/// `bool(v)` de Python sobre valores JSON.
fn py_truthy(v: &Value) -> bool {
    match v {
        Value::Null => false,
        Value::Bool(b) => *b,
        Value::Number(n) => n.as_f64().map(|f| f != 0.0).unwrap_or(false),
        Value::String(s) => !s.is_empty(),
        Value::Array(a) => !a.is_empty(),
        Value::Object(o) => !o.is_empty(),
    }
}

/// `str(v)` de Python sobre valores JSON (escalares; contenedores →
/// representación compacta, fuera de los contratos gateados).
fn py_str(v: &Value) -> String {
    match v {
        Value::String(s) => s.clone(),
        Value::Bool(true) => "True".to_string(),
        Value::Bool(false) => "False".to_string(),
        Value::Number(n) => n.to_string(),
        Value::Array(_) | Value::Object(_) => v.to_string(),
        Value::Null => "None".to_string(),
    }
}

/// `_str_list`: no-lista ⇒ []; filtra None; str() por elemento.
fn str_list(args: &Value, key: &str) -> Vec<String> {
    match opt(args, key) {
        Some(Value::Array(items)) => items.iter().filter(|v| !v.is_null()).map(py_str).collect(),
        Some(Value::Null) | None => vec![],
        Some(_) => vec![],
    }
}

fn opt_string(args: &Value, key: &str) -> Option<String> {
    match opt(args, key) {
        None | Some(Value::Null) => None,
        Some(v) => Some(py_str(v)),
    }
}

fn parse_mode(raw: Option<&str>) -> Result<Option<String>, AutopilotToolError> {
    match raw {
        None => Ok(None),
        Some(m @ ("observe" | "assist" | "autopilot")) => Ok(Some(m.to_string())),
        Some(other) => Err(AutopilotToolError::Autopilot(format!(
            "unknown mode '{}'; valid: observe, assist, autopilot",
            other
        ))),
    }
}

/// `_format_error(tool_name, exc)`.
fn format_error(tool_name: &str, exc: &AutopilotToolError) -> String {
    match exc {
        AutopilotToolError::NoActiveSession(msg) => format!("Error ({tool_name}): {msg}"),
        AutopilotToolError::SessionNotFound(msg) => {
            format!("Error ({tool_name}): Session not found — {msg}")
        }
        AutopilotToolError::Autopilot(msg) => format!("Error ({tool_name}): {msg}"),
        AutopilotToolError::Other { kind, message } => {
            format!("Error ({tool_name}): {kind}: {message}")
        }
    }
}

fn join_warnings(warnings: &[String]) -> String {
    warnings.join("; ")
}

// ── Handlers (texto byte-parity con mcp_tools.py) ───────────────────────────

pub fn autopilot_start_text(b: &mut dyn AutopilotBackend, args: &Value) -> Result<String, String> {
    let mode = match parse_mode(opt_string(args, "mode").as_deref()) {
        Ok(m) => m,
        Err(exc) => return Ok(format_error("cortex_autopilot_start", &exc)),
    };
    match b.start(mode.as_deref()) {
        Ok(out) => {
            let mut lines = vec![
                format!("Session adopted: {}", out.session_id),
                format!("Mode: {} | Status: {}", out.mode, out.status),
            ];
            if !out.warnings.is_empty() {
                lines.push(format!("Warnings: {}", join_warnings(&out.warnings)));
            }
            Ok(lines.join("\n"))
        }
        Err(exc) => Ok(format_error("cortex_autopilot_start", &exc)),
    }
}

pub fn autopilot_preflight_text(
    b: &mut dyn AutopilotBackend,
    args: &Value,
) -> Result<String, String> {
    let changed_files = str_list(args, "changed_files");
    let result = b.preflight(
        opt_string(args, "user_request").as_deref(),
        &changed_files,
        opt_string(args, "git_diff_stat").as_deref(),
    );
    match result {
        Ok(d) => Ok(format!(
            "Preflight (dry-run): {} (confidence={:.2}, complexity={})\nReason: {}",
            d.task_type, d.confidence, d.suggested_complexity, d.reason
        )),
        Err(exc) => Ok(format_error("cortex_autopilot_preflight", &exc)),
    }
}

pub fn autopilot_checkpoint_text(
    b: &mut dyn AutopilotBackend,
    args: &Value,
) -> Result<String, String> {
    let files_in_scope = {
        let list = str_list(args, "files_in_scope");
        if list.is_empty() {
            None
        } else {
            Some(list)
        }
    };
    let result = b.checkpoint(
        &opt_str_default(args, "source", "manual"),
        str_list(args, "verified_claims"),
        str_list(args, "unverified_claims"),
        str_list(args, "artifacts_touched"),
        &opt_str_default(args, "note", ""),
        files_in_scope,
    );
    match result {
        Ok(out) => {
            let mut lines = vec![
                format!("Checkpoint recorded for {}", out.session_id),
                format!(
                    "Total checkpoints: {} | Status: {}",
                    out.total_checkpoints, out.status
                ),
            ];
            if !out.warnings.is_empty() {
                lines.push(format!("Warnings: {}", join_warnings(&out.warnings)));
            }
            Ok(lines.join("\n"))
        }
        Err(exc) => Ok(format_error("cortex_autopilot_checkpoint", &exc)),
    }
}

pub fn autopilot_finish_text(b: &mut dyn AutopilotBackend, args: &Value) -> Result<String, String> {
    let result = b.finish(
        opt_string(args, "session_id").as_deref(),
        opt_bool(args, "auto"),
        &opt_str_default(args, "intent", "closed"),
        &opt_str_default(args, "reason", ""),
    );
    match result {
        Ok(out) if out.blocked => Ok(format!("Finish blocked by policy: {}", out.blocked_reason)),
        Ok(out) => {
            let mut lines = vec![
                format!("Finish: {}", out.session_id),
                format!(
                    "Status: {} | Documented: {}",
                    out.status,
                    if out.documented { "True" } else { "False" }
                ),
            ];
            if let Some(path) = &out.session_note_path {
                lines.push(format!("Note: {path}"));
            }
            if !out.warnings.is_empty() {
                lines.push(format!("Warnings: {}", join_warnings(&out.warnings)));
            }
            Ok(lines.join("\n"))
        }
        Err(exc) => Ok(format_error("cortex_autopilot_finish", &exc)),
    }
}

pub fn autopilot_status_text(b: &mut dyn AutopilotBackend, args: &Value) -> Result<String, String> {
    match b.status(opt_string(args, "session_id").as_deref()) {
        Ok(out) if !out.active => Ok("No active Autopilot session found.".to_string()),
        Ok(out) => Ok(format!(
            "Session: {}\nStatus: {} | Mode: {}\nInferred mode: {}\nCheckpoints: {} | Branch: {}",
            out.session_id,
            out.status,
            out.mode.unwrap_or_else(|| "unknown".to_string()),
            out.inferred_mode,
            out.checkpoint_count,
            out.start_branch
        )),
        Err(exc) => Ok(format_error("cortex_autopilot_status", &exc)),
    }
}
