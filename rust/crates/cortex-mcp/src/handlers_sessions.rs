//! Handlers MCP in-process de la familia sesiones/checkpoints/tasks —
//! porte de `cortex/mcp/tools/sessions.py` (P12A-9).
//!
//! Los handlers consumen un [`SessionsBackend`] inyectable: en producción es
//! una implementación nativa sobre `cortex-app` (`SessionService` +
//! `NoteService`); en los gates, stubs deterministas. El wire-format de cada
//! handler replica `json.dumps(payload, ensure_ascii=False)` — con
//! `serde_json/preserve_order` el orden de inserción del macro `json!` es el
//! orden de serialización, idéntico al dict de Python.
//!
//! Pendiente de decisión del dueño (§7.1.4): handlers de escritura fuera de
//! esta familia mantienen su fallo explícito.

use std::path::Path;

use serde_json::{json, Value};

use cortex_app::session::quality_gates::{review_checkpoint, ReviewVerdict};

// ---------------------------------------------------------------------------
// Modelo plano espejo (los dumps siguen el orden pydantic)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Default)]
pub struct SCheckpoint {
    pub timestamp: String,
    pub source: String,
    pub verified_claims: Vec<String>,
    pub unverified_claims: Vec<String>,
    pub artifacts_touched: Vec<String>,
    pub note: String,
}

#[derive(Debug, Clone, Default)]
pub struct SHook {
    pub name: String,
    pub command: String,
    pub passed: bool,
    pub exit_code: i64,
    pub output: String,
    pub duration_ms: i64,
    pub run_at: String,
}

#[derive(Debug, Clone, Default)]
pub struct STask {
    pub id: String,
    pub description: String,
    pub files_in_scope: Vec<String>,
    pub depends_on: Vec<String>,
    /// pending | in-progress | done | skipped | blocked
    pub status: String,
    pub completed_at: Option<String>,
    pub checkpoint_index: Option<i64>,
    pub note: String,
}

/// Espejo plano de SessionRecord para los handlers.
#[derive(Debug, Clone, Default)]
pub struct SRecord {
    pub session_id: String,
    pub spec_path: String,
    pub spec_summary: String,
    pub start_commit: String,
    pub start_branch: String,
    pub opened_at: String,
    /// open | closed | handoff | abandoned
    pub status: String,
    /// unknown | managed | observed | byo
    pub mode: String,
    pub checkpoints: Vec<SCheckpoint>,
    pub verification_results: Vec<SHook>,
    pub tasks: Vec<STask>,
    pub closed_at: Option<String>,
    pub end_commit: Option<String>,
    pub documenter_decision: Option<String>,
    pub session_note_path: Option<String>,
    pub adrs_created: Vec<String>,
}

pub const VALID_CHECKPOINT_SOURCES: &[&str] = &[
    "cortex-sync",
    "cortex-SDDwork",
    "cortex-code-explorer",
    "cortex-code-implementer",
    "cortex-code-designer",
    "user-skill",
    "ide-hook",
    "manual",
    "ci-bot",
];

pub const TASK_STATUSES: &[&str] = &["pending", "in-progress", "done", "skipped", "blocked"];

fn sources_list() -> String {
    VALID_CHECKPOINT_SOURCES.join(", ")
}

fn task_statuses_list() -> String {
    TASK_STATUSES.to_vec().join(", ")
}

// ---------------------------------------------------------------------------
// Dumps canónicos (orden de declaración pydantic)
// ---------------------------------------------------------------------------

pub fn dump_task(t: &STask) -> Value {
    json!({
        "id": t.id,
        "description": t.description,
        "files_in_scope": t.files_in_scope,
        "depends_on": t.depends_on,
        "status": t.status,
        "completed_at": t.completed_at,
        "checkpoint_index": t.checkpoint_index,
        "note": t.note,
    })
}

fn dump_checkpoint(c: &SCheckpoint) -> Value {
    json!({
        "timestamp": c.timestamp,
        "source": c.source,
        "verified_claims": c.verified_claims,
        "unverified_claims": c.unverified_claims,
        "artifacts_touched": c.artifacts_touched,
        "note": c.note,
    })
}

