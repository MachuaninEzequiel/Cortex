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
use std::sync::{Arc, Mutex};
use std::time::Instant;

use cortex_actions::catalog::build_default_registry;
use cortex_actions::context::ActionContext;
use cortex_actions::models::Action;
use cortex_actions::runner::Runner;
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
    /// Último checkpoint con phase, recorriendo `checkpoints` al revés.
    /// None = sesión sin fase COMPOSED (BYO/Observed/legado).
    pub phase: Option<String>,
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
    /// `id` de la memoria episódica (feedback [Útil], B7); `None` en hits
    /// semánticos — espejo de `core.py:274` (`getattr(hit.entry, "id", None)`
    /// ⇒ sin id no hay qué puntuar).
    pub id: Option<String>,
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
    /// Líneas del detalle de una sesión (checkpoints y tasks) para el panel
    /// Sessions (B6).
    fn session_detail(&self, session_id: &str) -> Result<Vec<String>, String>;

    // ---- mutaciones (siempre detrás de approval) ----
    fn close_session(&self, session_id: &str) -> Result<(), String>;
    fn checkpoint_session(&self, note: &str) -> Result<(), String>;
    fn approve_action(&self, action_id: &str) -> Result<(), String>;

    /// Feedback explícito "marcar útil" (B7). NO pasa por approval: es la
    /// marca de aprendizaje del motor (dato del usuario sobre el propio
    /// índice), con la misma semántica que la tecla `y` de la TUI y el
    /// `Nº para marcar útil` de `cortex/tui/core.py`. Default honesto
    /// P6/P9: backends sin store de feedback fallan explícito.
    fn mark_useful(&self, _memory_id: &str) -> Result<crate::feedback::AppendOutcome, String> {
        Err("feedback no disponible en este backend".to_string())
    }

    // ---- ejecución del Menu (B5) ----
    /// Ejecuta una familia+args del catálogo. Default honesto P6/P9: cada
    /// backend integra las suyas y el resto falla explícito con el comando
    /// exacto a correr en terminal (nunca paridad fingida, nunca subprocess).
    fn menu_run(&self, family: &str, args: &[String]) -> Result<String, String> {
        let mut cmd = String::from("cortex ");
        cmd.push_str(family);
        for a in args {
            cmd.push(' ');
            cmd.push_str(a);
        }
        Err(format!(
            "«{family}» no integrada al Companion en esta versión — corré `{cmd}` en tu terminal"
        ))
    }
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

/// Memoria nativa lazy con **un slot por modo** (G-B1 fix round 1 + B7).
///
/// Desde B7, `NativeMemory::open_without_embeddings` NO abre el ort Session
/// (embedder `None`): los comandos sin retrieve (`stats`, `forget`) no pagan
/// ~90 MB de RSS ni ~150 ms de carga. El slot con embeddings abre el modelo y
/// adjunta vectores al vault (búsqueda real). Se mantienen DOS slots: un
/// singleton único quedaría mode-locked por el primer accesor (stats→search
/// rompía la paridad en silencio — fix round 1 de G-B1).
#[derive(Default)]
struct MemorySlots {
    without_embeddings: Option<NativeMemory>,
    with_embeddings: Option<NativeMemory>,
}

/// Implementación nativa sobre los servicios del CLI.
pub struct InProcessBackend {
    pub root: PathBuf,
    pub layout: WorkspaceLayout,
    pub session: SessionService,
    /// Memoria nativa lazy por modo (`MemorySlots`). `Mutex` porque
    /// `NativeMemory::retrieve` es `&mut` y el trait pide `&self`
    /// (Send + Sync para el runtime TUI en B3+).
    memory: Mutex<MemorySlots>,
}

fn summary_of(r: &SessionRecord) -> SessionSummary {
    let phase = r
        .checkpoints
        .iter()
        .rev()
        .find_map(|c| c.phase)
        .map(|p| p.as_str().to_string());
    SessionSummary {
        id: r.session_id.clone(),
        status: r.status.as_str().to_string(),
        mode: mode_str(r.mode).to_string(),
        opened_at: r.opened_at.clone(),
        phase,
    }
}

