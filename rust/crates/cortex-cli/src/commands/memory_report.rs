//! `cortex memory-report` — puerto de cli/main.py::memory_report.
//!
//! Cierra el seam P12B-3→P12B-4: `EnterpriseReportingService` +
//! `NativeDoctorBackend`. `--telemetry` NO se wirea: fallo explícito
//! documentado (baja física — sin passthrough a Python).

use std::path::Path;

use clap::Parser;

use crate::paths::{expand_user, python_resolve};
use crate::pyjson::{Num, PyVal};

#[derive(Parser, Debug)]
#[command(
    name = "memory-report",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct MemoryReportArgs {
    /// Absolute path to the target project root.
    #[arg(long)]
    pub project_root: Option<String>,

    /// Report scope: local, enterprise, or all.
    #[arg(long, default_value = "local")]
    pub scope: String,

    /// Output raw JSON payload.
    #[arg(long)]
    pub json: bool,

    /// Include retrieval telemetry (delegado al CLI Python).
    #[arg(long)]
    pub telemetry: bool,

    /// Telemetry window in days (used only with --telemetry).
    #[arg(long, default_value_t = 7)]
    pub since_days: i64,
}

/// `--telemetry` no es nativo (baja física sin passthrough a Python).
pub fn run(tokens: &[String]) -> bool {
    let args = MemoryReportArgs::parse_from(
        std::iter::once("memory-report".to_string()).chain(tokens.iter().cloned()),
    );
    if args.telemetry {
        eprintln!("memory-report --telemetry no nativo en build Rust — el passthrough a Python fue eliminado; usá el CLI Python legacy");
        std::process::exit(1);
    }
    std::process::exit(execute(
        args.project_root.as_deref(),
        &args.scope,
        args.json,
    ));
}

fn resolve(raw: Option<&str>) -> std::path::PathBuf {
    match raw {
        Some(p) => python_resolve(&expand_user(Path::new(p))),
        None => python_resolve(&std::env::current_dir().unwrap_or_default()),
    }
}

fn parse_scope(raw: &str) -> Option<cortex_enterprise::reporting::ReportingScope> {
    use cortex_enterprise::reporting::ReportingScope;
    match raw {
        "local" => Some(ReportingScope::Local),
        "enterprise" => Some(ReportingScope::Enterprise),
        "all" => Some(ReportingScope::All),
        _ => None,
    }
}

pub fn execute(project_root: Option<&str>, scope: &str, json_output: bool) -> i32 {
    use cortex_doctor::native::NativeDoctorBackend;
    use cortex_enterprise::reporting::EnterpriseReportingService;

    let Some(scope_val) = parse_scope(scope) else {
        eprintln!("Invalid --scope value. Use one of: local, enterprise, all.");
        return 1;
    };

    let root = resolve(project_root);
    let layout = cortex_workspace::WorkspaceLayout::discover(&root);
    let service = match EnterpriseReportingService::from_project_root(&root, Some(layout)) {
        Ok(svc) => svc.with_doctor_backend(NativeDoctorBackend::new()),
        Err(err) => {
            eprintln!("{err}");
            return 1;
        }
    };

    // Scope inválido ya filtrado; el servicio mapea local→project etc.
    let report = match service.build_memory_report(scope_val) {
        Ok(report) => report,
        Err(err) => {
            eprintln!("{err}");
            return 1;
        }
    };

    if json_output {
        println!(
            "{}",
            crate::pyjson::stdlib_dumps_indent2(&payload_pyval(&report))
        );
        return 0;
    }

    println!();
    println!("Cortex Enterprise Memory Report");
    println!("-----------------------------");
    println!("Project root: {}", report.project_root);
    // Los f-strings de Python capitalizan los bools (lección P12B-8 #1).
    println!("Enterprise enabled: {}", py_bool(report.enterprise_enabled));
    println!("Scope: {scope}");
    println!();

    for src in &report.sources {
        println!(
            "[{}] vault={}",
            scope_as_str(src.scope),
            src.vault_path.as_deref().unwrap_or("(disabled)")
        );
        println!("  markdown_files: {}", src.markdown_files);
        println!("  validation_errors: {}", src.validation_errors);
        println!("  validation_warnings: {}", src.validation_warnings);
        for note in &src.notes {
            println!("  note: {note}");
        }
        println!();
    }

    let promo = &report.promotion;
    println!("Promotion");
    println!("---------");
    println!("enabled: {}", py_bool(promo.enabled));
    if promo.enabled {
        println!("require_review: {}", py_bool(promo.require_review));
        println!(
            "records_path: {}",
            promo.records_path.as_deref().unwrap_or("None")
        );
        println!("candidates_discovered: {}", promo.candidates_discovered);
        println!(
            "candidates_ready_to_promote: {}",
            promo.candidates_ready_to_promote
        );
        if !promo.latest_events.is_empty() {
            println!("latest_events:");
            for ev in &promo.latest_events {
                let actor = ev
                    .actor
                    .as_ref()
                    .map(|a| format!(" actor={a}"))
                    .unwrap_or_default();
                let at = ev
                    .updated_at
                    .as_ref()
                    .map(|t| format!(" at={t}"))
                    .unwrap_or_default();
                println!("  - {} status={}{}{}", ev.origin_id, ev.status, actor, at);
            }
        }
    }
    if !promo.warnings.is_empty() {
        println!("warnings:");
        for w in &promo.warnings {
            println!("  - {w}");
        }
    }
    0
}

/// `f"{bool}"` de Python: "True"/"False".
fn py_bool(b: bool) -> &'static str {
    if b {
        "True"
    } else {
        "False"
    }
}

