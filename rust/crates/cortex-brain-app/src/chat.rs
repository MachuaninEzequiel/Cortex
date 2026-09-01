//! Chat in-process con el motor `cortex_brain` (Obra 20, G-A4+G-A5).
//!
//! Cuando la UI (o una query IPC) pide algo sobre un proyecto, el
//! engine corre un turno con el motor YA mergeado (`cortex-brain`
//! como lib): backend por proyecto, protocolo TOOL, i18n ES/EN.
//! Sin IPC para esto: todo in-process.
//!
//! G-A5: con el feature `llama` (compila llama.cpp vía cmake) y el
//! GGUF en la convención de rutas (`cortex_brain::paths`), la
//! fábrica monta `LlamaChatBackend` perezosamente por proyecto
//! (carga real del modelo en el primer query). Sin feature o sin
//! GGUF: `DeterministicBackend` (router 1:1, igual que `--no-model`
//! del binario del motor).
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
//! G-A5 (load/unload, doc 20 §2.2):
//! - **Load perezoso:** el modelo entra en RAM en el primer query del
//!   proyecto (cada proyecto tiene su historial/contexto propio).
//! - **Unload por idle:** los backends vencidos (> 90s sin uso,
//!   configurable) se descargan al inicio del próximo turno y via
//!   `reap_idle()`, que la UI llamará desde su ticker (G-A7/G-A10 con
//!   `MarkRam`). Sin ticker aún: si nadie consulta, el modelo queda
//!   en RAM hasta el próximo turno o el cierre.
//! - Limitación v1: N proyectos activos en simultáneo = N copias del
//!   modelo en RAM; el reap las baja a lo sumo a las realmente
//!   recientes. Modelo compartido entre proyectos: futuro.
//!
//! El estado conversacional (historial interno del backend) vive en
//! RAM por proyecto y se pierde al cerrar (doc 20 §9: sin
//! persistencia de historial en v1).
//!
//! Spec: docs/transformacion/20-CORTEX-BRAIN-APP.md §7 (G-A4/G-A5) y
//! docs/transformacion/21-CORTEX-BRAIN-APP-ESTADO.md §12/§13.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use cortex_brain::chat::{DeterministicBackend, LlmBackend, extraer_tool};
use cortex_brain::i18n::{self, Lang};
use cortex_brain::tools::Tier;

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

/// Mensaje persistido en el historial conversacional del proyecto (`.cortex/brain/history.jsonl`).
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct ChatMessagePayload {
    pub id: String,
    pub sender: String, // "user" | "brain"
    pub text: String,
    pub timestamp: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tool_calls: Option<Vec<ToolCall>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub backend: Option<String>,
}

/// Información de un modelo GGUF para la UI (topbar y settings).
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct ModelEntry {
    pub name: String,
    pub filename: String,
    pub path: String,
    pub exists: bool,
    pub active: bool,
    pub size_bytes: Option<u64>,
    pub url: Option<String>,
    pub description: Option<String>,
}

struct CuratedModelInfo {
    name: &'static str,
    filename: &'static str,
    url: &'static str,
    description: &'static str,
    estimated_size: u64,
}

const CURATED_MODELS: &[CuratedModelInfo] = &[
    CuratedModelInfo {
        name: "Liquid LFM2.5 1.2B Instruct (Q4_K_M)",
        filename: "LFM2.5-1.2B-Instruct-Q4_K_M.gguf",
        url: "https://huggingface.co/LiquidCloud/LFM2.5-1.2B-Instruct-GGUF/resolve/main/LFM2.5-1.2B-Instruct-Q4_K_M.gguf",
        description: "Oficial Cortex. Arquitectura híbrida ultraligera optimizada para CPU y bajo consumo de RAM (~730 MB).",
        estimated_size: 728_500_000,
    },
    CuratedModelInfo {
        name: "Qwen 2.5 Coder 1.5B Instruct (Q4_K_M)",
        filename: "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
        url: "https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
        description: "Especialista en código fuente, refactorizaciones y generación multilingüe (~1.1 GB).",
        estimated_size: 1_100_000_000,
    },
    CuratedModelInfo {
        name: "Qwen 2.5 Coder 3B Instruct (Q4_K_M)",
        filename: "qwen2.5-coder-3b-instruct-q4_k_m.gguf",
        url: "https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF/resolve/main/qwen2.5-coder-3b-instruct-q4_k_m.gguf",
        description: "Mayor capacidad de razonamiento en código, ideal para GPUs o CPUs potentes (~2.1 GB).",
        estimated_size: 2_100_000_000,
    },
    CuratedModelInfo {
        name: "DeepSeek R1 Distill 1.5B (Q4_K_M)",
        filename: "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf",
        url: "https://huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf",
        description: "Especialista en razonamiento matemático y deducción paso a paso (Chain-of-Thought) (~1.1 GB).",
        estimated_size: 1_100_000_000,
    },
];

