//! Puerto de `cortex/ci/result.py` — inputs/outputs tipados del validador.

use std::path::{Path, PathBuf};

use crate::context::pyjson::Pj;
use crate::documenter::spec_loader::LoadedSpec;
use crate::session::service::SessionMatchKind;
use crate::session::{SessionRecord, VerificationHookResult};

/// `ValidationStatus`: pass | warn | blocked | error.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ValidationStatus {
    Pass,
    Warn,
    Blocked,
    Error,
}

impl ValidationStatus {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Pass => "pass",
            Self::Warn => "warn",
            Self::Blocked => "blocked",
            Self::Error => "error",
        }
    }
}

/// Todo lo que el validador necesita para evaluar un PR.
#[derive(Debug, Clone, Default)]
pub struct ValidationInput {
    pub diff_text: String,
    pub repo_root: PathBuf,
    pub base_commit: Option<String>,
    pub head_commit: Option<String>,
    pub base_branch: Option<String>,
    pub head_branch: Option<String>,
    pub pr_number: Option<i64>,
    pub pr_author: Option<String>,
    pub explicit_session_id: Option<String>,
}

impl ValidationInput {
    pub fn new(diff_text: impl Into<String>, repo_root: &Path) -> Self {
        Self {
            diff_text: diff_text.into(),
            repo_root: repo_root.to_path_buf(),
            base_commit: None,
            head_commit: None,
            base_branch: None,
            head_branch: None,
            pr_number: None,
            pr_author: None,
            explicit_session_id: None,
        }
    }
}

/// Razón de un hallazgo de scope drift.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DriftReason {
    OutOfScope,
    Unimplemented,
}

impl DriftReason {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::OutOfScope => "out_of_scope",
            Self::Unimplemented => "unimplemented",
        }
    }
}

/// Un archivo que violó `spec.files_in_scope`.
#[derive(Debug, Clone)]
pub struct ScopeDriftFinding {
    pub path: PathBuf,
    pub reason: DriftReason,
}

/// Resultado de `CiValidator.validate`.
///
/// El esquema JSON (`to_json_dict`) es estable entre releases; el formatter
/// Markdown opera sobre este objeto directamente.
#[derive(Debug, Clone)]
pub struct ValidationResult {
    pub session_match: SessionMatchKind,
    pub matched_session: Option<SessionRecord>,
    pub spec: Option<LoadedSpec>,
    pub files_in_diff: Vec<PathBuf>,
    pub scope_drift: Vec<ScopeDriftFinding>,
    pub verification_results: Vec<VerificationHookResult>,
    pub blockers: Vec<String>,
    pub warnings: Vec<String>,
    pub exit_code: i32,
    pub status: ValidationStatus,
    pub summary_text: String,
    // Inputs originales del PR, para el formatter Markdown.
    pub pr_number: Option<i64>,
    pub pr_author: Option<String>,
    pub head_branch: Option<String>,
}

impl ValidationResult {
    /// Representación JSON-serializable con orden de claves del oráculo
    /// (dict literal de `to_json_dict`).
    pub fn to_json_pj(&self) -> Pj {
        let scope_drift: Vec<Pj> = self
            .scope_drift
            .iter()
            .map(|f| {
                Pj::Obj(vec![
                    ("path".into(), Pj::Str(f.path.to_string_lossy().to_string())),
                    ("reason".into(), Pj::Str(f.reason.as_str().into())),
                ])
            })
            .collect();
        let verif: Vec<Pj> = self
            .verification_results
            .iter()
            .map(|r| {
                Pj::Obj(vec![
                    ("name".into(), Pj::Str(r.name.clone())),
                    ("passed".into(), Pj::Bool(r.passed)),
                    ("exit_code".into(), Pj::I64(r.exit_code as i64)),
                    ("duration_ms".into(), Pj::U64(r.duration_ms)),
                ])
            })
            .collect();
        let opt_str = |o: &Option<String>| match o {
            Some(s) => Pj::Str(s.clone()),
            None => Pj::Null,
        };
        Pj::Obj(vec![
            ("status".into(), Pj::Str(self.status.as_str().into())),
            ("exit_code".into(), Pj::I64(self.exit_code as i64)),
            (
                "session_match".into(),
                Pj::Str(self.session_match.as_str().into()),
            ),
            (
                "session_id".into(),
                match &self.matched_session {
                    Some(r) => Pj::Str(r.session_id.clone()),
                    None => Pj::Null,
                },
            ),
            (
                "spec_path".into(),
                match &self.spec {
                    Some(s) => Pj::Str(s.path.to_string_lossy().to_string()),
                    None => Pj::Null,
                },
            ),
            (
                "files_in_diff".into(),
                Pj::Arr(
                    self.files_in_diff
                        .iter()
                        .map(|p| Pj::Str(p.to_string_lossy().to_string()))
                        .collect(),
                ),
            ),
            ("scope_drift".into(), Pj::Arr(scope_drift)),
            ("verification_results".into(), Pj::Arr(verif)),
            (
                "blockers".into(),
                Pj::Arr(self.blockers.iter().map(|b| Pj::Str(b.clone())).collect()),
            ),
            (
                "warnings".into(),
                Pj::Arr(self.warnings.iter().map(|w| Pj::Str(w.clone())).collect()),
            ),
            ("summary_text".into(), Pj::Str(self.summary_text.clone())),
            (
                "pr_number".into(),
                match self.pr_number {
                    Some(n) => Pj::I64(n),
                    None => Pj::Null,
                },
            ),
            ("pr_author".into(), opt_str(&self.pr_author)),
            ("head_branch".into(), opt_str(&self.head_branch)),
        ])
    }

    /// `json.dumps(to_json_dict(), ensure_ascii=False, indent=2)` del CLI.
    pub fn to_json_string(&self) -> String {
        crate::context::pyjson::dumps(&self.to_json_pj())
    }
}
