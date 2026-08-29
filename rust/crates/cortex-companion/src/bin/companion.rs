//! Binario `cortex-companion` (B4-B8): render de Home, Menu, Sessions,
//! Actions, Search y Brain con ratatui + crossterm, mouse-first.

#![forbid(unsafe_code)]

use cortex_companion::runner::run_app;
use cortex_companion::CompanionMode;
use std::path::PathBuf;

fn main() {
    let (root, model, mode) = parse_args();
    run_app(mode, root, model);
}

fn parse_args() -> (PathBuf, Option<String>, CompanionMode) {
    let mut project_root: Option<String> = None;
    let mut model: Option<String> = None;
    let mut mode = CompanionMode::Normal;
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
            "--mode" => match args.next().as_deref() {
                Some("sidecar") => mode = CompanionMode::Sidecar,
                Some("float") => mode = CompanionMode::Float,
                Some("copilot") => mode = CompanionMode::Copilot,
                Some("normal") => mode = CompanionMode::Normal,
                Some(other) => {
                    eprintln!("modo desconocido: '{other}' (use: normal, sidecar, float, copilot)");
                    std::process::exit(2);
                }
                None => {
                    eprintln!("--mode requiere un valor (normal, sidecar, float, copilot)");
                    std::process::exit(2);
                }
            },
            "--model" => match args.next() {
                Some(v) if !v.starts_with("--") => model = Some(v),
                _ => {
                    eprintln!("--model requiere la ruta de un GGUF (--model <ruta>)");
                    std::process::exit(2);
                }
            },
            "--no-model" => model = None,
            "-h" | "--help" => {
                println!(
                    "Uso: cortex-companion [--project-root <ruta>] [--mode <normal|sidecar|float|copilot>] [--model <gguf>|--no-model]"
                );
                std::process::exit(0);
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
    (root, model, mode)
}
