//! Puerto de `cortex.autopilot.policies`: modo, policy inmutable y enforcer
//! de lifecycle hooks. Todos los mensajes contractuales se replican.

use std::sync::Arc;

use chrono::{DateTime, Utc};

use cortex_enterprise::clock::Clock;
use cortex_enterprise::error::EnterpriseError;

use crate::config::AutopilotConfig;
use crate::session_models::{Checkpoint, SessionRecord, SessionStatus};

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AutopilotMode {
    Observe,
    Assist,
    Autopilot,
}

impl AutopilotMode {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Observe => "observe",
            Self::Assist => "assist",
            Self::Autopilot => "autopilot",
        }
    }
    fn parse(s: &str) -> Option<Self> {
        match s {
            "observe" => Some(Self::Observe),
            "assist" => Some(Self::Assist),
            "autopilot" => Some(Self::Autopilot),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EnforcementSeverity {
    Proceed,
    Warn,
    Block,
}

impl PartialEq<&str> for EnforcementSeverity {
    fn eq(&self, other: &&str) -> bool {
        matches!(
            (self, *other),
            (Self::Proceed, "proceed") | (Self::Warn, "warn") | (Self::Block, "block")
        )
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct EnforcementResult {
    pub severity: EnforcementSeverity,
    pub reason: String,
}

impl EnforcementResult {
    pub fn allowed(&self) -> bool {
        self.severity != EnforcementSeverity::Block
    }
    pub fn proceed() -> Self {
        Self {
            severity: EnforcementSeverity::Proceed,
            reason: String::new(),
        }
    }
    pub fn warn(reason: impl Into<String>) -> Self {
        Self {
            severity: EnforcementSeverity::Warn,
            reason: reason.into(),
        }
    }
    pub fn block(reason: impl Into<String>) -> Self {
        Self {
            severity: EnforcementSeverity::Block,
            reason: reason.into(),
        }
    }
}

pub const DEFAULT_BUDGET_PROFILE: &str = "fast_code";
pub const KNOWN_BUDGET_PROFILES: &[&str] = &[
    "question_only",
    "docs_only",
    "fast_code",
    "deep_code",
    "finish_only",
];

const SECURITY_KEYWORD_PATTERN_WORDS: &[&str] = &[
    "password",
    "secret",
    "token",
    "jwt",
    "oauth",
    "auth",
    "login",
    "permission",
    "role",
    "rbac",
    "acl",
    "crypto",
    "encrypt",
    "decrypt",
    "hash",
    "salt",
];

fn looks_security_sensitive(text: &str) -> bool {
    if text.is_empty() {
        return false;
    }
    // \b(palabra)\b case-insensitive — replica el regex de Python.
    let lower = format!(" {text} ").to_lowercase();
    for kw in SECURITY_KEYWORD_PATTERN_WORDS {
        let mut from = 0usize;
        while let Some(pos) = lower[from..].find(kw) {
            let start = from + pos;
            let end = start + kw.len();
            let before = lower[..start].chars().next_back();
            let after = lower[end..].chars().next();
            let boundary_before = before
                .map(|c| !(c.is_alphanumeric() || c == '_'))
                .unwrap_or(true);
            let boundary_after = after
                .map(|c| !(c.is_alphanumeric() || c == '_'))
                .unwrap_or(true);
            if boundary_before && boundary_after {
                return true;
            }
            from = start + 1;
        }
    }
    false
}

fn has_verified_checkpoint(session: &SessionRecord) -> bool {
    session
        .checkpoints
        .iter()
        .any(|cp| !cp.verified_claims.is_empty())
}

fn files_since_last_verified(session: &SessionRecord) -> usize {
    let mut touched = std::collections::BTreeSet::new();
    for cp in session.checkpoints.iter().rev() {
        if !cp.verified_claims.is_empty() {
            break;
        }
        touched.extend(cp.artifacts_touched.iter().cloned());
    }
    touched.len()
}

#[derive(Debug, Clone)]
pub struct AutopilotPolicy {
    pub mode: AutopilotMode,
    pub budget_profile: String,
    pub pre_commit_verification: bool,
    pub out_of_scope_warning: bool,
    pub auto_checkpoint_threshold_files: i64,
    pub auto_checkpoint_threshold_minutes: i64,
    pub warn_on_security_summary: bool,
}

impl AutopilotPolicy {
    /// Construcción directa con validaciones de `__post_init__`.
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        mode: AutopilotMode,
        budget_profile: String,
        pre_commit_verification: bool,
        out_of_scope_warning: bool,
        auto_checkpoint_threshold_files: i64,
        auto_checkpoint_threshold_minutes: i64,
        _clock: Arc<dyn Clock>,
    ) -> Result<Self, EnterpriseError> {
        if !KNOWN_BUDGET_PROFILES.contains(&budget_profile.as_str()) {
            let mut sorted: Vec<&str> = KNOWN_BUDGET_PROFILES.to_vec();
            sorted.sort_unstable();
            return Err(EnterpriseError::Validation(format!(
                "unknown budget_profile '{}'; must be one of [{}]",
                budget_profile,
                sorted
                    .iter()
                    .map(|s| format!("{s:?}"))
                    .collect::<Vec<_>>()
                    .join(", ")
            )));
        }
        if auto_checkpoint_threshold_files < 1 {
            return Err(EnterpriseError::Validation(format!(
                "auto_checkpoint_threshold_files must be >= 1, got {auto_checkpoint_threshold_files}"
            )));
        }
        if auto_checkpoint_threshold_minutes < 1 {
            return Err(EnterpriseError::Validation(format!(
                "auto_checkpoint_threshold_minutes must be >= 1, got {auto_checkpoint_threshold_minutes}"
            )));
        }
        Ok(Self {
            mode,
            budget_profile,
            pre_commit_verification,
            out_of_scope_warning,
            auto_checkpoint_threshold_files,
            auto_checkpoint_threshold_minutes,
            warn_on_security_summary: true,
        })
    }

    /// `from_config`: typos caen a defaults seguros (nunca falla).
    pub fn from_config_values(
        mode: &str,
        default_budget_profile: &str,
        auto_checkpoint_files: i64,
        auto_checkpoint_minutes: i64,
        clock: Arc<dyn Clock>,
    ) -> Result<Self, EnterpriseError> {
        let parsed_mode = AutopilotMode::parse(mode).unwrap_or(AutopilotMode::Assist);
        let budget = if KNOWN_BUDGET_PROFILES.contains(&default_budget_profile) {
            default_budget_profile.to_string()
        } else {
            DEFAULT_BUDGET_PROFILE.to_string()
        };
        let is_observe = parsed_mode == AutopilotMode::Observe;
        Self::new(
            parsed_mode,
            budget,
            parsed_mode == AutopilotMode::Autopilot,
            !is_observe,
            (auto_checkpoint_files).max(1),
            (auto_checkpoint_minutes).max(1),
            clock,
        )
        .map(|mut p| {
            p.warn_on_security_summary = !is_observe;
            p
        })
    }

    /// `from_config(config)`.
    pub fn from_config(
        config: &AutopilotConfig,
        clock: Arc<dyn Clock>,
    ) -> Result<Self, EnterpriseError> {
        Self::from_config_values(
            &config.mode,
            &config.default_budget_profile,
            config.auto_checkpoint_files,
            config.auto_checkpoint_minutes,
            clock,
        )
    }
}

pub struct PolicyEnforcer {
    policy: AutopilotPolicy,
    clock: Arc<dyn Clock>,
}

impl PolicyEnforcer {
    pub fn new(policy: AutopilotPolicy) -> Self {
        // El enforcer usa el reloj del sistema salvo inyección explícita
        // (with_clock) para tests/gate.
        Self {
            policy,
            clock: Arc::new(cortex_enterprise::clock::SystemClock),
        }
    }

    /// Inyección de reloj para tests/gate.
    pub fn with_clock(mut self, clock: Arc<dyn Clock>) -> Self {
        self.clock = clock;
        self
    }

    pub fn policy(&self) -> &AutopilotPolicy {
        &self.policy
    }

    /// `on_session_open`.
    pub fn on_session_open(
        &self,
        session: &SessionRecord,
        spec_summary: Option<&str>,
    ) -> Vec<EnforcementResult> {
        let mut results = Vec::new();
        if self.policy.mode == AutopilotMode::Observe {
            return results;
        }
        let summary = spec_summary.unwrap_or(&session.spec_summary);
        if self.policy.warn_on_security_summary && looks_security_sensitive(summary) {
            results.push(EnforcementResult::warn(
                "Spec summary mentions security-sensitive terms — review the diff carefully before closing the session.",
            ));
        }
        results
    }

    /// `on_checkpoint`.
    pub fn on_checkpoint(
        &self,
        session: &SessionRecord,
        checkpoint: &Checkpoint,
        files_in_scope: Option<&[String]>,
    ) -> Vec<EnforcementResult> {
        let mut results = Vec::new();
        if self.policy.mode == AutopilotMode::Observe {
            return results;
        }

        if self.policy.out_of_scope_warning {
            if let Some(scope) = files_in_scope {
                let drift: Vec<&String> = checkpoint
                    .artifacts_touched
                    .iter()
                    .filter(|a| !scope.contains(a))
                    .collect();
                if !drift.is_empty() {
                    let mut sorted: Vec<String> = drift.into_iter().cloned().collect();
                    sorted.sort();
                    results.push(EnforcementResult::warn(format!(
                        "Checkpoint touches files outside spec scope: {}",
                        py_list_repr(&sorted)
                    )));
                }
            }
        }

        let since_verified = files_since_last_verified(session);
        if since_verified > self.policy.auto_checkpoint_threshold_files as usize {
            results.push(EnforcementResult::warn(format!(
                "{since_verified} artifact paths touched without a checkpoint that records verified claims"
            )));
        }

        let prior = session.checkpoints.len().saturating_sub(1);
        if prior > 0 && !checkpoint.artifacts_touched.is_empty() {
            let prev_ts: DateTime<Utc> = session.checkpoints[prior - 1].timestamp;
            let elapsed = self.clock.now() - prev_ts;
            let threshold =
                chrono::Duration::minutes(self.policy.auto_checkpoint_threshold_minutes);
            if elapsed > threshold {
                let minutes = elapsed.num_minutes();
                results.push(EnforcementResult::warn(format!(
                    "{minutes} minutes since the previous checkpoint and the new one already touches files — consider checkpointing more often"
                )));
            }
        }
        results
    }

    /// `on_pre_close`.
    pub fn on_pre_close(&self, session: &SessionRecord) -> Vec<EnforcementResult> {
        let mut results = Vec::new();
        let _ = SessionStatus::Open;
        if self.policy.mode == AutopilotMode::Autopilot
            && self.policy.pre_commit_verification
            && !has_verified_checkpoint(session)
        {
            results.push(EnforcementResult::block(
                "Autopilot mode requires at least one checkpoint with verified claims before closing the session (set pre_commit_verification=False to opt out).",
            ));
        }
        results
    }
}

/// `repr(list_de_str_python)`: elementos con comillas simples
/// (`['a', 'b']`), formato canónico de `{sorted(drift)}` en el oráculo.
pub(crate) fn py_list_repr(items: &[String]) -> String {
    let inner: Vec<String> = items.iter().map(|s| format!("'{s}'")).collect();
    format!("[{}]", inner.join(", "))
}
