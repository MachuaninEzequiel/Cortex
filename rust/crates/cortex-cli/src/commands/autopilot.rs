//! `cortex autopilot ...` — puerto de `cortex/autopilot/cli.py` (Cierre T3).
//!
//! Subcomandos NATIVOS sobre [`cortex_autopilot::service::AutopilotService`]
//! (SessionService nativo): start / preflight / checkpoint / finish / status.
//!
//! `doctor`, `install` y `uninstall` caen al passthrough
//! (external_subcommand): doctor vive en el oráculo con checks de sesión
//! propios del trunk; hooks de IDE viven en `cortex session hooks`.

use std::path::PathBuf;

use clap::Parser;

use cortex_autopilot::policies::AutopilotMode;
use cortex_autopilot::service::{AutopilotService, ServiceError};

use crate::pyjson::{Num, PyVal};

pub const VALID_MODES: &[&str] = &["observe", "assist", "autopilot"];

#[derive(Parser, Debug)]
#[command(
    name = "autopilot",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct AutopilotArgs {
    #[command(subcommand)]
    pub cmd: AutopilotCmd,
}

#[derive(clap::Subcommand, Debug)]
pub enum AutopilotCmd {
    /// Adopt the active session under the requested mode and surface warnings.
    Start {
        /// Mode: observe, assist, autopilot.
        #[arg(long, default_value = "assist")]
        mode: String,
        /// Absolute path to the project root.
        #[arg(long)]
        project_root: Option<String>,
        /// Output JSON.
        #[arg(long)]
        json: bool,
    },
    /// Run the detector pipeline as a dry-run; do not touch any session state.
    Preflight {
        /// User request text.
        #[arg(long)]
        request: Option<String>,
        /// Changed file (repeatable).
        #[arg(long = "file")]
        files: Vec<String>,
        /// Absolute path to the project root.
        #[arg(long)]
        project_root: Option<String>,
        /// Output JSON.
        #[arg(long)]
        json: bool,
    },
    /// Append a checkpoint to the active session.
    Checkpoint {
        /// CheckpointSource value (e.g. manual, cortex-SDDwork).
        #[arg(long, default_value = "manual")]
        source: String,
        /// Free-form note for the next step.
        #[arg(long, default_value = "")]
        note: String,
        /// A verified claim (repeatable).
        #[arg(long = "verified-claim")]
        verified_claims: Vec<String>,
        /// A claim not yet verified (repeatable).
        #[arg(long = "unverified-claim")]
        unverified_claims: Vec<String>,
        /// Artifact path touched (repeatable).
        #[arg(long = "artifact")]
        artifacts: Vec<String>,
        /// Spec scope path (repeatable); enables out-of-scope warning.
        #[arg(long = "in-scope")]
        in_scope: Vec<String>,
        /// Absolute path to the project root.
        #[arg(long)]
        project_root: Option<String>,
        /// Output JSON.
        #[arg(long)]
        json: bool,
    },
    /// Close the active session — `--auto` runs the canonical documenter.
    Finish {
        /// Invoke the documenter pipeline (reconstruct, verify, persist).
        #[arg(long)]
        auto: bool,
        /// Force the session to close as HANDOFF.
        #[arg(long)]
        handoff: bool,
        /// Force the session to close as ABANDONED.
        #[arg(long)]
        abandon: bool,
        /// Reason recorded when --handoff or --abandon.
        #[arg(long, default_value = "")]
        reason: String,
        /// Explicit session id (default: active).
        #[arg(long = "session-id")]
        session_id: Option<String>,
        /// Absolute path to the project root.
        #[arg(long)]
        project_root: Option<String>,
        /// Output JSON.
        #[arg(long)]
        json: bool,
    },
    /// Show the active or named session.
    Status {
        /// Session ID (optional).
        #[arg(long = "session-id")]
        session_id: Option<String>,
        /// Absolute path to the project root.
        #[arg(long)]
        project_root: Option<String>,
        /// Output JSON.
        #[arg(long)]
        json: bool,
    },
    /// Comandos no wireados (doctor/install/uninstall y desconocidos) →
    /// passthrough al CLI Python.
    #[command(external_subcommand)]
    Other(Vec<String>),
}

