//! Binario `cortex-brain` — chat loop interactivo (stdin/stdout).
//!
//! Modo default: determinista (--no-model, spec BRAIN-1). El backend
//! llama.cpp/GGUF se conecta vía trait LlmBackend en el próximo incremento.

use cortex_brain::chat::{help_text, DeterministicBackend, LlmBackend, BANNER};
use cortex_brain::router::route_intent;
use cortex_brain::tools::build_tools;
use std::io::{BufRead, Write};

struct Args {
    project_root: Option<String>,
    model: bool,
}

fn parse_args() -> Args {
    let mut args = Args {
        project_root: None,
        model: false,
    };
    let mut it = std::env::args().skip(1);
    while let Some(a) = it.next() {
        match a.as_str() {
            "--project-root" => args.project_root = it.next(),
            "--model" => args.model = true,
            "--no-model" => args.model = false,
            "--help" | "-h" => {
                println!(
                    "cortex-brain — asistente local experto de ESTE proyecto\n\n\
                     Uso: cortex-brain [--project-root <ruta>] [--no-model|--model]\n\n\
                     --no-model  router determinista, cero tokens (default hoy)\n\
                     --model     backend LLM llama.cpp/GGUF (BRAIN-2, pendiente)\n\nEl brain NUNCA ejecuta mutaciones: propone el comando exacto."
                );
                std::process::exit(0);
            }
            other => {
                eprintln!("argumento desconocido: {other} (usá --help)");
                std::process::exit(1);
            }
        }
    }
    args
}

fn main() {
    let args = parse_args();
    if let Some(root) = &args.project_root {
        let _ = std::env::set_current_dir(root);
    }

    // ── Banner ≤80 columnas (spec test_banner_renderiza_en_80) ──
    for line in BANNER.lines() {
        assert!(line.chars().count() <= 80, "banner excede 80 columnas");
        println!("{line}");
    }
    println!("🧠 cortex-brain — backend: determinista (sin modelo)");
    if args.model {
        println!(
            "--model: backend llama.cpp/GGUF aún no integrado; se usa el router determinista."
        );
    }
    println!("{}", help_text());
    let _ = std::io::stdout().flush();

    let tools = build_tools();
    let _ = &tools; // catálogo expuesto vía /help; dispatch valida por nombre

    let stdin = std::io::stdin();
    let mut backend = DeterministicBackend;
    for line in stdin.lock().lines() {
        let Ok(line) = line else { break };
        let texto = line.trim();
        if texto.is_empty() {
            continue;
        }
        if route_intent(texto).slash.as_deref() == Some("quit") {
            println!("¡hasta la próxima!");
            break;
        }
        match backend.generate(texto, "") {
            Ok(out) => {
                if out == "/quit" {
                    println!("¡hasta la próxima!");
                    break;
                }
                println!("{out}\n");
            }
            Err(e) => println!("⚠ {e}\n"),
        }
        let _ = std::io::stdout().flush();
    }
}
