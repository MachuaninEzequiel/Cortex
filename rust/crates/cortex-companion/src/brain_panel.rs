//! B8 — Panel Brain híbrido (G-B4, doc 14 §2.2/§2.3).
//!
//! El brain entra como LIBRERÍA (`cortex-brain`: router determinista,
//! catálogo de tools, protocolo TOOL, `LlmBackend`) pero SUS tools se
//! enrutan por el engine in-process del Companion con un **mapa 1:1**
//! (§2.2): nada de subprocess. Tool sin mapping en v1 ⇒ fallo explícito
//! (patrón P6/P9), nunca subprocess silencioso.
//!
//! Regla híbrida (§2.3):
//! - **Tier Read** (memory.search, docs.related, cortex.health, vault.stats,
//!   session.current, actions.propose): ejecución **directa, sin aprobación**.
//! - **Mutaciones**: el brain sigue "proponiendo, nunca mutando" — una
//!   propuesta con comando CLI mutador (`cortex <familia> …` que
//!   `menu::command_is_guarded` clasifica como mutante) se muestra como
//!   [`BrainMsg::Proposal`] con botón [Ejecutar] → `run_guarded` (B2). La
//!   aprobación vive en la superficie, no en el brain.
//!
//! El `brain` standalone (`cortex-brain` bin) NO se toca: su `dispatch` por
//! subprocess sigue igual. Este módulo es el equivalente in-process.
//!
//! Divergencias declaradas vs el brain CLI:
//! - `/quit`: en el Companion el chat es un panel; salir es `q`/Ctrl+C
//!   (se responde con la pista, no se ejecuta nada).
//! - `webgraph.serve` (SafeAction del brain, spawn detached): NO se replica
//!   — Err explícito con el comando exacto.

use serde_json::{json, Value};

use cortex_brain::chat::{extraer_tool, help_text, respuesta_sin_tool, LlmBackend};
use cortex_brain::i18n::{
    self, acciones_footer, acciones_intro, actual, falta_query, related_precision,
};
use cortex_brain::router::route_intent;
use cortex_brain::tools::build_tools;

use crate::app::OutcomeLine;
use crate::engine::{Backend, SearchHit};
use crate::menu;

/// Modo del panel: determinista (default, cero tokens — como el binario del
/// brain sin `--model`) o LLM local (`ScriptedBackend` en tests/CI;
/// `LlamaChatBackend` bajo feature `llama`).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum BrainMode {
    #[default]
    Deterministic,
    Llm,
}

/// Línea del chat del brain.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BrainMsg {
    User(String),
    Brain(String),
    /// Propuesta de MUTACIÓN detectada en la salida (comando guardado):
    /// render con botón [Ejecutar] → `run_guarded`. `audit_key` viaja al
    /// modal y a la línea de auditoría.
    Proposal {
        command: String,
        audit_key: String,
    },
}

/// Estado del panel (datos puros; el runtime ejecuta).
#[derive(Debug, Clone, Default)]
pub struct BrainPanel {
    pub messages: Vec<BrainMsg>,
    pub mode: BrainMode,
    /// Texto del input de chat (el reducer lo llena con `Typed`).
    pub input: String,
    /// Resultado de la última ejecución guardada (visible en status).
    pub outcome: Option<OutcomeLine>,
}

/// Tokeniza respetando `'simple'` y `"doble"` (los comandos propuestos por
/// el brain llevan notas entre comillas). Comilla sin cerrar: el resto
/// entra completo (nunca se pierde input).
#[must_use]
pub fn tokenize(line: &str) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    let mut cur = String::new();
    let mut quote: Option<char> = None;
    let mut has = false;
    for c in line.chars() {
        match quote {
            Some(q) if c == q => quote = None,
            Some(_) => {
                cur.push(c);
                has = true;
            }
            None if c == '\'' || c == '"' => {
                quote = Some(c);
                has = true;
            }
            None if c.is_whitespace() => {
                if has {
                    out.push(std::mem::take(&mut cur));
                }
                has = false;
            }
            None => {
                cur.push(c);
                has = true;
            }
        }
    }
    if has {
        out.push(cur);
    }
    out
}

