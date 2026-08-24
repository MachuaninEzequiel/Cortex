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
    Checkpoint, CheckpointSource, SessionRecord, SessionStatus, SessionStorage,
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
}