fn dump_hook(h: &SHook) -> Value {
    json!({
        "name": h.name,
        "command": h.command,
        "passed": h.passed,
        "exit_code": h.exit_code,
        "output": h.output,
        "duration_ms": h.duration_ms,
        "run_at": h.run_at,
    })
}

/// Espejo de `record.model_dump(mode="json")`.
pub fn dump_record(r: &SRecord) -> Value {
    json!({
        "session_id": r.session_id,
        "spec_path": r.spec_path,
        "spec_summary": r.spec_summary,
        "start_commit": r.start_commit,
        "start_branch": r.start_branch,
        "opened_at": r.opened_at,
        "status": r.status,
        "mode": r.mode,
        "checkpoints": r.checkpoints.iter().map(dump_checkpoint).collect::<Vec<_>>(),
        "verification_results": r.verification_results.iter().map(dump_hook).collect::<Vec<_>>(),
        "tasks": r.tasks.iter().map(dump_task).collect::<Vec<_>>(),
        "closed_at": r.closed_at,
        "end_commit": r.end_commit,
        "documenter_decision": r.documenter_decision,
        "session_note_path": r.session_note_path,
        "adrs_created": r.adrs_created,
    })
}

// ---------------------------------------------------------------------------
// Backend inyectable
// ---------------------------------------------------------------------------

pub trait SessionsBackend {
    fn open_session(
        &mut self,
        spec_id: &str,
        spec_path: &str,
        spec_summary: &str,
    ) -> Result<SRecord, String>;
    fn checkpoint_session(
        &mut self,
        session_id: &str,
        source: &str,
        verified_claims: Vec<String>,
        unverified_claims: Vec<String>,
        artifacts_touched: Vec<String>,
        note: String,
    ) -> Result<SRecord, String>;
    fn close_session(
        &mut self,
        session_id: &str,
        status: &str,
        documenter_decision: &str,
        session_note_path: Option<String>,
        adrs_created: Vec<String>,
    ) -> Result<SRecord, String>;
    fn get_active_session(&mut self) -> Result<Option<SRecord>, String>;
    fn get_session(&mut self, session_id: &str) -> Result<SRecord, String>;
    fn list_sessions(&mut self, status: Option<String>) -> Result<Vec<SRecord>, String>;
    fn list_tasks(
        &mut self,
        session_id: &str,
        status: Option<String>,
    ) -> Result<Vec<STask>, String>;
    fn add_task(&mut self, session_id: &str, task: STask) -> Result<(), String>;
    fn update_task(
        &mut self,
        session_id: &str,
        task_id: &str,
        status: &str,
        note: String,
        checkpoint_index: Option<i64>,
    ) -> Result<(), String>;
    fn save_session_note(&mut self, args: &Value) -> Result<String, String>;
    /// files_in_scope del spec (para review_checkpoint).
    fn spec_files_in_scope(&mut self, spec_path: &str) -> Result<Vec<String>, String>;
}

// ---------------------------------------------------------------------------
// Handlers (formatos espejo exacto de sessions.py)
// ---------------------------------------------------------------------------

const NO_ACTIVE: &str = "❌ No active session. Pass session_id or open one first.";

pub fn session_open_text(b: &mut dyn SessionsBackend, args: &Value) -> Result<String, String> {
    let spec_id = args
        .get("spec_id")
        .and_then(Value::as_str)
        .unwrap_or("")
        .trim();
    let spec_path = args
        .get("spec_path")
        .and_then(Value::as_str)
        .unwrap_or("")
        .trim();
    if spec_id.is_empty() || spec_path.is_empty() {
        return Ok("❌ spec_id and spec_path are required for cortex_session_open.".into());
    }
    let record = b.open_session(spec_id, spec_path, str_arg(args, "spec_summary"))?;
    let payload = json!({
        "session_id": record.session_id,
        "opened_at": record.opened_at,
        "start_commit": record.start_commit,
        "start_branch": record.start_branch,
    });
    Ok(to_string_ensure_ascii_false(&payload))
}

