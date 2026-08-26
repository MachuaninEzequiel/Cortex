//! Passthrough residual al CLI Python (contrato fachada G6 preservado).
//!
//! El argv ORIGINAL se reenvía byte-idéntico: stdin/stdout/stderr heredados,
//! exit code propagado. Es la vía por la que viajan todos los comandos no
//! wireados y el mecanismo del rollback `CORTEX_PY=1`.

use std::io::Write;
use std::process::Command;

/// Resolución del CLI Python: `CORTEX_BIN` override, si no `cortex` en PATH.
pub fn python_bin() -> String {
    std::env::var("CORTEX_BIN").unwrap_or_else(|_| String::from("cortex"))
}

/// Reenvía `argv` tal cual al CLI Python y sale con su código de salida.
/// Nunca retorna.
pub fn passthrough(argv: &[String]) -> ! {
    let bin = python_bin();

    let status = Command::new(&bin)
        .args(argv)
        .stdin(std::process::Stdio::inherit())
        .stdout(std::process::Stdio::inherit())
        .stderr(std::process::Stdio::inherit())
        .status();

    match status {
        Ok(s) => std::process::exit(s.code().unwrap_or(1)),
        Err(e) => {
            let _ = writeln!(
                std::io::stderr(),
                "cortex-cli: no pude ejecutar '{bin}' ({e}).\n\
                 Instalá Cortex (pip install -e .) o apuntá CORTEX_BIN al CLI."
            );
            std::process::exit(127);
        }
    }
}
