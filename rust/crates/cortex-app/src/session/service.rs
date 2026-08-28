//! Puerto de `cortex/session/service.py` — capa de servicio sobre el
//! storage (Obra 07 fase P11-ci, stream A).
//!
//! Espeja la API que consumen `cortex.ci` (validator, review_session) y los
//! tests unitarios Python: open/checkpoint/close con invariantes de ciclo de
//! vida, find_for_pr (prioridad explícito > by_commit > by_branch > none),
//! ids únicos por sufijo `-2`, `-3`…, session.lock best-effort para lectores
//! externos y puntero activo.
//!
//! Nota de alcance: el `mutate` transaccional del storage Python usa lock
//! por-archivo para workers MCP concurrentes; acá load→mutate→save corre en
//! un solo hilo (los gates de paridad no ejercitan la concurrencia).

use std::fs;
use std::path::{Path, PathBuf};

use super::{
    Checkpoint, CheckpointSource, SessionRecord, SessionStatus, SessionStorage, Task, TaskStatus,
    GITLESS_COMMIT_PLACEHOLDER,
};
use crate::git;

/// Tipos de match de sesión para un PR (orden de prioridad del oráculo).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SessionMatchKind {
    Explicit,
    ByCommit,
    ByBranch,
    NoneKind,
}

impl SessionMatchKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Explicit => "explicit",
            Self::ByCommit => "by_commit",
            Self::ByBranch => "by_branch",
            Self::NoneKind => "none",
        }
    }
}

/// `datetime.now(UTC)` serializado como el modelo Python (offset +00:00).
pub fn now_iso() -> String {
    chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Micros, false)
}

#[derive(Clone)]
pub struct SessionService {
    pub storage: SessionStorage,
    repo_root: PathBuf,
}

impl SessionService {
    pub fn new(storage: SessionStorage, repo_root: &Path) -> Self {
        Self {
            storage,
            repo_root: repo_root.to_path_buf(),
        }
    }

    /// `git diff <start_commit>..<end_ref>` — port de
    /// `SessionService.compute_diff` del oráculo (session/service.py:476):
    /// `end_commit` si la sesión está cerrada, `HEAD` si no; vacío en modo
    /// gitless (el documenter inspecciona checkpoints en ese caso).
    /// Inseguro nunca: start/end ya validados (SHA 40-hex o HEAD).
    pub fn compute_diff(&self, session_id: &str) -> Result<String, String> {
        let record = self.get(session_id)?;
        if record.is_gitless() {
            return Ok(String::new());
        }
        let end_ref = record
            .end_commit
            .clone()
            .unwrap_or_else(|| "HEAD".to_string());
        let start = record.start_commit.clone();
        let output = std::process::Command::new("git")
            .arg("diff")
            .arg(format!("{start}..{end_ref}"))
            .current_dir(&self.repo_root)
            .output()
            .map_err(|e| format!("git diff: {e}"))?;
        if !output.status.success() {
            return Err(format!(
                "git diff {start}..{end_ref}: {}",
                String::from_utf8_lossy(&output.stderr).trim()
            ));
        }
        Ok(String::from_utf8_lossy(&output.stdout).into_owned())
    }

    pub fn repo_root(&self) -> &Path {
        &self.repo_root
    }

    /// Persistir un record NUEVO sin tocar el puntero activo (falla si existe).
    pub fn save_new_record(&self, record: &SessionRecord) -> Result<PathBuf, String> {
        if self.storage.exists(&record.session_id) {
            return Err(format!("SessionAlreadyExists: {}", record.session_id));
        }
        self.storage.save(record)
    }

    pub fn path_for(&self, session_id: &str) -> PathBuf {
        self.storage.file_path(session_id)
    }

    pub fn active_pointer_path(&self) -> PathBuf {
        self.storage.active_pointer_path()
    }