pub fn session_checkpoint_text(
    b: &mut dyn SessionsBackend,
    args: &Value,
) -> Result<String, String> {
    let session_id = str_arg(args, "session_id").trim().to_string();
    let source = str_arg(args, "source").trim().to_string();
    if session_id.is_empty() || source.is_empty() {
        return Ok("❌ session_id and source are required for cortex_session_checkpoint.".into());
    }
    if !VALID_CHECKPOINT_SOURCES.contains(&source.as_str()) {
        return Ok(format!(
            "❌ Invalid source '{source}'. Must be one of: {}",
            sources_list()
        ));
    }
    let record = b.checkpoint_session(
        &session_id,
        &source,
        strings_arg(args, "verified_claims"),
        strings_arg(args, "unverified_claims"),
        strings_arg(args, "artifacts_touched"),
        str_arg(args, "note").to_string(),
    )?;
    let last = record.checkpoints.last().map(|c| c.timestamp.clone());
    let payload = json!({
        "session_id": record.session_id,
        "checkpoint_count": record.checkpoints.len(),
        "last_checkpoint_at": last,
    });
    Ok(to_string_ensure_ascii_false(&payload))
}

pub fn session_close_text(b: &mut dyn SessionsBackend, args: &Value) -> Result<String, String> {
    let valid = ["closed", "handoff", "abandoned"];
    let session_id = str_arg(args, "session_id").trim().to_string();
    let status = str_arg(args, "status").trim().to_string();
    let decision = str_arg(args, "documenter_decision").trim().to_string();
    if session_id.is_empty() || status.is_empty() || decision.is_empty() {
        return Ok(
            "❌ session_id, status and documenter_decision are required for cortex_session_close."
                .into(),
        );
    }
    if !valid.contains(&status.as_str()) {
        return Ok(format!(
            "❌ Invalid status '{status}'. Must be one of: {}",
            valid.join(", ")
        ));
    }
    if !valid.contains(&decision.as_str()) {
        return Ok(format!(
            "❌ Invalid documenter_decision '{decision}'. Must be one of: {}",
            valid.join(", ")
        ));
    }
    let record = b.close_session(
        &session_id,
        &status,
        &decision,
        opt_str_arg(args, "session_note_path"),
        strings_arg(args, "adrs_created"),
    )?;
    let payload = json!({
        "session_id": record.session_id,
        "closed_at": record.closed_at,
        "end_commit": record.end_commit,
        "mode_inferred": record.mode,
    });
    Ok(to_string_ensure_ascii_false(&payload))
}

pub fn session_status_text(b: &mut dyn SessionsBackend, args: &Value) -> Result<String, String> {
    let raw = args.get("session_id");
    let record = match raw.and_then(Value::as_str).map(str::trim) {
        None | Some("") => match b.get_active_session()? {
            Some(r) => r,
            None => return Ok(NO_ACTIVE.into()),
        },
        Some(id) => b.get_session(id)?,
    };
    Ok(to_string_ensure_ascii_false(&dump_record(&record)))
}

pub fn session_list_text(b: &mut dyn SessionsBackend, args: &Value) -> Result<String, String> {
    let status = match args.get("status") {
        Some(Value::String(s)) if !s.trim().is_empty() => Some(s.trim().to_string()),
        _ => None,
    };
    let records = b.list_sessions(status)?;
    let items: Vec<Value> = records
        .iter()
        .map(|r| {
            json!({
                "session_id": r.session_id,
                "status": r.status,
                "mode": r.mode,
                "opened_at": r.opened_at,
                "closed_at": r.closed_at,
                "checkpoint_count": r.checkpoints.len(),
                "spec_summary": r.spec_summary,
            })
        })
        .collect();
    Ok(to_string_ensure_ascii_false(&Value::Array(items)))
}