pub fn run(tokens: &[String]) -> bool {
    let args = AutopilotArgs::parse_from(
        std::iter::once("autopilot".to_string()).chain(tokens.iter().cloned()),
    );
    match args.cmd {
        AutopilotCmd::Start {
            mode,
            project_root,
            json,
        } => std::process::exit(execute_start(&mode, project_root.as_deref(), json)),
        AutopilotCmd::Preflight {
            request,
            files,
            project_root,
            json,
        } => std::process::exit(execute_preflight(
            request.as_deref(),
            &files,
            project_root.as_deref(),
            json,
        )),
        AutopilotCmd::Checkpoint {
            source,
            note,
            verified_claims,
            unverified_claims,
            artifacts,
            in_scope,
            project_root,
            json,
        } => std::process::exit(execute_checkpoint(
            &source,
            &note,
            &verified_claims,
            &unverified_claims,
            &artifacts,
            &in_scope,
            project_root.as_deref(),
            json,
        )),
        AutopilotCmd::Finish {
            auto,
            handoff,
            abandon,
            reason,
            session_id,
            project_root,
            json,
        } => std::process::exit(execute_finish(
            auto,
            handoff,
            abandon,
            &reason,
            session_id.as_deref(),
            project_root.as_deref(),
            json,
        )),
        AutopilotCmd::Status {
            session_id,
            project_root,
            json,
        } => std::process::exit(execute_status(
            session_id.as_deref(),
            project_root.as_deref(),
            json,
        )),
        AutopilotCmd::Other(_) => false,
    }
}

// ── Helpers de emisión (`_emit`) ────────────────────────────────────────────

/// `json.dumps(payload, indent=2, default=str)` o `f"{key}: {value}"` por
/// clave, en el orden de inserción del dict del oráculo.
fn emit(payload: &PyVal, pairs: &[(&str, String)], json_mode: bool) {
    if json_mode {
        println!("{}", crate::pyjson::stdlib_dumps_indent2(payload));
        return;
    }
    for (key, value) in pairs {
        println!("{key}: {value}");
    }
}

fn py_bool(b: bool) -> &'static str {
    if b {
        "True"
    } else {
        "False"
    }
}

fn py_list_str(items: &[String]) -> String {
    let inner: Vec<String> = items.iter().map(|s| format!("'{s}'")).collect();
    format!("[{}]", inner.join(", "))
}

fn json_warnings(items: &[String]) -> PyVal {
    PyVal::Arr(items.iter().map(|s| PyVal::s(s.clone())).collect())
}

fn abort_no_session(exc: &ServiceError, json_mode: bool) -> ! {
    let msg = exc.to_string();
    if json_mode {
        eprintln!("{}", stderr_json_error(&msg));
    } else {
        eprintln!("✗ {msg}");
    }
    std::process::exit(1);
}

/// `json.dumps({"error": msg})` compacto (separadores `, ` `: `,
/// ensure_ascii=True vía el escritor compartido, que YA agrega comillas).
fn stderr_json_error(msg: &str) -> String {
    let mut out = String::from("{\"error\": ");
    crate::pyjson::write_escaped(msg, &mut out);
    out.push('}');
    out
}

/// `json.dumps({"blocked": True, "reason": …, "warnings": [...]})` compacto.
fn stderr_json_blocked(reason: &str, warnings: &[String]) -> String {
    let mut out = String::from("{\"blocked\": true, \"reason\": ");
    crate::pyjson::write_escaped(reason, &mut out);
    out.push_str(", \"warnings\": [");
    for (i, w) in warnings.iter().enumerate() {
        if i > 0 {
            out.push_str(", ");
        }
        crate::pyjson::write_escaped(w, &mut out);
    }
    out.push_str("]}");
    out
}

/// `_parse_mode`: inválido ⇒ stderr + exit 2.
fn parse_mode(raw: &str) -> Option<AutopilotMode> {
    Some(match raw {
        "observe" => AutopilotMode::Observe,
        "assist" => AutopilotMode::Assist,
        "autopilot" => AutopilotMode::Autopilot,
        _ => {
            eprintln!("Invalid --mode '{raw}'; valid: observe, assist, autopilot");
            std::process::exit(2);
        }
    })
}

fn resolve_service(project_root: Option<&str>) -> AutopilotService {
    let root = resolve_root(project_root);
    match AutopilotService::from_project_root(&root, None) {
        Ok(svc) => svc,
        // Fallo explícito (el oráculo tracebackea ante config rota).
        Err(exc) => {
            eprintln!("✗ ConfigError: {}", exc.0);
            std::process::exit(1);
        }
    }
}