    /// Mantener sincronizado `<repo_root>/.cortex/session.lock`.
    ///
    /// Best-effort: un fallo de FS NUNCA rompe el ciclo de vida.
    fn write_session_lock(&self, session_id: Option<&str>) {
        let lock_path = self.repo_root.join(".cortex").join("session.lock");
        let _ = (|| -> std::io::Result<()> {
            match session_id {
                None => {
                    if lock_path.is_file() {
                        fs::remove_file(&lock_path)?;
                    }
                }
                Some(id) => {
                    if let Some(parent) = lock_path.parent() {
                        fs::create_dir_all(parent)?;
                    }
                    // `<id>\n` literal (write_bytes: sin traducción CRLF).
                    fs::write(&lock_path, format!("{id}\n"))?;
                }
            }
            Ok(())
        })();
    }

    pub fn get(&self, session_id: &str) -> Result<SessionRecord, String> {
        self.storage.load(session_id)
    }

    /// Sesión activa o None (punteros stale degradan a None).
    pub fn get_active(&self) -> Option<SessionRecord> {
        let session_id = self.storage.get_active_session_id()?;
        self.storage.load(&session_id).ok()
    }

    /// Promover a activo: debe existir y estar OPEN.
    pub fn set_active(&self, session_id: &str) -> Result<(), String> {
        let record = self.storage.load(session_id)?;
        if record.status != SessionStatus::Open {
            return Err(format!(
                "Cannot set active a session in status {:?}; only OPEN sessions can be active.",
                record.status.as_str()
            ));
        }
        self.storage.set_active_session_id(Some(session_id))?;
        self.write_session_lock(Some(session_id));
        Ok(())
    }

    pub fn list(&self, status: Option<SessionStatus>) -> Result<Vec<SessionRecord>, String> {
        let all = self.storage.list_all()?;
        Ok(match status {
            None => all,
            Some(s) => all.into_iter().filter(|r| r.status == s).collect(),
        })
    }

    /// Resolver la Session que posee un PR
    /// (prioridad explícito > by_commit > by_branch > none).
    ///
    /// Sustituye el acceso privado `service._storage` que hacía
    /// `cortex.ci.validator`. Devuelve `(record, match_kind)`.
    pub fn find_for_pr(
        &self,
        explicit_session_id: Option<&str>,
        base_commit: Option<&str>,
        head_branch: Option<&str>,
    ) -> (Option<SessionRecord>, SessionMatchKind) {
        if let Some(id) = explicit_session_id.filter(|s| !s.is_empty()) {
            return match self.storage.load(id) {
                Ok(record) => (Some(record), SessionMatchKind::Explicit),
                Err(_) => (None, SessionMatchKind::NoneKind),
            };
        }
        let records = match self.storage.list_all() {
            Ok(r) => r,
            Err(_) => return (None, SessionMatchKind::NoneKind),
        };
        if let Some(base) = base_commit.filter(|s| !s.is_empty()) {
            for record in &records {
                if record.start_commit == base {
                    return (Some(record.clone()), SessionMatchKind::ByCommit);
                }
            }
        }
        if let Some(branch) = head_branch.filter(|s| !s.is_empty()) {
            for record in &records {
                if record.start_branch == branch {
                    return (Some(record.clone()), SessionMatchKind::ByBranch);
                }
            }
        }
        (None, SessionMatchKind::NoneKind)
    }

    /// Crear una sesión OPEN para `spec_id` y promoverla a activa.
    ///
    /// Colisiones id ⇒ sufijo -2/-3…; colisión con id existente aún OPEN ⇒ se
    /// devuelve ese record (idempotencia anti-fantasma del oráculo). Sin git ⇒
    /// modo gitless con placeholder.
    pub fn open(
        &self,
        spec_id: &str,
        spec_path: &str,
        spec_summary: &str,
    ) -> Result<SessionRecord, String> {
        if self.storage.exists(spec_id) {
            if let Ok(rec) = self.storage.load(spec_id) {
                if rec.status == SessionStatus::Open {
                    self.storage.set_active_session_id(Some(&rec.session_id))?;
                    self.write_session_lock(Some(&rec.session_id));
                    return Ok(rec);
                }
            }
        }
        let session_id = self.make_unique_session_id(spec_id);
        let (start_commit, start_branch) = if git::is_git_repo(&self.repo_root) {
            (
                git::get_head_commit(&self.repo_root).map_err(|e| e.to_string())?,
                git::get_current_branch(&self.repo_root).map_err(|e| e.to_string())?,
            )
        } else {
            (GITLESS_COMMIT_PLACEHOLDER.to_string(), String::new())
        };
        let record = SessionRecord {
            session_id,
            spec_path: spec_path.to_string(),
            spec_summary: spec_summary.to_string(),
            start_commit,
            start_branch,
            opened_at: now_iso(),
            ..Default::default()
        };
        self.save_new_record(&record)?;
        self.storage
            .set_active_session_id(Some(&record.session_id))?;
        self.write_session_lock(Some(&record.session_id));
        Ok(record)
    }

