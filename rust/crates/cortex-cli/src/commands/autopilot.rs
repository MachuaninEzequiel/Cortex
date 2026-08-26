//! `cortex autopilot preflight` — puerto de cortex/autopilot/cli.py.
//!
//! Solo `preflight` es wireado (capa de decisión pura, sin sesiones —
//! decisión P12B-5). start/checkpoint/finish/status/doctor caen al
//! passthrough (external_subcommand).

use clap::Parser;

use cortex_autopilot::detectors::{default_detectors, resolve_detectors};
use cortex_autopilot::models::DetectionRequest;

use crate::pyjson::PyVal;

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
    /// Comandos no wireados (start/checkpoint/finish/status/doctor) → passthrough.
    #[command(external_subcommand)]
    Other(Vec<String>),
}

pub fn run(tokens: &[String]) -> bool {
    let args = AutopilotArgs::parse_from(
        std::iter::once("autopilot".to_string()).chain(tokens.iter().cloned()),
    );
    match args.cmd {
        AutopilotCmd::Preflight {
            request,
            files,
            json,
            ..
        } => {
            std::process::exit(execute(request.as_deref(), &files, json));
        }
        AutopilotCmd::Other(_) => false,
    }
}

/// `_emit`: texto `k: v` o `json.dumps(payload, indent=2)`.
fn emit(payload: &PyVal, keys: &[&str], values: &[String], json_mode: bool) {
    if json_mode {
        println!("{}", crate::pyjson::stdlib_dumps_indent2(payload));
        return;
    }
    for (key, value) in keys.iter().zip(values.iter()) {
        println!("{key}: {value}");
    }
}

pub fn execute(request: Option<&str>, files: &[String], json_output: bool) -> i32 {
    let detectors = default_detectors();
    let result = resolve_detectors(
        &detectors,
        &DetectionRequest {
            user_request: request.map(str::to_string),
            changed_files: files.to_vec(),
            git_diff_stat: None,
            session_state: None,
        },
    );

    // confidence float → repr Python vía stdlib writer (Num::Float).
    let payload = PyVal::obj(vec![
        ("task_type", PyVal::s(&result.task_type)),
        (
            "confidence",
            PyVal::Num(crate::pyjson::Num::Float(result.confidence)),
        ),
        ("reason", PyVal::s(&result.reason)),
        (
            "suggested_complexity",
            PyVal::s(&result.suggested_complexity),
        ),
    ]);
    let keys = ["task_type", "confidence", "reason", "suggested_complexity"];
    let values = [
        result.task_type.clone(),
        crate::pyjson::format_float(result.confidence),
        result.reason.clone(),
        result.suggested_complexity.clone(),
    ];
    emit(&payload, &keys, &values, json_output);
    0
}