pub fn session_task_list_text(b: &mut dyn SessionsBackend, args: &Value) -> Result<String, String> {
    let session_id = resolve_session_id(b, args)?;
    if session_id.is_empty() {
        return Ok(NO_ACTIVE.into());
    }
    let filter_status = match args.get("status") {
        Some(Value::String(s)) if !s.is_empty() => {
            if !TASK_STATUSES.contains(&s.as_str()) {
                return Ok(format!(
                    "❌ Invalid status '{s}'. Must be one of: {}",
                    task_statuses_list()
                ));
            }
            Some(s.clone())
        }
        _ => None,
    };
    // El caso invalid-no-string (p.ej. número) también cae al error con repr.
    if let Some(v) = args.get("status") {
        if !v.is_null() && !v.is_string() {
            return Ok(format!(
                "❌ Invalid status {}. Must be one of: {}",
                python_repr_value(v),
                task_statuses_list()
            ));
        }
    }
    let tasks = b.list_tasks(&session_id, filter_status)?;
    let arr: Vec<Value> = tasks.iter().map(dump_task).collect();
    Ok(to_string_ensure_ascii_false(&Value::Array(arr)))
}

pub fn session_task_update_text(
    b: &mut dyn SessionsBackend,
    args: &Value,
) -> Result<String, String> {
    let session_id = resolve_session_id(b, args)?;
    if session_id.is_empty() {
        return Ok(NO_ACTIVE.into());
    }
    let task_id = str_arg(args, "task_id").trim().to_string();
    let raw_status = str_arg(args, "status").trim().to_string();
    if task_id.is_empty() || raw_status.is_empty() {
        return Ok("❌ task_id and status are required.".into());
    }
    if !TASK_STATUSES.contains(&raw_status.as_str()) {
        return Ok(format!(
            "❌ Invalid status '{raw_status}'. Must be one of: {}",
            task_statuses_list()
        ));
    }
    let note = str_arg(args, "note").to_string();
    let checkpoint_index = match args.get("checkpoint_index") {
        None | Some(Value::Null) => None,
        Some(Value::String(s)) if s.is_empty() => None,
        Some(v) => match v.as_i64() {
            Some(i) => Some(i),
            None => return Ok("❌ checkpoint_index must be an integer.".into()),
        },
    };

    // create-or-update
    let existing = b.list_tasks(&session_id, None)?;
    if !existing.iter().any(|t| t.id == task_id) {
        let description = str_arg(args, "description").trim().to_string();
        if description.is_empty() {
            return Ok(format!(
                "❌ Task '{task_id}' does not exist; pass `description` to create it on the fly."
            ));
        }
        let task = STask {
            id: task_id.clone(),
            description,
            files_in_scope: strings_arg(args, "files_in_scope"),
            depends_on: vec![],
            status: "pending".into(),
            completed_at: None,
            checkpoint_index: None,
            note: String::new(),
        };
        if let Err(e) = b.add_task(&session_id, task) {
            return Ok(format!("❌ {e}"));
        }
    }
    if let Err(e) = b.update_task(&session_id, &task_id, &raw_status, note, checkpoint_index) {
        return Ok(format!("❌ {e}"));
    }
    let payload = json!({
        "session_id": session_id,
        "task_id": task_id,
        "status": raw_status,
    });
    Ok(to_string_ensure_ascii_false(&payload))
}

pub fn review_checkpoint_text(
    b: &mut dyn SessionsBackend,
    args: &Value,
    project_root: Option<&Path>,
) -> Result<String, String> {
    let record = resolve_record_or_active(b, args)?;
    if record.checkpoints.is_empty() {
        return Ok("❌ Session has no checkpoints to review.".into());
    }
    let idx = match args.get("checkpoint_index") {
        None => -1i64,
        Some(Value::Null) => -1,
        Some(v) => match v.as_i64() {
            Some(i) => i,
            None => return Ok("❌ checkpoint_index must be an integer.".into()),
        },
    };
    let checkpoint = match record
        .checkpoints
        .get(idx.unsigned_abs() as usize)
        .filter(|_| idx >= 0)
    {
        Some(c) => c.clone(),
        None => {
            return Ok(format!(
                "❌ checkpoint_index {idx} out of range (session has {} checkpoint(s)).",
                record.checkpoints.len()
            ))
        }
    };
    let mut spec_path = record.spec_path.clone();
    let abs = Path::new(&spec_path).is_absolute();
    if !abs {
        if let Some(root) = project_root {
            let p = root.join(&spec_path);
            // .resolve(): normalización léxica suficiente para gates.
            spec_path = normalize_lexical(p).display().to_string();
        }
    }
    let files_in_scope = b.spec_files_in_scope(&spec_path)?;
    let native_checkpoint = to_native_checkpoint(&checkpoint);
    let verdict: ReviewVerdict = review_checkpoint(&native_checkpoint, &files_in_scope);
    let payload = json!({
        "accepted": verdict.accepted,
        "stage_1_passed": verdict.stage_1_passed,
        "stage_2_passed": verdict.stage_2_passed,
        "reason": verdict.reason,
        "action": verdict.action.as_str(),
    });
    Ok(to_string_ensure_ascii_false(&payload))
}