    /// Agregar un checkpoint a una sesión OPEN.
    #[allow(clippy::too_many_arguments)]
    pub fn checkpoint(
        &self,
        session_id: &str,
        source: CheckpointSource,
        verified_claims: Vec<String>,
        unverified_claims: Vec<String>,
        artifacts_touched: Vec<String>,
        note: &str,
    ) -> Result<SessionRecord, String> {
        let mut record = self.storage.load(session_id)?;
        if record.status != SessionStatus::Open {
            return Err(format!(
                "Cannot append checkpoint to session in status {:?}",
                record.status.as_str()
            ));
        }
        record.checkpoints.push(Checkpoint {
            timestamp: now_iso(),
            source,
            verified_claims,
            unverified_claims,
            artifacts_touched,
            note: note.to_string(),
        });
        self.storage.save(&record)?;
        Ok(record)
    }

    /// Cerrar una sesión OPEN en estado terminal.
    ///
    /// Captura HEAD como end_commit (gitless/rotura de git ⇒ placeholder),
    /// infiere el modo de los checkpoints y limpia el puntero activo si
    /// apuntaba a esta sesión.
    #[allow(clippy::too_many_arguments)]
    pub fn close(
        &self,
        session_id: &str,
        status: SessionStatus,
        documenter_decision: SessionStatus,
        session_note_path: Option<String>,
        adrs_created: Vec<String>,
    ) -> Result<SessionRecord, String> {
        if !status.is_terminal() {
            return Err(format!(
                "status passed to close() must be terminal (CLOSED | HANDOFF | ABANDONED), got {:?}",
                status.as_str()
            ));
        }
        let mut record = self.storage.load(session_id)?;
        if record.status != SessionStatus::Open {
            return Err(format!(
                "Cannot close session in status {:?}",
                record.status.as_str()
            ));
        }
        let end_commit = if record.is_gitless() {
            GITLESS_COMMIT_PLACEHOLDER.to_string()
        } else {
            git::get_head_commit(&self.repo_root).unwrap_or(GITLESS_COMMIT_PLACEHOLDER.to_string())
        };
        let checkpoints = record.checkpoints.clone();
        let mode = super::infer_mode(&checkpoints);
        record.status = status;
        record.mode = mode;
        record.closed_at = Some(now_iso());
        record.end_commit = Some(end_commit);
        record.documenter_decision = Some(documenter_decision);
        record.session_note_path = session_note_path;
        record.adrs_created = adrs_created;
        self.storage.save(&record)?;
        if self.storage.get_active_session_id().as_deref() == Some(session_id) {
            self.storage.set_active_session_id(None)?;
            self.write_session_lock(None);
        }
        Ok(record)
    }

    /// `base`, o `base-2`, `base-3`… si storage ya lo tiene.
    pub fn make_unique_session_id(&self, base: &str) -> String {
        if !self.storage.exists(base) {
            return base.to_string();
        }
        let mut counter = 2;
        loop {
            let candidate = format!("{base}-{counter}");
            if !self.storage.exists(&candidate) {
                return candidate;
            }
            counter += 1;
        }
    }

