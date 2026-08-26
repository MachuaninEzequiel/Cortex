//! Porteo de `cortex/mcp/server.py` (Obra 07 P9, stream B).
//!
//! Dispatcher sincrónico con la tabla de rutas `_TOOL_ROUTES` congelada por
//! `tests/unit/mcp/test_golden_contract.py`, la ruta inline histórica
//! `cortex_sync_vault`, el mensaje estable de herramienta desconocida y el
//! `cortex_ping` completo (payload JSON indent=2, ensure_ascii=False).
//!
//! Estado del porteo (paridad honesta, patrón P6):
//! - `cortex_ping`: implementación COMPLETA (solo lee estado in-memory).
//! - `cortex_sync_vault`: ruta inline espejada contra un backend inyectable.
//! - Resto de tools: rutean correctamente pero devuelven fallo explícito
//!   documentado hasta que sus backends sean nativos (P11/P12).
//! - Transporte rmcp stdio funcional; el wire-format exacto del transporte
//!   (nulls explícitos del modelo Python vs omisión rmcp) es tema P12 — el
//!   gate de P9 es contrato de catálogo + dispatch, no bytes de transporte.

use std::collections::{BTreeMap, VecDeque};
use std::sync::{Arc, Mutex};
use std::time::Instant;

use crate::tools_catalog::{build_tool_definitions, SERVER_VERSION};
use crate::{handlers_autopilot, handlers_docs, handlers_finish, handlers_search, handlers_spec};

/// Grace de arranque: `starting` durante los primeros 2.0 s (espejo de
/// `_STARTUP_GRACE_SECONDS`).
pub const STARTUP_GRACE_SECONDS: f64 = 2.0;
/// Ventana de errores recientes para `degraded`/`recent_errors_count`
/// (espejo de `_ERROR_RECENT_WINDOW_SECONDS`).
pub const ERROR_RECENT_WINDOW_SECONDS: f64 = 300.0;
/// Capacidad del rolling buffer de errores (espejo de `deque(maxlen=10)`).
pub const ERROR_HISTORY_MAXLEN: usize = 10;

/// Entrada del historial de errores (espejo del dict de Python:
/// {"tool", "error", "timestamp"} con ISO local).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ErrorEntry {
    pub tool: String,
    pub error: String,
    pub timestamp: String,
}

impl ErrorEntry {
    /// Constructor con timestamp explícito (tests/paridad inyectan reloj).
    pub fn new(tool: &str, error: &str, timestamp: impl Into<String>) -> Self {
        ErrorEntry {
            tool: tool.to_string(),
            error: error.to_string(),
            timestamp: timestamp.into(),
        }
    }

    /// Registro con el reloj real del proceso (`datetime.now().isoformat()`).
    pub fn now(tool: &str, error: &str) -> Self {
        ErrorEntry::new(tool, error, format_iso_now())
    }
}

/// Backend de memoria inyectable para la ruta inline `cortex_sync_vault`.
pub trait MemoryBackend: Send + Sync {
    fn sync_vault(&mut self) -> Result<u64, String>;
}

/// Handlers in-process de la familia sesiones (P12A-9).
pub use crate::handlers_sessions as sessions_handlers;
pub use crate::handlers_sessions::SessionsBackend;

/// Contador simple de documentos indexados (tests / modo embebido).
#[derive(Default)]
pub struct CountingMemory {
    pub count: u64,
}

impl MemoryBackend for CountingMemory {
    fn sync_vault(&mut self) -> Result<u64, String> {
        Ok(self.count)
    }
}