/// Lista los modelos disponibles en la convención `~/.cache/cortex/models/`.
/// Incluye el catálogo curado oficial y cualquier archivo GGUF adicional en disco.
#[must_use]
pub fn list_available_models() -> Vec<ModelEntry> {
    let dir = cortex_brain::paths::default_model_dir();
    let mut models = Vec::new();
    let mut seen_filenames = std::collections::HashSet::new();

    // 1. Catálogo curado oficial
    for cm in CURATED_MODELS {
        let p = dir.join(cm.filename);
        let exists = p.is_file();
        let size = if exists {
            p.metadata().ok().map(|m| m.len())
        } else {
            Some(cm.estimated_size)
        };
        seen_filenames.insert(cm.filename.to_string());
        models.push(ModelEntry {
            name: cm.name.to_string(),
            filename: cm.filename.to_string(),
            path: p.to_string_lossy().into_owned(),
            exists,
            active: cm.filename == cortex_brain::paths::DEFAULT_MODEL_FILENAME && exists,
            size_bytes: size,
            url: Some(cm.url.to_string()),
            description: Some(cm.description.to_string()),
        });
    }

    // 2. Archivos GGUF adicionales escaneados en disco
    if let Ok(entries) = std::fs::read_dir(&dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_file() {
                let name_os = entry.file_name();
                let name_str = name_os.to_string_lossy();
                if name_str.ends_with(".gguf") && !seen_filenames.contains(name_str.as_ref()) {
                    let size = entry.metadata().ok().map(|m| m.len());
                    models.push(ModelEntry {
                        name: name_str.trim_end_matches(".gguf").replace('_', " ").replace('-', " "),
                        filename: name_str.to_string(),
                        path: path.to_string_lossy().into_owned(),
                        exists: true,
                        active: false,
                        size_bytes: size,
                        url: None,
                        description: Some("Modelo GGUF personalizado detectado en caché local.".to_string()),
                    });
                }
            }
        }
    }

    models
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

/// Timeout de idle antes de descargar el backend del proyecto
/// (doc 20 §2.2: 90s default, configurable en la settings GUI G-A7).
const DEFAULT_IDLE_TIMEOUT: Duration = Duration::from_secs(90);

/// Fábrica de backend default (sin inyección). Con feature `llama` +
/// GGUF presente monta el modelo real; si no, None ⇒ determinista.
type BackendFactory = fn(&str) -> Option<BoxBackend>;

/// Backend de un proyecto + cuándo se usó por última vez (para el
/// unload por idle).
struct TurnState {
    backend: BoxBackend,
    last_used: Instant,
}

/// Engine de chat in-process. Un backend por proyecto; los proyectos
/// sin backend asignado se crean via la fábrica (llama si hay feature
/// + GGUF, determinista si no).
pub struct BrainEngine {
    backends: Mutex<HashMap<String, TurnState>>,
    idle_timeout: Duration,
    factory: BackendFactory,
    active_model: Mutex<String>,
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
    /// Engine con la fábrica default (llama real si hay feature +
    /// GGUF, determinista si no) y el idle timeout del doc 20 (90s).
    pub fn new() -> Self {
        Self::with_factory(DEFAULT_IDLE_TIMEOUT, factory_backend_default)
    }

    /// Engine con timeout y fábrica a medida. La fábrica inyectable
    /// permite que la suite corra idéntica con y sin feature `llama`
    /// (los tests inyectan `|_| None` para no cargar el GGUF real).
    pub fn with_factory(idle_timeout: Duration, factory: BackendFactory) -> Self {
        Self {
            backends: Mutex::new(HashMap::new()),
            idle_timeout,
            factory,
            active_model: Mutex::new(cortex_brain::paths::DEFAULT_MODEL_FILENAME.to_string()),
        }
    }