    /// `service.list_tasks` (oráculo `cortex session task list`): las tareas
    /// de una sesión, opcionalmente filtradas por estado. Puerto de
    /// `cortex/session/service.py::list_tasks`.
    pub fn list_tasks(
        &self,
        session_id: &str,
        status: Option<TaskStatus>,
    ) -> Result<Vec<Task>, String> {
        let record = self.storage.load(session_id)?;
        Ok(match status {
            None => record.tasks,
            Some(s) => record.tasks.into_iter().filter(|t| t.status == s).collect(),
        })
    }

    /// `service.update_task_status` (oráculo `cortex session task
    /// done|in-progress|skip|block`): muta el estado de una tarea y persiste
    /// la sesión. Espejo de `service.py::update_task_status`:
    /// - sesión NO OPEN ⇒ `Cannot update task in session with status
    ///   '<estado>'`;
    /// - task inexistente ⇒ `Task id '<id>' not found in session
    ///   '<sid>'`;
    /// - nota no vacía se escribe;
    /// - DONE ⇒ `completed_at` automático si faltaba; PENDING/IN_PROGRESS ⇒
    ///   `completed_at = None` (invariante del modelo).
    pub fn update_task_status(
        &self,
        session_id: &str,
        task_id: &str,
        new_status: TaskStatus,
        note: &str,
    ) -> Result<Task, String> {
        let mut record = self.storage.load(session_id)?;
        if record.status != SessionStatus::Open {
            return Err(format!(
                "Cannot update task in session with status '{}'",
                record.status.as_str()
            ));
        }
        let idx = record
            .tasks
            .iter()
            .position(|t| t.id == task_id)
            .ok_or_else(|| format!("Task id '{task_id}' not found in session '{session_id}'"))?;
        {
            let task = &mut record.tasks[idx];
            task.status = new_status;
            if !note.is_empty() {
                task.note = note.to_string();
            }
            match new_status {
                TaskStatus::Done => {
                    if task.completed_at.is_none() {
                        task.completed_at = Some(now_iso());
                    }
                }
                TaskStatus::Pending | TaskStatus::InProgress => {
                    task.completed_at = None;
                }
                TaskStatus::Skipped | TaskStatus::Blocked => {}
            }
        }
        let updated = record.tasks[idx].clone();
        self.storage.save(&record)?;
        Ok(updated)
    }
}

#[cfg(test)]
mod task_tests {
    use super::*;

    fn tmp_svc(tag: &str) -> (SessionService, std::path::PathBuf) {
        let dir = std::env::temp_dir().join(format!(
            "cortex_session_service_{tag}_{}",
            std::process::id()
        ));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let storage = SessionStorage::new(dir.join("sessions"));
        let svc = SessionService::new(storage, &dir);
        (svc, dir)
    }

    fn task(id: &str, status: TaskStatus) -> Task {
        let mut t = Task {
            id: id.to_string(),
            description: format!("desc {id}"),
            files_in_scope: vec![],
            depends_on: vec![],
            status,
            completed_at: None,
            checkpoint_index: None,
            note: String::new(),
        };
        // Invariante del modelo Python: done ⇒ completed_at seteado.
        if status == TaskStatus::Done {
            t.completed_at = Some(now_iso());
        }
        t
    }

    fn seed_session(svc: &SessionService) -> SessionRecord {
        let record = SessionRecord {
            session_id: "2026-08-25_demo".to_string(),
            spec_path: "vault/specs/demo.md".to_string(),
            spec_summary: "demo".to_string(),
            start_commit: GITLESS_COMMIT_PLACEHOLDER.to_string(),
            start_branch: String::new(),
            opened_at: now_iso(),
            status: SessionStatus::Open,
            tasks: vec![
                task("T1", TaskStatus::Pending),
                task("T1.2", TaskStatus::Done),
            ],
            ..Default::default()
        };
        svc.save_new_record(&record).unwrap();
        record
    }