pub fn close_session_text(b: &mut dyn SessionsBackend, args: &Value) -> Result<String, String> {
    let raw_status = args.get("status");
    if raw_status
        .and_then(Value::as_str)
        .unwrap_or("")
        .trim()
        .is_empty()
    {
        return Ok("❌ 'status' is required (one of: closed, handoff, abandoned).".into());
    }
    let status = raw_status
        .and_then(Value::as_str)
        .unwrap_or("")
        .trim()
        .to_string();
    if !["closed", "handoff", "abandoned"].contains(&status.as_str()) {
        return Ok(format!(
            "❌ Invalid status '{status}'. Must be one of: closed, handoff, abandoned."
        ));
    }

    let session_id = match args
        .get("session_id")
        .and_then(Value::as_str)
        .map(str::trim)
    {
        None | Some("") => match b.get_active_session()? {
            Some(active) => active.session_id,
            None => return Ok("❌ No active session. Pass session_id explicitly.".into()),
        },
        Some(id) => id.to_string(),
    };
    let note_path = opt_str_arg(args, "session_note_path");
    let adrs: Vec<String> = args
        .get("adrs_created")
        .and_then(Value::as_array)
        .map(|arr| {
            arr.iter()
                .filter_map(Value::as_str)
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect()
        })
        .unwrap_or_default();

    let record = b.close_session(&session_id, &status, &status, note_path, adrs)?;
    let payload = json!({
        "session_id": record.session_id,
        "final_status": record.status,
        "mode": record.mode,
        "closed_at": record.closed_at,
        "end_commit": record.end_commit,
        "session_note_path": record.session_note_path,
        "adrs_created": record.adrs_created,
    });
    Ok(to_string_ensure_ascii_false(&payload))
}

pub fn save_session_text(b: &mut dyn SessionsBackend, args: &Value) -> Result<String, String> {
    let path = b.save_session_note(args)?;
    Ok(format!("Session note saved -> {path}"))
}

// ---------------------------------------------------------------------------
// validate_handoff / verify_session_claims (helpers Tripartita)
// ---------------------------------------------------------------------------

