//! Puerto de `cortex.autopilot.service` — `AutopilotService` (Cierre T3).
//!
//! Orquestador delgado que cablea:
//! - [`cortex_app::session::service::SessionService`] NATIVO para el ciclo
//!   de vida (el `SessionRecord` es el estado canónico),
//! - la capa de decisión P12B-5 ([`crate::policies`] + [`crate::detectors`])
//!   para warnings/bloqueos en los hooks y el dry-run *preflight*,
//! - un backend opcional [`DocumenterFinalize`] para `finish(auto=True)`
//!   (equivalente del `memory_factory` perezoso del oráculo; sin él el
//!   cierre automático devuelve fallo EXPLÍCITO con el mensaje exacto).
//!
//! El servicio NO abre sesiones: `start` ADOPTA la sesión activa
//! (`cortex create-spec` es quien la crea).

use std::path::{Path, PathBuf};
use std::sync::Arc;

use cortex_app::session::service::SessionService;
use cortex_app::session::{
    infer_mode, Checkpoint as NativeCheckpoint, CheckpointSource, SessionRecord, SessionStatus,
    SessionStorage,
};

use crate::detectors::{default_detectors, resolve_detectors, AutopilotDetector};
use crate::models::DetectionRequest;
use crate::policies::{AutopilotMode, AutopilotPolicy, EnforcementSeverity, PolicyEnforcer};
use crate::session_models as decision;

// ── Errores ──────────────────────────────────────────────────────────────────

/// Excepciones del módulo autopilot relevantes para la paridad de mensajes:
/// `NoActiveSessionError`, `AutopilotError` genérico y
/// `cortex.session.errors.SessionNotFound`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ServiceError {
    NoActiveSession(String),
    Autopilot(String),
    SessionNotFound(String),
}

impl std::fmt::Display for ServiceError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NoActiveSession(m) | Self::Autopilot(m) | Self::SessionNotFound(m) => {
                f.write_str(m)
            }
        }
    }
}
impl std::error::Error for ServiceError {}

const NO_ACTIVE_SESSION_MSG: &str =
    "No active session. Run `cortex create-spec` first to open one.";

// ── Backend documenter (finish auto) ────────────────────────────────────────

/// Resultado de `DocumenterPersister.finalize(out, overrides)`.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct FinalizeOutcome {
    pub already_closed: bool,
    pub session_note_path: Option<String>,
    pub adrs_created: Vec<String>,
    pub summary: String,
}

/// Puerto del pipeline documenter canónico (`Reconstructor` +
/// `DocumenterPersister.finalize`). Producción: cortex-app::documenter +
/// NoteService; gates: stubs deterministas.
pub trait DocumenterFinalize: Send {
    fn finalize(
        &mut self,
        session_id: &str,
        forced_status: Option<&str>,
    ) -> Result<FinalizeOutcome, String>;
}

// ── Outcomes ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct StartOutcome {
    pub session: SessionRecord,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct PreflightOutcome {
    pub detection: crate::models::DetectionResult,
}