    /// Establece el modelo activo (filename) y desaloja los backends en RAM para que el siguiente turno monte el nuevo modelo.
    pub fn set_active_model(&self, filename: &str) {
        if let Ok(mut cur) = self.active_model.lock() {
            *cur = filename.to_string();
        }
        if let Ok(mut map) = self.backends.lock() {
            map.clear();
        }
        eprintln!("chat: modelo activo cambiado a '{filename}' (backends descargados).");
    }

    /// Obtiene el filename del modelo activo actualmente.
    pub fn active_model(&self) -> String {
        self.active_model
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .clone()
    }

    /// Inyecta/reemplaza el backend de un proyecto (tests; y para
    /// forzar un backend concreto por encima de la fábrica).
    pub fn insert_backend(&self, project: &str, backend: BoxBackend) {
        self.backends
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .insert(
                project.to_string(),
                TurnState {
                    backend,
                    last_used: Instant::now(),
                },
            );
    }

    /// Proyectos con backend vivo en RAM (status bar G-A10: "proyectos
    /// cargados").
    #[must_use]
    pub fn loaded_projects(&self) -> Vec<String> {
        self.backends
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .keys()
            .cloned()
            .collect()
    }

    /// Descarga los backends vencidos por idle (libera RAM: el modelo
    /// sale). La UI lo llama desde su ticker (G-A7/G-A10); `respond`
    /// también reap-ea al empezar cada turno.
    pub fn reap_idle(&self) {
        if let Ok(mut map) = self.backends.lock() {
            self.reap_locked(&mut map);
        }
    }

    /// Resetea y desaloja el contexto conversacional del backend cargado en RAM de un proyecto.
    pub fn clear_project_context(&self, project: &str) {
        if let Ok(mut map) = self.backends.lock() {
            if map.remove(project).is_some() {
                eprintln!("chat: contexto en RAM de {project} reseteado.");
            }
        }
    }

    fn reap_locked(&self, map: &mut HashMap<String, TurnState>) {
        map.retain(|project, ts| {
            let idle = ts.last_used.elapsed();
            if idle <= self.idle_timeout {
                return true;
            }
            eprintln!(
                "chat: descargo '{}' de {project} (idle {}s) para liberar RAM",
                ts.backend.name(),
                idle.as_secs()
            );
            false
        });
    }

    /// Atiende un turno de chat para `project` (modo batch). Espeja
    /// el loop del binario del motor (main.rs): `generate(texto,
    /// catálogo)` → `procesar_respuesta_modelo`. Serializado por el
    /// lock interno: el chdir y el i18n global de proceso son seguros
    /// acá dentro.
    ///
    /// `project` vacío = sin contexto de proyecto (no hay chdir ni
    /// re-detección de idioma; útil para queries sin `--project`).
    pub fn respond(&self, project: &str, text: &str) -> Result<ChatTurn, String> {
        self.respond_streaming(project, text, &mut |_p: &str| {})
    }