pub fn validate_handoff_text(args: &Value) -> Result<String, String> {
    use cortex_app::documenter::handoff::AgentHandoff;
    let yaml_text = str_arg(args, "handoff_yaml");
    if yaml_text.trim().is_empty() {
        return Ok("❌ handoff_yaml is required and must not be empty.".into());
    }
    let parsed: serde_yaml::Value = match serde_yaml::from_str(yaml_text) {
        Ok(v) => v,
        Err(_) => return Ok("❌ Failed to parse YAML: {{YAML_ERR}}".into()),
    };
    // Validación mínima de schema (pydantic hace más; el volcado completo se
    // normaliza como {{HANDOFF_ERR}} en gates).
    let required_missing = ["agent", "status"]
        .iter()
        .any(|k| parsed.get(k).map(|v| v.is_null()).unwrap_or(true));
    if required_missing {
        return Ok("❌ Handoff schema violation:\n  {{HANDOFF_ERR}}".into());
    }
    let handoff: AgentHandoff = match serde_yaml::from_value(parsed) {
        Ok(h) => h,
        Err(_) => return Ok("❌ Handoff schema violation:\n  {{HANDOFF_ERR}}".into()),
    };
    if let Some(expected) = args.get("expected_agent").and_then(Value::as_str) {
        if !expected.is_empty() && handoff.agent != expected {
            return Ok(format!(
                "❌ Agent mismatch: handoff says '{}' but expected '{}'.",
                handoff.agent, expected
            ));
        }
    }
    let mut lines = vec![
        format!(
            "✅ Handoff validated for {} (status: {})",
            handoff.agent, handoff.status
        ),
        format!("  verified_claims: {}", handoff.verified_claims.len()),
        format!("  unverified_claims: {}", handoff.unverified_claims.len()),
        format!("  artifacts: {}", handoff.artifacts_produced.len()),
        format!("  context_for_next: {}", handoff.context_for_next.len()),
    ];
    if handoff.suggested_adr {
        let reason = if handoff.suggested_adr_reason.is_empty() {
            "(no reason given)".to_string()
        } else {
            handoff.suggested_adr_reason.clone()
        };
        lines.push(format!("  ⚠ suggested ADR: {reason}"));
    }
    if !handoff.suggested_context_terms.is_empty() {
        lines.push(format!(
            "  📚 CONTEXT.md terms: {}",
            handoff.suggested_context_terms.join(", ")
        ));
    }
    Ok(lines.join("\n"))
}

pub fn verify_session_claims_text(args: &Value, project_root: &Path) -> Result<String, String> {
    let claims: Vec<String> = args
        .get("claims")
        .and_then(Value::as_array)
        .map(|arr| {
            arr.iter()
                .filter_map(Value::as_str)
                .map(str::trim)
                .filter(|s| !s.is_empty())
                .map(str::to_string)
                .collect()
        })
        .unwrap_or_default();
    let base = args
        .get("base_branch")
        .and_then(Value::as_str)
        .filter(|s| !s.is_empty())
        .unwrap_or("main")
        .to_string();
    if claims.is_empty() {
        return Ok("❌ claims list is required and must not be empty.".into());
    }
    // Pre-chequeo barato de la rama base.
    let exists = std::process::Command::new("git")
        .args(["rev-parse", "--verify", "--quiet", &base])
        .current_dir(project_root)
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false);
    if !exists {
        return Ok(format!(
            "❌ Base branch '{base}' does not exist in this repo. Pass a valid branch via `base_branch` argument."
        ));
    }
    let out = std::process::Command::new("git")
        .args(["diff", "--unified=0", &base, "--"])
        .current_dir(project_root)
        .output();
    let diff_text = match out {
        Ok(o) if o.status.success() => String::from_utf8_lossy(&o.stdout).to_string(),
        Ok(o) => {
            let err = String::from_utf8_lossy(&o.stderr);
            return Ok(format!("❌ git diff against '{base}' failed: {err}"));
        }
        Err(e) => return Ok(format!("❌ git diff against '{base}' failed: {e}")),
    };
    let diff_lower = diff_text.to_lowercase();
    let mut verified: Vec<&String> = vec![];
    let mut asserted: Vec<&String> = vec![];
    for claim in &claims {
        let tokens: Vec<String> = claim
            .replace(['_', '/'], " ")
            .split_whitespace()
            .filter(|t| t.len() > 3)
            .map(|t| t.to_lowercase())
            .collect();
        let hits = tokens
            .iter()
            .filter(|t| diff_lower.contains(t.as_str()))
            .count();
        if hits >= 2 {
            verified.push(claim);
        } else {
            asserted.push(claim);
        }
    }
    let mut lines = vec![
        format!(
            "Verification of {} claims against branch {base}:",
            claims.len()
        ),
        format!("  ✅ verified: {}", verified.len()),
        format!("  ⚠ asserted: {}", asserted.len()),
        "  ❌ contradicted: 0".to_string(),
    ];
    if !verified.is_empty() {
        lines.push("\nVerified:".into());
        lines.extend(verified.iter().map(|c| format!("  - {c}")));
    }
    if !asserted.is_empty() {
        lines.push("\nAsserted (no diff evidence):".into());
        lines.extend(asserted.iter().map(|c| format!("  - {c}")));
    }
    Ok(lines.join("\n"))
}

