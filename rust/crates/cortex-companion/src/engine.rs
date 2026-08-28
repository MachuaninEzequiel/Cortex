//! Backend in-proceso del Companion (G-B1).
//!
//! Paridad-como-contrato POR CONSTRUCCIÓN: el engine inyecta los mismos
//! servicios que usa el CLI nativo (`cortex_cli::memory::NativeMemory`,
//! `SessionService`, `cortex-actions`) y serializa con el MISMO `pyjson`,
//! así las salidas `--json` son byte-idénticas (verificado en
//! `tests/parity_cli.rs`).
//!
//! Los métodos mutantes (close_session / checkpoint_session /
//! approve_action) llegan con la capa de aprobación (B2: `run_guarded`);
//! en esta etapa devuelven error explícito (patrón P6/P9, nunca paridad
//! fingida).

use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::Instant;

use cortex_actions::catalog::build_default_registry;
use cortex_actions::context::ActionContext;
use cortex_actions::scheduler::Scheduler;
use cortex_actions::store::PreferencesStore;
use cortex_app::session::service::SessionService;
use cortex_app::session::{SessionRecord, SessionStorage};
use cortex_cli::commands::session_cmd::{mode_str, record_summary_pv};
use cortex_cli::memory::NativeMemory;
use cortex_cli::memory_cmds::retrieval_json;
use cortex_cli::paths::resolve_project_root;
use cortex_cli::pyjson::{Num, PyVal};
use cortex_workspace::WorkspaceLayout;

/// Sesión resumida para las pantallas.
#[derive(Debug, Clone)]
pub struct SessionSummary {
    pub id: String,
    pub status: String,
    pub mode: String,
    pub opened_at: String,
}

/// Propuesta del Action Engine para la pantalla Actions.
#[derive(Debug, Clone)]
pub struct ActionProposal {
    pub id: String,
    pub title: String,
    pub score: f64,
    pub cost: String,
    pub reversible: bool,
    pub effect: String,
}

/// Hit unificado (RRF) para la pantalla Search.
#[derive(Debug, Clone)]
pub struct SearchHit {
    pub source: String,
    pub title: String,
    pub path: String,
    pub score: f64,
    pub snippet: String,
}

/// Doctor-lite para Home (v1; se enriquece en B4).
#[derive(Debug, Clone)]
pub struct DoctorSummary {
    pub ok: bool,
    pub checks: Vec<(String, String)>, // (name, ok|warn|fail)
}

/// Conteos de memoria para Home.
#[derive(Debug, Clone)]
pub struct StatsSummary {
    pub episodic: usize,
    pub semantic: usize,
    pub vault_path: String,
}

/// Contrato del engine: lecturas directas; mutaciones SIEMPRE detrás de la
/// aprobación (B2), que vive en la capa de UI, NO en el backend.
pub trait Backend: Send + Sync {
    fn session_current(&self) -> Result<Option<SessionSummary>, String>;
    fn session_list(&self) -> Result<Vec<SessionSummary>, String>;
    fn next_actions(&self) -> Result<Vec<ActionProposal>, String>;
    fn search(&self, query: &str, top_k: usize) -> Result<Vec<SearchHit>, String>;
    fn doctor(&self) -> Result<DoctorSummary, String>;
    fn stats(&self) -> Result<StatsSummary, String>;

    // ---- mutaciones (siempre detrás de approval) ----
    fn close_session(&self, session_id: &str) -> Result<(), String>;
    fn checkpoint_session(&self, note: &str) -> Result<(), String>;
    fn approve_action(&self, action_id: &str) -> Result<(), String>;
}

/// Propuesta enriquecida (interna): todo lo que expone `cortex next --json`.
struct Proposed {
    id: String,
    title: String,
    category: String,
    effect: String,
    cost: String,
    reversible: bool,
    auto_ok: bool,
    score: f64,
}

/// Implementación nativa sobre los servicios del CLI.
pub struct InProcessBackend {
    pub root: PathBuf,
    pub layout: WorkspaceLayout,
    pub session: SessionService,
    /// Memoria nativa (NativeMemory). Se abre SIN embeddings en idle
    /// (patrón lazy de CliSearchAdapter); búsqueda la abre con embeddings.
    /// `Mutex` porque `NativeMemory::retrieve` es `&mut` y el trait pide
    /// `&self` (Send + Sync para el runtime TUI en B3+).
    memory: Mutex<Option<NativeMemory>>,
}

