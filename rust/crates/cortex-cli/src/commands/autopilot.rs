//! `cortex autopilot ...` — puerto de `cortex/autopilot/cli.py` (Cierre T3).
//!
//! Subcomandos NATIVOS sobre [`cortex_autopilot::service::AutopilotService`]
//! (SessionService nativo): start / preflight / checkpoint / finish / status
//! (T3) + doctor (BAJA DEFINITIVA RUTA 2, MITAD A).
//!
//! `install` / `uninstall` fueron ELIMINADOS del oráculo en la Fase 04
//! (`cortex/autopilot/cli.py` — usar `cortex session hooks`); el nativo los
//! RECHAZA con el mismo comportamiento que el CLI Python real (comando
//! desconocido, rc=2) y NUNCA ejecuta Python. Cualquier otro subcomando
//! desconocido también se rechaza nativamente (baja física: sin passthrough).

use std::fs;
use std::path::PathBuf;

use clap::Parser;

use cortex_app::session::{SessionStatus, SessionStorage};
use cortex_autopilot::config::load_autopilot_config;
use cortex_autopilot::policies::AutopilotMode;
use cortex_autopilot::service::{AutopilotService, ServiceError};
use cortex_setup::session_hooks::default_installer;
use cortex_workspace::WorkspaceLayout;

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
    /// Diagnose the Autopilot installation and state. (Read-only)
    Doctor {
        /// Absolute path to the project root.
        #[arg(long)]
        project_root: Option<String>,
        /// Output JSON.
        #[arg(long)]
        json: bool,
    },
    /// Subcomandos desconocidos → rechazo nativo (Typer-like): NUNCA
    /// passthrough a Python (baja física). `install`/`uninstall` fueron
    /// ELIMINADOS del oráculo en la Fase 04 (`cortex/autopilot/cli.py`).
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
        AutopilotCmd::Doctor { project_root, json } => {
            std::process::exit(execute_doctor(project_root.as_deref(), json))
        }
        AutopilotCmd::Other(tokens) => {
            // Baja física: el passthrough a Python fue eliminado ⇒ TODO
            // subcomando desconocido se rechaza nativamente (Typer-like,
            // precedente Fase 04 install/uninstall): `No such command`, rc 2.
            if let Some(first) = tokens.first() {
                eprintln!("No such command '{first}'.");
                std::process::exit(2);
            }
            false
        }
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

// ── doctor (BAJA DEFINITIVA RUTA 2, MITAD A) ──────────────────────────────
//
// Port exacto de `cortex/autopilot/doctor.py::run_diagnosis` + `_emit` del
// oráculo: payload `{project_root, ok, checks, warnings}`, 6 checks en
// orden (config, sessions_dir, adapters, hooks, last_finish, service),
// rc 0 siempre (el oráculo NO sale 1 ante checks fallidos; `sessions_dir`
// se auto-repara con mkdir como el doctor Python).

/// Un check del diagnóstico (espejo de `DoctorCheck`).
struct DoctorCheck {
    name: &'static str,
    ok: bool,
    detail: String,
    action: String,
}

/// `repr()` de CPython para el dominio (ASCII imprimible + unicode):
/// comillas simples salvo strings con comillas simples (⇒ dobles);
/// escapes de backslash/quote en el orden de Python.
fn py_str_repr(s: &str) -> String {
    if s.contains('\'') && !s.contains('"') {
        format!("\"{}\"", s.replace('\\', "\\\\").replace('"', "\\\""))
    } else {
        format!("'{}'", s.replace('\\', "\\\\").replace('\'', "\\'"))
    }
}

/// `str(lista[str])` de Python.
fn py_str_list_repr(items: &[String]) -> String {
    let inner: Vec<String> = items.iter().map(|s| py_str_repr(s)).collect();
    format!("[{}]", inner.join(", "))
}

