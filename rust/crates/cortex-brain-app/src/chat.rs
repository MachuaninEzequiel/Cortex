//! Chat in-process con el motor `cortex_brain` (Obra 20, G-A4).
//!
//! Cuando la UI (o una query IPC) pide algo sobre un proyecto, el
//! engine corre un turno con el motor YA mergeado (`cortex-brain`
//! como lib): backend por proyecto, protocolo TOOL, i18n ES/EN.
//! Sin IPC para esto: todo in-process. El modelo GGUF real entra en
//! G-A5 (feature `llama`); hoy el default es `DeterministicBackend`
//! (router 1:1, igual que `--no-model` del binario del motor).
//!
//! Decisiones cerradas con el dueño (G-A4):
//! - **Read-tools auto-ejecutadas:** las `TOOL:` que propone el
//!   modelo con tier `Read` (memory.search, cortex.health, etc.) se
//!   ejecutan sin confirmación. Las `SafeAction` (webgraph.serve) se
//!   DENIEGAN hasta que exista el modal de aprobación (G-A7+) y se
//!   reportan en `ChatTurn::tool_calls` para que la UI las ofrezca.
//! - **CWD de las tools:** `tools::dispatch` shell-out al CLI
//!   `cortex` heredando CWD (así lo hace el binario del motor con
//!   `set_current_dir`). Acá el chdir al proyecto se hace DENTRO del
//!   lock del engine: los turnos están serializados y el resto de la
//!   app usa rutas absolutas, así que el CWD de proceso es seguro.
//!   Un guard restaura el CWD previo al terminar el turno.
//! - **`/quit` vía IPC no mata la app:** devuelve la despedida.
//!
//! El estado conversacional (historial interno del backend) vive en
//! RAM por proyecto y se pierde al cerrar (doc 20 §9: sin
//! persistencia de historial en v1).
//!
//! Spec: docs/transformacion/20-CORTEX-BRAIN-APP.md §7 (G-A4) y
//! docs/transformacion/21-CORTEX-BRAIN-APP-ESTADO.md §12.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

use cortex_brain::chat::{
    extraer_tool, procesar_respuesta_modelo, DeterministicBackend, LlmBackend,
};
use cortex_brain::i18n::{self, Lang};
use cortex_brain::tools::{build_tools, Tier};

/// Backend de un proyecto. `Send` porque el engine se comparte por
/// `Arc` entre threads del server IPC.
type BoxBackend = Box<dyn LlmBackend + Send>;

/// Un tool call propuesto por el modelo. Hoy viaja en la respuesta
/// IPC para que el cliente lo liste; en G-A7 la UI lo muestra con el
/// botón [Ejecutar] (modal de aprobación, mismo patrón del Companion).
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct ToolCall {
    pub tool: String,
    pub args: String,
}

/// Resultado de un turno de chat. Serialize porque es el return de
/// un command Tauri (IpcResponse exige Serialize).
#[derive(Debug, Clone, serde::Serialize)]
pub struct ChatTurn {
    /// Texto a mostrar al usuario: sin líneas `TOOL:`, con la salida
    /// de las read-tools auto-ejecutadas ya integrada.
    pub text: String,
    /// Tool call detectado en la respuesta (el primero, que es el que
    /// procesa `procesar_respuesta_modelo`). Vacío si no hubo.
    pub tool_calls: Vec<ToolCall>,
    /// `name()` del backend que atendió el turno (status bar futuro).
    pub backend: String,
}

/// Engine de chat in-process. Un backend por proyecto; los proyectos
/// sin backend asignado usan `DeterministicBackend`.
pub struct BrainEngine {
    backends: Mutex<HashMap<String, BoxBackend>>,
}

/// Engine compartido: un único `Arc` para el server IPC y para el
/// estado Tauri (`app.manage`), de modo que el estado conversacional
/// por proyecto es el MISMO desde ambos caminos (G-A7 lo consume).
pub type SharedEngine = std::sync::Arc<BrainEngine>;

impl Default for BrainEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl BrainEngine {
    /// Engine vacío: todo proyecto cae al backend determinista.
    /// G-A5 monta `LlamaChatBackend` por proyecto cuando haya GGUF.
    pub fn new() -> Self {
        Self {
            backends: Mutex::new(HashMap::new()),
        }
    }

    /// Inyecta/reemplaza el backend de un proyecto (tests hoy; G-A5
    /// lo usa para montar el backend llama).
    pub fn insert_backend(&self, project: &str, backend: BoxBackend) {
        self.backends
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .insert(project.to_string(), backend);
    }

