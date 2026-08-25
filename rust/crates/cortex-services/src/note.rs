//! Puerto de `cortex.services.note_service.NoteService` (P12A-5).
//!
//! Contrato duro: después de persistir, cualquier error de index semántico,
//! sync completo o memoria episódica elimina la nota y propaga el error. Así
//! se conserva `file on disk ⇒ indexed in memory`.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use chrono::{DateTime, Utc};
use serde_json::{Map, Value};

use crate::{persist_note, EpisodicPort, EpisodicRequest, SemanticPort};

/// Entrada completa de `NoteService.create`.
#[derive(Debug, Clone, Default)]
pub struct NoteCreate {
    pub title: String,
    pub spec_summary: String,
    pub changes_made: Vec<String>,
    pub files_touched: Vec<String>,
    pub key_decisions: Vec<String>,
    pub next_steps: Vec<String>,
    pub tags: Vec<String>,
    pub sync_vault: bool,
    pub remember: bool,
    pub handoff: bool,
    pub blockers: Vec<String>,
    pub verified_state: Vec<String>,
    pub unverified_claims: Vec<String>,
    pub suggested_skills: Vec<String>,
    pub cortex_telemetry: Option<Value>,
    pub task_type: String,
    pub tasks: Vec<Value>,
    pub tasks_total: i64,
    pub tasks_done: i64,
    pub tasks_skipped: i64,
    pub gitless: bool,
}

impl NoteCreate {
    /// Defaults Python: remember=True; el derive Default de bool es false.
    pub fn basic(title: impl Into<String>, spec_summary: impl Into<String>) -> Self {
        Self {
            title: title.into(),
            spec_summary: spec_summary.into(),
            remember: true,
            ..Default::default()
        }
    }
}

pub struct NoteService<'a> {
    vault_path: PathBuf,
    semantic: &'a mut dyn SemanticPort,
    episodic: &'a mut dyn EpisodicPort,
    context_metadata: BTreeMap<String, Value>,
}

impl<'a> NoteService<'a> {
    pub fn new(
        vault_path: impl Into<PathBuf>,
        semantic: &'a mut dyn SemanticPort,
        episodic: &'a mut dyn EpisodicPort,
    ) -> Self {
        Self {
            vault_path: vault_path.into(),
            semantic,
            episodic,
            context_metadata: BTreeMap::new(),
        }
    }

    pub fn with_context_metadata(mut self, metadata: BTreeMap<String, Value>) -> Self {
        self.context_metadata = metadata;
        self
    }

    /// API real: id uuid4 hex[:12]. `now` queda explícito como writers P8.
    pub fn create(&mut self, args: NoteCreate, now: DateTime<Utc>) -> Result<PathBuf, String> {
        let id = uuid::Uuid::new_v4().simple().to_string();
        self.create_with_id(args, &id[..12], now)
    }

    /// Variante determinista para gates/tests.
    pub fn create_with_id(
        &mut self,
        args: NoteCreate,
        session_id: &str,
        now: DateTime<Utc>,
    ) -> Result<PathBuf, String> {
        let mut final_tags = vec!["session".to_string()];
        final_tags.extend(args.tags.iter().cloned());
        if args.handoff && !final_tags.iter().any(|t| t == "handoff") {
            final_tags.push("handoff".into());
        }
        let status = if args.handoff { "handoff" } else { "completed" };

        let mut fields = Map::new();
        put_s(&mut fields, "title", &args.title);
        put_s(&mut fields, "status", status);
        put_list(&mut fields, "tags", &final_tags);
        put_s(&mut fields, "session_id", session_id);
        put_s(&mut fields, "spec_summary", &args.spec_summary);
        put_list(&mut fields, "changes_made", &args.changes_made);
        put_list(&mut fields, "files_touched", &args.files_touched);
        put_list(&mut fields, "key_decisions", &args.key_decisions);
        put_list(&mut fields, "next_steps", &args.next_steps);
        put_list(&mut fields, "verified_state", &args.verified_state);
        put_list(&mut fields, "unverified_claims", &args.unverified_claims);
        put_list(&mut fields, "blockers", &args.blockers);
        put_list(&mut fields, "suggested_skills", &args.suggested_skills);
        fields.insert(
            "cortex_telemetry".into(),
            args.cortex_telemetry.clone().unwrap_or(Value::Null),
        );
        put_s(&mut fields, "task_type", &args.task_type);
        fields.insert("tasks".into(), Value::Array(args.tasks.clone()));
        fields.insert("tasks_total".into(), Value::from(args.tasks_total));
        fields.insert("tasks_done".into(), Value::from(args.tasks_done));
        fields.insert("tasks_skipped".into(), Value::from(args.tasks_skipped));
        fields.insert("gitless".into(), Value::Bool(args.gitless));

        let mut req = cortex_setup::writers::NoteRequest::from_json("session", fields)?;
        let path = persist_note(&mut req, &self.vault_path, now)?;

        // Todo lo posterior es transaccional: error ⇒ unlink + propagación.
        let post = self.post_persist(&path, &args);
        if let Err(error) = post {
            let _ = std::fs::remove_file(&path);
            return Err(error);
        }
        Ok(path)
    }