    /// Igual que [`respond`](Self::respond) pero en modo streaming
    /// (G-A6): cada pieza que genera el backend sale por `on_piece` a
    /// medida que se genera. Con backends batch (determinista, o el
    /// default del trait) se emite una única pieza con todo el texto.
    ///
    /// Las piezas son la respuesta CRUDA del modelo (incluye líneas
    /// `TOOL:` si el modelo las produce); `ChatTurn::text` sigue
    /// siendo el texto procesado autoritativo (con la salida de las
    /// tools ya integrada) que viaja en el `done`.
    pub fn respond_streaming(
        &self,
        project: &str,
        text: &str,
        on_piece: &mut dyn FnMut(&str),
    ) -> Result<ChatTurn, String> {
        let mut map = self
            .backends
            .lock()
            .map_err(|_| String::from("engine de chat envenenado"))?;
        // Unload por idle: antes de tocar nada, bajo los vencidos.
        self.reap_locked(&mut map);
        let _cwd = ChdirGuard::nuevo(project)?;
        let lang = Self::fijar_idioma(project);

        let active_model_name = self.active_model();
        let ts = map.entry(project.to_string()).or_insert_with(|| {
            let backend = (self.factory)(&active_model_name)
                .unwrap_or_else(|| Box::new(DeterministicBackend) as BoxBackend);
            TurnState {
                backend,
                last_used: Instant::now(),
            }
        });
        let backend_name = ts.backend.name().to_string();
        let out = ts
            .backend
            .generate_streaming(text, &catalogo_tools(), on_piece)?;
        ts.last_used = Instant::now();

        // /quit del slash determinista: despedida, NUNCA exit del proceso.
        if out.trim() == "/quit" {
            return Ok(ChatTurn {
                text: i18n::hasta_proxima(lang).into(),
                tool_calls: Vec::new(),
                backend: backend_name,
            });
        }

        let all_tools = build_all_tools();
        let tool_calls = extraer_tool(&out)
            .map(|(tool, args)| vec![ToolCall { tool, args }])
            .unwrap_or_default();

        let processed = if let Some((ref tool, ref args_tool)) = extraer_tool(&out) {
            if let Some(spec) = all_tools.get(tool.as_str()) {
                if spec.tier == Tier::Read {
                    let tool_out = match dispatch_tool(tool, args_tool, Path::new(project)) {
                        Ok(res) => res,
                        Err(e) => format!("⚠ {e}"),
                    };
                    let sin_tool = cortex_brain::chat::respuesta_sin_tool(&out);
                    if sin_tool.trim().is_empty() {
                        format!("{tool_out}\n")
                    } else {
                        format!("{sin_tool}\n\n{tool_out}\n")
                    }
                } else {
                    // SafeAction: se reporta para confirmación del usuario y se avisa en el texto
                    let mut s = cortex_brain::chat::respuesta_sin_tool(&out);
                    if !s.trim().is_empty() {
                        s.push('\n');
                    }
                    s.push_str(i18n::no_ejecutado(lang));
                    s.push('\n');
                    s
                }
            } else {
                format!("{}\n{}", out, i18n::tool_inexistente(lang, tool))
            }
        } else {
            out
        };

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
        let p = Path::new(project);
        if !p.is_dir() {
            return Ok(Self { previo: None });
        }
        let previo = std::env::current_dir().ok();
        std::env::set_current_dir(p)
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

/// Catálogo completo de tools de Cortex Brain (base + gobernanza + webgraph).
pub fn build_all_tools() -> std::collections::BTreeMap<&'static str, cortex_brain::tools::ToolSpec> {
    let mut t = cortex_brain::tools::build_tools();
    t.insert(
        "session.status",
        cortex_brain::tools::ToolSpec {
            name: "session.status",
            description: "Consulta la sesión activa en .cortex/sessions/, spec asociada y checkpoints.",
            tier: Tier::Read,
            args_hint: "",
        },
    );
    t.insert(
        "session.checkpoint",
        cortex_brain::tools::ToolSpec {
            name: "session.checkpoint",
            description: "Registra un checkpoint en la sesión activa.",
            tier: Tier::SafeAction,
            args_hint: "<nota>",
        },
    );
    t.insert(
        "session.finish_and_document",
        cortex_brain::tools::ToolSpec {
            name: "session.finish_and_document",
            description: "Coordina la documentación de evidencia y cierre de la sesión.",
            tier: Tier::SafeAction,
            args_hint: "",
        },
    );
    t.insert(
        "doctor.inspect",
        cortex_brain::tools::ToolSpec {
            name: "doctor.inspect",
            description: "Diagnóstico de salud de Cortex (workspace, vault, memoria).",
            tier: Tier::Read,
            args_hint: "",
        },
    );
    t.insert(
        "webgraph.query",
        cortex_brain::tools::ToolSpec {
            name: "webgraph.query",
            description: "Consulta archivos, módulos y specs en el grafo del proyecto.",
            tier: Tier::Read,
            args_hint: "<termino>",
        },
    );
    t
}

/// Ejecuta una tool despachando entre las herramientas de la app y el motor base.
pub fn dispatch_tool(tool: &str, args: &str, project_root: &Path) -> Result<String, String> {
    match tool {
        "session.status" => {
            let s = crate::graph::inspect_session_status(project_root);
            if s.active {
                let id = s.session_id.unwrap_or_else(|| "activa".to_string());
                let spec = s.spec_path.unwrap_or_else(|| "vault/specs/spec.md".to_string());
                let last = s.last_checkpoint.unwrap_or_else(|| "Inicio".to_string());
                Ok(format!(
                    "📌 **Sesión Activa:** [Sesión #{id}]({spec})\n- **Checkpoints:** {}\n- **Último avance:** {last}",
                    s.checkpoints_count
                ))
            } else {
                Ok("○ No hay ninguna sesión de trabajo activa en .cortex/sessions/. Podés iniciar una nueva sesión para registrar tus avances.".to_string())
            }
        }
        "doctor.inspect" => {
            let doc = crate::graph::inspect_doctor_health(project_root);
            let mut out = format!(
                "🛡️ **Auditoría de Salud de Cortex:** {}\n\n",
                if doc.is_healthy { "✓ Proyecto en estado óptimo" } else { "⚠ Se detectaron detalles para corregir" }
            );
            for c in doc.checks {
                let icon = match c.status.as_str() {
                    "ok" => "✓",
                    "warn" => "▲",
                    _ => "✗",
                };
                out.push_str(&format!("- [{icon}] **{}**: {}\n", c.name, c.message));
            }
            Ok(out)
        }
        "webgraph.query" => {
            let g = crate::graph::extract_project_graph(project_root);
            let q = args.trim().to_lowercase();
            let matches: Vec<_> = g.nodes.into_iter().filter(|n| {
                q.is_empty() || n.label.to_lowercase().contains(&q) || n.path.to_lowercase().contains(&q)
            }).take(8).collect();

            if matches.is_empty() {
                Ok(format!("No se encontraron nodos en el grafo para '{args}'."))
            } else {
                let mut out = format!("🕸️ **Nodos encontrados en WebGraph para '{args}':**\n");
                for m in matches {
                    let icon = match m.kind.as_str() { "module" => "📦", "spec" => "📄", "adr" => "🏛️", _ => "📄" };
                    out.push_str(&format!("- {} [{}]({})\n", icon, m.label, m.path));
                }
                Ok(out)
            }
        }
        "vault.stats" => {
            let count = count_markdown(&project_root.join("vault"));
            Ok(format!("Vault: {count} notas .md"))
        }
        _ => cortex_brain::tools::dispatch(tool, std::slice::from_ref(&args.to_string())),
    }
}

fn count_markdown(dir: &Path) -> usize {
    if !dir.is_dir() {
        return 0;
    }
    let mut count = 0;
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let p = entry.path();
            if p.is_dir() {
                count += count_markdown(&p);
            } else if p.extension().is_some_and(|e| e == "md") {
                count += 1;
            }
        }
    }
    count
}