    /// Atiende un turno de chat para `project`. Espeja el loop del
    /// binario del motor (main.rs): `generate(texto, catálogo)` →
    /// `procesar_respuesta_modelo`. Serializado por el lock interno:
    /// el chdir y el i18n global de proceso son seguros acá dentro.
    ///
    /// `project` vacío = sin contexto de proyecto (no hay chdir ni
    /// re-detección de idioma; útil para queries sin `--project`).
    pub fn respond(&self, project: &str, text: &str) -> Result<ChatTurn, String> {
        let mut map = self
            .backends
            .lock()
            .map_err(|_| String::from("engine de chat envenenado"))?;
        let _cwd = ChdirGuard::nuevo(project)?;
        let lang = Self::fijar_idioma(project);

        let backend = map
            .entry(project.to_string())
            .or_insert_with(|| Box::new(DeterministicBackend) as BoxBackend);
        let backend_name = backend.name().to_string();
        let out = backend.generate(text, &catalogo_tools())?;

        // /quit del slash determinista: despedida, NUNCA exit del proceso.
        if out.trim() == "/quit" {
            return Ok(ChatTurn {
                text: i18n::hasta_proxima(lang).into(),
                tool_calls: Vec::new(),
                backend: backend_name,
            });
        }

        let tool_calls = extraer_tool(&out)
            .map(|(tool, args)| vec![ToolCall { tool, args }])
            .unwrap_or_default();
        let processed = procesar_respuesta_modelo(&out, &build_tools(), &mut |tool, _args| {
            // Read ⇒ auto-ejecuta (decisión del dueño, G-A4);
            // SafeAction y desconocidas ⇒ denegadas (el modal de
            // aprobación llega con la UI completa).
            build_tools()
                .get(tool)
                .is_some_and(|spec| spec.tier == Tier::Read)
        });

        Ok(ChatTurn {
            text: processed,
            tool_calls,
            backend: backend_name,
        })
    }

    /// Idioma del chrome para el proyecto: CORTEX_LANG >
    /// `<proyecto>/.cortex/config.yaml` > `<proyecto>/config.yaml` >
    /// es (misma resolución que el binario del motor). Se fija bajo
    /// el lock del engine, así que no hay carrera entre turnos.
    fn fijar_idioma(project: &str) -> Lang {
        if project.is_empty() {
            return i18n::actual();
        }
        let root = Path::new(project);
        let lang = i18n::detectar(
            std::env::var("CORTEX_LANG").ok().as_deref(),
            &root.join(".cortex").join("config.yaml"),
            &root.join("config.yaml"),
        );
        i18n::fijar(lang);
        lang
    }
}

/// chdir al proyecto durante el turno. Las tools del motor invocan el
/// CLI `cortex` heredando CWD; el lock del engine garantiza que ningún
/// otro turno pise el CWD mientras éste corre. Al dropear restaura.
struct ChdirGuard {
    previo: Option<PathBuf>,
}

impl ChdirGuard {
    fn nuevo(project: &str) -> Result<Self, String> {
        if project.is_empty() {
            return Ok(Self { previo: None });
        }
        let previo = std::env::current_dir().ok();
        std::env::set_current_dir(project)
            .map_err(|e| format!("no pude entrar al proyecto {project}: {e}"))?;
        Ok(Self { previo })
    }
}

impl Drop for ChdirGuard {
    fn drop(&mut self) {
        if let Some(previo) = &self.previo {
            let _ = std::env::set_current_dir(previo);
        }
    }
}

/// Catálogo compacto de tools para el prompt del LLM. Espejo de
/// `cortex-brain/src/main.rs::catalogo_tools` (esa vive en el binario
/// del motor, no en la lib; duplicarla acá evita tocar el crate del
/// motor, que no es de esta obra).
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

// ── Tests ─────────────────────────────────────────────────────────────────
//
// ENV_LOCK serializa los tests que tocan CORTEX_BIN (env de proceso;
// los tests del mismo binario corren en paralelo). Mismo patrón que
// ipc.rs. Los tests de server e2e (lib.rs) comparten este lock vía
// crate::ipc::tests::ENV_LOCK para no pisar XDG_RUNTIME_DIR.

#[cfg(test)]
mod tests {
    use super::*;
    use cortex_brain::chat::ScriptedBackend;

    static ENV_LOCK: Mutex<()> = Mutex::new(());

