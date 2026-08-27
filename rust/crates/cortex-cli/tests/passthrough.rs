//! Baja física: la fachada de passthrough a Python fue ELIMINADA.
//!
//! Antes (G6): `CORTEX_BIN` apuntaba al binario destino y el argv se
//! reenviaba byte-a-byte con stdio/rc propagados. Post-BAJA DEFINITIVA no
//! existe ningún reenvío a Python: `CORTEX_BIN`/`CORTEX_PY` no se consultan
//! y todo comando desconocido falla nativamente con rc 2.
//!
//! Estos tests fijan el contrato residual: la variable CORTEX_BIN dejó de
//! tener efecto (nunca se ejecuta un binario externo) y el arranque nativo
//! sigue siendo instantáneo.

use std::process::Command;

/// Corre el binario con CORTEX_BIN "roto" y devuelve (stdout, stderr, rc).
fn run(bin: &std::path::Path, args: &[&str]) -> (String, String, Option<i32>) {
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
fn cortex_bin_is_no_op_no_external_execution() {
    // Un script ejecutable de prueba como CORTEX_BIN: si el passthrough
    // existiera, `bogus` reenviaría argv y veríamos su stdout. Post-baja no
    // se ejecuta NADA externo ⇒ stdout vacío y error nativo rc 2.
    let tmp = tempfile::tempdir().unwrap();
    let stub = tmp.path().join("stub");
    std::fs::write(&stub, "#!/bin/sh\necho 'NO DEBE APARECER'\n").unwrap();
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        std::fs::set_permissions(&stub, std::fs::Permissions::from_mode(0o755)).unwrap();
    }
    let (f_out, f_err, f_code) = run(stub.as_path(), &["bogus"]);
    assert_eq!(f_out, "");
    assert_eq!(f_err, "No such command 'bogus'.\n");
    assert_eq!(f_code, Some(2));
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
