//! Paridad G6: la fachada reenvía argv byte-a byte (stdout, stderr y código
//! de salida idénticos a llamar el binario destino directamente).

use std::path::{Path, PathBuf};
use std::process::Command;

/// Script destino de prueba: imprime stdout+stderr y sale con código dado.
fn escribir_stub(dir: &Path, nombre: &str, rc: i32) -> PathBuf {
    let ruta = dir.join(nombre);
    std::fs::write(
        &ruta,
        format!(
            "#!/bin/sh\necho 'línea stdout {nombre}'\necho 'línea stderr {nombre}' >&2\nexit {rc}\n"
        ),
    )
    .unwrap();
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        std::fs::set_permissions(&ruta, std::fs::Permissions::from_mode(0o755)).unwrap();
    }
    ruta
}

/// Corre la fachada con CORTEX_BIN=bin y devuelve (stdout, stderr, rc).
fn facade(bin: &Path, args: &[&str]) -> (String, String, Option<i32>) {
    let out = Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
        .env("CORTEX_BIN", bin)
        .args(args)
        .output()
        .unwrap();
    (
        String::from_utf8_lossy(&out.stdout).into_owned(),
        String::from_utf8_lossy(&out.stderr).into_owned(),
        out.status.code(),
    )
}

#[test]
fn passthrough_stdout_stderr_y_codigo_de_salida() {
    let tmp = tempfile::tempdir().unwrap();
    let stub = escribir_stub(tmp.path(), "stub-ok", 3);

    // Directo (referencia):
    let directo = Command::new(&stub).arg("extra").output().unwrap();
    // Vía fachada:
    let (f_out, f_err, f_code) = facade(stub.as_path(), &["extra"]);

    assert_eq!(f_out, String::from_utf8_lossy(&directo.stdout));
    assert_eq!(f_err, String::from_utf8_lossy(&directo.stderr));
    assert_eq!(f_code, directo.status.code());
}

#[test]
fn cli_version_nativa_rapida() {
    let inicio = std::time::Instant::now();
    let out = Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
        .arg("--cli-version")
        .output()
        .unwrap();
    let ms = inicio.elapsed().as_millis();
    assert!(out.status.success());
    assert!(ms < 50, "startup {ms}ms >= 50ms");
}
