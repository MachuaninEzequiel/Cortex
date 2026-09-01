//! Backend nativo de la familia SESIONES (SessionsBackend) sobre
//! `cortex-app::SessionService` — mapeo 1:1 con los métodos del trac; los
//! handlers mantienen los formatos del oráculo byte a byte.

use crate::handlers_sessions::{SCheckpoint, SHook, SRecord, STask, SessionsBackend};
use cortex_app::session::service::SessionService;
use cortex_app::session::{CheckpointSource, SessionRecord, TaskStatus};
use std::path::Path;

/// Backend de producción sobre el service nativo.
pub struct NativeSessionsBackend {
    service: SessionService,
}

impl NativeSessionsBackend {
    pub fn new(root: &Path) -> Self {
        let storage =
            cortex_app::session::SessionStorage::new(root.join(".cortex").join("sessions"));
        Self {
            service: SessionService::new(storage, root),
        }
    }
}

impl SessionsBackend for NativeSessionsBackend {
    fn open_session(
        &mut self,
        spec_id: &str,
        spec_path: &str,
        spec_summary: &str,
    ) -> Result<SRecord, String> {
        let record = self.service.open(spec_id, spec_path, spec_summary)?;
        Ok(srecord(record))
    }

    fn checkpoint_session(
        &mut self,
        session_id: &str,
        source: &str,
        verified_claims: Vec<String>,
        unverified_claims: Vec<String>,
        artifacts_touched: Vec<String>,
        note: String,
        phase: Option<&str>,
    ) -> Result<SRecord, String> {
        let source = checkpoint_source(source).unwrap_or(CheckpointSource::Manual);
        let record = self.service.checkpoint(
            session_id,
            source,
            verified_claims,
            unverified_claims,
            artifacts_touched,
            &note,
            phase,
        )?;
        Ok(srecord(record))
    }

    fn close_session(
        &mut self,
        session_id: &str,
        status: &str,
        documenter_decision: &str,
        session_note_path: Option<String>,
        adrs_created: Vec<String>,
    ) -> Result<SRecord, String> {
        let status = status_of(status)?;
        let decision = status_of(documenter_decision)?;
        let record = self.service.close(
            session_id,
            status,
            decision,
            session_note_path,
            adrs_created,
        )?;
        Ok(srecord(record))
    }

    fn get_active_session(&mut self) -> Result<Option<SRecord>, String> {
        Ok(self.service.get_active().map(srecord))
    }

    fn get_session(&mut self, session_id: &str) -> Result<SRecord, String> {
        Ok(srecord(self.service.get(session_id)?))
    }

    fn list_sessions(&mut self, status: Option<String>) -> Result<Vec<SRecord>, String> {
        let filter = status.as_deref().map(status_of).transpose()?;
        let mut records = self.service.list(filter)?;
        // Newest-first (mismo orden que `session list`).
        records.sort_by(|a, b| b.opened_at.cmp(&a.opened_at));
        Ok(records.into_iter().map(srecord).collect())
    }

    fn list_tasks(
        &mut self,
        session_id: &str,
        status: Option<String>,
    ) -> Result<Vec<STask>, String> {
        let filter = status.as_deref().map(task_status).transpose()?;
        let tasks = self.service.list_tasks(session_id, filter)?;
        Ok(tasks.into_iter().map(stask).collect())
    }

    fn add_task(&mut self, session_id: &str, task: STask) -> Result<(), String> {
        let mut record = self.service.get(session_id)?;
        let t = cortex_app::session::Task {
            id: task.id,
            description: task.description,
            files_in_scope: task.files_in_scope,
            depends_on: task.depends_on,
            status: task_status(&task.status)?,
            completed_at: task.completed_at,
            checkpoint_index: task.checkpoint_index.map(|i| i as u64),
            note: task.note,
        };
        record.tasks.push(t);
        self.service.storage.save(&record)?;
        Ok(())
    }

