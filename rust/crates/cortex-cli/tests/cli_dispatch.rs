//! Tests de dispatch del binario cortex-cli (P12B-8).
//!
//! Contrato (diseño aprobado en progreso-p12b.md):
//! 1. `CORTEX_PY=1` → passthrough TOTAL inmediato (antes de cualquier
//!    dispatch nativo, incluso `--cli-version`).
//! 2. `--cli-version` → línea nativa `cortex-cli <versión>` rc=0.
//! 3. argv desconocido → reenvío byte-idéntico del argv original al CLI
//!    Python (`CORTEX_BIN` override), heredando stdio y propagando el rc.

use std::process::Command;

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
}

#[test]
fn cli_version_is_native() {
    let out = bin().arg("--cli-version").output().unwrap();
    assert!(out.status.success());
    assert_eq!(
        String::from_utf8_lossy(&out.stdout).trim_end(),
        "cortex-cli 0.1.0"
    );
}

#[test]
fn cortex_py_is_checked_before_native_dispatch() {
    // CORTEX_PY=1 + --cli-version delega al binario externo aunque el flag
    // sería nativo: prueba que el rollback se evalúa primero.
    let out = bin()
        .env("CORTEX_PY", "1")
        .env("CORTEX_BIN", "/bin/false") // existe y termina rc=1
        .arg("--cli-version")
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(1));
}

#[test]
fn unknown_command_passes_through_original_argv() {
    let out = bin()
        .env("CORTEX_PY", "1")
        .env("CORTEX_BIN", "/bin/echo")
        .args(["frobnicate", "--x", "1"])
        .output()
        .unwrap();
    assert!(out.status.success());
    assert_eq!(String::from_utf8_lossy(&out.stdout), "frobnicate --x 1\n");
}

#[test]
fn missing_python_bin_reports_127_with_contract_message() {
    let out = bin()
        .env("CORTEX_PY", "1")
        .env("CORTEX_BIN", "/no/existe/cortex-bin-xyz")
        .arg("--version")
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(127));
    let err = String::from_utf8_lossy(&out.stderr);
    assert!(
        err.contains("cortex-cli: no pude ejecutar"),
        "mensaje contractual ausente: {err}"
    );
}
