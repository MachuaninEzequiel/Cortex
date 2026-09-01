//! Backend nativo de la familia FINISH (FinishBackend): reconstrucción y
//! cierre de sesión con datos reales (diff git, verificación existente,
//! nota de sesión). La re-ejecución de hooks (run_hooks=true) y la
//! sugerencia de ADRs esperan el wiring P12: acá se reporta lo persistido
//! con honestidad.

use crate::handlers_finish::{
    AdrSuggestionMirror, ContradictionMirror, DiffEntryMirror, FinishBackend, FinishResultMirror,
    RawCheckpointMirror, ReconstructionMirror, SpecInfoMirror, VerifResultMirror,
};
use cortex_app::session::service::SessionService;
use cortex_app::session::{SessionStatus, SessionStorage};
use std::path::{Path, PathBuf};
use std::process::Command;

/// Backend de producción para la familia finish.
pub struct NativeFinishBackend {
    root: PathBuf,
}

impl NativeFinishBackend {
    pub fn new(root: &Path) -> Self {
        Self {
            root: root.to_path_buf(),
        }
    }

    fn service(&self) -> SessionService {
        let storage = SessionStorage::new(self.root.join(".cortex").join("sessions"));
        SessionService::new(storage, &self.root)
    }

    fn head_commit(&self) -> String {
        Command::new("git")
            .args(["rev-parse", "HEAD"])
            .current_dir(&self.root)
            .output()
            .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
            .unwrap_or_default()
    }

    /// `git diff --name-status start..end` → (files_touched, entries).
    fn name_status(&self, start: &str, end: &str) -> (Vec<String>, Vec<DiffEntryMirror>) {
        let mut files = Vec::new();
        let mut entries = Vec::new();
        let out = Command::new("git")
            .args(["diff", "--name-status", &format!("{start}..{end}")])
            .current_dir(&self.root)
            .output();
        let Ok(out) = out else {
            return (files, entries);
        };
        if !out.status.success() {
            return (files, entries);
        }
        for line in String::from_utf8_lossy(&out.stdout).lines() {
            let mut it = line.split('\t');
            let action = it.next().unwrap_or("").to_string();
            let path = it.next().unwrap_or("").to_string();
            if path.is_empty() {
                continue;
            }
            files.push(path.clone());
            entries.push(DiffEntryMirror { action, path });
        }
        (files, entries)
    }
}

impl FinishBackend for NativeFinishBackend {
    fn get_active_session_id(&mut self) -> Result<Option<String>, String> {
        Ok(self.service().get_active().map(|r| r.session_id))
    }

    fn get_session_status(&mut self, session_id: &str) -> Result<String, String> {
        Ok(self.service().get(session_id)?.status.as_str().to_string())
    }

    fn reconstruct(
        &mut self,
        session_id: &str,
        run_hooks: bool,
    ) -> Result<ReconstructionMirror, String> {
        let service = self.service();
        let mut record = service.get(session_id)?;
        let gitless = record.is_gitless();

        // Hooks declarados en el spec: se RE-EJECUTAN con el runner nativo
        // (run_hooks=true) y se persisten en el record — como el oráculo.
        if run_hooks && record.status == cortex_app::session::SessionStatus::Open {
            let hooks = self.spec_hooks(&record)?;
            if !hooks.is_empty() {
                let runner =
                    cortex_app::session::verification::VerificationRunner::new(self.root.clone());
                let results = runner.run_all(&hooks);
                record.verification_results = results
                    .into_iter()
                    .map(|r| cortex_app::session::VerificationHookResult {
                        name: r.name,
                        command: r.command,
                        passed: r.passed,
                        exit_code: r.exit_code,
                        output: r.output,
                        duration_ms: r.duration_ms,
                        run_at: r.run_at,
                    })
                    .collect();
                let _ = service.storage.save(&record);
            }
        }
        let end = record
            .end_commit
            .clone()
            .unwrap_or_else(|| self.head_commit());

        // Spec info (frontmatter del spec).
        let spec_path = PathBuf::from(&record.spec_path);
        let spec_info = SpecInfoMirror {
            path: record.spec_path.clone(),
            title: record.spec_summary.clone(),
            goal: String::new(),
            files_in_scope: Vec::new(),
            constraints: Vec::new(),
            acceptance_criteria: Vec::new(),
            verification_hooks: Vec::new(),
        };
        let _ = spec_path;

        // Diff real (port compute_diff) + archivos tocados.
        let diff_text = service.compute_diff(session_id).unwrap_or_default();
        let (files_touched, diff_entries) = if gitless {
            (Vec::new(), Vec::new())
        } else {
            let start = record.start_commit.clone();
            self.name_status(&start, &end)
        };

        // Verificación existente (run_hooks: re-ejecución pendiente P12).
        let verification_results: Vec<VerifResultMirror> = record
            .verification_results
            .iter()
            .map(|v| VerifResultMirror {
                name: v.name.clone(),
                command: v.command.clone(),
                passed: v.passed,
                exit_code: v.exit_code as i64,
                output: v.output.clone(),
                duration_ms: v.duration_ms as i64,
                run_at: v.run_at.clone(),
            })
            .collect();

        let any_failed = verification_results.iter().any(|v| !v.passed);
        let no_verif_ok = verification_results.is_empty() && !record.checkpoints.is_empty();
        let suggested_status = if any_failed || no_verif_ok {
            "handoff".to_string()
        } else {
            "closed".to_string()
        };

        Ok(ReconstructionMirror {
            session_id: record.session_id.clone(),
            spec: spec_info,
            diff_text,
            diff_entries,
            files_touched,
            files_verified_by_git: Vec::new(),
            files_declared_only: Vec::new(),
            in_scope_files: Vec::new(),
            out_of_scope_files: Vec::new(),
            unimplemented_files: Vec::new(),
            verification_results,
            contradictions: Vec::<ContradictionMirror>::new(),
            suggested_status,
            suggested_adrs: Vec::<AdrSuggestionMirror>::new(),
            raw_checkpoints: record
                .checkpoints
                .iter()
                .map(|c| RawCheckpointMirror {
                    timestamp: c.timestamp.clone(),
                    source: source_str(&c.source),
                    verified_claims: c.verified_claims.clone(),
                    unverified_claims: c.unverified_claims.clone(),
                    artifacts_touched: c.artifacts_touched.clone(),
                    note: c.note.clone(),
                })
                .collect(),
            end_commit: end,
            gitless,
        })
    }