    #[test]
    fn list_tasks_filtra_por_estado() {
        let (svc, _dir) = tmp_svc("lt");
        let record = seed_session(&svc);

        let all = svc.list_tasks(&record.session_id, None).unwrap();
        assert_eq!(all.len(), 2);
        assert_eq!(all[0].id, "T1");
        assert_eq!(all[1].id, "T1.2");

        let done = svc
            .list_tasks(&record.session_id, Some(TaskStatus::Done))
            .unwrap();
        assert_eq!(done.len(), 1);
        assert_eq!(done[0].id, "T1.2");

        let blocked = svc
            .list_tasks(&record.session_id, Some(TaskStatus::Blocked))
            .unwrap();
        assert!(blocked.is_empty());

        // Sesión inexistente ⇒ error (espejo de SessionNotFound del storage).
        assert!(svc.list_tasks("2099-01-01_nope", None).is_err());
    }

    #[test]
    fn update_task_status_terminal_y_nota() {
        let (svc, _dir) = tmp_svc("ut");
        let record = seed_session(&svc);
        let sid = record.session_id.clone();

        let updated = svc
            .update_task_status(&sid, "T1", TaskStatus::Done, "primer fix")
            .unwrap();
        assert_eq!(updated.status, TaskStatus::Done);
        assert_eq!(updated.note, "primer fix");
        assert!(updated.completed_at.is_some(), "done ⇒ completed_at");

        // Persistido: recargar la sesión muestra la mutación.
        let reloaded = svc.get(&sid).unwrap();
        let t1 = reloaded.tasks.iter().find(|t| t.id == "T1").unwrap();
        assert_eq!(t1.status, TaskStatus::Done);
        assert_eq!(t1.completed_at.as_deref(), updated.completed_at.as_deref());
        assert_eq!(t1.note, "primer fix");
        assert!(t1.completed_at.is_some());
        // La otra tarea no se tocó.
        let t12 = reloaded.tasks.iter().find(|t| t.id == "T1.2").unwrap();
        assert_eq!(t12.status, TaskStatus::Done);
        assert!(t12.completed_at.is_some());
    }

    #[test]
    fn update_task_status_resetea_completed_at() {
        let (svc, _dir) = tmp_svc("ur");
        let record = seed_session(&svc);
        let sid = record.session_id.clone();

        let up = svc
            .update_task_status(&sid, "T1.2", TaskStatus::InProgress, "")
            .unwrap();
        assert_eq!(up.status, TaskStatus::InProgress);
        assert!(up.completed_at.is_none(), "in-progress ⇒ completed_at None");

        let up = svc
            .update_task_status(&sid, "T1.2", TaskStatus::Pending, "")
            .unwrap();
        assert_eq!(up.status, TaskStatus::Pending);
        assert!(up.completed_at.is_none());

        // done sobre una ya hecha conserva completed_at existente.
        let first = svc
            .update_task_status(&sid, "T1", TaskStatus::Done, "")
            .unwrap();
        let second = svc
            .update_task_status(&sid, "T1", TaskStatus::Done, "")
            .unwrap();
        assert_eq!(first.completed_at, second.completed_at);
    }

    #[test]
    fn update_task_status_errores_del_oraculo() {
        let (svc, _dir) = tmp_svc("ue");
        let record = seed_session(&svc);
        let sid = record.session_id.clone();

        let err = svc
            .update_task_status(&sid, "T99", TaskStatus::Done, "")
            .unwrap_err();
        assert_eq!(err, "Task id 'T99' not found in session '2026-08-25_demo'");

        // Sesión cerrada ⇒ invalid state transition del oráculo.
        let closed = SessionRecord {
            session_id: "2026-08-24_cerrada".to_string(),
            spec_path: "x.md".to_string(),
            spec_summary: "x".to_string(),
            start_commit: GITLESS_COMMIT_PLACEHOLDER.to_string(),
            start_branch: String::new(),
            opened_at: now_iso(),
            status: SessionStatus::Closed,
            closed_at: Some(now_iso()),
            end_commit: Some(GITLESS_COMMIT_PLACEHOLDER.to_string()),
            documenter_decision: Some(SessionStatus::Closed),
            tasks: vec![task("T1", TaskStatus::Pending)],
            ..Default::default()
        };
        svc.save_new_record(&closed).unwrap();
        let err = svc
            .update_task_status(&closed.session_id, "T1", TaskStatus::Done, "")
            .unwrap_err();
        assert_eq!(err, "Cannot update task in session with status 'closed'");
    }
}
