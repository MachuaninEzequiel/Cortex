//! Loop de chat del brain nativo + backend LLM.
//!
//! BRAIN-2 (llama.cpp/GGUF) se conecta vía el trait `LlmBackend`; hoy existe
//! `DeterministicBackend` (fallback --no-model, spec BRAIN-1: cero tokens,
//! router determinista). El binding llama.cpp queda scoped como próximo
//! incremento (ver HANDOFF §ESTADO-GATES).

pub use crate::router::{route_intent, Intent};
pub use crate::tools::{build_tools, dispatch, Tier, ToolSpec};

use std::collections::{BTreeMap, VecDeque};
use std::sync::OnceLock;

/// Backend de generación. Contrato mínimo para tool-calling: recibe el
/// historial + catálogo de tools y devuelve texto o una llamada a tool.
pub trait LlmBackend {
    fn name(&self) -> &str;
    /// Genera la próxima respuesta del asistente. `prompt` ya incluye el
    /// contexto conversacional; `tools_help` es el catálogo renderizado.
    fn generate(&mut self, prompt: &str, tools_help: &str) -> Result<String, String>;

    /// Modo streaming: el callback recibe cada fragmento a medida que
    /// se genera. Default = `generate` y emitir TODO en un solo
    /// callback (compatibilidad hacia atrás; doc 19 §3.2). Sólo los
    /// backends que generan de a piezas (llama.cpp) lo overridean.
    /// `&mut dyn` (y no `impl Fn`) para mantener el trait
    /// dyn-compatible (`Box<dyn LlmBackend>` se usa en binario,
    /// companion y brain-app).
    fn generate_streaming(
        &mut self,
        prompt: &str,
        tools_help: &str,
        on_piece: &mut dyn FnMut(&str),
    ) -> Result<String, String> {
        let full = self.generate(prompt, tools_help)?;
        on_piece(&full);
        Ok(full)
    }
}

/// Backend FALSO scriptado: devuelve respuestas encoladas en orden y falla
/// ruidosamente al agotarse. Es el motor del gate CI del protocolo TOOL:
/// ejercita todo el loop de chat SIN GGUF ni red (decisión dueño 2026-08-24b:
/// "CI con backend falso scriptado"). No es un mock interno de tests: es
/// parte pública de la librería, reutilizable por quien integre el brain.
pub struct ScriptedBackend {
    nombre: String,
    cola: VecDeque<String>,
}

impl ScriptedBackend {
    /// Script de respuestas crudas (pueden incluir líneas "TOOL: ...").
    pub fn new<I, S>(nombre: &str, respuestas: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        Self {
            nombre: nombre.to_string(),
            cola: respuestas.into_iter().map(Into::into).collect(),
        }
    }
}

impl LlmBackend for ScriptedBackend {
    fn name(&self) -> &str {
        &self.nombre
    }