fn scope_as_str(scope: cortex_enterprise::reporting::ReportingScope) -> &'static str {
    use cortex_enterprise::reporting::ReportingScope;
    match scope {
        ReportingScope::Local => "local",
        ReportingScope::Enterprise => "enterprise",
        ReportingScope::All => "all",
    }
}

/// Reconstruye `model_dump(mode="json")` en orden pydantic. El campo
/// `doctor` llega como `serde_json::Value` (BTreeMap ⇒ claves ordenadas);
/// se reordenan a la secuencia canónica de `_doctor_to_payload`.
fn payload_pyval(report: &cortex_enterprise::reporting::MemoryReportPayload) -> PyVal {
    PyVal::obj(vec![
        ("generated_at", PyVal::s(&report.generated_at)),
        ("project_root", PyVal::s(&report.project_root)),
        ("enterprise_enabled", PyVal::Bool(report.enterprise_enabled)),
        (
            "sources",
            PyVal::Arr(report.sources.iter().map(source_pyval).collect()),
        ),
        ("promotion", promotion_pyval(&report.promotion)),
        ("doctor", reorder_doctor(&report.doctor)),
    ])
}

fn source_pyval(src: &cortex_enterprise::reporting::MemorySourceReport) -> PyVal {
    PyVal::obj(vec![
        ("scope", PyVal::s(scope_as_str(src.scope))),
        (
            "vault_path",
            src.vault_path.as_ref().map(PyVal::s).unwrap_or(PyVal::Null),
        ),
        (
            "markdown_files",
            PyVal::Num(Num::Int(src.markdown_files as i64)),
        ),
        (
            "validation_errors",
            PyVal::Num(Num::Int(src.validation_errors as i64)),
        ),
        (
            "validation_warnings",
            PyVal::Num(Num::Int(src.validation_warnings as i64)),
        ),
        (
            "notes",
            PyVal::Arr(src.notes.iter().map(PyVal::s).collect()),
        ),
    ])
}

fn promotion_pyval(promo: &cortex_enterprise::reporting::PromotionReport) -> PyVal {
    PyVal::obj(vec![
        ("enabled", PyVal::Bool(promo.enabled)),
        ("require_review", PyVal::Bool(promo.require_review)),
        (
            "records_path",
            promo
                .records_path
                .as_ref()
                .map(PyVal::s)
                .unwrap_or(PyVal::Null),
        ),
        (
            "candidates_discovered",
            PyVal::Num(Num::Int(promo.candidates_discovered as i64)),
        ),
        (
            "candidates_ready_to_promote",
            PyVal::Num(Num::Int(promo.candidates_ready_to_promote as i64)),
        ),
        (
            "latest_events",
            PyVal::Arr(
                promo
                    .latest_events
                    .iter()
                    .map(|ev| {
                        PyVal::obj(vec![
                            ("origin_id", PyVal::s(&ev.origin_id)),
                            ("status", PyVal::s(&ev.status)),
                            (
                                "actor",
                                ev.actor.as_ref().map(PyVal::s).unwrap_or(PyVal::Null),
                            ),
                            (
                                "updated_at",
                                ev.updated_at.as_ref().map(PyVal::s).unwrap_or(PyVal::Null),
                            ),
                        ])
                    })
                    .collect(),
            ),
        ),
        (
            "warnings",
            PyVal::Arr(promo.warnings.iter().map(PyVal::s).collect()),
        ),
    ])
}

/// Reordena `{checks, has_failures, has_warnings, project_root}` (alfabético)
/// al orden pydantic `{project_root, checks, has_failures, has_warnings}` con
/// checks `{name, ok, severity, detail}`.
fn reorder_doctor(doctor: &serde_json::Value) -> PyVal {
    let obj = match doctor.as_object() {
        Some(obj) => obj,
        None => return json_to_pyval(doctor),
    };
    let get = |key: &str| obj.get(key).map(json_to_pyval).unwrap_or(PyVal::Null);
    PyVal::obj(vec![
        ("project_root", get("project_root")),
        (
            "checks",
            match obj.get("checks").and_then(|v| v.as_array()) {
                Some(items) => PyVal::Arr(items.iter().map(reorder_check).collect()),
                None => PyVal::Arr(vec![]),
            },
        ),
        ("has_failures", get("has_failures")),
        ("has_warnings", get("has_warnings")),
    ])
}

fn reorder_check(check: &serde_json::Value) -> PyVal {
    let obj = match check.as_object() {
        Some(obj) => obj,
        None => return json_to_pyval(check),
    };
    let get = |key: &str| obj.get(key).map(json_to_pyval).unwrap_or(PyVal::Null);
    PyVal::obj(vec![
        ("name", get("name")),
        ("ok", get("ok")),
        ("severity", get("severity")),
        ("detail", get("detail")),
    ])
}

fn json_to_pyval(v: &serde_json::Value) -> PyVal {
    match v {
        serde_json::Value::Null => PyVal::Null,
        serde_json::Value::Bool(b) => PyVal::Bool(*b),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                PyVal::Num(Num::Int(i))
            } else {
                PyVal::Num(Num::Float(n.as_f64().unwrap_or(0.0)))
            }
        }
        serde_json::Value::String(s) => PyVal::s(s),
        serde_json::Value::Array(items) => PyVal::Arr(items.iter().map(json_to_pyval).collect()),
        serde_json::Value::Object(map) => PyVal::Obj(
            map.iter()
                .map(|(k, v)| (k.clone(), json_to_pyval(v)))
                .collect(),
        ),
    }
}
