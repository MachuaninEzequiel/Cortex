// Binario `cortex-brain` — chat loop interactivo (stdin/stdout).
//
// Modo default: determinista (--no-model, spec BRAIN-1). El backend
// llama.cpp/GGUF se conecta vía trait LlmBackend con --features llama.

use std::io::{BufRead, Write};

use cortex_brain::chat::{help_text, DeterministicBackend, LlmBackend, BANNER};
#[cfg(feature = "llama")]
use cortex_brain::llama::{model_path_default, LlamaChatBackend};
use cortex_brain::router::route_intent;
use cortex_brain::tools::{build_tools, Tier};

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
                     --model     backend LLM llama.cpp/GGUF (requiere --features llama)\n\nEl brain NUNCA ejecuta mutaciones: propone el comando exacto."
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

    // ── Backend según flags/feature ──
    #[cfg(feature = "llama")]
    let model_path = model_path_default();
    #[cfg(feature = "llama")]
    let mut backend: Box<dyn LlmBackend> = if args.model && model_path.exists() {
        println!("🧠 cargando GGUF: {}", model_path.display());
        let system = format!(
            "Sos el asistente local de Cortex, experto en ESTE proyecto.\n\n{}\nReglas estrictas:\n- NUNCA ejecutás mutaciones: proponés el comando CLI exacto para que el usuario lo corra.\n- Respondé breve y citá rutas reales cuando uses herramientas.",
            help_text()
        );
        match LlamaChatBackend::open(&model_path, Some(&system)) {
            Ok(b) => Box::new(b),
            Err(e) => {
                println!("⚠ no pude cargar el modelo ({e}); modo determinista.");
                Box::new(DeterministicBackend)
            }
        }
    } else {
        if args.model {
            println!(
                "⚠ --model pero no existe {} o el binario se compiló sin --features llama; modo determinista.",
                model_path.display()
            );
        }
        Box::new(DeterministicBackend)
    };

    #[cfg(not(feature = "llama"))]
    let mut backend: Box<dyn LlmBackend> = {
        if args.model {
            println!("⚠ binario sin feature llama; modo determinista.");
        }
        Box::new(DeterministicBackend)
    };

    println!("🧠 cortex-brain — backend: {}", backend.name());
    println!("{}", help_text());
    let _ = std::io::stdout().flush();

    let stdin = std::io::stdin();
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
        // El LLM conoce el catálogo para decidir entre responder o sugerir
        // la herramienta; la EJECUCIÓN sigue siendo del brain (nunca del modelo).
        let catalogo: String = build_tools()
            .values()
            .map(|t| {
                let tier = match t.tier {
                    Tier::Read => "read",
                    Tier::SafeAction => "safe",
                };
                format!("- {} [{}] {}", t.name, tier, t.args_hint)
            })
            .collect::<Vec<_>>()
            .join("\n");
        match backend.generate(texto, &catalogo) {
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