/// `str(lista[DoctorCheck])` de Python: dicts en orden de inserción
/// (name, ok, detail, action).
fn checks_text_repr(checks: &[DoctorCheck]) -> String {
    let items: Vec<String> = checks
        .iter()
        .map(|c| {
            format!(
                "{{'name': {}, 'ok': {}, 'detail': {}, 'action': {}}}",
                py_str_repr(c.name),
                if c.ok { "True" } else { "False" },
                py_str_repr(&c.detail),
                py_str_repr(&c.action),
            )
        })
        .collect();
    format!("[{}]", items.join(", "))
}

/// 1. `config` — `AutopilotConfig` parsea sin error.
fn check_config(layout: &WorkspaceLayout) -> DoctorCheck {
    match load_autopilot_config(layout) {
        Ok(cfg) => DoctorCheck {
            name: "config",
            ok: true,
            detail: format!("mode={}, profile={}", cfg.mode, cfg.default_budget_profile),
            action: String::new(),
        },
        Err(exc) => DoctorCheck {
            name: "config",
            ok: false,
            detail: exc.0.clone(),
            action: "Fix `autopilot.yaml` syntax or run `cortex setup agent`.".to_string(),
        },
    }
}

/// 2. `sessions_dir` — `.cortex/sessions/` existe y es writable.
///    El oráculo hace `mkdir(parents=True, exist_ok=True)` y luego
///    chequea `W_OK` (se auto-repara).
fn check_sessions_dir(layout: &WorkspaceLayout) -> DoctorCheck {
    let sessions = layout.sessions_dir();
    match fs::create_dir_all(&sessions) {
        Err(exc) => DoctorCheck {
            name: "sessions_dir",
            ok: false,
            detail: exc.to_string(),
            action: "Run `cortex setup agent` to initialize `.cortex/sessions/`.".to_string(),
        },
        Ok(()) => {
            let writable = fs::metadata(&sessions)
                .map(|m| !m.permissions().readonly())
                .unwrap_or(false);
            if writable {
                DoctorCheck {
                    name: "sessions_dir",
                    ok: true,
                    detail: sessions.display().to_string(),
                    action: String::new(),
                }
            } else {
                DoctorCheck {
                    name: "sessions_dir",
                    ok: false,
                    detail: format!("Not writable: {}", sessions.display()),
                    action: "Ensure the workspace root is writable.".to_string(),
                }
            }
        }
    }
}

/// 3. `adapters` — registry devuelve sus nombres conocidos.
fn check_adapters() -> DoctorCheck {
    let known: Vec<String> = default_installer()
        .list_available_adapters()
        .into_iter()
        .map(str::to_string)
        .collect();
    DoctorCheck {
        name: "adapters",
        ok: true,
        detail: format!(
            "Known IDE adapters (cortex.session.hooks): {}",
            py_str_list_repr(&known)
        ),
        action: String::new(),
    }
}

/// 4. `hooks` — adapters instalados bajo el repo root.
fn check_hooks(layout: &WorkspaceLayout) -> DoctorCheck {
    let installed: Vec<String> = default_installer()
        .status_all(&layout.repo_root)
        .into_iter()
        .filter(|s| s.installed)
        .map(|s| s.ide.to_string())
        .collect();
    if installed.is_empty() {
        DoctorCheck {
            name: "hooks",
            ok: false,
            detail: "No Cortex session hooks detected".to_string(),
            action: "Run `cortex session hooks install --ide <name>`.".to_string(),
        }
    } else {
        DoctorCheck {
            name: "hooks",
            ok: true,
            detail: format!("Installed adapters: {}", py_str_list_repr(&installed)),
            action: String::new(),
        }
    }
}

