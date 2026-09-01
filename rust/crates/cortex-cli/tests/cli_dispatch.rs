//! Tests de dispatch del binario cortex-cli (P12B-8, baja física actualizados).
//!
//! Contrato post-BAJA DEFINITIVA (fase física, head `6612449`+):
//! 1. `CORTEX_PY=1` → aviso histórico en stderr y CONTINÚA nativo (el
//!    rollback a Python fue eliminado; CORTEX_BIN ya no se consulta).
//! 2. `--cli-version` → línea nativa `cortex-cli <versión>` rc=0.
//! 3. argv desconocido → error nativo Typer-like `No such command '<first>'.`
//!    rc=2 (NUNCA delega al CLI Python).

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
fn cortex_py_is_historical_and_native_continues() {
    // CORTEX_PY=1 ya NO delega: imprime el aviso histórico en stderr y el
    // flag --cli-version sigue siendo nativo (antes llegaba al Python).
    let out = bin()
        .env("CORTEX_PY", "1")
        .env("CORTEX_BIN", "/bin/false") // irrelevante: no se ejecuta
        .arg("--cli-version")
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(0));
    assert_eq!(
        String::from_utf8_lossy(&out.stdout).trim_end(),
        "cortex-cli 0.1.0"
    );
    let err = String::from_utf8_lossy(&out.stderr);
    assert!(
        err.contains("CORTEX_PY=1 es rollback histórico de la migración"),
        "aviso histórico ausente: {err}"
    );
}

#[test]
fn unknown_command_reports_no_such_command_rc2() {
    // Con CORTEX_BIN apuntando a /bin/echo: el catch-all es nativo
    // (`No such command`) y nunca reenvía el argv al CLI Python (antes
    // habría impreso "frobnicate --x 1").
    let out = bin()
        .env("CORTEX_BIN", "/bin/echo")
        .args(["frobnicate", "--x", "1"])
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(2));
    assert_eq!(String::from_utf8_lossy(&out.stdout), "");
    assert_eq!(
        String::from_utf8_lossy(&out.stderr),
        "No such command 'frobnicate'.\n"
    );
}

#[test]
fn missing_python_bin_is_irrelevant_no_delegation() {
    // CORTEX_BIN inexistente ya no produce 127: no hay passthrough que
    // ejecute Python. `--version` es un flag NATIVO (rc 0, estándar que
    // las integraciones esperan); un token no wireado (frobnicate) sigue
    // siendo comando desconocido ⇒ rc 2.
    let out = bin()
        .env("CORTEX_BIN", "/no/existe/cortex-bin-xyz")
        .arg("--version")
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(0));
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(
        stdout.contains("cortex-cli 0.1.0") || stdout.starts_with("cortex-cli"),
        "salida de --version: {stdout}"
    );
}
