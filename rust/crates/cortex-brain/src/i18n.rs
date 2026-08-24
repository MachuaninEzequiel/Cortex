//! i18n del brain — espejo de `cortex/action_engine/i18n.py` (Obra 05 Fase E).
//!
//! Resolución del idioma (misma convención que Python):
//! 1. env `CORTEX_LANG` (`es`|`en`) — override para CI/tests,
//! 2. clave `ui.language` en `<repo>/.cortex/config.yaml` (o `config.yaml`
//!    legacy), parseada con un mini-escáner de UNA clave (sin deps yaml),
//! 3. fallback `es` (idioma del dueño). Config rota no rompe la UI.
//!
//! Alcance: SOLO el chrome del brain (help, prompts, avisos). Las salidas de
//! tools son respuestas del CLI cortex (ES) y los patrones del router son la
//! spec BRAIN-1 — ambos quedan como están.

use std::path::Path;
use std::sync::RwLock;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Lang {
    Es,
    En,
}

impl Lang {
    #[must_use]
    pub fn parse(s: &str) -> Self {
        match s.trim().to_lowercase().as_str() {
            "en" => Self::En,
            _ => Self::Es, // fallback: cualquier otra cosa = español
        }
    }

    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::Es => "es",
            Self::En => "en",
        }
    }
}

static ACTUAL: RwLock<Lang> = RwLock::new(Lang::Es);

/// Fija el idioma global (una vez al arrancar; en tests con lock de serialización).
pub fn fijar(lang: Lang) {
    *ACTUAL.write().unwrap_or_else(|e| e.into_inner()) = lang;
}

/// Idioma global vigente (default Es hasta que main llame `fijar`).
#[must_use]
pub fn actual() -> Lang {
    *ACTUAL.read().unwrap_or_else(|e| e.into_inner())
}

// ── Textos del chrome del brain ─────────────────────────────────────────────

/// Ayuda completa (/help) en el idioma dado. `herramientas` es el catálogo
/// ya renderizado por el llamador (nombres/tiers son invariantes).
#[must_use]
pub fn ayuda(lang: Lang, herramientas: &str) -> String {
    let mut out = String::new();
    out.push_str(match lang {
        Lang::Es => "Comandos:\n",
        Lang::En => "Commands:\n",
    });
    out.push_str(match lang {
        Lang::Es => {
            "\
             /help    muestra esta ayuda\n\
             /doctor  estado de salud de Cortex\n\
             /stats   conteos del vault\n\
             /search <q>  búsqueda híbrida\n\
             /session sesión actual\n\
             /webgraph levanta el visualizador\n\
             /actions acciones sugeridas\n\
             /quit    salir\n\n"
        }
        Lang::En => {
            "\
             /help    show this help\n\
             /doctor  Cortex health status\n\
             /stats   vault counts\n\
             /search <q>  hybrid search\n\
             /session current session\n\
             /webgraph launch the visualizer\n\
             /actions suggested actions\n\
             /quit    quit\n\n"
        }
    });
    out.push_str(match lang {
        Lang::Es => "Herramientas:\n",
        Lang::En => "Tools:\n",
    });
    out.push_str(herramientas);
    out.push('\n');
    out.push_str(match lang {
        Lang::Es => "\nEl brain NUNCA ejecuta mutaciones: propone el comando exacto.\n",
        Lang::En => "\nThe brain NEVER runs mutations: it proposes the exact command.\n",
    });
    out
}

/// Aviso cuando el usuario rechaza la ejecución sugerida.
#[must_use]
pub fn no_ejecutado(lang: Lang) -> &'static str {
    match lang {
        Lang::Es => "(no ejecutado)",
        Lang::En => "(not executed)",
    }
}

/// Aviso para una tool fuera del catálogo (jamás se despacha).
#[must_use]
pub fn tool_inexistente(lang: Lang, tool: &str) -> String {
    match lang {
        Lang::Es => format!("(el modelo sugirió una tool inexistente: {tool})"),
        Lang::En => format!("(the model suggested an unknown tool: {tool})"),
    }
}

#[must_use]
pub fn hasta_proxima(lang: Lang) -> &'static str {
    match lang {
        Lang::Es => "¡hasta la próxima!",
        Lang::En => "See you next time!",
    }
}

#[must_use]
pub fn cargando_gguf(lang: Lang, ruta: &Path) -> String {
    match lang {
        Lang::Es => format!("🧠 cargando GGUF: {}", ruta.display()),
        Lang::En => format!("🧠 loading GGUF: {}", ruta.display()),
    }
}

#[must_use]
pub fn sugerencia(lang: Lang, etiqueta: &str, tool: &str, args: &str) -> String {
    match lang {
        Lang::Es => format!("🔧 sugerencia del modelo [{etiqueta}]: {tool} {args}"),
        Lang::En => format!("🔧 model suggestion [{etiqueta}]: {tool} {args}"),
    }
}

