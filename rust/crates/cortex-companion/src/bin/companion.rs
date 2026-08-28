//! Binario `cortex-companion` (G-B1): arranque mínimo y snapshot no-TTY.
//!
//! B3+ lo convierte en la app ratatui mouse-first. Por ahora: parseo manual
//! de `--project-root`, apertura del backend in-proceso y estado en stdout.

use std::path::PathBuf;

fn main() {
    let mut project_root: Option<String> = None;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--project-root" => match args.next() {
                Some(v) => project_root = Some(v),
                None => {
                    eprintln!("--project-root requiere un valor");
                    std::process::exit(2);
                }
            },
            "-h" | "--help" => {
                println!("Uso: cortex-companion [--project-root <ruta>]");
                return;
            }
            _ => {
                eprintln!("argumento desconocido: '{a}'");
                std::process::exit(2);
            }
        }
    }

    let root = match project_root {
        Some(p) => PathBuf::from(p),
        None => std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")),
    };

    match cortex_companion::engine::InProcessBackend::open(&root) {
        Ok(be) => {
            println!(
                "Cortex Companion (obra08, WIP) — project: {}",
                be.root.display()
            );
        }
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(1);
        }
    }
}