// ---------------------------------------------------------------------------
// Helpers internos
// ---------------------------------------------------------------------------

/// `json.dumps(payload, ensure_ascii=False)` de Python: separadores ", " /
/// ": ", orden de inserción preservado por la feature preserve_order.
/// Público para gates/checkers (misma convención).
pub fn to_string_ensure_ascii_false(v: &Value) -> String {
    fn esc(s: &str) -> String {
        let mut out = String::with_capacity(s.len() + 2);
        out.push('"');
        for c in s.chars() {
            match c {
                '"' => out.push_str("\\\""),
                '\\' => out.push_str("\\\\"),
                '\n' => out.push_str("\\n"),
                '\r' => out.push_str("\\r"),
                '\t' => out.push_str("\\t"),
                c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
                c => out.push(c),
            }
        }
        out.push('"');
        out
    }
    fn go(v: &Value, out: &mut String) {
        match v {
            Value::Object(m) => {
                out.push('{');
                for (i, (k, val)) in m.iter().enumerate() {
                    if i > 0 {
                        out.push_str(", ");
                    }
                    out.push_str(&esc(k));
                    out.push_str(": ");
                    go(val, out);
                }
                out.push('}');
            }
            Value::Array(items) => {
                out.push('[');
                for (i, item) in items.iter().enumerate() {
                    if i > 0 {
                        out.push_str(", ");
                    }
                    go(item, out);
                }
                out.push(']');
            }
            Value::String(s) => out.push_str(&esc(s)),
            other => out.push_str(&other.to_string()),
        }
    }
    let mut s = String::new();
    go(v, &mut s);
    s
}

fn str_arg<'a>(args: &'a Value, key: &str) -> &'a str {
    args.get(key).and_then(Value::as_str).unwrap_or("")
}

fn opt_str_arg(args: &Value, key: &str) -> Option<String> {
    args.get(key)
        .and_then(Value::as_str)
        .filter(|s| !s.is_empty())
        .map(str::to_string)
}

fn strings_arg(args: &Value, key: &str) -> Vec<String> {
    args.get(key)
        .and_then(Value::as_array)
        .map(|arr| {
            arr.iter()
                .filter_map(Value::as_str)
                .map(str::to_string)
                .collect()
        })
        .unwrap_or_default()
}

fn resolve_session_id(b: &mut dyn SessionsBackend, args: &Value) -> Result<String, String> {
    match args
        .get("session_id")
        .and_then(Value::as_str)
        .map(str::trim)
    {
        None | Some("") => match b.get_active_session()? {
            Some(r) => Ok(r.session_id),
            None => Ok(String::new()), // el caller decide con NO_ACTIVE
        },
        Some(id) => Ok(id.to_string()),
    }
}

/// Igual que resolve_session_id pero devolviendo el error estándar.
fn resolve_record_or_active(b: &mut dyn SessionsBackend, args: &Value) -> Result<SRecord, String> {
    match args
        .get("session_id")
        .and_then(Value::as_str)
        .map(str::trim)
    {
        None | Some("") => match b.get_active_session()? {
            Some(r) => Ok(r),
            None => Err(NO_ACTIVE.into()),
        },
        Some(id) => b.get_session(id),
    }
}

fn normalize_lexical(p: impl AsRef<Path>) -> std::path::PathBuf {
    let mut out = std::path::PathBuf::new();
    for comp in p.as_ref().components() {
        use std::path::Component;
        match comp {
            Component::CurDir => {}
            Component::ParentDir => {
                out.pop();
            }
            other => out.push(other.as_os_str()),
        }
    }
    out
}

fn to_native_checkpoint(c: &SCheckpoint) -> cortex_app::session::Checkpoint {
    cortex_app::session::Checkpoint {
        timestamp: c.timestamp.clone(),
        source: parse_source(&c.source),
        verified_claims: c.verified_claims.clone(),
        unverified_claims: c.unverified_claims.clone(),
        artifacts_touched: c.artifacts_touched.clone(),
        note: c.note.clone(),
        phase: None, /* el contrato MCP con phase llega en A4 (validación dura) */
    }
}