    fn post_persist(&mut self, path: &Path, args: &NoteCreate) -> Result<(), String> {
        let rel = path
            .strip_prefix(&self.vault_path)
            .map_err(|e| e.to_string())?
            .to_string_lossy()
            .replace('\\', "/");
        self.semantic.index_file(&rel)?;
        if args.sync_vault {
            self.semantic.sync()?;
        }
        if args.remember {
            let mut tags = args.tags.clone();
            if args.handoff && !tags.iter().any(|t| t == "handoff") {
                tags.push("handoff".into());
            }
            self.store_episodic(args, tags)?;
        }
        Ok(())
    }

    fn store_episodic(&mut self, args: &NoteCreate, tags: Vec<String>) -> Result<(), String> {
        let mut summary = vec![
            format!("Session: {}", args.title),
            format!("Specification: {}", args.spec_summary),
        ];
        if !args.changes_made.is_empty() {
            summary.push(format!(
                "Changes: {}",
                args.changes_made
                    .iter()
                    .take(8)
                    .cloned()
                    .collect::<Vec<_>>()
                    .join("; ")
            ));
        }
        if !args.key_decisions.is_empty() {
            summary.push(format!(
                "Decisions: {}",
                args.key_decisions
                    .iter()
                    .take(5)
                    .cloned()
                    .collect::<Vec<_>>()
                    .join("; ")
            ));
        }
        let mut final_tags = vec!["session".to_string()];
        final_tags.extend(tags);
        self.episodic.add(EpisodicRequest {
            content: summary.join("\n"),
            memory_type: "session".into(),
            tags: final_tags,
            files: args.files_touched.clone(),
            extra_metadata: self.context_metadata.clone(),
        })
    }
}

fn put_s(fields: &mut Map<String, Value>, key: &str, value: &str) {
    fields.insert(key.into(), Value::String(value.into()));
}

fn put_list(fields: &mut Map<String, Value>, key: &str, values: &[String]) {
    fields.insert(
        key.into(),
        Value::Array(values.iter().cloned().map(Value::String).collect()),
    );
}

/// Alias nominal del servicio legacy (`cortex.services.session_service`).
pub type SessionNoteService<'a> = NoteService<'a>;

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{EpisodicPort, EpisodicRequest, SemanticPort};

    struct Sem {
        fail: bool,
        indexed: Vec<String>,
    }
    impl SemanticPort for Sem {
        fn index_file(&mut self, rel: &str) -> Result<bool, String> {
            if self.fail {
                return Err("semantic indexing failed".into());
            }
            self.indexed.push(rel.into());
            Ok(true)
        }
        fn sync(&mut self) -> Result<usize, String> {
            Ok(0)
        }
    }
    #[derive(Default)]
    struct Ep {
        added: Vec<EpisodicRequest>,
    }
    impl EpisodicPort for Ep {
        fn add(&mut self, r: EpisodicRequest) -> Result<(), String> {
            self.added.push(r);
            Ok(())
        }
    }
    fn now() -> DateTime<Utc> {
        chrono::TimeZone::with_ymd_and_hms(&Utc, 2026, 6, 1, 12, 0, 0).unwrap()
    }

    #[test]
    fn success_preserva_e_indexa() {
        let root = std::env::temp_dir().join(format!("svc_note_ok_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        let mut sem = Sem {
            fail: false,
            indexed: vec![],
        };
        let mut ep = Ep::default();
        let mut svc = NoteService::new(&root, &mut sem, &mut ep);
        let p = svc
            .create_with_id(NoteCreate::basic("Happy", "spec"), "abcdef123456", now())
            .unwrap();
        drop(svc);
        assert!(p.is_file());
        assert_eq!(sem.indexed.len(), 1);
        assert_eq!(ep.added.len(), 1);
        std::fs::remove_dir_all(root).ok();
    }

    #[test]
    fn semantic_error_hace_rollback() {
        let root = std::env::temp_dir().join(format!("svc_note_rb_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        let mut sem = Sem {
            fail: true,
            indexed: vec![],
        };
        let mut ep = Ep::default();
        let mut svc = NoteService::new(&root, &mut sem, &mut ep);
        let err = svc
            .create_with_id(NoteCreate::basic("Rollback", "spec"), "abcdef123456", now())
            .unwrap_err();
        assert_eq!(err, "semantic indexing failed");
        let md = root.join("sessions");
        assert!(std::fs::read_dir(md)
            .map(|mut r| r.next().is_none())
            .unwrap_or(true));
        std::fs::remove_dir_all(root).ok();
    }
}
