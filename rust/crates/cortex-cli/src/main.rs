// cortex-cli — fachada nativa de arranque instantáneo (Gate G6, decisión
// del dueño 2026-08-24b: "fachada sobre CLI Python").
//
// Los servicios (session/actions/context/documenter…) siguen Python hasta
// Obra E: este binario reenvía TODO el argv al CLI existente con stdio
// heredado, así que la salida —incluida --json— es idéntica por construcción
// (paridad G6). Lo único nativo hoy es el arranque y `--cli-version`.
//
// Nota de diseño: el plan original mencionaba clap, pero declarar
// subcomandos en clap interceptaría los --help/--json del CLI real y rompería
// la paridad. El passthrough puro es el contrato correcto para una fachada.
// Cuando los servicios migren a Rust (Obra E), los subcomands nativos se
// agregan acá sin tocar la fachada.
//
// Override para tests/desarrollo: env CORTEX_BIN.

use std::io::Write;
use std::process::Command;

/// Versión de esta fachada nativa.
const CLI_VERSION: &str = "0.1.0";

const AYUDA_FACHADA: &str = "\
cortex-cli {CLI_VERSION} — fachada nativa del CLI Cortex.

Uso: cortex-cli <COMANDO [args…]>   (reenvía al CLI Cortex tal cual)

El binario `cortex` resuelve en este orden:
  1. $CORTEX_BIN si está definido
  2. `cortex` en PATH

Flags propias de esta fachada (no se reenvían):
  --cli-version    versión del binario nativo

Todo lo demás —incluidos --help, --version y --json— se reenvía sin tocar:
la salida es idéntica a `cortex …` porque ES `cortex …`.";

fn main() {
    let argv: Vec<String> = std::env::args().skip(1).collect();

    match argv.first().map(String::as_str) {
        Some("--cli-version") => {
            println!("cortex-cli {CLI_VERSION}");
            std::process::exit(0);
        }
        Some("--help") | Some("-h") if argv.len() == 1 => {
            println!("{AYUDA_FACHADA}");
            std::process::exit(0);
        }
        _ => {}
    }

    let bin = std::env::var("CORTEX_BIN").unwrap_or_else(|_| String::from("cortex"));

    let status = Command::new(&bin)
        .args(&argv)
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
