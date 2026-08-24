// Binario `cortex-brain` — chat loop interactivo (stdin/stdout).
//
// Modo default: determinista (--no-model, spec BRAIN-1). El backend
// llama.cpp/GGUF se conecta vía trait LlmBackend con --features llama.

use cortex_brain::chat::{
    confirma, help_text, procesar_respuesta_modelo, DeterministicBackend, LlmBackend, BANNER,
};
use cortex_brain::i18n;
#[cfg(feature = "llama")]
use cortex_brain::llama::{model_path_default, LlamaChatBackend};
use cortex_brain::router::route_intent;
use cortex_brain::tools::{build_tools, Tier, ToolSpec};
use std::collections::BTreeMap;
use std::io::{BufRead, Write};

struct Args {
    project_root: Option<String>,
    model: bool,
    temp: f32,
    seed: u32,
    window: bool,
}

fn parse_args() -> Args {
    let mut args = Args {
        project_root: None,
        model: false,
        temp: 0.0,
        seed: 42,
        window: false,
    };
    let mut it = std::env::args().skip(1);
    while let Some(a) = it.next() {
        match a.as_str() {
            "--project-root" => args.project_root = it.next(),
            "--model" => args.model = true,
            "--no-model" => args.model = false,
            "--temp" => args.temp = it.next().and_then(|v| v.parse().ok()).unwrap_or(0.0),
            "--seed" => args.seed = it.next().and_then(|v| v.parse().ok()).unwrap_or(42),
            "--window" => args.window = true,
            "--help" | "-h" => {
                println!(
                    "cortex-brain — asistente local experto de ESTE proyecto\n\n\
                     Uso: cortex-brain [--project-root <ruta>] [--no-model|--model]\n\
                          [--temp <f>] [--seed <n] [--window]\n\n\
                     --no-model  router determinista, cero tokens (default hoy)\n\
                     --model     backend LLM llama.cpp/GGUF (requiere --features llama)\n\
                     --temp      temperatura (>0 activa muestreo; 0 = greedy)\n\
                     --seed      semilla del muestreo (default 42)\n\
                     --window    abre el brain en una terminal dedicada\n\nEl brain NUNCA ejecuta mutaciones: propone el comando exacto."
                );
                std::process::exit(0);
            }
            other => {
                eprintln!("{}", i18n::warn_arg_desconocido(i18n::actual(), other));
                std::process::exit(1);
            }
        }
    }
    args
}

/// Confirmación con IO real: muestra la sugerencia y pide [s/N] por stdin.
/// La DECISIÓN vive en `chat::confirma` (testeable); acá solo hay IO.
fn confirmar_ejecucion(
    tool: &str,
    args_tool: &str,
    tools: &BTreeMap<&'static str, ToolSpec>,
) -> bool {
    let lang = i18n::actual();
    let Some(spec) = tools.get(tool) else {
        println!("{}", i18n::tool_inexistente(lang, tool));
        return false;
    };
    let etiqueta = match spec.tier {
        Tier::Read => "read",
        Tier::SafeAction => "safe-action",
    };
    println!("{}", i18n::sugerencia(lang, etiqueta, tool, args_tool));
    print!("{}", i18n::prompt_confirmar(lang, tool, args_tool));
    let _ = std::io::stdout().flush();
    let mut ok = String::new();
    let aprobado = std::io::stdin().read_line(&mut ok).is_ok() && confirma(&ok);
    if !aprobado {
        println!("{}", i18n::no_ejecutado(lang));
    }
    aprobado
}

/// Catálogo compacto para el prompt del LLM.
fn catalogo_tools() -> String {
    build_tools()
        .values()
        .map(|t| {
            let tier = match t.tier {
                Tier::Read => "read",
                Tier::SafeAction => "safe",
            };
            format!("- {} [{}] {}", t.name, tier, t.args_hint)
        })
        .collect::<Vec<_>>()
        .join("\n")
}