/// `Path(project_root or cwd).expanduser().resolve()`.
fn resolve_root(project_root: Option<&str>) -> PathBuf {
    let raw = match project_root {
        Some(p) => {
            if let Some(rest) = p.strip_prefix('~') {
                let home = std::env::var("HOME").unwrap_or_default();
                PathBuf::from(format!("{home}{rest}"))
            } else {
                PathBuf::from(p)
            }
        }
        None => std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")),
    };
    raw.canonicalize().unwrap_or(raw)
}

// ── start ────────────────────────────────────────────────────────────────────

pub fn execute_start(mode: &str, project_root: Option<&str>, json_mode: bool) -> i32 {
    let parsed_mode = parse_mode(mode);
    let mut svc = resolve_service(project_root);
    match svc.start(parsed_mode) {
        Err(exc) => {
            abort_no_session(&exc, json_mode);
        }
        Ok(out) => {
            let payload = PyVal::obj(vec![
                ("session_id", PyVal::s(out.session.session_id.clone())),
                ("mode", PyVal::s(svc.policy().mode.as_str())),
                ("status", PyVal::s(out.session.status.as_str())),
                ("warnings", json_warnings(&out.warnings)),
            ]);
            let pairs = [
                ("session_id", out.session.session_id.clone()),
                ("mode", svc.policy().mode.as_str().to_string()),
                ("status", out.session.status.as_str().to_string()),
                ("warnings", py_list_str(&out.warnings)),
            ];
            emit(&payload, &pairs, json_mode);
        }
    }
    0
}

// ── preflight ────────────────────────────────────────────────────────────────

pub fn execute_preflight(
    request: Option<&str>,
    files: &[String],
    project_root: Option<&str>,
    json_mode: bool,
) -> i32 {
    let svc = resolve_service(project_root);
    let result = svc.preflight(request, files, None);
    let payload = PyVal::obj(vec![
        ("task_type", PyVal::s(&result.detection.task_type)),
        (
            "confidence",
            PyVal::Num(Num::Float(result.detection.confidence)),
        ),
        ("reason", PyVal::s(&result.detection.reason)),
        (
            "suggested_complexity",
            PyVal::s(&result.detection.suggested_complexity),
        ),
    ]);
    let pairs = [
        ("task_type", result.detection.task_type.clone()),
        (
            "confidence",
            crate::pyjson::format_float(result.detection.confidence),
        ),
        ("reason", result.detection.reason.clone()),
        (
            "suggested_complexity",
            result.detection.suggested_complexity.clone(),
        ),
    ];
    emit(&payload, &pairs, json_mode);
    0
}

// ── checkpoint ───────────────────────────────────────────────────────────────

#[allow(clippy::too_many_arguments)]
pub fn execute_checkpoint(
    source: &str,
    note: &str,
    verified_claims: &[String],
    unverified_claims: &[String],
    artifacts: &[String],
    in_scope: &[String],
    project_root: Option<&str>,
    json_mode: bool,
) -> i32 {
    let mut svc = resolve_service(project_root);
    let files_in_scope = if in_scope.is_empty() {
        None
    } else {
        Some(in_scope.to_vec())
    };
    match svc.checkpoint(
        source,
        verified_claims.to_vec(),
        unverified_claims.to_vec(),
        artifacts.to_vec(),
        note,
        files_in_scope,
    ) {
        Err(exc) => {
            abort_no_session(&exc, json_mode);
        }
        Ok(out) => {
            let count = out.session.checkpoints.len();
            let payload = PyVal::obj(vec![
                ("session_id", PyVal::s(out.session.session_id.clone())),
                ("checkpoints_count", PyVal::Num(Num::Int(count as i64))),
                ("warnings", json_warnings(&out.warnings)),
            ]);
            let pairs = [
                ("session_id", out.session.session_id.clone()),
                ("checkpoints_count", count.to_string()),
                ("warnings", py_list_str(&out.warnings)),
            ];
            emit(&payload, &pairs, json_mode);
        }
    }
    0
}

// ── finish ───────────────────────────────────────────────────────────────────

