//! Loop de chat del brain nativo + backend LLM.
//!
//! BRAIN-2 (llama.cpp/GGUF) se conecta vía el trait `LlmBackend`; hoy existe
//! `DeterministicBackend` (fallback --no-model, spec BRAIN-1: cero tokens,
//! router determinista). El binding llama.cpp queda scoped como próximo
//! incremento (ver HANDOFF §ESTADO-GATES).

pub use crate::router::{route_intent, Intent};
pub use crate::tools::{build_tools, dispatch, Tier, ToolSpec};

/// Backend de generación. Contrato mínimo para tool-calling: recibe el
/// historial + catálogo de tools y devuelve texto o una llamada a tool.
pub trait LlmBackend {
    fn name(&self) -> &str;
    /// Genera la próxima respuesta del asistente. `prompt` ya incluye el
    /// contexto conversacional; `tools_help` es el catálogo renderizado.
    fn generate(&mut self, prompt: &str, tools_help: &str) -> Result<String, String>;
}

/// Fallback determinista (--no-model): sin LLM, sin RAM extra, respuesta
/// instantánea vía router + tools. Es el modo default del binario.
#[derive(Default)]
pub struct DeterministicBackend;

impl LlmBackend for DeterministicBackend {
    fn name(&self) -> &str {
        "determinista (sin modelo)"
    }

    fn generate(&mut self, prompt: &str, _tools_help: &str) -> Result<String, String> {
        let intent = route_intent(prompt);
        if let Some(slash) = &intent.slash {
            return Ok(match slash.as_str() {
                "help" => help_text(),
                "quit" => "/quit".into(),
                other => dispatch_slash(other, &intent.args["resto"]),
            });
        }
        match &intent.tool {
            Some(tool) => dispatch(tool, &args_vec(&intent)),
            None => Ok(format!("{}\n{}", intent.razon, help_text())),
        }
    }
}

fn args_vec(intent: &Intent) -> Vec<String> {
    intent
        .args
        .get("query")
        .or_else(|| intent.args.get("tema"))
        .map(|q| vec![q.clone()])
        .unwrap_or_default()
}

fn dispatch_slash(cmd: &str, resto: &str) -> String {
    match cmd {
        "doctor" | "stats" | "session" | "webgraph" | "actions" => {
            let tool = match cmd {
                "doctor" => "cortex.health",
                "stats" => "vault.stats",
                "session" => "session.current",
                "webgraph" => "webgraph.serve",
                _ => "actions.propose",
            };
            match dispatch(tool, &[resto.to_string()]) {
                Ok(out) => out,
                Err(e) => format!("⚠ {e}"),
            }
        }
        "search" => match dispatch("memory.search", &[resto.to_string()]) {
            Ok(out) => out,
            Err(e) => format!("⚠ {e}"),
        },
        _ => help_text(),
    }
}

/// Banner ASCII ≤80 columnas (spec test_banner_renderiza_en_80).
pub const BANNER: &str = "\
   ______ __  __ ____  _____ _   _____  __
  / ____// / / //  _// ___// | / /   \\/ /
 / /    / /_/ / / /  \\__ \\/  |/ / /\\ / /
/ /___ / __  _/ / / ___/ / /|  / /_/  /
\\____//_/ /_/___//____/_/ |_/\\____/
";

pub fn help_text() -> String {
    let mut out = String::from(
        "Comandos:\n\
         /help    muestra esta ayuda\n\
         /doctor  estado de salud de Cortex\n\
         /stats   conteos del vault\n\
         /search <q>  búsqueda híbrida\n\
         /session sesión actual\n\
         /webgraph levanta el visualizador\n\
         /actions acciones sugeridas\n\
         /quit    salir\n\nHerramientas:\n",
    );
    for spec in build_tools().values() {
        let tier = match spec.tier {
            Tier::Read => "read",
            Tier::SafeAction => "safe",
        };
        out.push_str(&format!(
            "  · {:<16} [{tier}] {}\n",
            spec.name, spec.description
        ));
    }
    out.push_str("\nEl brain NUNCA ejecuta mutaciones: propone el comando exacto.\n");
    out
}