/// 5. `last_finish` — último `SessionRecord` en estado sensible.
///
/// Máximo por `opened_at` (ISO-8601; orden lexicográfico = cronológico,
/// ambos lados listan por nombre de archivo ordenado). EMPATE EXACTO ⇒ gana
/// el PRIMERO en orden de lista, igual que `max(records, key=lambda r:
/// r.opened_at)` de Python (doctor.py:123), que devuelve el primer máximo:
/// el fold usa `>=` a propósito (con `>` ganaría el último del empate).
fn check_last_finish(layout: &WorkspaceLayout) -> DoctorCheck {
    let storage = SessionStorage::new(layout.sessions_dir());
    let records = match storage.list_all() {
        Ok(r) => r,
        Err(exc) => {
            return DoctorCheck {
                name: "last_finish",
                ok: false,
                detail: format!("Could not list sessions: {exc}"),
                action: String::new(),
            };
        }
    };
    let Some(latest) = records.iter().reduce(|acc, next| {
        // `>=` (no `>`): empate exacto de `opened_at` ⇒ gana `acc`, el
        // primero en orden de lista — primer máximo, como `max(key=...)`
        // de Python (con `>` ganaría `next`, el último del empate).
        if acc.opened_at >= next.opened_at {
            acc
        } else {
            next
        }
    }) else {
        return DoctorCheck {
            name: "last_finish",
            ok: true,
            detail: "No sessions on disk yet".to_string(),
            action: String::new(),
        };
    };
    if latest.status == SessionStatus::Open {
        DoctorCheck {
            name: "last_finish",
            ok: true,
            detail: format!(
                "Session {} still OPEN — finish or abandon when ready",
                latest.session_id
            ),
            action: String::new(),
        }
    } else {
        DoctorCheck {
            name: "last_finish",
            ok: true,
            detail: format!("Latest: {} ({})", latest.session_id, latest.status.as_str()),
            action: String::new(),
        }
    }
}

/// 6. `service` — `AutopilotService` se construye (nativo T3).
fn check_service(layout: &WorkspaceLayout) -> DoctorCheck {
    match AutopilotService::from_project_root(&layout.repo_root, None) {
        Ok(_) => DoctorCheck {
            name: "service",
            ok: true,
            detail: "AutopilotService.from_project_root wired OK".to_string(),
            action: String::new(),
        },
        Err(exc) => DoctorCheck {
            name: "service",
            ok: false,
            detail: format!("Could not build AutopilotService: {}", exc.0),
            action: "Run `cortex setup agent` to configure the workspace.".to_string(),
        },
    }
}

/// `autopilot doctor [--project-root] [--json]` — payload EXACTO y rc del
/// oráculo (`_emit` sobre `run_diagnosis`).
pub fn execute_doctor(project_root: Option<&str>, json_mode: bool) -> i32 {
    let root = resolve_root(project_root);
    let layout = WorkspaceLayout::discover(&root);
    let checks = vec![
        check_config(&layout),
        check_sessions_dir(&layout),
        check_adapters(),
        check_hooks(&layout),
        check_last_finish(&layout),
        check_service(&layout),
    ];
    let ok = checks.iter().all(|c| c.ok);
    let warnings: Vec<String> = checks
        .iter()
        .filter(|c| !c.ok)
        .map(|c| c.detail.clone())
        .collect();
    let root_str = root.display().to_string();
    let payload = PyVal::obj(vec![
        ("project_root", PyVal::s(root_str.clone())),
        ("ok", PyVal::Bool(ok)),
        (
            "checks",
            PyVal::Arr(
                checks
                    .iter()
                    .map(|c| {
                        PyVal::obj(vec![
                            ("name", PyVal::s(c.name)),
                            ("ok", PyVal::Bool(c.ok)),
                            ("detail", PyVal::s(c.detail.clone())),
                            ("action", PyVal::s(c.action.clone())),
                        ])
                    })
                    .collect(),
            ),
        ),
        ("warnings", json_warnings(&warnings)),
    ]);
    let pairs = [
        ("project_root", root_str),
        (
            "ok",
            if ok {
                "True".to_string()
            } else {
                "False".to_string()
            },
        ),
        ("checks", checks_text_repr(&checks)),
        ("warnings", py_str_list_repr(&warnings)),
    ];
    emit(&payload, &pairs, json_mode);
    0
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
