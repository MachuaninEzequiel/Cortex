//! Router determinista del brain (puerto 1:1 de `cortex/brain/router.py`).
//!
//! ESPECIFICACIÓN CONDUCTUAL: tests/unit/brain/test_brain_v1.py (BRAIN-1
//! Python). Las decisiones de ruteo deben coincidir exactamente; el renderizado
//! de respuestas es responsabilidad de las tools.

use regex::Regex;
use std::collections::HashMap;

#[derive(Debug, Clone, Default, PartialEq)]
pub struct Intent {
    /// None ⇒ no es una consulta mapeable (razón lo explica).
    pub tool: Option<String>,
    pub args: HashMap<String, String>,
    /// Comando slash detectado (/help, /quit…).
    pub slash: Option<String>,
    pub razon: String,
}

struct Patron {
    tool: &'static str,
    re: Regex,
}

fn patron(tool: &'static str, pattern: &str) -> Patron {
    Patron {
        tool,
        re: Regex::new(&format!("(?i){pattern}")).expect("patrón inválido"),
    }
}

/// Mismos patrones, en el MISMO orden que `_PATRONES` de Python.
fn patrones() -> Vec<Patron> {
    vec![
        patron(
            "cortex.health",
            r"cómo está|como esta|estado|salud|health|doctor",
        ),
        patron(
            "vault.stats",
            r"cuántas notas|cuantas notas|stats|estadística|estadistica",
        ),
        patron("session.current", r"sesión|sesion|checkpoint|session"),
        patron(
            "webgraph.serve",
            r"webgraph|grafo|abrí el grafo|abri el grafo",
        ),
        patron(
            "actions.propose",
            r"acciones|pendiente|sugerí|sugiere|qué hago|que hago",
        ),
    ]
}

const SLASHES: [&str; 8] = [
    "help", "doctor", "stats", "session", "webgraph", "actions", "quit", "search",
];

const VERBOS_SEARCH: &str = r"busca|buscá|search|encontrá|encontrar|relacionad";
const PREFIJO_QUERY: &str = r"^(busca|buscá|search|encontrá)\s+(me\s+)?(docs?\s+(sobre|de)\s+)?";

/// Mapea texto libre → intent determinista. Los slash tienen prioridad.
pub fn route_intent(texto: &str) -> Intent {
    let limpio = texto.trim();
    if let Some(resto_slash) = limpio.strip_prefix('/') {
        let mut partes = resto_slash.splitn(2, char::is_whitespace);
        let cmd = partes.next().unwrap_or("").to_lowercase();
        if SLASHES.contains(&cmd.as_str()) {
            let mut args = HashMap::new();
            args.insert("resto".into(), partes.next().unwrap_or("").to_string());
            return Intent {
                slash: Some(cmd),
                args,
                ..Default::default()
            };
        }
        return Intent {
            tool: None,
            args: HashMap::new(),
            slash: None,
            razon: format!("slash desconocido: /{cmd}"),
        };
    }

    for p in patrones() {
        if p.re.is_match(limpio) {
            return Intent {
                tool: Some(p.tool.to_string()),
                razon: "match de keywords".into(),
                ..Default::default()
            };
        }
    }

    // Búsqueda semántica: frase imperativa de búsqueda.
    let re_verbos = Regex::new(&format!("(?i){VERBOS_SEARCH}")).expect("regex");
    if re_verbos.is_match(limpio) {
        let re_prefijo = Regex::new(&format!("(?i){PREFIJO_QUERY}")).expect("regex");
        let query = match re_prefijo.replace(limpio, "") {
            s if s.trim().is_empty() => limpio.to_string(),
            s => s.trim().to_string(),
        };
        let mut args = HashMap::new();
        args.insert("query".into(), query);
        return Intent {
            tool: Some("memory.search".into()),
            args,
            slash: None,
            razon: "búsqueda libre".into(),
        };
    }

    // Pregunta abierta (≥3 palabras terminando en ?) → docs.related con opt-in.
    let palabras = limpio.split_whitespace().count();
    if palabras >= 3 && limpio.ends_with('?') {
        let tema = limpio.trim_end_matches('?').trim().to_string();
        let mut args = HashMap::new();
        args.insert("tema".into(), tema);
        return Intent {
            tool: Some("docs.related".into()),
            args,
            slash: None,
            razon: "pregunta abierta → related con opt-in de engine".into(),
        };
    }

    Intent {
        tool: None,
        args: HashMap::new(),
        slash: None,
        razon: "sin match — el brain lista qué sabe hacer".into(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn salud_a_cortex_health() {
        assert_eq!(
            route_intent("¿cómo está cortex?").tool.as_deref(),
            Some("cortex.health")
        );
    }

    #[test]
    fn webgraph_a_serve() {
        assert_eq!(
            route_intent("abrí el grafo").tool.as_deref(),
            Some("webgraph.serve")
        );
    }

    #[test]
    fn busqueda_extrae_query() {
        let intent = route_intent("busca docs sobre autenticación jwt");
        assert_eq!(intent.tool.as_deref(), Some("memory.search"));
        assert!(intent.args["query"].contains("autenticación"));
    }

    #[test]
    fn pregunta_abierta_va_a_related() {
        assert_eq!(
            route_intent("que documentos hablan de la migracion de datos?")
                .tool
                .as_deref(),
            Some("docs.related")
        );
    }

    #[test]
    fn slash_quit() {
        assert_eq!(route_intent("/quit").slash.as_deref(), Some("quit"));
    }

    #[test]
    fn sin_match_devuelve_razon() {
        let intent = route_intent("xyzzy");
        assert!(intent.tool.is_none());
        assert!(!intent.razon.is_empty());
    }

    #[test]
    fn slash_desconocido_da_razon() {
        let intent = route_intent("/noexiste");
        assert!(intent.slash.is_none());
        assert!(intent.razon.contains("slash desconocido"));
    }

    #[test]
    fn search_con_resto() {
        let intent = route_intent("/search autenticación jwt");
        assert_eq!(intent.slash.as_deref(), Some("search"));
        assert_eq!(intent.args["resto"], "autenticación jwt");
    }
}