/// Servidor MCP nativo. Espejo mínimo de `CortexMCPServer`.
pub struct CortexMcpServer<M: MemoryBackend = CountingMemory> {
    startup_time: Instant,
    /// Segundos desde epoch UTC (inyectable para tests).
    now_epoch: Box<dyn Fn() -> f64 + Send + Sync>,
    error_history: VecDeque<ErrorEntry>,
    memory: Option<M>,
    models_loaded: Vec<String>,
    /// Backend in-process de sesiones (P12A-9). None ⇒ fallo explícito.
    sessions_backend: Option<std::sync::Arc<std::sync::Mutex<dyn SessionsBackend + Send>>>,
    /// Backends in-process de las familias no-sesión (Cierre T1).
    search_backend:
        Option<std::sync::Arc<std::sync::Mutex<dyn handlers_search::SearchBackend + Send>>>,
    docs_backend: Option<std::sync::Arc<std::sync::Mutex<dyn handlers_docs::DocsBackend + Send>>>,
    spec_backend: Option<std::sync::Arc<std::sync::Mutex<dyn handlers_spec::SpecBackend + Send>>>,
    finish_backend:
        Option<std::sync::Arc<std::sync::Mutex<dyn handlers_finish::FinishBackend + Send>>>,
    /// Backend in-process de la familia autopilot (Cierre T3).
    autopilot_backend:
        Option<std::sync::Arc<std::sync::Mutex<dyn handlers_autopilot::AutopilotBackend + Send>>>,
    /// Estado transversal de la familia spec (`_called_tools` + stamp del
    /// gap de proposal). Se alimenta con CADA tool llamada, como el
    /// `_log_tool_call` de Python.
    spec_state: handlers_spec::SpecServerState,
    /// Raíz del proyecto para `_extract_candidate_files` / claims.
    pub project_root: std::path::PathBuf,
}

/// Tabla de ruteo nombre → handler. CONGELADA por
/// tests/unit/mcp/test_golden_contract.py (el orden no es significativo;
/// el contenido sí). La ruta especial `cortex_sync_vault` NO está acá: el
/// dispatcher la resuelve inline contra memory.sync_vault().
pub fn tool_routes() -> BTreeMap<&'static str, &'static str> {
    [
        ("cortex_ping", "_ping_text"),
        ("cortex_search", "_search_text_dispatch"),
        ("cortex_search_vector", "_search_vector_text"),
        ("cortex_context", "_context_text"),
        ("cortex_sync_ticket", "_build_sync_ticket_context"),
        ("cortex_create_spec", "_create_spec_text"),
        ("cortex_emit_proposal", "_emit_proposal_text"),
        ("cortex_save_session", "_save_session_text"),
        ("cortex_validate_handoff", "_validate_handoff_text"),
        (
            "cortex_verify_session_claims",
            "_verify_session_claims_text",
        ),
        ("cortex_import_hu", "_import_hu_text"),
        ("cortex_get_hu", "_get_hu_text"),
        ("cortex_autopilot_start", "_autopilot_tools.start"),
        ("cortex_autopilot_preflight", "_autopilot_tools.preflight"),
        ("cortex_autopilot_checkpoint", "_autopilot_tools.checkpoint"),
        ("cortex_autopilot_finish", "_autopilot_tools.finish"),
        ("cortex_autopilot_status", "_autopilot_tools.status"),
        ("cortex_session_open", "_session_open_text"),
        ("cortex_session_checkpoint", "_session_checkpoint_text"),
        ("cortex_session_close", "_session_close_text"),
        ("cortex_session_status", "_session_status_text"),
        ("cortex_session_list", "_session_list_text"),
        ("cortex_finish_session", "_finish_session_text"),
        ("cortex_documenter_briefing", "_documenter_briefing_text"),
        ("cortex_close_session", "_close_session_text"),
        (
            "cortex_review_checkpoint",
            "_session_review_checkpoint_text",
        ),
        ("write_design_note_canonical", "_write_design_note_text"),
        ("cortex_write_doc", "_write_doc_text"),
        ("cortex_self_review_note", "_self_review_note_text"),
        ("cortex_session_task_list", "_session_task_list_text"),
        ("cortex_session_task_update", "_session_task_update_text"),
    ]
    .into_iter()
    .collect()
}

impl Default for CortexMcpServer<CountingMemory> {
    fn default() -> Self {
        Self::new()
    }
}

impl CortexMcpServer<CountingMemory> {
    /// Servidor "bare" como el fixture Python: sin backend de memoria
    /// (`indices_loaded=false`) ni modelos cargados.
    pub fn new() -> Self {
        Self::build(None)
    }
}