    fn update_task(
        &mut self,
        session_id: &str,
        task_id: &str,
        status: &str,
        note: String,
        checkpoint_index: Option<i64>,
    ) -> Result<(), String> {
        let mut record = self.service.get(session_id)?;
        let Some(task) = record.tasks.iter_mut().find(|t| t.id == task_id) else {
            return Err(format!(
                "Task id '{task_id}' not found in session '{session_id}'"
            ));
        };
        task.status = task_status(status)?;
        if !note.is_empty() {
            task.note = note;
        }
        if task.status == TaskStatus::Done && task.completed_at.is_none() {
            task.completed_at = Some(cortex_app::session::service::now_iso());
        }
        if task.status != TaskStatus::Done {
            task.completed_at = None;
        }
        task.checkpoint_index = checkpoint_index.map(|i| i as u64);
        self.service.storage.save(&record)?;
        Ok(())
    }

    fn save_session_note(&mut self, args: &serde_json::Value) -> Result<String, String> {
        let title = args
            .get("title")
            .and_then(serde_json::Value::as_str)
            .unwrap_or("Session note");
        let spec_summary = args
            .get("spec_summary")
            .and_then(serde_json::Value::as_str)
            .unwrap_or("")
            .to_string();
        let summary = args
            .get("summary")
            .and_then(serde_json::Value::as_str)
            .unwrap_or("")
            .to_string();
        let root = self.service_root();
        let vault = root.join(".cortex").join("vault");
        std::fs::create_dir_all(vault.join("session-notes"))
            .map_err(|e| format!("session note: {e}"))?;
        let slug = title.to_lowercase().replace(' ', "-");
        let path = vault.join("session-notes").join(format!("{slug}.md"));
        let body =
            format!("---\ntitle: {title}\nspec_summary: \"{spec_summary}\"\n---\n\n{summary}\n");
        std::fs::write(&path, body).map_err(|e| format!("session note: {e}"))?;
        Ok(path.display().to_string())
    }

    fn spec_files_in_scope(&mut self, spec_path: &str) -> Result<Vec<String>, String> {
        let root = self.service_root();
        let full = if spec_path.starts_with('/') {
            std::path::PathBuf::from(spec_path)
        } else {
            root.join(".cortex").join(spec_path)
        };
        let text = std::fs::read_to_string(&full).map_err(|e| format!("spec: {e}"))?;
        Ok(extract_files_in_scope(&text))
    }
}

impl NativeSessionsBackend {
    fn service_root(&self) -> std::path::PathBuf {
        self.service
            .storage
            .root()
            .parent()
            .unwrap_or_else(|| std::path::Path::new(""))
            .to_path_buf()
    }
}

fn status_of(s: &str) -> Result<cortex_app::session::SessionStatus, String> {
    match s {
        "open" => Ok(cortex_app::session::SessionStatus::Open),
        "closed" => Ok(cortex_app::session::SessionStatus::Closed),
        "handoff" => Ok(cortex_app::session::SessionStatus::Handoff),
        "abandoned" => Ok(cortex_app::session::SessionStatus::Abandoned),
        other => Err(format!("invalid session status: {other}")),
    }
}

fn checkpoint_source(s: &str) -> Option<CheckpointSource> {
    match s {
        "cortex-sync" => Some(CheckpointSource::CortexSync),
        "cortex-SDDwork" => Some(CheckpointSource::CortexSddwork),
        "cortex-code-explorer" => Some(CheckpointSource::CortexCodeExplorer),
        "cortex-code-implementer" => Some(CheckpointSource::CortexCodeImplementer),
        "cortex-code-designer" => Some(CheckpointSource::CortexCodeDesigner),
        "user-skill" => Some(CheckpointSource::UserSkill),
        "ide-hook" => Some(CheckpointSource::IdeHook),
        "manual" => Some(CheckpointSource::Manual),
        "ci-bot" => Some(CheckpointSource::CiBot),
        _ => None,
    }
}

fn task_status(s: &str) -> Result<TaskStatus, String> {
    match s {
        "pending" => Ok(TaskStatus::Pending),
        "in-progress" => Ok(TaskStatus::InProgress),
        "done" => Ok(TaskStatus::Done),
        "skipped" => Ok(TaskStatus::Skipped),
        "blocked" => Ok(TaskStatus::Blocked),
        other => Err(format!("invalid task status: {other}")),
    }
}