#[allow(clippy::too_many_arguments)]
pub fn execute_finish(
    auto: bool,
    handoff: bool,
    abandon: bool,
    reason: &str,
    session_id: Option<&str>,
    project_root: Option<&str>,
    json_mode: bool,
) -> i32 {
    let _ = reason;
    if handoff && abandon {
        eprintln!("--handoff and --abandon are mutually exclusive.");
        return 2;
    }
    let intent = if handoff {
        "handoff"
    } else if abandon {
        "abandoned"
    } else {
        "closed"
    };
    let mut svc = resolve_service(project_root);
    match svc.finish(session_id, auto, intent) {
        Err(exc) => {
            abort_no_session(&exc, json_mode);
        }
        Ok(out) if out.blocked => {
            if json_mode {
                eprintln!(
                    "{}",
                    stderr_json_blocked(&out.blocked_reason, &out.warnings)
                );
            } else {
                eprintln!("✗ blocked by policy: {}", out.blocked_reason);
            }
            std::process::exit(1);
        }
        Ok(out) => {
            let mut payload = Vec::from([
                ("session_id", PyVal::s(out.session.session_id.clone())),
                ("status", PyVal::s(out.session.status.as_str())),
                ("documented", PyVal::Bool(out.documented)),
                ("summary", PyVal::s(&out.summary)),
                ("warnings", json_warnings(&out.warnings)),
            ]);
            let mut pairs = Vec::from([
                ("session_id", out.session.session_id.clone()),
                ("status", out.session.status.as_str().to_string()),
                ("documented", py_bool(out.documented).to_string()),
                ("summary", out.summary.clone()),
                ("warnings", py_list_str(&out.warnings)),
            ]);
            if let Some(path) = &out.session_note_path {
                payload.push(("session_note_path", PyVal::s(path.clone())));
                pairs.push(("session_note_path", path.clone()));
            }
            if !out.adrs_created.is_empty() {
                payload.push(("adrs_created", json_warnings(&out.adrs_created)));
                pairs.push(("adrs_created", py_list_str(&out.adrs_created)));
            }
            emit(&PyVal::obj(payload), &pairs, json_mode);
        }
    }
    0
}

// ── status ───────────────────────────────────────────────────────────────────

pub fn execute_status(
    session_id: Option<&str>,
    project_root: Option<&str>,
    json_mode: bool,
) -> i32 {
    let mut svc = resolve_service(project_root);
    // El oráculo traga SessionNotFound dentro de service.status(): esta
    // llamada no falla para los flujos del CLI.
    let result = match svc.status(session_id) {
        Ok(r) => r,
        Err(_) => cortex_autopilot::service::StatusOutcome {
            active: false,
            session: None,
            checkpoint_count: 0,
            inferred_mode: None,
        },
    };
    if !result.active {
        let mode = svc.policy().mode.as_str().to_string();
        let payload = PyVal::obj(vec![
            ("active", PyVal::Bool(false)),
            ("policy_mode", PyVal::s(&mode)),
        ]);
        let pairs = [("active", "False".to_string()), ("policy_mode", mode)];
        emit(&payload, &pairs, json_mode);
        return 0;
    }
    let session = result.session.expect("activo implica record");
    let start_commit: String = session.start_commit.chars().take(12).collect();
    let mode = svc.policy().mode.as_str().to_string();
    let inferred = result.inferred_mode.clone().unwrap_or_default();
    let payload = PyVal::obj(vec![
        ("active", PyVal::Bool(true)),
        ("session_id", PyVal::s(&session.session_id)),
        ("status", PyVal::s(session.status.as_str())),
        ("mode", PyVal::s(&mode)),
        ("inferred_mode", PyVal::s(&inferred)),
        (
            "checkpoint_count",
            PyVal::Num(Num::Int(result.checkpoint_count as i64)),
        ),
        ("start_commit", PyVal::s(&start_commit)),
        ("start_branch", PyVal::s(&session.start_branch)),
        ("spec_path", PyVal::s(&session.spec_path)),
    ]);
    let pairs = [
        ("active", "True".to_string()),
        ("session_id", session.session_id.clone()),
        ("status", session.status.as_str().to_string()),
        ("mode", mode),
        ("inferred_mode", inferred),
        ("checkpoint_count", result.checkpoint_count.to_string()),
        ("start_commit", start_commit),
        ("start_branch", session.start_branch.clone()),
        ("spec_path", session.spec_path.clone()),
    ];
    emit(&payload, &pairs, json_mode);
    0
}