impl<M: MemoryBackend + 'static> CortexMcpServer<M> {
    pub fn with_memory(memory: M) -> Self {
        Self::build(Some(memory))
    }

    fn build(memory: Option<M>) -> Self {
        Self {
            startup_time: Instant::now(),
            now_epoch: Box::new(|| {
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_secs_f64()
            }),
            error_history: VecDeque::with_capacity(ERROR_HISTORY_MAXLEN),
            memory,
            models_loaded: Vec::new(),
            sessions_backend: None,
            search_backend: None,
            docs_backend: None,
            spec_backend: None,
            finish_backend: None,
            autopilot_backend: None,
            spec_state: handlers_spec::SpecServerState::default(),
            project_root: std::env::current_dir().unwrap_or_default(),
        }
    }

    /// Wirea el backend in-process de sesiones (P12A-9).
    pub fn with_sessions_backend(
        mut self,
        backend: std::sync::Arc<std::sync::Mutex<dyn SessionsBackend + Send>>,
    ) -> Self {
        self.sessions_backend = Some(backend);
        self
    }

    /// Wirea el backend in-process de la familia search/context (Cierre T1).
    pub fn with_search_backend(
        mut self,
        backend: std::sync::Arc<std::sync::Mutex<dyn handlers_search::SearchBackend + Send>>,
    ) -> Self {
        self.search_backend = Some(backend);
        self
    }

    /// Wirea el backend in-process de docs/HU (Cierre T1).
    pub fn with_docs_backend(
        mut self,
        backend: std::sync::Arc<std::sync::Mutex<dyn handlers_docs::DocsBackend + Send>>,
    ) -> Self {
        self.docs_backend = Some(backend);
        self
    }

    /// Wirea el backend in-process de spec/proposal (Cierre T1).
    pub fn with_spec_backend(
        mut self,
        backend: std::sync::Arc<std::sync::Mutex<dyn handlers_spec::SpecBackend + Send>>,
    ) -> Self {
        self.spec_backend = Some(backend);
        self
    }

    /// Wirea el backend in-process de finish/briefing (Cierre T1).
    pub fn with_finish_backend(
        mut self,
        backend: std::sync::Arc<std::sync::Mutex<dyn handlers_finish::FinishBackend + Send>>,
    ) -> Self {
        self.finish_backend = Some(backend);
        self
    }

    /// Wirea el backend in-process de la familia autopilot (Cierre T3).
    pub fn with_autopilot_backend(
        mut self,
        backend: std::sync::Arc<
            std::sync::Mutex<dyn crate::handlers_autopilot::AutopilotBackend + Send>,
        >,
    ) -> Self {
        self.autopilot_backend = Some(backend);
        self
    }

    /// Inyecta el reloj (segundos desde epoch) para tests deterministas.
    pub fn set_now_epoch(&mut self, f: impl Fn() -> f64 + Send + Sync + 'static) {
        self.now_epoch = Box::new(f);
    }

    pub fn server_version(&self) -> &'static str {
        SERVER_VERSION
    }

    /// Uptime en segundos desde el arranque del server.
    pub fn uptime_seconds(&self) -> f64 {
        self.startup_time.elapsed().as_secs_f64()
    }

    /// `_register_error`: agrega al rolling buffer respetando maxlen=10.
    pub fn register_error(&mut self, tool: &str, error: &str) {
        self.register_error_at(ErrorEntry::now(tool, error));
    }

    /// Variante con entrada pre-construida (tests inyectan timestamp).
    pub fn register_error_at(&mut self, entry: ErrorEntry) {
        if self.error_history.len() == ERROR_HISTORY_MAXLEN {
            self.error_history.pop_front();
        }
        self.error_history.push_back(entry);
    }

    /// `_ping_text`: payload JSON del health check (sin IO). Estructura y
    /// orden de claves espejo exacto; serialización idéntica a
    /// `json.dumps(payload, indent=2, ensure_ascii=False)` (serde_json
    /// pretty usa el mismo indent/separadores/UTF-8 literal).
    pub fn ping_text(&self) -> String {
        let now_epoch = (self.now_epoch)();
        let uptime = self.uptime_seconds();

        // Errorecientes dentro de la ventana; los viejos quedan como audit
        // trail pero no latchingean `degraded` (incident 2026-05-15).
        let mut recent: Vec<&ErrorEntry> = Vec::new();
        for entry in &self.error_history {
            if let Some(age) = age_seconds(&entry.timestamp, now_epoch) {
                if age <= ERROR_RECENT_WINDOW_SECONDS {
                    recent.push(entry);
                }
            }
        }

        let status = if uptime < STARTUP_GRACE_SECONDS {
            "starting"
        } else if !recent.is_empty() {
            "degraded"
        } else {
            "ok"
        };

        // indices_loaded: proxy = self.memory existe y no es None.
        let indices_loaded = self.memory.is_some();

        // last_error = recent_errors[-1] si hay.
        let last_error = recent.last().map(|e| {
            serde_json::json!({
                "tool": e.tool,
                "error": e.error,
                "timestamp": e.timestamp,
            })
        });

        let payload = serde_json::json!({
            "status": status,
            "version": SERVER_VERSION,
            "uptime_seconds": round3(uptime),
            "indices_loaded": indices_loaded,
            "models_loaded": self.models_loaded.clone(),
            "last_error_seen": last_error,
            "recent_errors_count": recent.len(),
            "error_window_seconds": ERROR_RECENT_WINDOW_SECONDS,
        });
        serde_json::to_string_pretty(&payload).expect("ping serializable")
    }

    /// `_dispatch_tool_sync`: dispatcher de tabla. `Ok(texto)` va al cliente
    /// como TextContent; los fallos duros suben como `Err` y el caller los
    /// formatea con marca de error (espejo de `handle_call_tool`).
    pub fn dispatch_tool_sync(
        &mut self,
        name: &str,
        _arguments: &serde_json::Value,
    ) -> Result<String, String> {
        // Espejo de `_log_tool_call`: TODA llamada se registra en
        // `_called_tools` ANTES de routear (el guard de gobernanza lo
        // consume; ping incluido, como handle_call_tool en Python).
        self.spec_state.called_tools.insert(name.to_string());

        // Ruta especial histórica: inline contra memory.sync_vault().
        if name == "cortex_sync_vault" {
            let count = match self.memory.as_mut() {
                Some(mem) => mem.sync_vault()?,
                None => return Err("no memory backend configured".into()),
            };
            return Ok(format!("Vault synced - {count} documents indexed."));
        }

        match tool_routes().get(name) {
            None => {
                // Mensaje estable congelado por el golden contract test.
                Ok(format!("Herramienta desconocida: {name}"))
            }
            Some(route) => {
                if name == "cortex_ping" {
                    return Ok(self.ping_text());
                }
                // Espejo de `_log_tool_call`: la tool ya quedó registrada
                // al inicio del dispatcher.
                let arguments = _arguments;

                // Familia sesiones (P12A-9): in-process cuando hay backend.
                const SESSION_TOOLS: &[&str] = &[
                    "cortex_session_open",
                    "cortex_session_checkpoint",
                    "cortex_session_close",
                    "cortex_session_status",
                    "cortex_session_list",
                    "cortex_session_task_list",
                    "cortex_session_task_update",
                    "cortex_review_checkpoint",
                    "cortex_close_session",
                    "cortex_save_session",
                    "cortex_validate_handoff",
                    "cortex_verify_session_claims",
                ];
                if SESSION_TOOLS.contains(&name) {
                    if let Some(b) = &self.sessions_backend {
                        let mut guard = b.lock().map_err(|_| "poisoned state".to_string())?;
                        let project_root = std::env::current_dir().unwrap_or_default();
                        return dispatch_session_tool(name, arguments, &mut *guard, &project_root);
                    }
                }

                // Familia search/context/sync_ticket (Cierre T1).
                const SEARCH_TOOLS: &[&str] = &[
                    "cortex_search",
                    "cortex_search_vector",
                    "cortex_context",
                    "cortex_sync_ticket",
                ];
                if SEARCH_TOOLS.contains(&name) {
                    if let Some(b) = &self.search_backend {
                        let mut guard = b.lock().map_err(|_| "poisoned state".to_string())?;
                        return match name {
                            "cortex_search" => {
                                handlers_search::search_text_dispatch(&mut *guard, arguments)
                            }
                            "cortex_search_vector" => {
                                handlers_search::search_vector_text(&mut *guard, arguments)
                            }
                            "cortex_context" => {
                                handlers_search::context_text(&mut *guard, arguments)
                            }
                            _ => handlers_search::build_sync_ticket_context(
                                &mut *guard,
                                arguments,
                                &self.project_root,
                            ),
                        };
                    }
                }

                // Familia docs/HU (Cierre T1).
                const DOCS_TOOLS: &[&str] = &[
                    "write_design_note_canonical",
                    "cortex_write_doc",
                    "cortex_import_hu",
                    "cortex_get_hu",
                ];
                if DOCS_TOOLS.contains(&name) {
                    if let Some(b) = &self.docs_backend {
                        let mut guard = b.lock().map_err(|_| "poisoned state".to_string())?;
                        return match name {
                            "write_design_note_canonical" => {
                                handlers_docs::write_design_note_text(&mut *guard, arguments)
                            }
                            "cortex_write_doc" => {
                                handlers_docs::write_doc_text(&mut *guard, arguments)
                            }
                            "cortex_import_hu" => {
                                handlers_docs::import_hu_text(&mut *guard, arguments)
                            }
                            _ => handlers_docs::get_hu_text(&mut *guard, arguments),
                        };
                    }
                }

                // Familia spec/proposal (Cierre T1).
                if name == "cortex_create_spec" || name == "cortex_emit_proposal" {
                    let now_epoch = (self.now_epoch)();
                    if name == "cortex_emit_proposal" {
                        return handlers_spec::emit_proposal_text(
                            &mut self.spec_state,
                            arguments,
                            now_epoch,
                        );
                    }
                    if let Some(b) = &self.spec_backend {
                        let mut guard = b.lock().map_err(|_| "poisoned state".to_string())?;
                        return handlers_spec::create_spec_text(
                            &mut self.spec_state,
                            &mut *guard,
                            arguments,
                            now_epoch,
                        );
                    }
                }
                if name == "cortex_self_review_note" {
                    return handlers_spec::self_review_note_text(arguments);
                }

                // Familia finish/briefing (Cierre T1).
                const FINISH_TOOLS: &[&str] =
                    &["cortex_finish_session", "cortex_documenter_briefing"];
                if FINISH_TOOLS.contains(&name) {
                    if let Some(b) = &self.finish_backend {
                        let mut guard = b.lock().map_err(|_| "poisoned state".to_string())?;
                        return match name {
                            "cortex_finish_session" => {
                                handlers_finish::finish_session_text(&mut *guard, arguments)
                            }
                            _ => handlers_finish::documenter_briefing_text(&mut *guard, arguments),
                        };
                    }
                }

                // Familia autopilot (Cierre T3).
                const AUTOPILOT_TOOLS: &[&str] = &[
                    "cortex_autopilot_start",
                    "cortex_autopilot_preflight",
                    "cortex_autopilot_checkpoint",
                    "cortex_autopilot_finish",
                    "cortex_autopilot_status",
                ];
                if AUTOPILOT_TOOLS.contains(&name) {
                    if let Some(b) = &self.autopilot_backend {
                        let mut guard = b.lock().map_err(|_| "poisoned state".to_string())?;
                        use crate::handlers_autopilot as ha;
                        return match name {
                            "cortex_autopilot_start" => {
                                ha::autopilot_start_text(&mut *guard, arguments)
                            }
                            "cortex_autopilot_preflight" => {
                                ha::autopilot_preflight_text(&mut *guard, arguments)
                            }
                            "cortex_autopilot_checkpoint" => {
                                ha::autopilot_checkpoint_text(&mut *guard, arguments)
                            }
                            "cortex_autopilot_finish" => {
                                ha::autopilot_finish_text(&mut *guard, arguments)
                            }
                            _ => ha::autopilot_status_text(&mut *guard, arguments),
                        };
                    }
                }

                // Fallo explícito documentado (patrón P6): el backend del
                // handler aún no es nativo. NO se finge paridad conductual.
                Err(format!(
                    "Tool '{name}' ruteada ({route}) pero su backend aún no es \
                     nativo (backlog P11/P12 de Obra 07)."
                ))
            }
        }
    }

    /// Catálogo `list_tools` completo (congelado byte-a-byte vs golden).
    pub fn list_tools(&self) -> Vec<serde_json::Value> {
        build_tool_definitions()
    }
}

