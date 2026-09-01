//! Puerto de `cortex/ci/` — plugin CI (Pluggable Middle Phase 07, Obra 07
//! fase P11-ci, stream A).
//!
//! Validación provider-agnostic de PRs contra la Cortex Session + spec:
//! matcher de sesiones, carga de spec, scope cross-check, runner de hooks
//! y formatters JSON/Markdown. Espejo 1:1 de los módulos Python:
//!
//! - `result` ← result.py (ValidationInput/Result + `to_json_dict` ordenado)
//! - `validator` ← validator.py (CiValidator + parseo del diff)
//! - `session_matcher` ← session_matcher.py
//! - `diff_io` ← diff_io.py (tres modos de entrada del diff)
//! - `review_session` ← review_session.py (sesiones CI_BOT audit-only)
//! - `markdown_formatter` ← markdown_formatter.py (comentario de PR)

pub mod diff_io;
pub mod markdown_formatter;
pub mod result;
pub mod review_session;
pub mod session_matcher;
pub mod validator;

pub use crate::session::service::SessionMatchKind;
pub use diff_io::{read_diff_from_args, DiffResolutionError};
pub use markdown_formatter::{render_pr_comment, DEFAULT_MARKER};
pub use result::{DriftReason, ValidationInput, ValidationResult, ValidationStatus};
pub use review_session::{close_review_session, open_review_session, report_ci_checkpoint};
pub use session_matcher::find_session_for_pr;
pub use validator::{
    validate_pull_request, CiValidator, EXIT_BLOCKED, EXIT_ERROR, EXIT_PASS, EXIT_WARN,
};

/// Guard de directorio temporal único para tests (patrón del crate: sin
/// dependencia `tempfile`; cleanup automático al soltar).
#[cfg(test)]
pub(crate) struct TempGuard(std::path::PathBuf);

#[cfg(test)]
impl TempGuard {
    pub(crate) fn new(tag: &str) -> Self {
        let p = std::env::temp_dir().join(format!(
            "cortex-ci-{tag}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_nanos())
                .unwrap_or_default()
        ));
        std::fs::create_dir_all(&p).expect("crear tmpdir");
        TempGuard(p)
    }

    pub(crate) fn path(&self) -> &std::path::Path {
        &self.0
    }
}

#[cfg(test)]
impl Drop for TempGuard {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}