fn summary_of(r: &SessionRecord) -> SessionSummary {
    SessionSummary {
        id: r.session_id.clone(),
        status: r.status.as_str().to_string(),
        mode: mode_str(r.mode).to_string(),
        opened_at: r.opened_at.clone(),
    }
}

impl InProcessBackend {
    /// Abre los servicios con la misma resolución de rutas que el CLI
    /// (`cortex_cli::paths::resolve_project_root`).
    pub fn open(project_root: &Path) -> Result<Self, String> {
        let root = resolve_project_root(Some(&project_root.to_string_lossy()));
        let layout = WorkspaceLayout::discover(&root);
        let storage = SessionStorage::new(layout.sessions_dir());
        let session = SessionService::new(storage, &layout.repo_root);
        Ok(Self {
            root,
            layout,
            session,
            memory: Mutex::new(None),
        })
    }

    /// Memoria nativa lazy: con embeddings para búsqueda, sin embeddings
    /// para conteos (stats).
    fn memory(
        &self,
        want_embeddings: bool,
    ) -> Result<std::sync::MutexGuard<'_, Option<NativeMemory>>, String> {
        let mut guard = self
            .memory
            .lock()
            .map_err(|_| "memory lock poisoned".to_string())?;
        if guard.is_none() {
            let mem = if want_embeddings {
                NativeMemory::open(Some(&self.root))
            } else {
                NativeMemory::open_without_embeddings(Some(&self.root))
            }
            .map_err(|e| e.message())?;
            *guard = Some(mem);
        }
        Ok(guard)
    }

    /// Candidatos del Action Engine (misma construcción que `cortex next`).
    fn propose(&self) -> Result<Vec<Proposed>, String> {
        let ctx = ActionContext::from_project_root(Some(&self.root));
        if !ctx.config_existe() {
            return Err(format!(
                "Cortex no está configurado en {} (no encuentro config.yaml) — corré \
                 `cortex setup agent` primero.",
                ctx.workspace_root.display()
            ));
        }
        let registry = build_default_registry(&ctx);
        let prefs = PreferencesStore::new(&ctx.dot_cortex());
        let scheduler = Scheduler::new(&prefs);
        let propuestas = scheduler.propose(&registry, false);
        Ok(propuestas
            .iter()
            .filter_map(|p| {
                let a = registry.get(&p.action_id)?;
                Some(Proposed {
                    id: a.id.clone(),
                    title: a.title.clone(),
                    category: a.category.as_str().to_string(),
                    effect: a.effect.clone(),
                    cost: a.cost.as_str().to_string(),
                    reversible: a.reversible,
                    auto_ok: a.auto_ok,
                    score: p.score,
                })
            })
            .collect())
    }

    /// `cortex session list --json` byte-idéntico (paneles y tests).
    pub fn session_list_json(&self) -> Result<String, String> {
        let mut records = self.session.list(None)?;
        records.sort_by(|a, b| b.opened_at.cmp(&a.opened_at));
        let items: Vec<PyVal> = records.iter().map(record_summary_pv).collect();
        Ok(cortex_cli::pyjson::stdlib_dumps_compact_array(&items))
    }

    /// `cortex search Q --json` byte-idéntico (mismo retrieval + pyjson).
    pub fn search_json(&self, query: &str, top_k: usize) -> Result<String, String> {
        let mut guard = self.memory(true)?;
        let mem = guard.as_mut().expect("memory just opened");
        let result = mem.retrieve(query, top_k, true);
        Ok(retrieval_json(&result))
    }

    /// `cortex next --json` byte-idéntico salvo `elapsed_ms` (variable real;
    /// los gates lo normalizan como {{ELAPSED}}).
    pub fn next_actions_json(&self) -> Result<String, String> {
        let t0 = Instant::now();
        let props = self.propose()?;
        let elapsed_ms = t0.elapsed().as_millis() as i64;
        let mut payload: Vec<(String, PyVal)> =
            vec![("elapsed_ms".into(), PyVal::Num(Num::Int(elapsed_ms)))];
        let acciones: Vec<PyVal> = props
            .iter()
            .map(|p| {
                PyVal::obj(vec![
                    ("id", PyVal::s(p.id.clone())),
                    ("title", PyVal::s(p.title.clone())),
                    ("category", PyVal::s(p.category.clone())),
                    ("effect", PyVal::s(p.effect.clone())),
                    ("cost", PyVal::s(p.cost.clone())),
                    ("reversible", PyVal::Bool(p.reversible)),
                    ("auto_ok", PyVal::Bool(p.auto_ok)),
                    ("score", PyVal::Num(Num::Float(p.score))),
                ])
            })
            .collect();
        payload.push(("acciones".into(), PyVal::Arr(acciones)));
        Ok(cortex_cli::pyjson::pydantic_dumps_indent2(&PyVal::Obj(
            payload,
        )))
    }
}