/// Formatea hits de búsqueda (misma info que el panel Search, en texto).
fn render_hits(q: &str, hits: &[SearchHit]) -> String {
    if hits.is_empty() {
        return format!("sin resultados para «{q}»");
    }
    hits.iter()
        .enumerate()
        .map(|(i, h)| format!("{}. [{}] {}  {:.2}", i + 1, h.source, h.title, h.score))
        .collect::<Vec<_>>()
        .join("\n")
}

/// Mapa 1:1 de tools del brain → engine in-process (doc 14 §2.2).
/// `args` es el objeto de argumentos del `Intent` (claves `query`/`tema`/
/// `resto`) o `{"query": <args del TOOL>}` desde el protocolo LLM.
///
/// Nunca mutaciones: todo lo de aquí es lectura sobre el engine; las
/// herramientas mutadoras no existen en el catálogo del brain (test
/// `no_hay_herramientas_mutadoras` de cortex-brain) y una sugerencia mutante
/// llega como texto → [`BrainMsg::Proposal`], jamás por esta ruta.
pub fn route_brain_tool(name: &str, args: &Value, be: &dyn Backend) -> Result<String, String> {
    let q = ["query", "tema", "resto"]
        .iter()
        .find_map(|k| {
            args.get(*k)
                .and_then(Value::as_str)
                .filter(|s| !s.trim().is_empty())
        })
        .unwrap_or("");
    match name {
        "memory.search" => {
            if q.is_empty() {
                return Err(falta_query(actual()).to_string());
            }
            let hits = be.search(q, 5)?;
            Ok(render_hits(q, &hits))
        }
        "docs.related" => {
            if q.is_empty() {
                return Ok(related_precision(actual()));
            }
            // Espejo fiel del `dispatch` del brain: docs.related corre HOY
            // `cortex search <tema>` (sin filtro doc_type) ⇒ la misma
            // pipeline del engine, in-process.
            let hits = be.search(q, 5)?;
            Ok(render_hits(q, &hits))
        }
        "session.current" => match be.session_current()? {
            Some(s) => Ok(format!(
                "{}  {}  mode: {}  opened: {}",
                s.id, s.status, s.mode, s.opened_at
            )),
            None => Ok("No hay sesión activa".to_string()),
        },
        "actions.propose" => {
            let props = be.next_actions()?;
            if props.is_empty() {
                return Ok(i18n::nada_pendiente(actual()).to_string());
            }
            let lang = actual();
            let mut out = acciones_intro(lang);
            for p in &props {
                out.push_str(&format!(
                    "  · {} — {}  score {:.2} · costo {}\n      efecto: {}\n",
                    p.id, p.title, p.score, p.cost, p.effect
                ));
            }
            out.push_str(acciones_footer(lang));
            Ok(out)
        }
        "cortex.health" => {
            let d = be.doctor()?;
            let mut out = d
                .checks
                .iter()
                .map(|(n, v)| format!("{n}: [{}]", v.to_uppercase()))
                .collect::<Vec<_>>()
                .join("\n");
            out.push_str(if d.ok {
                "\nsalud: OK"
            } else {
                "\nsalud: PROBLEMAS — ver doctor"
            });
            Ok(out)
        }
        "vault.stats" => {
            let s = be.stats()?;
            Ok(format!(
                "episódica {} · semántica {} · {}",
                s.episodic, s.semantic, s.vault_path
            ))
        }
        // SafeAction del brain (spawn detached): no se replica en v1.
        "webgraph.serve" => Err(
            "webgraph.serve no mapeada en v1 — corré `cortex webgraph serve` en tu terminal"
                .to_string(),
        ),
        other => Err(format!("tool no mapeada en el Companion: {other}")),
    }
}

/// Convierte el `args` del `Intent` (HashMap<String,String>) en el `Value`
/// que consume [`route_brain_tool`].
fn intent_args(args: &std::collections::HashMap<String, String>) -> Value {
    Value::Object(
        args.iter()
            .map(|(k, v)| (k.clone(), Value::String(v.clone())))
            .collect::<serde_json::Map<String, Value>>(),
    )
}