/// Ruta in-process de la familia sesiones (P12A-9).
fn dispatch_session_tool(
    name: &str,
    args: &serde_json::Value,
    b: &mut dyn SessionsBackend,
    project_root: &std::path::Path,
) -> Result<String, String> {
    use sessions_handlers as h;
    match name {
        "cortex_session_open" => h::session_open_text(b, args),
        "cortex_session_checkpoint" => h::session_checkpoint_text(b, args),
        "cortex_session_close" => h::session_close_text(b, args),
        "cortex_session_status" => h::session_status_text(b, args),
        "cortex_session_list" => h::session_list_text(b, args),
        "cortex_session_task_list" => h::session_task_list_text(b, args),
        "cortex_session_task_update" => h::session_task_update_text(b, args),
        "cortex_review_checkpoint" => h::review_checkpoint_text(b, args, Some(project_root)),
        "cortex_close_session" => h::close_session_text(b, args),
        "cortex_save_session" => h::save_session_text(b, args),
        "cortex_validate_handoff" => h::validate_handoff_text(args),
        "cortex_verify_session_claims" => h::verify_session_claims_text(args, project_root),
        _ => Err(format!("Herramienta desconocida: {name}")),
    }
}

// ---------------------------------------------------------------------------
// Helpers numéricos / temporales
// ---------------------------------------------------------------------------