/// Vista de transporte `Arc<Action>` para ejecutar una acción del registry
/// con el `Runner` (mismo patrón que el WIP de cortex-tui con `arc_for_run`:
/// closures compartidos por `Arc`, precondiciones omitidas porque el
/// scheduler ya las evaluó al proponer). Local al Companion para no tocar
/// cortex-actions.
fn action_for_run(a: &Action) -> Arc<Action> {
    Arc::new(Action {
        id: a.id.clone(),
        title: a.title.clone(),
        category: a.category,
        effect: a.effect.clone(),
        preconditions: Vec::new(),
        reversible: a.reversible,
        undo: a.undo.clone(),
        cost: a.cost,
        auto_ok: a.auto_ok,
        run: a.run.clone(),
    })
}

/// Recorta a `max` chars con elipsis (líneas del detalle).
fn trunc(s: &str, max: usize) -> String {
    let n = s.chars().count();
    if n <= max {
        s.to_string()
    } else {
        let cut: String = s.chars().take(max.saturating_sub(1)).collect();
        format!("{cut}…")
    }
}

/// `source`/`status` serializados con el MISMO serde que el storage de
/// sesiones (serde renames canónicos: "cortex-sync", "in-progress"…).
fn serde_label<T: serde::Serialize>(v: &T) -> String {
    serde_json::to_value(v)
        .ok()
        .and_then(|j| j.as_str().map(str::to_string))
        .unwrap_or_else(|| "?".to_string())
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
            memory: Mutex::new(MemorySlots::default()),
        })
    }

    /// Rama actual del repo (lectura pura de fs, SIN subprocess — la
    /// filosofía in-process del Companion). Soporta `.git` directorio y
    /// `.git` archivo (worktree). Detached ⇒ `None`.
    pub fn current_branch(&self) -> Result<Option<String>, String> {
        let git_dir = self.layout.repo_root.join(".git");
        let head_path = if git_dir.is_dir() {
            git_dir.join("HEAD")
        } else if git_dir.is_file() {
            let content = std::fs::read_to_string(&git_dir).map_err(|e| e.to_string())?;
            let target = content.trim().trim_start_matches("gitdir:").trim();
            PathBuf::from(target).join("HEAD")
        } else {
            return Ok(None);
        };
        let head = std::fs::read_to_string(head_path).map_err(|e| e.to_string())?;
        match head.trim().strip_prefix("ref: refs/heads/") {
            Some(branch) => Ok(Some(branch.to_string())),
            None => Ok(None), // detached
        }
    }

    /// Directorio del `action_log.jsonl` (`.cortex/`), misma regla que el
    /// runner de `cortex-actions` — para el `ActionLog` de aprobaciones (B2).
    pub fn action_log_dir(&self) -> std::path::PathBuf {
        use cortex_actions::context::ActionContext;
        ActionContext::from_project_root(Some(&self.root)).dot_cortex()
    }

    /// Memoria nativa lazy, slot por modo: con embeddings para búsqueda,
    /// sin embeddings para conteos (stats). Un modo jamás contamina al otro.
    fn memory(
        &self,
        want_embeddings: bool,
    ) -> Result<std::sync::MutexGuard<'_, MemorySlots>, String> {
        let mut guard = self
            .memory
            .lock()
            .map_err(|_| "memory lock poisoned".to_string())?;
        let slot = if want_embeddings {
            &mut guard.with_embeddings
        } else {
            &mut guard.without_embeddings
        };
        if slot.is_none() {
            let mem = if want_embeddings {
                NativeMemory::open(Some(&self.root))
            } else {
                NativeMemory::open_without_embeddings(Some(&self.root))
            }
            .map_err(|e| e.message())?;
            *slot = Some(mem);
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
        let mem = guard
            .with_embeddings
            .as_mut()
            .expect("with_embeddings just opened");
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
        let mem = guard
            .with_embeddings
            .as_mut()
            .expect("with_embeddings just opened");
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
                    // feedback [Útil] (B7): id episódico; semánticos None.
                    id: h.entry.as_ref().map(|e| e.id.clone()),
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
        let mem = guard
            .without_embeddings
            .as_ref()
            .expect("without_embeddings just opened");
        Ok(StatsSummary {
            episodic: mem.episodic_count(),
            semantic: mem.semantic.docs.len(),
            vault_path: mem.vault_path_string(),
        })
    }

    /// Detalle de una sesión: estado/modo + checkpoints (fuente, nota, claims)
    /// y tasks (id, estado, descripción) — líneas listas para el panel.
    fn session_detail(&self, session_id: &str) -> Result<Vec<String>, String> {
        let r = self.session.get(session_id)?;
        let mut lines = vec![format!(
            "status: {} · modo: {} · abierta: {}",
            r.status.as_str(),
            mode_str(r.mode),
            r.opened_at
        )];
        lines.push(format!("checkpoints ({}):", r.checkpoints.len()));
        for c in &r.checkpoints {
            lines.push(format!(
                "  · [{}] {}",
                serde_label(&c.source),
                if c.note.is_empty() {
                    format!("{} claims verificadas", c.verified_claims.len())
                } else {
                    trunc(&c.note, 60)
                }
            ));
        }
        lines.push(format!("tasks ({}):", r.tasks.len()));
        for t in &r.tasks {
            lines.push(format!(
                "  · {} [{}] {}",
                t.id,
                serde_label(&t.status),
                trunc(&t.description, 40)
            ));
        }
        Ok(lines)
    }

    // ---- mutaciones: siempre detrás de la aprobación (B2/B6) ----

    fn close_session(&self, session_id: &str) -> Result<(), String> {
        cortex_cli::commands::finish_cmd::finish_session(Some(&self.root), Some(session_id), "auto")
            .map(|_| ())
    }

    fn checkpoint_session(&self, _note: &str) -> Result<(), String> {
        Err("checkpoint interactivo no integrado al Companion — usá `cortex session checkpoint --note '…'`".to_string())
    }

    /// Escribe el evento explícito positivo con el formato del oráculo
    /// (`cortex/feedback_store.py` vía `feedback.rs`) en `.cortex/` — mismo
    /// directorio que el action_log, misma regla de resolución.
    fn mark_useful(&self, memory_id: &str) -> Result<crate::feedback::AppendOutcome, String> {
        crate::feedback::append_useful(
            &self.action_log_dir(),
            "companion",
            memory_id,
            crate::feedback::MAX_BYTES_DEFAULT,
        )
    }

    /// Aprueba y ejecuta una acción del catálogo: MISMO runner nativo que
    /// usa el repo (`dry_run=false`, `approved=true`, vía "companion") — el
    /// runner además registra la ejecución en action_log.
    fn approve_action(&self, action_id: &str) -> Result<(), String> {
        let ctx = ActionContext::from_project_root(Some(&self.root));
        if !ctx.config_existe() {
            return Err(format!(
                "Cortex no está configurado en {} — corré `cortex setup agent` primero.",
                ctx.workspace_root.display()
            ));
        }
        let registry = build_default_registry(&ctx);
        let action = registry
            .get(action_id)
            .ok_or_else(|| format!("acción desconocida: {action_id}"))?;
        let mut runner = Runner::new(&ctx.dot_cortex());
        let res = runner.execute(&action_for_run(action), false, true, "companion");
        if res.ok {
            Ok(())
        } else {
            Err(res.message)
        }
    }

    fn menu_run(&self, family: &str, args: &[String]) -> Result<String, String> {
        let args: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
        match (family, args.as_slice()) {
            // Familias integradas in-process: paridad por construcción.
            ("session", []) => self.session_list_json(),
            ("session", ["current"]) => match self.session_current()? {
                Some(s) => Ok(format!(
                    "{}  {}  mode: {}  opened: {}",
                    s.id, s.status, s.mode, s.opened_at
                )),
                None => Ok("No hay sesión activa".to_string()),
            },
            ("next", []) => self.next_actions_json(),
            ("search", [q]) => self.search_json(q, 5),
            ("search", []) => Err(
                "la búsqueda necesita una consulta — usá el panel Search o `cortex search <query>`"
                    .to_string(),
            ),
            ("stats", []) => {
                let s = self.stats()?;
                Ok(format!(
                    "episódica {} · semántica {} · {}",
                    s.episodic, s.semantic, s.vault_path
                ))
            }
            ("doctor", []) => Ok(self
                .doctor()?
                .checks
                .into_iter()
                .map(|(n, v)| format!("{n}: [{}]", v.to_uppercase()))
                .collect::<Vec<String>>()
                .join("\n")),
            // Resto: fallo explícito honesto (P6/P9), con el comando exacto.
            (family, args) => {
                let mut cmd = String::from("cortex ");
                cmd.push_str(family);
                for a in args {
                    cmd.push(' ');
                    cmd.push_str(a);
                }
                Err(format!(
                    "«{family}» no integrada al Companion en esta versión — corré `{cmd}` en tu terminal"
                ))
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn committed_fixture() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../../bench/parity/archive/.p12b-doctor/.work/ap_e2e/acme-api")
    }

    /// Invariante del fix round 1: cada modo de memoria tiene SU slot, y los
    /// dos slots son instancias distintas (stats jamás contamina search).
    #[test]
    fn memory_slots_are_isolated_by_mode() {
        let be = InProcessBackend::open(&committed_fixture()).expect("abrir backend");

        // stats() abre SOLO el slot sin embeddings.
        {
            let g = be.memory(false).unwrap();
            assert!(g.without_embeddings.is_some(), "stats abre sin embeddings");
            assert!(
                g.with_embeddings.is_none(),
                "stats no debe abrir el slot con embeddings"
            );
        }

        // search() abre SU slot con embeddings, sin reusar el de stats.
        {
            let g = be.memory(true).unwrap();
            assert!(
                g.with_embeddings.is_some(),
                "search debe abrir con embeddings"
            );
        }

        // Instancias DISTINTAS: el modo sin embeddings no es el de search.
        let g = be.memory(true).unwrap();
        let without: *const NativeMemory = g.without_embeddings.as_ref().unwrap();
        let with: *const NativeMemory = g.with_embeddings.as_ref().unwrap();
        assert_ne!(without, with, "los slots deben ser instancias distintas");
    }

    /// B7 (ítem obligatorio review B4): el slot SIN embeddings jamás abre el
    /// ort Session — stats/doctor no cargan el modelo ONNX (~90 MB de RSS).
    /// Con el modelo instalado en la máquina este test es determinista y
    /// prueba el desacople: `open_without_embeddings` ⇒ `embedder.is_none()`
    /// SIEMPRE (post-fix), no solo cuando falta el modelo.
    #[test]
    fn stats_slot_never_opens_onnx_model() {
        let be = InProcessBackend::open(&committed_fixture()).expect("abrir backend");
        be.stats().expect("stats");
        let g = be.memory(false).unwrap();
        let mem = g.without_embeddings.as_ref().unwrap();
        assert!(
            mem.embedder.is_none(),
            "el slot sin embeddings NO debe abrir el modelo ONNX (RSS)"
        );
        // Y el slot con embeddings sigue abriéndolo cuando el modelo existe
        // (paridad de búsqueda intacta).
        drop(g); // `g` es el guard del Mutex de slots: sin soltarlo,
                 // be.memory(true) re-lockea el mismo mutex ⇒ deadlock.
        drop(be.memory(true).unwrap());
    }
}