#[must_use]
pub fn prompt_confirmar(lang: Lang, tool: &str, args: &str) -> String {
    match lang {
        Lang::Es => format!("¿Ejecutás '{tool} {args}'? [s/N]: "),
        Lang::En => format!("Run '{tool} {args}'? [y/N]: "),
    }
}

#[must_use]
pub fn backend_line(lang: Lang, backend: &str) -> String {
    match lang {
        Lang::Es => format!("🧠 cortex-brain — backend: {backend}"),
        Lang::En => format!("🧠 cortex-brain — backend: {backend}"),
    }
}

#[must_use]
pub fn warn_model_falta(lang: Lang, ruta: &Path) -> String {
    match lang {
        Lang::Es => format!(
            "⚠ --model pero no existe {} o el binario se compiló sin --features llama; modo determinista.",
            ruta.display()
        ),
        Lang::En => format!(
            "⚠ --model but {} is missing or the binary was built without --features llama; deterministic mode.",
            ruta.display()
        ),
    }
}

#[must_use]
pub fn warn_sin_llama(lang: Lang) -> &'static str {
    match lang {
        Lang::Es => "⚠ binario sin feature llama; modo determinista.",
        Lang::En => "⚠ binary built without the llama feature; deterministic mode.",
    }
}

#[must_use]
pub fn warn_arg_desconocido(lang: Lang, other: &str) -> String {
    match lang {
        Lang::Es => format!("argumento desconocido: {other} (usá --help)"),
        Lang::En => format!("unknown argument: {other} (use --help)"),
    }
}

#[must_use]
pub fn warn_ventana(lang: Lang, e: &str) -> String {
    match lang {
        Lang::Es => format!("⚠ no pude abrir ventana: {e}"),
        Lang::En => format!("⚠ could not open window: {e}"),
    }
}

// ── Textos de la capa tools (dispatch/propose/run_cli) ──────────────────────

#[must_use]
pub fn falta_query(lang: Lang) -> &'static str {
    match lang {
        Lang::Es => "falta <query>",
        Lang::En => "missing <query>",
    }
}

#[must_use]
pub fn related_precision(lang: Lang) -> String {
    match lang {
        Lang::Es => "¿Qué precisión preferís?\n  \
             · precise → e5-large multilingüe, máxima calidad (~2GB RAM)\n  \
             · fast    → MiniLM, liviano y veloz\nRespondé 'docs.related <tema> fast'."
            .into(),
        Lang::En => "Which precision do you want?\n  \
             · precise → multilingual e5-large, max quality (~2GB RAM)\n  \
             · fast    → MiniLM, light and fast\nReply 'docs.related <topic> fast'."
            .into(),
    }
}

#[must_use]
pub fn vault_stats(lang: Lang, count: usize) -> String {
    match lang {
        Lang::Es => format!("Vault: {count} notas .md"),
        Lang::En => format!("Vault: {count} .md notes"),
    }
}

#[must_use]
pub fn webgraph_ok(lang: Lang) -> String {
    match lang {
        Lang::Es => "Webgraph abierto en http://127.0.0.1:8000 — mirá ese puerto.".into(),
        Lang::En => "Webgraph opened at http://127.0.0.1:8000 — check that port.".into(),
    }
}

#[must_use]
pub fn tool_desconocida(lang: Lang, other: &str) -> String {
    match lang {
        Lang::Es => format!("tool desconocida: {other}"),
        Lang::En => format!("unknown tool: {other}"),
    }
}

#[must_use]
pub fn cli_no_ejecutado(lang: Lang, bin: &str, e: &str) -> String {
    match lang {
        Lang::Es => format!("no pude ejecutar {bin}: {e}"),
        Lang::En => format!("could not run {bin}: {e}"),
    }
}

#[must_use]
pub fn cli_fallo(lang: Lang, bin: &str, args: &str, rc: &str, stderr: &str) -> String {
    match lang {
        Lang::Es => format!("{bin} {args} falló (rc={rc}): {stderr}"),
        Lang::En => format!("{bin} {args} failed (rc={rc}): {stderr}"),
    }
}

#[must_use]
pub fn nada_pendiente(lang: Lang) -> &'static str {
    match lang {
        Lang::Es => "Nada pendiente ✓",
        Lang::En => "Nothing pending ✓",
    }
}

#[must_use]
pub fn acciones_intro(lang: Lang) -> String {
    match lang {
        Lang::Es => "Acciones sugeridas (ejecutalas VOS con el comando indicado):\n".into(),
        Lang::En => "Suggested actions (run the given command yourself):\n".into(),
    }
}

#[must_use]
pub fn accion_efecto(lang: Lang, id: &str, title: &str) -> String {
    match lang {
        Lang::Es => {
            format!("  · {id} — {title}\n      → cortex next --json   |   efecto: ver doctor\n")
        }
        Lang::En => {
            format!("  · {id} — {title}\n      → cortex next --json   |   effect: see doctor\n")
        }
    }
}