/// round(x, 3): redondeo comercial a 3 decimales (duraciones positivas).
fn round3(x: f64) -> f64 {
    (x * 1000.0).round() / 1000.0
}

/// Edad en segundos entre ISO `YYYY-MM-DDTHH:MM:SS[.ffffff]` y now_epoch.
fn age_seconds(iso: &str, now_epoch: f64) -> Option<f64> {
    let (date, time) = iso.split_once('T')?;
    let mut it = date.split('-');
    let y: i64 = it.next()?.parse().ok()?;
    let mo: u32 = it.next()?.parse().ok()?;
    let d: u32 = it.next()?.parse().ok()?;
    let mut it = time.split(':');
    let h: i64 = it.next()?.parse().ok()?;
    let mi: i64 = it.next()?.parse().ok()?;
    let sec_part = it.next().unwrap_or("0");
    let (s, frac) = match sec_part.split_once('.') {
        Some((s, f)) => (
            s.parse::<i64>().ok()?,
            format!("0.{f}").parse::<f64>().unwrap_or(0.0),
        ),
        None => (sec_part.parse::<i64>().ok()?, 0.0),
    };
    let ts = days_from_civil(y, mo, d) * 86_400 + h * 3600 + mi * 60 + s;
    Some(now_epoch - (ts as f64 + frac))
}

