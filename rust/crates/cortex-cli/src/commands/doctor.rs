//! `cortex doctor` — puerto de la presentación de cli/main.py.
//!
//! Contrato de salida (main.py::doctor):
//! - check.ok            → stdout `[OK] {name}: {detail}`
//! - severity == "fail"  → stderr `[FAIL] {name}: {detail}`
//! - severity == "warn"  → stdout `[WARN] {name}: {detail}`
//! - resto (info)        → stdout `[INFO] {name}: {detail}`
//! - rc=1 si `has_failures`; rc=1 si `--strict` y `has_warnings`.
//!
//! Los checks stub contractuales (STUB_TABLE, P12B-4/P12B-5) emiten
//! `backend no nativo aún (<módulo>)`; el oráculo del gate normaliza el
//! lado Python al mismo texto antes de comparar.

use std::io::Write;

use clap::Parser;
use cortex_doctor::doctor::{run_doctor, DoctorScope};

use crate::paths::resolve_project_root;

#[derive(Parser, Debug)]
#[command(
    name = "doctor",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct DoctorArgs {
    /// Absolute path to the target project root (where config.yaml lives).
    #[arg(long)]
    pub project_root: Option<String>,

    /// Fail on warnings as well as hard errors.
    #[arg(long)]
    pub strict: bool,

    /// Validation scope: project, enterprise, or all.
    #[arg(long, default_value = "project")]
    pub scope: ScopeArg,
}

#[derive(Clone, Copy, Debug, clap::ValueEnum)]
pub enum ScopeArg {
    Project,
    Enterprise,
    All,
}

impl From<ScopeArg> for DoctorScope {
    fn from(value: ScopeArg) -> Self {
        match value {
            ScopeArg::Project => DoctorScope::Project,
            ScopeArg::Enterprise => DoctorScope::Enterprise,
            ScopeArg::All => DoctorScope::All,
        }
    }
}

/// Parsea `tokens` con clap (errores de args ⇒ self-golden, rc=2) y ejecuta.
/// Siempre retorna true: el subárbol es nuestro.
pub fn run(tokens: &[String]) -> bool {
    let args =
        DoctorArgs::parse_from(std::iter::once("doctor".to_string()).chain(tokens.iter().cloned()));
    let root = resolve_project_root(args.project_root.as_deref());
    std::process::exit(execute(&root, args.strict, args.scope.into()));
}

/// Ejecuta el doctor y devuelve el código de salida.
pub fn execute(root: &std::path::Path, strict: bool, scope: DoctorScope) -> i32 {
    let report = match run_doctor(root, scope) {
        Ok(report) => report,
        Err(err) => {
            let _ = writeln!(std::io::stderr(), "Failed to run doctor: {err}");
            return 1;
        }
    };

    let mut stdout = std::io::stdout().lock();
    let mut stderr = std::io::stderr().lock();
    for check in &report.checks {
        if check.ok {
            let _ = writeln!(stdout, "[OK] {}: {}", check.name, check.detail);
        } else if check.severity == "fail" {
            let _ = writeln!(stderr, "[FAIL] {}: {}", check.name, check.detail);
        } else if check.severity == "warn" {
            let _ = writeln!(stdout, "[WARN] {}: {}", check.name, check.detail);
        } else {
            let _ = writeln!(stdout, "[INFO] {}: {}", check.name, check.detail);
        }
    }
    let _ = stdout.flush();
    let _ = stderr.flush();

    if report.has_failures() {
        return 1;
    }
    if strict && report.has_warnings() {
        return 1;
    }
    0
}