    fn finalize(
        &mut self,
        session_id: &str,
        forced_status: Option<&str>,
    ) -> Result<FinishResultMirror, String> {
        let service = self.service();
        let record = service.get(session_id)?;
        let already_closed = record.status != SessionStatus::Open;
        if already_closed {
            return Ok(FinishResultMirror {
                session_id: record.session_id.clone(),
                final_status: record.status.as_str().to_string(),
                session_note_path: record.session_note_path.clone(),
                adrs_created: record.adrs_created.clone(),
                summary_text: record.spec_summary.clone(),
                already_closed: true,
            });
        }

        let status = match forced_status {
            Some(s) => {
                let s = s.to_string();
                match s.as_str() {
                    "closed" => SessionStatus::Closed,
                    "handoff" => SessionStatus::Handoff,
                    "abandoned" => SessionStatus::Abandoned,
                    _ => SessionStatus::Closed,
                }
            }
            None => SessionStatus::Closed,
        };

        // Nota de sesión (vault/session-notes) — escritura real y simple.
        let note_path = self.write_session_note(&record)?;
        let record = service.close(session_id, status, status, note_path.clone(), Vec::new())?;

        Ok(FinishResultMirror {
            session_id: record.session_id.clone(),
            final_status: status.as_str().to_string(),
            session_note_path: note_path,
            adrs_created: record.adrs_created.clone(),
            summary_text: record.spec_summary.clone(),
            already_closed: false,
        })
    }
}

impl NativeFinishBackend {
    /// Hooks del frontmatter del spec (`verification_hooks:` con
    /// name/command/required) — espejo del parser del oráculo.
    fn spec_hooks(
        &self,
        record: &cortex_app::session::SessionRecord,
    ) -> Result<Vec<cortex_app::session::VerificationHook>, String> {
        let text = std::fs::read_to_string(&record.spec_path)
            .or_else(|_| std::fs::read_to_string(self.root.join(&record.spec_path)))
            .map_err(|e| format!("spec: {e}"))?;
        let Some(fm) = crate::backends::sessions::frontmatter(&text) else {
            return Ok(Vec::new());
        };
        let Ok(v) = serde_yaml::from_str::<serde_yaml::Value>(fm) else {
            return Ok(Vec::new());
        };
        let Some(hooks) = v.get("verification_hooks").and_then(|h| h.as_sequence()) else {
            return Ok(Vec::new());
        };
        let mut out = Vec::new();
        for h in hooks {
            let name = h
                .get("name")
                .and_then(|x| x.as_str())
                .unwrap_or("hook")
                .to_string();
            let command = h
                .get("command")
                .and_then(|x| x.as_str())
                .unwrap_or("true")
                .to_string();
            let required = h.get("required").and_then(|x| x.as_bool()).unwrap_or(true);
            let timeout_seconds = h
                .get("timeout_seconds")
                .and_then(|x| x.as_u64())
                .unwrap_or(300);
            out.push(cortex_app::session::VerificationHook {
                name,
                command,
                required,
                success_criteria: "exit code 0".into(),
                timeout_seconds,
            });
        }
        Ok(out)
    }

    /// Nota breve de cierre en `vault/session-notes/{id}.md`.
    fn write_session_note(
        &self,
        record: &cortex_app::session::SessionRecord,
    ) -> Result<Option<String>, String> {
        let dir = self
            .root
            .join(".cortex")
            .join("vault")
            .join("session-notes");
        std::fs::create_dir_all(&dir).map_err(|e| format!("session note: {e}"))?;
        let path = dir.join(format!("{}.md", record.session_id));
        let body = format!(
            "---\ntitle: {}\nspec_summary: \"{}\"\n---\n\n# {}\n\n{}\n",
            record.session_id, record.spec_summary, record.session_id, record.spec_summary,
        );
        std::fs::write(&path, body).map_err(|e| format!("session note: {e}"))?;
        Ok(Some(path.display().to_string()))
    }
}

fn source_str(s: &cortex_app::session::CheckpointSource) -> String {
    match s {
        cortex_app::session::CheckpointSource::CortexSync => "cortex-sync",
        cortex_app::session::CheckpointSource::CortexSddwork => "cortex-SDDwork",
        cortex_app::session::CheckpointSource::CortexCodeExplorer => "cortex-code-explorer",
        cortex_app::session::CheckpointSource::CortexCodeImplementer => "cortex-code-implementer",
        cortex_app::session::CheckpointSource::CortexCodeDesigner => "cortex-code-designer",
        cortex_app::session::CheckpointSource::UserSkill => "user-skill",
        cortex_app::session::CheckpointSource::IdeHook => "ide-hook",
        cortex_app::session::CheckpointSource::Manual => "manual",
        cortex_app::session::CheckpointSource::CiBot => "ci-bot",
    }
    .to_string()
}