/// days_from_civil (Howard Hinnant): epoch day desde fecha civil.
fn days_from_civil(y: i64, m: u32, d: u32) -> i64 {
    let y = if m <= 2 { y - 1 } else { y };
    let era = if y >= 0 { y } else { y - 399 } / 400;
    let yoe = y - era * 400;
    let mp = (i64::from(m) + 9) % 12;
    let doy = (153 * mp + 2) / 5 + i64::from(d) - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146_097 + doe - 719_468
}

/// Timestamp ISO local estilo `datetime.now().isoformat()` (microsegundos).
fn format_iso_now() -> String {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let secs = now.as_secs();
    let micros = now.subsec_micros();
    let days = (secs / 86_400) as i64;
    let rem = secs % 86_400;
    let (y, mo, d) = civil_from_days(days);
    format!(
        "{y:04}-{mo:02}-{d:02}T{:02}:{:02}:{:02}.{micros:06}",
        rem / 3600,
        (rem % 3600) / 60,
        rem % 60
    )
}

/// civil_from_days (Howard Hinnant): inverso del anterior.
fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    (if m <= 2 { y + 1 } else { y }, m, d)
}

// ---------------------------------------------------------------------------
// Transporte rmcp (stdio)
// ---------------------------------------------------------------------------

mod transport {
    use super::*;
    use rmcp::model::{
        CallToolRequestParam, CallToolResult, Content, Implementation, ListToolsResult,
        PaginatedRequestParam, ProtocolVersion, ServerCapabilities, ServerInfo,
    };
    use rmcp::{ErrorData as McpError, RoleServer, ServerHandler, ServiceExt};