    /// Proyecto real en tempdir: el engine hace chdir al atender un
    /// turno, así que el path debe existir.
    fn tmp_project(tag: &str) -> String {
        let dir =
            std::env::temp_dir().join(format!("cortex-brain-chat-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir.to_string_lossy().into_owned()
    }

    fn engine_con(project: &str, respuestas: &[&str]) -> BrainEngine {
        let engine = BrainEngine::new();
        engine.insert_backend(
            project,
            Box::new(ScriptedBackend::new(
                "script-test",
                respuestas.iter().copied(),
            )),
        );
        engine
    }

    #[test]
    fn scripted_responde_y_mantiene_estado() {
        let proj = tmp_project("estado");
        let engine = engine_con(&proj, &["respuesta 1", "respuesta 2"]);
        let t1 = engine.respond(&proj, "hola").expect("turno 1");
        assert_eq!(t1.text.trim(), "respuesta 1");
        assert_eq!(t1.backend, "script-test");
        // Segunda query al MISMO proyecto consume el siguiente turno
        // del script: el estado conversacional persiste por proyecto.
        let t2 = engine.respond(&proj, "otra").expect("turno 2");
        assert_eq!(t2.text.trim(), "respuesta 2");
        std::fs::remove_dir_all(&proj).unwrap();
    }

    #[test]
    fn engine_aisla_proyectos() {
        let a = tmp_project("a");
        let b = tmp_project("b");
        let engine = BrainEngine::new();
        engine.insert_backend(&a, Box::new(ScriptedBackend::new("a", ["solo A"])));
        engine.insert_backend(&b, Box::new(ScriptedBackend::new("b", ["solo B"])));
        assert_eq!(engine.respond(&a, "x").unwrap().text.trim(), "solo A");
        assert_eq!(engine.respond(&b, "x").unwrap().text.trim(), "solo B");
        // El script de A se agotó: el error es del backend de A, no de B.
        let err = engine.respond(&a, "x").unwrap_err();
        assert!(err.contains("script agotado"), "err: {err}");
        let err_b = engine.respond(&b, "x").unwrap_err();
        assert!(err_b.contains("script agotado"), "err: {err_b}");
        std::fs::remove_dir_all(&a).unwrap();
        std::fs::remove_dir_all(&b).unwrap();
    }

    #[test]
    fn determinista_sin_match_no_necesita_cli() {
        // Sin backend inyectado ⇒ DeterministicBackend. Texto libre sin
        // match ni keywords ⇒ razón + ayuda, sin invocar el CLI cortex.
        let engine = BrainEngine::new();
        let turn = engine.respond("", "xyzzy").expect("turno");
        assert!(turn.text.contains("sin match"), "text: {}", turn.text);
        assert!(turn.text.contains("memory.search"), "text: {}", turn.text);
        assert!(turn.tool_calls.is_empty());
    }

    #[test]
    fn slash_quit_no_mata_la_app() {
        let engine = BrainEngine::new();
        let turn = engine.respond("", "/quit").expect("turno");
        assert_eq!(turn.text, i18n::hasta_proxima(i18n::actual()));
        assert!(turn.tool_calls.is_empty());
    }

    #[test]
    fn tool_read_se_autoejecuta_y_se_reporta() {
        let _env = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        unsafe { std::env::set_var("CORTEX_BIN", "/bin/echo") };
        let proj = tmp_project("tool");
        let engine = engine_con(&proj, &["TOOL: memory.search jwt"]);
        let turn = engine.respond(&proj, "busca jwt").expect("turno");
        unsafe { std::env::remove_var("CORTEX_BIN") };
        std::fs::remove_dir_all(&proj).unwrap();
        // La read-tool se ejecutó: la salida del CLI está en el texto.
        assert!(turn.text.contains("search jwt"), "text: {}", turn.text);
        assert!(!turn.text.contains("TOOL:"), "línea TOOL: no se muestra");
        assert_eq!(turn.tool_calls.len(), 1);
        assert_eq!(turn.tool_calls[0].tool, "memory.search");
        assert_eq!(turn.tool_calls[0].args, "jwt");
    }

    #[test]
    fn safe_action_se_deniega_y_se_reporta() {
        let proj = tmp_project("safe");
        let engine = engine_con(&proj, &["TOOL: webgraph.serve"]);
        let turn = engine.respond(&proj, "abrí el grafo").expect("turno");
        std::fs::remove_dir_all(&proj).unwrap();
        // Denegada: aviso visible, sin salida de la tool.
        assert!(
            turn.text.contains(i18n::no_ejecutado(i18n::actual())),
            "text: {}",
            turn.text
        );
        // Pero se reporta para que la UI la ofrezca con [Ejecutar].
        assert_eq!(turn.tool_calls.len(), 1);
        assert_eq!(turn.tool_calls[0].tool, "webgraph.serve");
    }
}
