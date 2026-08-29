//! Binario `cortex-herdr-sidecar`: Abre el Companion en modo Sidecar (dock lateral izquierdo).

use cortex_companion::herdr;
use cortex_companion::runner::run_app;
use cortex_companion::CompanionMode;
use std::path::PathBuf;

fn main() {
    let mut spawn = false;
    let mut project_root: Option<String> = None;
    let mut model: Option<String> = None;
    let mut args = std::env::args().skip(1);

    while let Some(a) = args.next() {
        match a.as_str() {
            "--spawn" => spawn = true,
            "--project-root" => match args.next() {
                Some(v) => project_root = Some(v),
                None => {
                    eprintln!("--project-root requiere un valor");
                    std::process::exit(2);
                }
            },
            "--model" => match args.next() {
                Some(v) if !v.starts_with("--") => model = Some(v),
                _ => {
                    eprintln!("--model requiere una ruta");
                    std::process::exit(2);
                }
            },
            "-h" | "--help" => {
                println!("Uso: cortex-herdr-sidecar [--spawn] [--project-root <ruta>]");
                std::process::exit(0);
            }
            _ => {}
        }
    }

    let root = match project_root {
        Some(p) => PathBuf::from(p),
        None => std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")),
    };

    if spawn {
        if let Err(e) = herdr::spawn_split_sidecar(&root) {
            eprintln!("Error al abrir sidecar en Herdr: {e}");
            std::process::exit(1);
        }
        return;
    }

    run_app(CompanionMode::Sidecar, root, model);
}