#[must_use]
pub fn acciones_footer(lang: Lang) -> &'static str {
    match lang {
        Lang::Es => "El brain propone; la ejecución es tuya (modo estricto).",
        Lang::En => "The brain proposes; execution is yours (strict mode).",
    }
}

#[must_use]
pub fn next_json_invalido(lang: Lang, e: &str) -> String {
    match lang {
        Lang::Es => format!("next --json no es JSON válido: {e}"),
        Lang::En => format!("next --json output is not valid JSON: {e}"),
    }
}

// ── Resolución ──────────────────────────────────────────────────────────────

/// Extrae `ui.language` de un contenido YAML/JSON-plano ya leído.
/// Devuelve None si no está declarado o el archivo está roto.
#[must_use]
pub fn leer_ui_language(contenido: &str) -> Option<Lang> {
    let mut dentro_ui = false;
    for linea in contenido.lines() {
        let sin_comentario = linea.split('#').next().unwrap_or("");
        if sin_comentario.trim().is_empty() {
            continue;
        }
        let indentada = sin_comentario.starts_with(' ') || sin_comentario.starts_with('\t');
        let Some((clave, valor)) = sin_comentario.split_once(':') else {
            continue;
        };
        if !indentada {
            dentro_ui = clave.trim() == "ui";
            continue;
        }
        if dentro_ui && clave.trim() == "language" {
            let limpio = valor
                .trim()
                .trim_matches('"')
                .trim_matches('\'')
                .trim()
                .to_lowercase();
            return matches!(limpio.as_str(), "es" | "en").then(|| Lang::parse(&limpio));
        }
    }
    None
}

/// Resolución completa inyectable: CORTEX_LANG > nueva > legacy > default.
/// `nueva`/`legacy` son rutas de config a leer si existen y son legibles.
#[must_use]
pub fn detectar(env_lang: Option<&str>, nueva: &Path, legacy: &Path) -> Lang {
    if let Some(v) = env_lang {
        match v.trim().to_lowercase().as_str() {
            "es" => return Lang::Es,
            "en" => return Lang::En,
            _ => {} // valor basura NO fuerza: cae a archivos/default
        }
    }
    for ruta in [nueva, legacy] {
        if let Ok(contenido) = std::fs::read_to_string(ruta) {
            if let Some(lang) = leer_ui_language(&contenido) {
                return lang;
            }
        }
    }
    Lang::Es
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_acepta_es_en_y_fallback() {
        assert_eq!(Lang::parse("en"), Lang::En);
        assert_eq!(Lang::parse("EN"), Lang::En);
        assert_eq!(Lang::parse("es"), Lang::Es);
        assert_eq!(Lang::parse(""), Lang::Es);
        assert_eq!(Lang::parse("fr"), Lang::Es);
    }

    #[test]
    fn ui_language_en_layout_nuevo() {
        let cfg = "episodic:\n  persist_dir: .memory\nsemantic:\n  vault_path: vault\nui:\n  language: en\n";
        assert_eq!(leer_ui_language(cfg), Some(Lang::En));
    }

    #[test]
    fn ui_language_con_comillas_y_comentario() {
        let cfg = "ui:\n  language: \"en\"  # idioma del usuario\n";
        assert_eq!(leer_ui_language(cfg), Some(Lang::En));
    }

    #[test]
    fn language_fuera_de_ui_se_ignora() {
        let cfg = "language: en\nui:\n  theme: dark\n";
        assert_eq!(leer_ui_language(cfg), None);
    }

    #[test]
    fn valor_invalido_devuelve_none() {
        let cfg = "ui:\n  language: fr\n";
        assert_eq!(leer_ui_language(cfg), None);
    }

    #[test]
    fn archivo_vacio_o_roto_devuelve_none() {
        assert_eq!(leer_ui_language(""), None);
        assert_eq!(leer_ui_language("[[[roto\n"), None);
    }

    #[test]
    fn detectar_prioriza_env_valido_sobre_archivo_en() {
        let dir = std::env::temp_dir().join(format!("brain-i18n-env-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("config.yaml"), "ui:\n  language: en\n").unwrap();
        let (nueva, legacy) = (dir.join(".cortex/config.yaml"), dir.join("config.yaml"));
        assert_eq!(detectar(Some("es"), &nueva, &legacy), Lang::Es);
        assert_eq!(detectar(Some("EN "), &nueva, &legacy), Lang::En);
        // env inválido no fuerza: gana el archivo.
        assert_eq!(detectar(Some("fr"), &nueva, &legacy), Lang::En);
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn detectar_lee_archivo_sin_env() {
        let dir = std::env::temp_dir().join(format!("brain-i18n-file-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("config.yaml"), "ui:\n  language: en\n").unwrap();
        assert_eq!(
            detectar(
                None,
                &dir.join(".cortex/config.yaml"),
                &dir.join("config.yaml")
            ),
            Lang::En
        );
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn detectar_default_es_si_no_hay_nada() {
        let fantasma = Path::new("/no/existe/config.yaml");
        assert_eq!(detectar(None, fantasma, fantasma), Lang::Es);
    }
}