impl Backend for InProcessBackend {
    fn session_current(&self) -> Result<Option<SessionSummary>, String> {
        Ok(self.session.get_active().map(|r| summary_of(&r)))
    }

    fn session_list(&self) -> Result<Vec<SessionSummary>, String> {
        let mut records = self.session.list(None)?;
        records.sort_by(|a, b| b.opened_at.cmp(&a.opened_at));
        Ok(records.iter().map(summary_of).collect())
    }

    fn next_actions(&self) -> Result<Vec<ActionProposal>, String> {
        Ok(self
            .propose()?
            .into_iter()
            .map(|p| ActionProposal {
                id: p.id,
                title: p.title,
                score: p.score,
                cost: p.cost,
                reversible: p.reversible,
                effect: p.effect,
            })
            .collect())
    }

    fn search(&self, query: &str, top_k: usize) -> Result<Vec<SearchHit>, String> {
        let mut guard = self.memory(true)?;
        let mem = guard.as_mut().expect("memory just opened");
        let result = mem.retrieve(query, top_k, true);
        Ok(result
            .unified_hits
            .iter()
            .map(|h| {
                let (title, path, snippet) = if h.source == "episodic" {
                    let e = h.entry.as_ref().expect("episodic hit");
                    (
                        cortex_cli::memory_cmds::display_title_episodic(e),
                        cortex_cli::memory_cmds::display_path_episodic(e),
                        e.content.clone(),
                    )
                } else {
                    let d = h.doc.expect("semantic hit");
                    (d.title.clone(), d.path.clone(), d.content.clone())
                };
                SearchHit {
                    source: h.source.to_string(),
                    title,
                    path,
                    score: h.score,
                    snippet,
                }
            })
            .collect())
    }

    fn doctor(&self) -> Result<DoctorSummary, String> {
        let checks: Vec<(String, String)> = vec![
            (
                "config_yaml".to_string(),
                if self.layout.config_path().exists() {
                    "ok"
                } else {
                    "fail"
                }
                .to_string(),
            ),
            (
                "sessions_dir".to_string(),
                if self.layout.sessions_dir().exists() {
                    "ok"
                } else {
                    "warn"
                }
                .to_string(),
            ),
        ];
        let ok = checks.iter().all(|(_, s)| s != "fail");
        Ok(DoctorSummary { ok, checks })
    }

    fn stats(&self) -> Result<StatsSummary, String> {
        let guard = self.memory(false)?;
        let mem = guard.as_ref().expect("memory just opened");
        Ok(StatsSummary {
            episodic: mem.episodic_count(),
            semantic: mem.semantic.docs.len(),
            vault_path: mem.vault_path_string(),
        })
    }

    // ---- mutaciones: llegan en B2 (run_guarded + aprobación) ----

    fn close_session(&self, _session_id: &str) -> Result<(), String> {
        Err("pendiente: close_session se implementa en B2/B3 detrás de la aprobación".to_string())
    }

    fn checkpoint_session(&self, _note: &str) -> Result<(), String> {
        Err(
            "pendiente: checkpoint_session se implementa en B2/B3 detrás de la aprobación"
                .to_string(),
        )
    }

    fn approve_action(&self, _action_id: &str) -> Result<(), String> {
        Err("pendiente: approve_action se implementa en B2/B3 detrás de la aprobación".to_string())
    }
}