fn main() {
    let args = parse_args();
    if let Some(root) = &args.project_root {
        let _ = std::env::set_current_dir(root);
    }
    // Idioma del chrome (i18n): CORTEX_LANG > .cortex/config.yaml > config.yaml > es.
    // Se resuelve DESPUÉS del chdir para que las rutas relativas sean del proyecto.
    i18n::fijar(i18n::detectar(
        std::env::var("CORTEX_LANG").ok().as_deref(),
        std::path::Path::new(".cortex/config.yaml"),
        std::path::Path::new("config.yaml"),
    ));
    let lang = i18n::actual();

    // ── Ventana dedicada (BRAIN-3): relanzar en terminal nueva y salir ──
    if args.window {
        let mut cmd: Vec<String> = vec![std::env::current_exe()
            .map(|p| p.display().to_string())
            .unwrap_or_else(|_| String::from("cortex-brain"))];
        if let Some(root) = &args.project_root {
            cmd.push(String::from("--project-root"));
            cmd.push(root.clone());
        }
        if args.model {
            cmd.push(String::from("--model"));
        }
        if args.temp > 0.0 {
            cmd.push(String::from("--temp"));
            cmd.push(args.temp.to_string());
        }
        if let Err(e) = cortex_brain::window::launch_window(&cmd) {
            eprintln!("{}", i18n::warn_ventana(lang, &e));
            std::process::exit(1);
        }
        return;
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
        println!("{}", i18n::cargando_gguf(lang, &model_path));
        let system = format!(
            "Sos el asistente local de Cortex, experto en ESTE proyecto.\n\n{}\nReglas estrictas:\n\
             - NUNCA ejecutás mutaciones: si la acción es mutante, proponés el comando CLI exacto para que el usuario lo corra.\n\
             - Si necesitás datos reales (salud, búsqueda, stats), respondé UNICAMENTE una línea con el formato:\nTOOL: <nombre> <argumentos>\n\
             y nada más; el brain la ejecutará con confirmación del usuario.\n\
             - Si no necesitás herramientas, respondé normalmente y breve.",
            help_text()
        );
        match LlamaChatBackend::open(&model_path, Some(&system))
            .map(|b| b.with_temp(args.temp).with_seed(args.seed))
        {
            Ok(b) => Box::new(b),
            Err(e) => {
                println!("⚠ no pude cargar el modelo ({e}); modo determinista.");
                Box::new(DeterministicBackend)
            }
        }
    } else {
        if args.model {
            println!("{}", i18n::warn_model_falta(lang, &model_path));
        }
        Box::new(DeterministicBackend)
    };

    #[cfg(not(feature = "llama"))]
    let mut backend: Box<dyn LlmBackend> = {
        if args.model {
            println!("{}", i18n::warn_sin_llama(lang));
        }
        Box::new(DeterministicBackend)
    };

    println!("{}", i18n::backend_line(lang, backend.name()));
    println!("{}", help_text());
    let _ = std::io::stdout().flush();

    let tools: BTreeMap<&'static str, ToolSpec> = build_tools();
    let stdin = std::io::stdin();
    for line in stdin.lock().lines() {
        let Ok(line) = line else { break };
        let texto = line.trim();
        if texto.is_empty() {
            continue;
        }
        if route_intent(texto).slash.as_deref() == Some("quit") {
            println!("{}", i18n::hasta_proxima(lang));
            break;
        }
        match backend.generate(texto, &catalogo_tools()) {
            Ok(out) => {
                if out == "/quit" {
                    println!("{}", i18n::hasta_proxima(lang));
                    break;
                }
                // Protocolo TOOL (chat.rs): separa líneas TOOL:, pide
                // confirmación al usuario y despacha SOLO si aprobó. El
                // mismo código queda gateado en CI vía ScriptedBackend.
                let salida = procesar_respuesta_modelo(&out, &tools, &mut |t, a| {
                    confirmar_ejecucion(t, a, &tools)
                });
                print!("{salida}");
            }
            Err(e) => println!("⚠ {e}\n"),
        }
        let _ = std::io::stdout().flush();
    }
}