/// Record nativo → espejo plano de los handlers.
pub fn srecord(r: SessionRecord) -> SRecord {
    SRecord {
        session_id: r.session_id,
        spec_path: r.spec_path,
        spec_summary: r.spec_summary,
        start_commit: r.start_commit,
        start_branch: r.start_branch,
        opened_at: r.opened_at,
        status: r.status.as_str().to_string(),
        mode: session_mode(&r.mode),
        checkpoints: r
            .checkpoints
            .iter()
            .map(|c| SCheckpoint {
                timestamp: c.timestamp.clone(),
                source: checkpoint_source_str(&c.source).to_string(),
                verified_claims: c.verified_claims.clone(),
                unverified_claims: c.unverified_claims.clone(),
                artifacts_touched: c.artifacts_touched.clone(),
                note: c.note.clone(),
            })
            .collect(),
        verification_results: r
            .verification_results
            .iter()
            .map(|v| SHook {
                name: v.name.clone(),
                command: v.command.clone(),
                passed: v.passed,
                exit_code: v.exit_code as i64,
                output: v.output.clone(),
                duration_ms: v.duration_ms as i64,
                run_at: v.run_at.clone(),
            })
            .collect(),
        tasks: r.tasks.iter().map(stask_proto).collect(),
        closed_at: r.closed_at,
        end_commit: r.end_commit,
        documenter_decision: r.documenter_decision.map(|s| s.as_str().to_string()),
        session_note_path: r.session_note_path,
        adrs_created: r.adrs_created,
    }
}

fn stask_proto(t: &cortex_app::session::Task) -> STask {
    STask {
        id: t.id.clone(),
        description: t.description.clone(),
        files_in_scope: t.files_in_scope.clone(),
        depends_on: t.depends_on.clone(),
        status: task_status_str(t.status).to_string(),
        completed_at: t.completed_at.clone(),
        checkpoint_index: t.checkpoint_index.map(|i| i as i64),
        note: t.note.clone(),
    }
}

fn stask(t: cortex_app::session::Task) -> STask {
    stask_proto(&t)
}

fn task_status_str(s: TaskStatus) -> &'static str {
    match s {
        TaskStatus::Pending => "pending",
        TaskStatus::InProgress => "in-progress",
        TaskStatus::Done => "done",
        TaskStatus::Skipped => "skipped",
        TaskStatus::Blocked => "blocked",
    }
}

fn session_mode(m: &cortex_app::session::SessionMode) -> String {
    match m {
        cortex_app::session::SessionMode::Unknown => "unknown",
        cortex_app::session::SessionMode::Managed => "managed",
        cortex_app::session::SessionMode::Observed => "observed",
        cortex_app::session::SessionMode::Byo => "byo",
        cortex_app::session::SessionMode::CiReview => "ci-review",
        cortex_app::session::SessionMode::Composed => "composed",
    }
    .to_string()
}

fn checkpoint_source_str(s: &CheckpointSource) -> &'static str {
    match s {
        CheckpointSource::CortexSync => "cortex-sync",
        CheckpointSource::CortexSddwork => "cortex-SDDwork",
        CheckpointSource::CortexCodeExplorer => "cortex-code-explorer",
        CheckpointSource::CortexCodeImplementer => "cortex-code-implementer",
        CheckpointSource::CortexCodeDesigner => "cortex-code-designer",
        CheckpointSource::UserSkill => "user-skill",
        CheckpointSource::IdeHook => "ide-hook",
        CheckpointSource::Manual => "manual",
        CheckpointSource::CiBot => "ci-bot",
    }
}

/// Frontmatter yaml del spec (bloque entre `---` iniciales).
pub fn frontmatter(text: &str) -> Option<&str> {
    let rest = text.strip_prefix("---\n")?;
    let end = rest.find("\n---")?;
    Some(&rest[..end])
}

/// `files_in_scope:` de YAML dentro del frontmatter (o lista inline).
fn extract_files_in_scope(text: &str) -> Vec<String> {
    let Some(fm) = frontmatter(text) else {
        return Vec::new();
    };
    let Ok(v) = serde_yaml::from_str::<serde_yaml::Value>(fm) else {
        return Vec::new();
    };
    v.get("files_in_scope")
        .and_then(|x| x.as_sequence())
        .map(|xs| {
            xs.iter()
                .filter_map(|x| x.as_str().map(str::to_string))
                .collect()
        })
        .unwrap_or_default()
}