#[derive(Debug, Clone)]
pub struct CheckpointOutcome {
    pub session: SessionRecord,
    pub checkpoint: NativeCheckpoint,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct FinishOutcome {
    pub session: SessionRecord,
    pub documented: bool,
    pub blocked: bool,
    pub blocked_reason: String,
    pub session_note_path: Option<String>,
    pub adrs_created: Vec<String>,
    pub summary: String,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct StatusOutcome {
    pub active: bool,
    pub session: Option<SessionRecord>,
    pub checkpoint_count: usize,
    /// `SessionMode.value` inferido (None cuando no hay sesión activa).
    pub inferred_mode: Option<String>,
}

// ── Servicio ─────────────────────────────────────────────────────────────────

pub struct AutopilotService {
    sessions: SessionService,
    policy: AutopilotPolicy,
    enforcer: PolicyEnforcer,
    repo_root: PathBuf,
    finisher: Option<Box<dyn DocumenterFinalize + Send>>,
    detectors: Vec<Box<dyn AutopilotDetector + Send>>,
}

impl AutopilotService {
    /// Cableo completo inyectable (espejo de `__init__`; `detectors` usa
    /// siempre el set default — ningún gate inyecta otros).
    pub fn new(
        sessions: SessionService,
        policy: AutopilotPolicy,
        repo_root: &Path,
        finisher: Option<Box<dyn DocumenterFinalize + Send>>,
    ) -> Self {
        Self {
            sessions,
            enforcer: PolicyEnforcer::new(policy.clone()),
            policy,
            repo_root: repo_root.to_path_buf(),
            finisher,
            detectors: default_detectors(),
        }
    }

    /// `from_project_root`: layout descubierto + storage nativo +
    /// policy desde `autopilot.yaml` (+ backend documenter inyectable).
    pub fn from_project_root(
        project_root: &Path,
        finisher: Option<Box<dyn DocumenterFinalize + Send>>,
    ) -> Result<Self, crate::config::ConfigError> {
        let layout = cortex_workspace::WorkspaceLayout::discover(project_root);
        let storage = SessionStorage::new(layout.repo_root.join(".cortex").join("sessions"));
        let session_service = SessionService::new(storage, &layout.repo_root);
        let cfg = crate::config::load_autopilot_config(&layout)?;
        let clock: Arc<dyn cortex_enterprise::clock::Clock> =
            Arc::new(cortex_enterprise::clock::SystemClock);
        let resolved_policy = AutopilotPolicy::from_config(&cfg, clock)
            .map_err(|e| crate::config::ConfigError(e.to_string()))?;
        Ok(Self::new(
            session_service,
            resolved_policy,
            &layout.repo_root,
            finisher,
        ))
    }

    // ── Properties ───────────────────────────────────────────────

    pub fn policy(&self) -> &AutopilotPolicy {
        &self.policy
    }

    pub fn session_service(&self) -> &SessionService {
        &self.sessions
    }

    pub fn repo_root(&self) -> &Path {
        &self.repo_root
    }

    // ── start ────────────────────────────────────────────────────

    /// Adoptar la sesión activa bajo el modo (opcionalmente sobrescrito).
    ///
    /// `Err(ServiceError::NoActiveSession)` si no hay sesión activa.
    pub fn start(&mut self, mode: Option<AutopilotMode>) -> Result<StartOutcome, ServiceError> {
        let active = self.require_active()?;

        if let Some(m) = mode {
            if m != self.policy.mode {
                self.policy = policy_with_mode(&self.policy, m);
                self.enforcer = PolicyEnforcer::new(self.policy.clone());
            }
        }

        let dec_active = to_decision_record(&active);
        let results = self.enforcer.on_session_open(&dec_active, None);
        Ok(StartOutcome {
            session: active,
            warnings: warnings_of(&results),
        })
    }

    // ── preflight (dry-run de detectors, sin mutación) ───────────

    pub fn preflight(
        &self,
        user_request: Option<&str>,
        changed_files: &[String],
        git_diff_stat: Option<&str>,
    ) -> PreflightOutcome {
        let detection = resolve_detectors(
            &self.detectors,
            &DetectionRequest {
                user_request: user_request.map(str::to_string),
                changed_files: changed_files.to_vec(),
                git_diff_stat: git_diff_stat.map(str::to_string),
                session_state: None,
            },
        );
        PreflightOutcome { detection }
    }

    // ── checkpoint ───────────────────────────────────────────────

    #[allow(clippy::too_many_arguments)]
    pub fn checkpoint(
        &mut self,
        source: &str,
        verified_claims: Vec<String>,
        unverified_claims: Vec<String>,
        artifacts_touched: Vec<String>,
        note: &str,
        files_in_scope: Option<Vec<String>>,
    ) -> Result<CheckpointOutcome, ServiceError> {
        let active = self.require_active()?;
        let parsed_source = parse_checkpoint_source(source).ok_or_else(|| {
            ServiceError::Autopilot(format!(
                "unknown checkpoint source {}; valid: {}",
                py_repr(source),
                VALID_SOURCES.join(", ")
            ))
        })?;

        let record = self
            .sessions
            .checkpoint(
                &active.session_id,
                parsed_source,
                verified_claims,
                unverified_claims,
                artifacts_touched,
                note,
                None, // autopilot no emite fase COMPOSED
            )
            .map_err(ServiceError::Autopilot)?;
        let new_checkpoint = record
            .checkpoints
            .last()
            .cloned()
            .expect("checkpoint recién agregado");

        let dec_record = to_decision_record(&record);
        let dec_checkpoint = dec_record
            .checkpoints
            .last()
            .cloned()
            .expect("checkpoint espejado");
        let results =
            self.enforcer
                .on_checkpoint(&dec_record, &dec_checkpoint, files_in_scope.as_deref());
        Ok(CheckpointOutcome {
            session: record,
            checkpoint: new_checkpoint,
            warnings: warnings_of(&results),
        })
    }

    // ── finish ───────────────────────────────────────────────────

    pub fn finish(
        &mut self,
        session_id: Option<&str>,
        auto: bool,
        intent: &str,
    ) -> Result<FinishOutcome, ServiceError> {
        let session = self.resolve_target_session(session_id)?;
        if session.status != SessionStatus::Open {
            let summary = format!(
                "session already in status {}; no-op",
                session.status.as_str()
            );
            return Ok(FinishOutcome {
                session,
                documented: false,
                blocked: false,
                blocked_reason: String::new(),
                session_note_path: None,
                adrs_created: vec![],
                summary,
                warnings: vec![],
            });
        }

        let pre = self.enforcer.on_pre_close(&to_decision_record(&session));
        let blocks: Vec<&crate::policies::EnforcementResult> = pre
            .iter()
            .filter(|r| r.severity == EnforcementSeverity::Block)
            .collect();
        if !blocks.is_empty() {
            let warnings = warnings_of(&pre);
            return Ok(FinishOutcome {
                session,
                documented: false,
                blocked: true,
                blocked_reason: blocks[0].reason.clone(),
                session_note_path: None,
                adrs_created: vec![],
                summary: String::new(),
                warnings,
            });
        }

        let warnings = warnings_of(&pre);
        if auto {
            self.finish_auto(&session, intent, warnings)
        } else {
            self.finish_manual(&session, intent, warnings)
        }
    }

    // ── status ───────────────────────────────────────────────────

    pub fn status(&mut self, session_id: Option<&str>) -> Result<StatusOutcome, ServiceError> {
        let found = match session_id {
            None => self.sessions.get_active(),
            Some(sid) => self.sessions.get(sid).ok(),
        };

        let Some(session) = found else {
            return Ok(StatusOutcome {
                active: false,
                session: None,
                checkpoint_count: 0,
                inferred_mode: None,
            });
        };

        let inferred = infer_mode(&session.checkpoints);
        Ok(StatusOutcome {
            active: true,
            checkpoint_count: session.checkpoints.len(),
            inferred_mode: Some(mode_value(inferred).to_string()),
            session: Some(session),
        })
    }

    // ── Internos ─────────────────────────────────────────────────

    fn require_active(&self) -> Result<SessionRecord, ServiceError> {
        self.sessions
            .get_active()
            .ok_or_else(|| ServiceError::NoActiveSession(NO_ACTIVE_SESSION_MSG.to_string()))
    }

    fn resolve_target_session(
        &self,
        session_id: Option<&str>,
    ) -> Result<SessionRecord, ServiceError> {
        match session_id {
            None => self.require_active(),
            Some(sid) => self.sessions.get(sid).map_err(|_| {
                ServiceError::Autopilot(format!("session {} not found", py_repr(sid)))
            }),
        }
    }

    /// Cerrar SIN invocar el documenter.
    fn finish_manual(
        &mut self,
        session: &SessionRecord,
        intent: &str,
        warnings: Vec<String>,
    ) -> Result<FinishOutcome, ServiceError> {
        let status = intent_to_status(intent);
        let updated = self
            .sessions
            .close(&session.session_id, status, status, None, vec![])
            .map_err(ServiceError::Autopilot)?;
        Ok(FinishOutcome {
            summary: format!("closed without documenting ({})", status.as_str()),
            session: updated,
            documented: false,
            blocked: false,
            blocked_reason: String::new(),
            session_note_path: None,
            adrs_created: vec![],
            warnings,
        })
    }

    /// Cierre vía pipeline documenter canónico.
    fn finish_auto(
        &mut self,
        session: &SessionRecord,
        intent: &str,
        warnings: Vec<String>,
    ) -> Result<FinishOutcome, ServiceError> {
        let forced = intent_to_forced_status(intent);
        let outcome = match self.finisher.as_mut() {
            None => {
                return Err(ServiceError::Autopilot(
                    "finish(auto=True) requires a memory_factory to invoke the documenter; \
                     either inject one or use finish(auto=False)."
                        .to_string(),
                ));
            }
            Some(f) => f
                .finalize(&session.session_id, forced)
                .map_err(ServiceError::Autopilot)?,
        };

        // Recargar la sesión para capturar el estado ya cerrado.
        let refreshed = self
            .sessions
            .get(&session.session_id)
            .map_err(ServiceError::Autopilot)?;
        Ok(FinishOutcome {
            session: refreshed,
            documented: !outcome.already_closed,
            session_note_path: outcome.session_note_path,
            adrs_created: outcome.adrs_created,
            summary: outcome.summary,
            blocked: false,
            blocked_reason: String::new(),
            warnings,
        })
    }
}

// ── Helpers de módulo ────────────────────────────────────────────────────────

/// Valores de `CheckpointSource` en el orden del enum Python (mensaje
/// "valid:" del error contractual).
pub const VALID_SOURCES: &[&str] = &[
    "cortex-sync",
    "cortex-SDDwork",
    "cortex-code-explorer",
    "cortex-code-implementer",
    "cortex-code-designer",
    "user-skill",
    "ide-hook",
    "manual",
    "ci-bot",
];

fn parse_checkpoint_source(raw: &str) -> Option<CheckpointSource> {
    Some(match raw {
        "cortex-sync" => CheckpointSource::CortexSync,
        "cortex-SDDwork" => CheckpointSource::CortexSddwork,
        "cortex-code-explorer" => CheckpointSource::CortexCodeExplorer,
        "cortex-code-implementer" => CheckpointSource::CortexCodeImplementer,
        "cortex-code-designer" => CheckpointSource::CortexCodeDesigner,
        "user-skill" => CheckpointSource::UserSkill,
        "ide-hook" => CheckpointSource::IdeHook,
        "manual" => CheckpointSource::Manual,
        "ci-bot" => CheckpointSource::CiBot,
        _ => return None,
    })
}

fn warnings_of(results: &[crate::policies::EnforcementResult]) -> Vec<String> {
    results
        .iter()
        .filter(|r| r.severity == EnforcementSeverity::Warn)
        .map(|r| r.reason.clone())
        .collect()
}

/// Copia de la policy con el modo reemplazado (flags consistentes con el
/// modo nuevo: OBSERVE apaga warnings; AUTOPILOT prende pre-commit).
fn policy_with_mode(policy: &AutopilotPolicy, mode: AutopilotMode) -> AutopilotPolicy {
    let is_observe = mode == AutopilotMode::Observe;
    let mut p = AutopilotPolicy::new(
        mode,
        policy.budget_profile.clone(),
        mode == AutopilotMode::Autopilot,
        !is_observe,
        policy.auto_checkpoint_threshold_files,
        policy.auto_checkpoint_threshold_minutes,
        Arc::new(cortex_enterprise::clock::SystemClock),
    )
    .expect("policy ya validada");
    p.warn_on_security_summary = !is_observe;
    p
}

/// `intent` → `SessionStatus` terminal.
fn intent_to_status(intent: &str) -> SessionStatus {
    let normalized = intent.trim().to_lowercase();
    match normalized.as_str() {
        "handoff" => SessionStatus::Handoff,
        "abandoned" | "abandon" => SessionStatus::Abandoned,
        _ => SessionStatus::Closed,
    }
}

/// `intent` → override de status para el documenter (`None` = decidir solo).
fn intent_to_forced_status(intent: &str) -> Option<&'static str> {
    let normalized = intent.trim().to_lowercase();
    match normalized.as_str() {
        "handoff" => Some("handoff"),
        "abandoned" | "abandon" => Some("abandoned"),
        _ => None,
    }
}

/// `str(SessionMode)` del oráculo ("ci-review" incluido).
fn mode_value(mode: cortex_app::session::SessionMode) -> &'static str {
    match mode {
        cortex_app::session::SessionMode::Unknown => "unknown",
        cortex_app::session::SessionMode::Managed => "managed",
        cortex_app::session::SessionMode::Observed => "observed",
        cortex_app::session::SessionMode::Byo => "byo",
        cortex_app::session::SessionMode::Composed => "composed",
        cortex_app::session::SessionMode::CiReview => "ci-review",
    }
}