/// Un turno de chat: User + respuesta. Con `llm` = protocolo TOOL del brain
/// (`ScriptedBackend` en CI, `LlamaChatBackend` bajo feature); sin `llm` =
/// router determinista 1:1 (cero tokens, cero subprocess).
pub fn run_turn(
    be: &dyn Backend,
    panel: &mut BrainPanel,
    text: &str,
    llm: Option<&mut dyn LlmBackend>,
) {
    panel.outcome = None;
    panel.messages.push(BrainMsg::User(text.to_string()));
    match llm {
        Some(l) => {
            panel.mode = BrainMode::Llm;
            match l.generate(text, &help_text()) {
                Ok(raw) => process_llm(be, panel, &raw),
                // Cerebro del patrón "⚠" del brain: el fallo se muestra,
                // nunca se traga.
                Err(e) => push_brain(panel, &format!("⚠ {e}")),
            }
        }
        None => {
            panel.mode = BrainMode::Deterministic;
            run_deterministic(be, panel, text);
        }
    }
}

/// Protocolo TOOL del brain, procesado contra el engine en vez del CLI:
/// línea `TOOL:` → catálogo (fuera de catálogo jamás se enruta — espejo de
/// `procesar_respuesta_modelo`) → `route_brain_tool` → visible + scan de
/// propuestas mutantes.
fn process_llm(be: &dyn Backend, panel: &mut BrainPanel, raw: &str) {
    let Some((tool, args_tool)) = extraer_tool(raw) else {
        push_brain(panel, raw);
        return;
    };
    let visible = respuesta_sin_tool(raw);
    if !visible.trim().is_empty() {
        push_brain(panel, &visible);
    }
    if !build_tools().contains_key(tool.as_str()) {
        // El brain jamas despacha tools fuera de catálogo; acá ni se enruta.
        panel
            .messages
            .push(BrainMsg::Brain(i18n::tool_inexistente(actual(), &tool)));
        return;
    }
    let out = route_brain_tool(&tool, &json!({ "query": args_tool }), be);
    match out {
        Ok(s) => push_brain(panel, &s),
        Err(e) => push_brain(panel, &format!("⚠ {e}")),
    }
}

/// Camino sin modelo: router determinista 1:1 del brain + engine.
fn run_deterministic(be: &dyn Backend, panel: &mut BrainPanel, text: &str) {
    let intent = route_intent(text);
    let out = if let Some(slash) = &intent.slash {
        match slash.as_str() {
            "help" => Ok(help_text()),
            "quit" => Ok(
                "para salir del Companion: q o Ctrl+C (el loop standalone vive en `cortex-brain`)"
                    .to_string(),
            ),
            "search" => {
                route_brain_tool("memory.search", &json!({"query": intent.args["resto"]}), be)
            }
            other => {
                let tool = match other {
                    "doctor" => "cortex.health",
                    "stats" => "vault.stats",
                    "session" => "session.current",
                    "webgraph" => "webgraph.serve",
                    _ => "actions.propose",
                };
                route_brain_tool(tool, &json!({"query": intent.args["resto"]}), be)
            }
        }
    } else if let Some(tool) = &intent.tool {
        route_brain_tool(tool, &intent_args(&intent.args), be)
    } else {
        // Mismo libreto que DeterministicBackend cuando no hay match.
        Ok(format!("{}\n{}", intent.razon, help_text()))
    };
    match out {
        Ok(s) => push_brain(panel, &s),
        Err(e) => push_brain(panel, &format!("⚠ {e}")),
    }
}

/// Agrega una respuesta del brain y escanea propuestas de MUTACIÓN: líneas
/// que empiezan con `cortex <familia> <args…>` y que `command_is_guarded`
/// clasifica como mutantes. Las lecturas sugeridas quedan como texto
/// informativo (el Menu ya las ejecuta directas).
fn push_brain(panel: &mut BrainPanel, text: &str) {
    panel.messages.push(BrainMsg::Brain(text.to_string()));
    for line in text.lines() {
        let t = line.trim();
        if !t.starts_with("cortex ") {
            continue;
        }
        let toks = tokenize(t);
        if toks.len() < 2 {
            continue;
        }
        let family = toks[1].clone();
        let args = toks[2..].to_vec();
        if !menu::command_is_guarded(&family, &args) {
            continue;
        }
        let seq = panel.messages.len();
        panel.messages.push(BrainMsg::Proposal {
            command: t.to_string(),
            audit_key: format!("brain.{family}.{seq}"),
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tokenize_sin_comillas() {
        assert_eq!(tokenize("cortex doctor"), ["cortex", "doctor"]);
    }

    #[test]
    fn comilla_sin_cerrar_no_pierde_texto() {
        assert_eq!(
            tokenize("cortex remember 'nota sin cerrar"),
            ["cortex", "remember", "nota sin cerrar"]
        );
    }
}