/// Catálogo compacto de tools para el prompt del LLM.
fn catalogo_tools() -> String {
    build_all_tools()
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

// ── Fábrica de backends (G-A5 / Pilar 3) ──────────────────────────────

/// Fábrica default del engine. Con feature `llama` intenta el GGUF;
/// sin feature no hay modelo posible (None ⇒ determinista).
#[cfg(feature = "llama")]
fn factory_backend_default(model_filename: &str) -> Option<BoxBackend> {
    crear_backend_llama(model_filename)
}

#[cfg(not(feature = "llama"))]
fn factory_backend_default(_model_filename: &str) -> Option<BoxBackend> {
    None
}

/// Monta `LlamaChatBackend` con el GGUF especificado (o el oficial por default).
/// Carga real: segundos de disco/CPU. Si falta el GGUF o la carga falla ⇒ None
/// (aviso) y el engine cae a determinista. Muestreo greedy (temp 0) con seed 42.
#[cfg(feature = "llama")]
fn crear_backend_llama(model_filename: &str) -> Option<BoxBackend> {
    let dir = cortex_brain::paths::default_model_dir();
    let model_path = dir.join(model_filename);
    let resolved_path = if model_path.is_file() {
        model_path
    } else {
        cortex_brain::paths::default_model_path_if_exists()?
    };
    eprintln!(
        "chat: cargando modelo {} (puede tardar unos segundos)…",
        resolved_path.display()
    );
    let start = Instant::now();
    match cortex_brain::llama::LlamaChatBackend::open(&resolved_path, Some(&system_prompt())) {
        Ok(backend) => {
            eprintln!(
                "chat: modelo cargado en {:.1}s",
                start.elapsed().as_secs_f32()
            );
            Some(Box::new(backend.with_temp(0.0).with_seed(42)))
        }
        Err(e) => {
            eprintln!("chat: no pude cargar el modelo ({e}); modo determinista");
            None
        }
    }
}

/// System prompt del brain. Espejo del binario del motor
/// (`cortex-brain/src/main.rs`, que lo arma con `help_text()` +
/// reglas TOOL), con la frase de ejecución adaptada a la GUI: las
/// read-tools se auto-ejecutan, las mutaciones se proponen como
/// comando exacto (decisión G-A4 del dueño).
#[cfg(feature = "llama")]
fn system_prompt() -> String {
    format!(
        "Sos el asistente local de Cortex, experto en gobernanza, arquitectura y ciclo de vida de ESTE proyecto.\n\n\
         Catálogo de herramientas disponibles:\n{}\n\n\
         Reglas estrictas:\n\
         - NUNCA ejecutás mutaciones destructivas: si la acción es mutante, proponés el comando exacto para que el usuario apruebe.\n\
         - Si necesitás datos reales (sesión, memoria, salud, grafo, stats), respondé UNICAMENTE una línea con el formato:\nTOOL: <nombre> <argumentos>\n\
         y nada más; las tools [read] el brain las ejecuta automáticamente y enriquece la respuesta.\n\
         - Si mencionás un archivo o spec, incluí su ruta en formato markdown: [nombre.md](file:///ruta).\n\
         - Si no necesitás herramientas, respondé normalmente y breve.",
        catalogo_tools()
    )
}

// ── Tests ─────────────────────────────────────────────────────────────────
//
// ENV_LOCK serializa los tests que tocan CORTEX_BIN (env de proceso;
// los tests del mismo binario corren en paralelo). Mismo patrón que
// ipc.rs. Los tests de server e2e (lib.rs) comparten este lock vía
// crate::ipc::tests::ENV_LOCK para no pisar XDG_RUNTIME_DIR.

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use cortex_brain::chat::ScriptedBackend;

    static ENV_LOCK: Mutex<()> = Mutex::new(());

    /// Backend de test que emite de a piezas (implementa
    /// generate_streaming con streaming real de a piezas). Lo usa el
    /// módulo de tests de lib.rs para el e2e del server.
    pub(crate) struct PiezasBackend {
        pub(crate) piezas: Vec<String>,
    }

    impl LlmBackend for PiezasBackend {
        fn name(&self) -> &str {
            "piezas-test"
        }

        fn generate(&mut self, _prompt: &str, _tools_help: &str) -> Result<String, String> {
            Ok(self.piezas.concat())
        }

        fn generate_streaming(
            &mut self,
            _prompt: &str,
            _tools_help: &str,
            on_piece: &mut dyn FnMut(&str),
        ) -> Result<String, String> {
            for p in &self.piezas {
                on_piece(p);
            }
            Ok(self.piezas.concat())
        }
    }

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
        // Fábrica None: aunque la suite corra con --features llama y
        // haya GGUF, los tests NUNCA cargan el modelo real (rápidos y
        // deterministas); el camino llama se cubre con el smoke
        // #[ignore].
        let engine = BrainEngine::with_factory(DEFAULT_IDLE_TIMEOUT, |_| None);
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
        // Sin backend inyectado ⇒ fábrica (None en tests ⇒
        // DeterministicBackend). Texto libre sin match ni keywords ⇒
        // razón + ayuda, sin invocar el CLI cortex.
        let engine = BrainEngine::with_factory(DEFAULT_IDLE_TIMEOUT, |_| None);
        let turn = engine.respond("", "xyzzy").expect("turno");
        assert!(turn.text.contains("sin match"), "text: {}", turn.text);
        assert!(turn.text.contains("memory.search"), "text: {}", turn.text);
        assert!(turn.tool_calls.is_empty());
    }

    #[test]
    fn slash_quit_no_mata_la_app() {
        let engine = BrainEngine::with_factory(DEFAULT_IDLE_TIMEOUT, |_| None);
        let turn = engine.respond("", "/quit").expect("turno");
        assert_eq!(turn.text, i18n::hasta_proxima(i18n::actual()));
        assert!(turn.tool_calls.is_empty());
    }

    #[test]
    fn reap_idle_descarga_backend_vencido() {
        let proj = tmp_project("reap");
        let engine = BrainEngine::with_factory(Duration::from_millis(10), |_| None);
        engine.insert_backend(&proj, Box::new(ScriptedBackend::new("reap-test", ["uno"])));
        let t = engine.respond(&proj, "x").expect("turno");
        assert_eq!(t.text.trim(), "uno");
        assert!(engine.loaded_projects().contains(&proj));

        std::thread::sleep(Duration::from_millis(40));
        engine.reap_idle();
        assert!(engine.loaded_projects().is_empty(), "vencido ⇒ reapeado");

        // El próximo turno re-crea el backend via fábrica: determinista
        // (el script muerto no resucita).
        let t2 = engine.respond(&proj, "xyzzy").expect("turno 2");
        assert!(
            t2.backend.contains("determinista"),
            "backend: {}",
            t2.backend
        );
        assert!(t2.text.contains("sin match"), "text: {}", t2.text);
        std::fs::remove_dir_all(&proj).unwrap();
    }

    #[test]
    fn backend_vigente_no_se_reapea() {
        let proj = tmp_project("vigente");
        let engine = BrainEngine::with_factory(Duration::from_secs(60), |_| None);
        engine.insert_backend(&proj, Box::new(ScriptedBackend::new("vigente", ["x"])));
        engine.respond(&proj, "q").expect("turno");
        engine.reap_idle();
        assert!(engine.loaded_projects().contains(&proj), "vivo ⇒ queda");
        std::fs::remove_dir_all(&proj).unwrap();
    }

    #[test]
    fn streaming_entrega_piezas_en_orden() {
        let proj = tmp_project("stream");
        let engine = BrainEngine::with_factory(DEFAULT_IDLE_TIMEOUT, |_| None);
        engine.insert_backend(
            &proj,
            Box::new(PiezasBackend {
                piezas: vec!["La ".into(), "sesión ".into(), "está activa".into()],
            }),
        );
        let mut recibidas: Vec<String> = Vec::new();
        let turn = engine
            .respond_streaming(&proj, "estado", &mut |p: &str| {
                recibidas.push(p.to_string())
            })
            .expect("turno");
        assert_eq!(recibidas, vec!["La ", "sesión ", "está activa"]);
        assert_eq!(turn.text.trim(), "La sesión está activa");
        assert_eq!(turn.backend, "piezas-test");
        std::fs::remove_dir_all(&proj).unwrap();
    }

    #[test]
    fn respond_batch_sigue_andando_sobre_streaming() {
        // respond() delega en respond_streaming con callback no-op: el
        // resultado final es idéntico al camino batch (G-A4 intacto).
        let proj = tmp_project("batch");
        let engine = BrainEngine::with_factory(DEFAULT_IDLE_TIMEOUT, |_| None);
        engine.insert_backend(
            &proj,
            Box::new(PiezasBackend {
                piezas: vec!["a".into(), "b".into()],
            }),
        );
        let turn = engine.respond(&proj, "x").expect("turno");
        assert_eq!(turn.text.trim(), "ab");
        std::fs::remove_dir_all(&proj).unwrap();
    }

    /// Smoke REAL del modelo (G-A5/G-A6, criterio de pase del doc 20).
    /// Carga el GGUF de ~/.cache/cortex/models/ y genera una respuesta:
    /// puede tardar decenas de segundos en CPU.
    /// Correr con: cargo test -p cortex-brain-app --features llama -- --ignored
    #[cfg(feature = "llama")]
    #[test]
    #[ignore = "carga el GGUF real (~730 MB) y genera con el modelo"]
    fn smoke_llama_real_responde() {
        let proj = tmp_project("llama-smoke");
        let engine = BrainEngine::new(); // fábrica default ⇒ llama
        let mut piezas: usize = 0;
        let turn = engine
            .respond_streaming(&proj, "contá hasta tres separado por comas", &mut |_p| {
                piezas += 1;
            })
            .expect("turno con modelo real");
        assert_eq!(turn.backend, "llama.cpp (GGUF)");
        assert!(!turn.text.trim().is_empty(), "text: {:?}", turn.text);
        // Streaming REAL: llama.cpp genera de a piezas, no de una.
        assert!(piezas > 1, "piezas generadas: {piezas} (¿streaming roto?)");
        eprintln!("smoke: {piezas} piezas, respuesta: {:?}", turn.text);
        std::fs::remove_dir_all(&proj).unwrap();
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

    #[test]
    fn lista_modelos_incluye_default() {
        let models = list_available_models();
        assert!(!models.is_empty());
        assert_eq!(
            models[0].filename,
            cortex_brain::paths::DEFAULT_MODEL_FILENAME
        );
        assert!(models[0].name.contains("LFM2.5"));
    }
}