/// `repr(str)` de Python (comillas simples por defecto).
pub(crate) fn py_repr(s: &str) -> String {
    if s.contains('\'') && !s.contains('"') {
        format!("\"{}\"", s.replace('\\', "\\\\").replace('"', "\\\""))
    } else {
        format!("'{}'", s.replace('\\', "\\\\").replace('\'', "\\'"))
    }
}

// ── Puente native → decisión (P12B-5 consume sus propios tipos) ─────────────

fn parse_ts(iso: &str) -> chrono::DateTime<chrono::Utc> {
    chrono::DateTime::parse_from_rfc3339(iso)
        .map(|dt| dt.with_timezone(&chrono::Utc))
        .unwrap_or_else(|_| chrono::Utc::now())
}

fn to_decision_status(s: SessionStatus) -> decision::SessionStatus {
    match s {
        SessionStatus::Open => decision::SessionStatus::Open,
        SessionStatus::Closed => decision::SessionStatus::Closed,
        SessionStatus::Handoff => decision::SessionStatus::Handoff,
        SessionStatus::Abandoned => decision::SessionStatus::Abandoned,
    }
}

fn to_decision_checkpoint(cp: &NativeCheckpoint) -> decision::Checkpoint {
    decision::Checkpoint {
        timestamp: parse_ts(&cp.timestamp),
        source: match cp.source {
            CheckpointSource::CortexSync => decision::CheckpointSource::CortexSync,
            CheckpointSource::CortexSddwork => decision::CheckpointSource::CortexSddwork,
            CheckpointSource::CortexCodeExplorer => decision::CheckpointSource::CortexCodeExplorer,
            CheckpointSource::CortexCodeImplementer => {
                decision::CheckpointSource::CortexCodeImplementer
            }
            CheckpointSource::CortexCodeDesigner => decision::CheckpointSource::CortexCodeDesigner,
            CheckpointSource::UserSkill => decision::CheckpointSource::UserSkill,
            CheckpointSource::IdeHook => decision::CheckpointSource::IdeHook,
            CheckpointSource::Manual => decision::CheckpointSource::Manual,
            CheckpointSource::CiBot => decision::CheckpointSource::CiBot,
        },
        verified_claims: cp.verified_claims.clone(),
        unverified_claims: cp.unverified_claims.clone(),
        artifacts_touched: cp.artifacts_touched.clone(),
        note: cp.note.clone(),
    }
}

/// Espejo fiel del record nativo en los tipos mínimos de la capa de
/// decisión (solo campos consumidos por policies/lifecycle).
pub fn to_decision_record(r: &SessionRecord) -> decision::SessionRecord {
    decision::SessionRecord {
        session_id: r.session_id.clone(),
        spec_path: r.spec_path.clone(),
        spec_summary: r.spec_summary.clone(),
        start_commit: r.start_commit.clone(),
        start_branch: r.start_branch.clone(),
        opened_at: parse_ts(&r.opened_at),
        status: to_decision_status(r.status),
        checkpoints: r.checkpoints.iter().map(to_decision_checkpoint).collect(),
        closed_at: r.closed_at.as_deref().map(parse_ts),
        end_commit: r.end_commit.clone(),
    }
}
