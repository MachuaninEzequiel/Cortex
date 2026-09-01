//! Backend nativo de la familia AUTOPILOT (AutopilotBackend) sobre
//! `cortex-autopilot::AutopilotService` (capa de decisión nativa): el
//! servicio ya orquesta session + políticas; este backend traduce
//! outcomes → mirrors de los handlers.

use crate::handlers_autopilot::{
    AutopilotBackend, AutopilotToolError, CheckpointData, FinishData, PreflightData, StartData,
    StatusData,
};
use cortex_autopilot::policies::AutopilotMode;
use cortex_autopilot::service::AutopilotService;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

/// Backend de producción: servicio autopilot lazy por proyecto.
pub struct NativeAutopilotBackend {
    root: PathBuf,
    service: Mutex<Option<AutopilotService>>,
}

impl NativeAutopilotBackend {
    pub fn new(root: &Path) -> Self {
        Self {
            root: root.to_path_buf(),
            service: Mutex::new(None),
        }
    }

    fn err(msg: impl Into<String>) -> AutopilotToolError {
        AutopilotToolError::Other {
            kind: "AutopilotServiceError".into(),
            message: msg.into(),
        }
    }

    fn svc(
        &self,
    ) -> Result<std::sync::MutexGuard<'_, Option<AutopilotService>>, AutopilotToolError> {
        self.service
            .lock()
            .map_err(|_| Self::err("poisoned autopilot state"))
    }

    fn ensure<'a>(
        guard: &'a mut Option<AutopilotService>,
        root: &Path,
    ) -> Result<&'a mut AutopilotService, AutopilotToolError> {
        if guard.is_none() {
            *guard = Some(
                AutopilotService::from_project_root(root, None)
                    .map_err(|e| Self::err(e.to_string()))?,
            );
        }
        Ok(guard.as_mut().expect("just initialized"))
    }
}

fn parse_mode(m: &str) -> Result<AutopilotMode, AutopilotToolError> {
    match m {
        "assist" => Ok(AutopilotMode::Assist),
        "auto" | "autopilot" => Ok(AutopilotMode::Autopilot),
        "observe" => Ok(AutopilotMode::Observe),
        other => Err(AutopilotToolError::Other {
            kind: "ValueError".into(),
            message: format!("Invalid mode '{other}'. Must be one of: assist, auto, interactive"),
        }),
    }
}

impl AutopilotBackend for NativeAutopilotBackend {
    fn start(&mut self, mode: Option<&str>) -> Result<StartData, AutopilotToolError> {
        let mut guard = self.svc()?;
        let svc = Self::ensure(&mut guard, &self.root)?;
        let parsed = mode.map(parse_mode).transpose()?;
        let outcome = svc.start(parsed).map_err(|e| Self::err(e.to_string()))?;
        Ok(StartData {
            session_id: outcome.session.session_id.clone(),
            mode: mode_to_str(&outcome.session.mode),
            status: outcome.session.status.as_str().to_string(),
            warnings: outcome.warnings,
        })
    }

    fn preflight(
        &mut self,
        user_request: Option<&str>,
        changed_files: &[String],
        git_diff_stat: Option<&str>,
    ) -> Result<PreflightData, AutopilotToolError> {
        let mut guard = self.svc()?;
        let svc = Self::ensure(&mut guard, &self.root)?;
        let outcome = svc.preflight(user_request, changed_files, git_diff_stat);
        Ok(PreflightData {
            task_type: outcome.detection.task_type.clone(),
            confidence: outcome.detection.confidence,
            reason: outcome.detection.reason.clone(),
            suggested_complexity: outcome.detection.suggested_complexity.clone(),
        })
    }

    fn checkpoint(
        &mut self,
        source: &str,
        verified_claims: Vec<String>,
        unverified_claims: Vec<String>,
        artifacts_touched: Vec<String>,
        note: &str,
        files_in_scope: Option<Vec<String>>,
    ) -> Result<CheckpointData, AutopilotToolError> {
        let mut guard = self.svc()?;
        let svc = Self::ensure(&mut guard, &self.root)?;
        let outcome = svc
            .checkpoint(
                source,
                verified_claims,
                unverified_claims,
                artifacts_touched,
                note,
                files_in_scope,
            )
            .map_err(|e| Self::err(e.to_string()))?;
        Ok(CheckpointData {
            session_id: outcome.session.session_id.clone(),
            total_checkpoints: outcome.session.checkpoints.len(),
            status: outcome.session.status.as_str().to_string(),
            warnings: outcome.warnings,
        })
    }

    fn finish(
        &mut self,
        session_id: Option<&str>,
        auto: bool,
        intent: &str,
        reason: &str,
    ) -> Result<FinishData, AutopilotToolError> {
        let mut guard = self.svc()?;
        let svc = Self::ensure(&mut guard, &self.root)?;
        // El service nativo no recibe `reason` (firma del oráculo 3 args);
        // el reason queda en el intent/estado.
        let _ = reason;
        let outcome = svc
            .finish(session_id, auto, intent)
            .map_err(|e| Self::err(e.to_string()))?;
        Ok(FinishData {
            session_id: outcome.session.session_id.clone(),
            status: outcome.session.status.as_str().to_string(),
            documented: outcome.documented,
            blocked: outcome.blocked,
            blocked_reason: outcome.blocked_reason,
            session_note_path: outcome.session_note_path,
            warnings: outcome.warnings,
        })
    }

    fn status(&mut self, session_id: Option<&str>) -> Result<StatusData, AutopilotToolError> {
        let mut guard = self.svc()?;
        let svc = Self::ensure(&mut guard, &self.root)?;
        let outcome = svc
            .status(session_id)
            .map_err(|e| Self::err(e.to_string()))?;
        Ok(StatusData {
            active: outcome.active,
            session_id: outcome
                .session
                .as_ref()
                .map(|s| s.session_id.clone())
                .unwrap_or_default(),
            status: outcome
                .session
                .as_ref()
                .map(|s| s.status.as_str().to_string())
                .unwrap_or_default(),
            mode: outcome.session.as_ref().map(|s| mode_to_str(&s.mode)),
            inferred_mode: outcome
                .inferred_mode
                .unwrap_or_else(|| "unknown".to_string()),
            checkpoint_count: outcome.checkpoint_count,
            start_branch: outcome
                .session
                .as_ref()
                .map(|s| s.start_branch.clone())
                .unwrap_or_default(),
        })
    }
}

fn mode_to_str(m: &cortex_app::session::SessionMode) -> String {
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