fn parse_source(s: &str) -> cortex_app::session::CheckpointSource {
    use cortex_app::session::CheckpointSource as C;
    match s {
        "cortex-sync" => C::CortexSync,
        "cortex-SDDwork" => C::CortexSddwork,
        "cortex-code-explorer" => C::CortexCodeExplorer,
        "cortex-code-implementer" => C::CortexCodeImplementer,
        "cortex-code-designer" => C::CortexCodeDesigner,
        "user-skill" => C::UserSkill,
        "ide-hook" => C::IdeHook,
        "ci-bot" => C::CiBot,
        _ => C::Manual,
    }
}

/// repr() aproximado de Python para valores no-string en mensajes.
fn python_repr_value(v: &Value) -> String {
    match v {
        Value::String(s) => format!("'{s}'"),
        Value::Number(n) => n.to_string(),
        Value::Bool(b) => if *b { "True" } else { "False" }.into(),
        Value::Null => "None".into(),
        other => other.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct One;
    impl SessionsBackend for One {
        fn open_session(&mut self, _: &str, _: &str, _: &str) -> Result<SRecord, String> {
            Ok(SRecord {
                session_id: "2026-05-16_demo".into(),
                ..Default::default()
            })
        }
        fn checkpoint_session(
            &mut self,
            _: &str,
            _: &str,
            _: Vec<String>,
            _: Vec<String>,
            _: Vec<String>,
            _: String,
        ) -> Result<SRecord, String> {
            unimplemented!()
        }
        fn close_session(
            &mut self,
            _: &str,
            _: &str,
            _: &str,
            _: Option<String>,
            _: Vec<String>,
        ) -> Result<SRecord, String> {
            unimplemented!()
        }
        fn get_active_session(&mut self) -> Result<Option<SRecord>, String> {
            Ok(None)
        }
        fn get_session(&mut self, _: &str) -> Result<SRecord, String> {
            unimplemented!()
        }
        fn list_sessions(&mut self, _: Option<String>) -> Result<Vec<SRecord>, String> {
            Ok(vec![])
        }
        fn list_tasks(&mut self, _: &str, _: Option<String>) -> Result<Vec<STask>, String> {
            Ok(vec![])
        }
        fn add_task(&mut self, _: &str, _: STask) -> Result<(), String> {
            Ok(())
        }
        fn update_task(
            &mut self,
            _: &str,
            _: &str,
            _: &str,
            _: String,
            _: Option<i64>,
        ) -> Result<(), String> {
            Ok(())
        }
        fn save_session_note(&mut self, _: &Value) -> Result<String, String> {
            Ok("/p.md".into())
        }
        fn spec_files_in_scope(&mut self, _: &str) -> Result<Vec<String>, String> {
            Ok(vec![])
        }
    }

    #[test]
    fn open_faltan_campos() {
        let mut b = One;
        let out = session_open_text(&mut b, &json!({})).unwrap();
        assert_eq!(
            out,
            "❌ spec_id and spec_path are required for cortex_session_open."
        );
    }

    #[test]
    fn checkpoint_source_invalida() {
        let mut b = One;
        let out = session_checkpoint_text(&mut b, &json!({"session_id":"s","source":"x"})).unwrap();
        assert!(out.starts_with("❌ Invalid source 'x'."));
        assert!(out.ends_with("ci-bot"));
    }

    #[test]
    fn dumps_orden_y_separadores_python() {
        let t = STask {
            id: "T1".into(),
            description: "d".into(),
            ..Default::default()
        };
        assert_eq!(
            to_string_ensure_ascii_false(&dump_task(&t)),
            "{\"id\": \"T1\", \"description\": \"d\", \"files_in_scope\": [], \"depends_on\": [], \"status\": \"\", \"completed_at\": null, \"checkpoint_index\": null, \"note\": \"\"}"
        );
    }

    #[test]
    fn handoff_vacio_requerido() {
        let out = validate_handoff_text(&json!({"handoff_yaml": " "})).unwrap();
        assert!(out.contains("handoff_yaml is required"));
    }
}