    fn generate(&mut self, _prompt: &str, _tools_help: &str) -> Result<String, String> {
        self.cola.pop_front().ok_or_else(|| {
            String::from("script agotado: el test/CI pidió más turnos de los scriptados")
        })
    }
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

// ── Protocolo TOOL (antes en main.rs; en lib para poder gatearlo en CI) ────

/// Extrae `(nombre, args)` de la primera línea `TOOL: <nombre> <args>`.
/// Los espacios interiores de `args` se normalizan a uno.
#[must_use]
pub fn extraer_tool(respuesta: &str) -> Option<(String, String)> {
    respuesta.lines().find_map(|l| {
        let resto = l.trim_start().strip_prefix("TOOL:")?;
        let mut partes = resto.split_whitespace();
        let name = partes.next()?.to_string();
        Some((name, partes.collect::<Vec<_>>().join(" ")))
    })
}

/// La respuesta sin las líneas `TOOL:` (lo que se muestra al usuario).
#[must_use]
pub fn respuesta_sin_tool(respuesta: &str) -> String {
    respuesta
        .lines()
        .filter(|l| !l.trim_start().starts_with("TOOL:"))
        .collect::<Vec<_>>()
        .join("\n")
}

/// Decisión pura de confirmación: acepta `s|si|sí|y|yes` (case-insensitive;
/// `y|yes` para UI en inglés); cualquier otra cosa —incluido Enter vacío—
/// rechaza (default N).
#[must_use]
pub fn confirma(input: &str) -> bool {
    matches!(
        input.trim().to_lowercase().as_str(),
        "s" | "si" | "sí" | "y" | "yes"
    )
}

/// Procesa la respuesta cruda del backend y devuelve el texto a mostrar.
///
/// Si contiene línea(s) `TOOL:`, las separa, consulta `aprobar` (que en el
/// binario pide confirmación al usuario; en CI/tests decide por script) y
/// despacha la tool SOLO si aprobó. Tool fuera del catálogo jamás llega a
/// `aprobar`, mucho menos a despachar.
pub fn procesar_respuesta_modelo(
    out: &str,
    tools: &BTreeMap<&'static str, ToolSpec>,
    aprobar: &mut dyn FnMut(&str, &str) -> bool,
) -> String {
    let Some((tool, args_tool)) = extraer_tool(out) else {
        return format!("{out}\n");
    };
    let mut salida = String::new();
    let sin_tool = respuesta_sin_tool(out);
    if !sin_tool.trim().is_empty() {
        salida.push_str(&sin_tool);
        salida.push('\n');
    }
    if !tools.contains_key(tool.as_str()) {
        salida.push_str(&crate::i18n::tool_inexistente(crate::i18n::actual(), &tool));
        salida.push('\n');
        return salida;
    }
    if aprobar(&tool, &args_tool) {
        match dispatch(&tool, std::slice::from_ref(&args_tool)) {
            Ok(res) => salida.push_str(&res),
            Err(e) => salida.push_str(&format!("⚠ {e}")),
        }
        salida.push('\n');
    } else {
        salida.push_str(crate::i18n::no_ejecutado(crate::i18n::actual()));
        salida.push('\n');
    }
    salida
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

/// Banner del brain: isotipo Cortex half-block + wordmark lado a lado
/// (≤80 columnas visibles, spec `banner_visible_en_80`). Coloreado si el
/// terminal lo soporta; silueta plana si no (prompt-logo.md §38).
pub fn banner() -> &'static str {
    if cortex_branding::ansi::should_color() {
        banner_ansi()
    } else {
        banner_plain()
    }
}

/// Banner coloreado según el modo detectado del entorno.
pub fn banner_ansi() -> &'static str {
    static BANNER: OnceLock<String> = OnceLock::new();
    BANNER.get_or_init(|| {
        let map = banner_map();
        cortex_branding::ansi::render_ansi(&map, cortex_branding::ansi::env_color_mode())
    })
}

/// Banner en silueta monocroma (sin escapes; NO_COLOR / piped).
pub fn banner_plain() -> &'static str {
    static BANNER: OnceLock<String> = OnceLock::new();
    BANNER.get_or_init(|| cortex_branding::ansi::render_plain(&banner_map()))
}

fn banner_map() -> cortex_branding::pixels::PixelMap {
    // Con el wordmark 3D ancho (53 cols), el Compact desbordaría el contrato
    // de 80 columnas del banner del chat; el Mark mantiene la marca visible.
    let logo = cortex_branding::logo::LogoVariant::Mark.pixel_map();
    let wordmark = cortex_branding::wordmark::wordmark();
    let gap = 2;
    let w = logo.w() + gap + wordmark.w();
    let h = logo.h().max(wordmark.h());
    let mut combined = cortex_branding::pixels::PixelMap::new(w, h);
    combined.blit(logo, 0, 0);
    combined.blit(wordmark, logo.w() + gap, (h - wordmark.h()) / 2);
    combined
}

pub fn help_text() -> String {
    let lang = crate::i18n::actual();
    let mut tools_render = String::new();
    for spec in build_tools().values() {
        let tier = match spec.tier {
            Tier::Read => "read",
            Tier::SafeAction => "safe",
        };
        tools_render.push_str(&format!(
            "  · {:<16} [{tier}] {}\n",
            spec.name, spec.description
        ));
    }
    crate::i18n::ayuda(lang, &tools_render)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// El default del trait es la red de seguridad de compatibilidad:
    /// emite la respuesta completa en UNA pieza (doc 19 §3.5).
    #[test]
    fn streaming_default_emite_todo_en_una_pieza() {
        let mut backend = ScriptedBackend::new("test", ["respuesta completa"]);
        let mut piezas: Vec<String> = Vec::new();
        let out = backend
            .generate_streaming("hola", "", &mut |p| piezas.push(p.to_string()))
            .expect("streaming");
        assert_eq!(out, "respuesta completa");
        assert_eq!(piezas, vec!["respuesta completa"]);
    }
}