    /// Adaptador `ServerHandler` sobre [`CortexMcpServer`] (mutex interno:
    /// los handlers de rmcp toman &self).
    pub struct CortexMcpService {
        inner: Arc<Mutex<CortexMcpServer>>,
    }

    impl CortexMcpService {
        pub fn new(server: CortexMcpServer) -> Self {
            CortexMcpService {
                inner: Arc::new(Mutex::new(server)),
            }
        }
    }

    impl ServerHandler for CortexMcpService {
        fn get_info(&self) -> ServerInfo {
            ServerInfo {
                protocol_version: ProtocolVersion::LATEST,
                capabilities: ServerCapabilities::builder().enable_tools().build(),
                server_info: Implementation::from_build_env(),
                instructions: Some(
                    "Cortex MCP nativo (Obra 07 P9). Contrato list_tools \
                     congelado contra golden Python."
                        .into(),
                ),
            }
        }

        async fn list_tools(
            &self,
            _request: Option<PaginatedRequestParam>,
            _context: rmcp::service::RequestContext<RoleServer>,
        ) -> Result<ListToolsResult, McpError> {
            let tools: Vec<_> = build_tool_definitions()
                .into_iter()
                .filter_map(|v| serde_json::from_value(v).ok())
                .collect();
            Ok(ListToolsResult {
                next_cursor: None,
                tools,
            })
        }

        async fn call_tool(
            &self,
            request: CallToolRequestParam,
            _context: rmcp::service::RequestContext<RoleServer>,
        ) -> Result<CallToolResult, McpError> {
            let args = request
                .arguments
                .map(value_or_object)
                .unwrap_or_else(|| serde_json::json!({}));
            let result = {
                let mut guard = self
                    .inner
                    .lock()
                    .map_err(|_| McpError::internal_error("poisoned state", None))?;
                guard.dispatch_tool_sync(request.name.as_ref(), &args)
            };
            // Espejo de handle_call_tool: los errores del handler NO son
            // errores de protocolo; vuelven como texto con marca de error.
            let text = match result {
                Ok(t) => t,
                Err(e) => format!("Error ejecutando {}: {e}", request.name),
            };
            Ok(CallToolResult::success(vec![Content::text(text)]))
        }
    }

    /// Los arguments de rmcp llegan como Map<String, Value>; el dispatcher
    /// consume un Value objeto (espejo del dict de Python).
    fn value_or_object(m: serde_json::Map<String, serde_json::Value>) -> serde_json::Value {
        serde_json::Value::Object(m)
    }

    /// Sirve por stdio (bloquea hasta EOF del cliente).
    pub fn serve_stdio_blocking(server: CortexMcpServer) -> Result<(), String> {
        tokio::runtime::Runtime::new()
            .map_err(|e| format!("tokio runtime: {e}"))?
            .block_on(async move {
                let service = CortexMcpService::new(server)
                    .serve(rmcp::transport::stdio())
                    .await
                    .map_err(|e| format!("serve: {e}"))?;
                service
                    .waiting()
                    .await
                    .map_err(|e| format!("waiting: {e}"))?;
                Ok(())
            })
    }
}

pub use transport::serve_stdio_blocking;
