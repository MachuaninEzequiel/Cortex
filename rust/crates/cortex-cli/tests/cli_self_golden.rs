//! SELF-GOLDEN P12B-8: textos de ayuda y errores de args del binario clap.
//!
//! Decisión del dueño: Typer y clap formatean distinto por diseño ⇒ estos
//! bytes se congelan (self-golden) en vez de replicar el render de Typer.
//! Divergencia cosmética documentada, mismo precedente que el ANSI del
//! tutor (P12B-7). La paridad funcional live vive en cli_golden_p12b.py.

use std::process::Command;

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
}

const HELP_ROOT: &str = r#"Cortex -- hybrid cognitive memory for AI agents (CLI nativo)

Usage: cortex-cli [COMMAND]

Commands:
  doctor             Validate Cortex runtime prerequisites and governance state
  tutor              Guía interactiva offline de Cortex. Zero tokens.
  hint               Tip contextual: qué hacer ahora con Cortex. Zero tokens.
  org-config         Display the resolved enterprise organization config
  promote-knowledge  Promote reviewed knowledge candidates into the enterprise vault
  review-knowledge   Enterprise review queue (pending/approve/reject/candidate)
  memory-report      Report enterprise memory health and promotion visibility
  webgraph           Webgraph snapshots (export/serve/doctor nativos)
  autopilot          Autopilot decision layer (subarbol 100% nativo)
  agent-guidelines   Display agent behavior guidelines
  install-skills     Install Obsidian skills into the project

Options:
  -h, --help  Print help

CLI 100% nativo (sin passthrough a Python). Instalá por binario: `cargo install --path rust/crates/cortex-cli`.
"#;

#[test]
fn selfgolden_root_help() {
    let out = bin().arg("--help").output().unwrap();
    assert!(out.status.success());
    assert_eq!(String::from_utf8_lossy(&out.stdout), HELP_ROOT);
    // -h es equivalente.
    let out_h = bin().arg("-h").output().unwrap();
    assert_eq!(String::from_utf8_lossy(&out_h.stdout), HELP_ROOT);
}

const HELP_DOCTOR: &str = r#"Usage: doctor [OPTIONS]

Options:
      --project-root <PROJECT_ROOT>  Absolute path to the target project root (where config.yaml lives)
      --strict                       Fail on warnings as well as hard errors
      --scope <SCOPE>                Validation scope: project, enterprise, or all [default: project] [possible values: project, enterprise, all]
  -h, --help                         Print help
"#;

#[test]
fn selfgolden_doctor_help() {
    let out = bin().args(["doctor", "--help"]).output().unwrap();
    assert!(out.status.success());
    assert_eq!(String::from_utf8_lossy(&out.stdout), HELP_DOCTOR);
}

const REJECT_MISSING_REASON: &str = "error: one or more required arguments were not provided
";

#[test]
fn selfgolden_review_reject_missing_reason() {
    let tmp = tempfile::tempdir().unwrap();
    let out = bin()
        .envs([
            ("USER", "tester"),
            ("LOGNAME", "tester"),
            ("LNAME", "tester"),
            ("USERNAME", "tester"),
        ])
        .args([
            "review-knowledge",
            "reject",
            "specs/x.md",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(2));
    assert_eq!(String::from_utf8_lossy(&out.stderr), REJECT_MISSING_REASON);
}

#[test]
fn selfgolden_tutor_slug_prints_embedded_content() {
    // tutor <slug> es self-golden por la divergencia cosmética ~98 col
    // heredada de P12B-7: los bytes deben ser EXACTAMENTE los embebidos.
    let body = cortex_tutor::engine::show_topic_by_slug("pipeline").unwrap();
    let out = bin().args(["tutor", "pipeline"]).output().unwrap();
    assert!(out.status.success());
    let stdout = String::from_utf8_lossy(&out.stdout);
    let expected = if body.ends_with('\n') {
        body.clone()
    } else {
        format!("{body}\n")
    };
    assert_eq!(stdout, expected);
}
