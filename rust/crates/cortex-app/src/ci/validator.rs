//! Puerto de `cortex/ci/validator.py` — validar un PR contra su Session+spec.
//!
//! Orquesta session matcher, spec loader, scope cross-check y verification
//! runner en un único `ValidationResult`. Es el corazón de
//! `cortex ci validate-pr` (Level 1).

use std::path::{Path, PathBuf};

use crate::ci::result::{
    DriftReason, ScopeDriftFinding, ValidationInput, ValidationResult, ValidationStatus,
};
use crate::documenter::spec_loader::{load_spec, LoadedSpec};
use crate::session::service::{SessionMatchKind, SessionService};
use crate::session::verification::VerificationRunner;

pub const EXIT_PASS: i32 = 0;
pub const EXIT_WARN: i32 = 1;
pub const EXIT_BLOCKED: i32 = 2;
pub const EXIT_ERROR: i32 = 3;

pub struct CiValidator {
    sessions: SessionService,
    verifier: VerificationRunner,
    repo_root: PathBuf,
}

impl CiValidator {
    pub fn new(
        session_service: SessionService,
        verification_runner: VerificationRunner,
        repo_root: &Path,
    ) -> Self {
        Self {
            sessions: session_service,
            verifier: verification_runner,
            repo_root: repo_root.to_path_buf(),
        }
    }

    pub fn validate(&self, payload: &ValidationInput) -> ValidationResult {
        let (record, match_kind) = self.sessions.find_for_pr(
            payload.explicit_session_id.as_deref(),
            payload.base_commit.as_deref(),
            payload.head_branch.as_deref(),
        );

        let files_in_diff = parse_files_from_diff(&payload.diff_text);

        let Some(record) = record else {
            return no_session_result(payload, files_in_diff, match_kind);
        };

        let spec = self.load_spec(&record);
        let mut warnings: Vec<String> = Vec::new();
        let mut blockers: Vec<String> = Vec::new();

        // Lifecycle: HANDOFF ⇒ warn; ABANDONED ⇒ block.
        match record.status {
            crate::session::SessionStatus::Handoff => warnings.push(format!(
                "Matched session '{}' is in HANDOFF status.",
                record.session_id
            )),
            crate::session::SessionStatus::Abandoned => blockers.push(format!(
                "Matched session '{}' is ABANDONED — block.",
                record.session_id
            )),
            _ => {}
        }

        // Scope cross-check (reusa el helper puro del documenter).
        let mut scope_drift: Vec<ScopeDriftFinding> = Vec::new();
        if let Some(spec) = &spec {
            if !spec.files_in_scope.is_empty() {
                let (_, out_of_scope, unimplemented) =
                    crate::documenter::scope_cross_check(&files_in_diff, &spec.files_in_scope);
                for path in out_of_scope {
                    warnings.push(format!(
                        "out-of-scope file in diff: {}",
                        path.to_string_lossy()
                    ));
                    scope_drift.push(ScopeDriftFinding {
                        path,
                        reason: DriftReason::OutOfScope,
                    });
                }
                for path in unimplemented {
                    blockers.push(format!(
                        "file in scope not implemented: {}",
                        path.to_string_lossy()
                    ));
                    scope_drift.push(ScopeDriftFinding {
                        path,
                        reason: DriftReason::Unimplemented,
                    });
                }
            }
        }

        // Verification hooks.
        let mut verif_results: Vec<crate::session::VerificationHookResult> = Vec::new();
        if let Some(spec) = &spec {
            if !spec.verification_hooks.is_empty() {
                verif_results = self.verifier.run_all(&spec.verification_hooks);
                for r in &verif_results {
                    if r.passed {
                        continue;
                    }
                    // VerificationHookResult no preserva `required`; se busca
                    // en la spec para decidir blocker vs warn.
                    let hook = spec.verification_hooks.iter().find(|h| h.name == r.name);
                    match hook {
                        Some(h) if !h.required => warnings.push(format!(
                            "non-required hook '{}' failed (exit {})",
                            r.name, r.exit_code
                        )),
                        _ => blockers.push(format!(
                            "required hook '{}' failed (exit {})",
                            r.name, r.exit_code
                        )),
                    }
                }
            } else {
                warnings.push("spec declares no verification_hooks — validation is partial".into());
            }
        }

        let (status, exit_code) = if !blockers.is_empty() {
            (ValidationStatus::Blocked, EXIT_BLOCKED)
        } else if !warnings.is_empty() {
            (ValidationStatus::Warn, EXIT_WARN)
        } else {
            (ValidationStatus::Pass, EXIT_PASS)
        };

        let summary = build_summary(
            &record.session_id,
            status.as_str(),
            files_in_diff.len(),
            verif_results.iter().filter(|r| r.passed).count(),
            verif_results.len(),
            warnings.len(),
            blockers.len(),
        );

        ValidationResult {
            session_match: match_kind,
            matched_session: Some(record),
            spec,
            files_in_diff,
            scope_drift,
            verification_results: verif_results,
            blockers,
            warnings,
            exit_code,
            status,
            summary_text: summary,
            pr_number: payload.pr_number,
            pr_author: payload.pr_author.clone(),
            head_branch: payload.head_branch.clone(),
        }
    }

    /// Spec del record: rutas relativas se resuelven contra repo_root.
    fn load_spec(&self, record: &crate::session::SessionRecord) -> Option<LoadedSpec> {
        let raw = PathBuf::from(&record.spec_path);
        let spec_path = if raw.is_absolute() {
            raw
        } else {
            // `resolve()` de Python: normaliza sin requerir existencia.
            let joined = self.repo_root.join(raw);
            normalize_path(&joined)
        };
        if !spec_path.is_file() {
            return None;
        }
        Some(load_spec(&spec_path))
    }
}

/// Normalización estilo `Path.resolve()` (lexicográfica, sin symlink-resolve:
/// suficiente para las specs commiteadas y los fixtures).
fn normalize_path(p: &Path) -> PathBuf {
    let mut out = PathBuf::new();
    for comp in p.components() {
        use std::path::Component;
        match comp {
            Component::ParentDir => {
                out.pop();
            }
            Component::CurDir => {}
            c => out.push(c.as_os_str()),
        }
    }
    out
}

/// Conveniencia usada por el CLI.
pub fn validate_pull_request(
    payload: &ValidationInput,
    session_service: SessionService,
    verification_runner: VerificationRunner,
) -> ValidationResult {
    CiValidator::new(
        session_service,
        verification_runner,
        &payload.repo_root.clone(),
    )
    .validate(payload)
}

/// Extraer archivos tocados de un diff unificado.
///
/// Solo líneas `+++ b/<path>` cuentan como lado derecho; un archivo
/// borrado aparece como `--- a/<path>` con `+++ /dev/null` — igual suma
/// como tocado. Dedup preservando orden.
pub fn parse_files_from_diff(diff_text: &str) -> Vec<PathBuf> {
    let mut seen: Vec<PathBuf> = Vec::new();
    for raw in diff_text.lines() {
        if let Some(rest) = raw.strip_prefix("+++ b/") {
            seen.push(PathBuf::from(rest.trim()));
        } else if let Some(rest) = raw.strip_prefix("--- a/") {
            let candidate = PathBuf::from(rest.trim());
            if !seen.contains(&candidate) {
                seen.push(candidate);
            }
        }
    }
    // Dedup final preservando orden.
    let mut out: Vec<PathBuf> = Vec::with_capacity(seen.len());
    for p in seen {
        if !out.contains(&p) {
            out.push(p);
        }
    }
    out
}

fn no_session_result(
    payload: &ValidationInput,
    files_in_diff: Vec<PathBuf>,
    match_kind: SessionMatchKind,
) -> ValidationResult {
    let blockers = vec![
        "No Cortex Session matches this PR. Open one before re-running CI: \
         `cortex create-spec ...` (creates the spec and the session)."
            .to_string(),
    ];
    let n = files_in_diff.len();
    ValidationResult {
        session_match: match_kind,
        matched_session: None,
        spec: None,
        files_in_diff,
        scope_drift: vec![],
        verification_results: vec![],
        blockers,
        warnings: vec![],
        exit_code: EXIT_BLOCKED,
        status: ValidationStatus::Blocked,
        summary_text: format!(
            "no session match (kind={}); diff has {n} files",
            match_kind.as_str()
        ),
        pr_number: payload.pr_number,
        pr_author: payload.pr_author.clone(),
        head_branch: payload.head_branch.clone(),
    }
}

fn build_summary(
    session_id: &str,
    status: &str,
    files: usize,
    hooks_passed: usize,
    hooks_total: usize,
    warnings: usize,
    blockers: usize,
) -> String {
    format!(
        "session={session_id} status={status} files={files} \
         hooks={hooks_passed}/{hooks_total} warnings={warnings} blockers={blockers}"
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ci::result::ValidationInput;
    use crate::session::service::SessionService;
    use crate::session::verification::VerificationRunner;
    use crate::session::{SessionStatus, SessionStorage};

    fn git(repo: &Path, args: &[&str]) {
        let out = std::process::Command::new("git")
            .args(args)
            .current_dir(repo)
            .env("GIT_AUTHOR_NAME", "T")
            .env("GIT_AUTHOR_EMAIL", "t@x.com")
            .env("GIT_COMMITTER_NAME", "T")
            .env("GIT_COMMITTER_EMAIL", "t@x.com")
            .output()
            .expect("git");
        assert!(
            out.status.success(),
            "git {args:?}: {}",
            String::from_utf8_lossy(&out.stderr)
        );
    }

    /// Fixture espejo de test_validator.py: repo git + spec demo con hook
    /// smoke configurable (pass/fail).
    struct Fixture {
        tmp: crate::ci::TempGuard,
        repo: PathBuf,
        service: Option<SessionService>,
    }

    impl Fixture {
        fn new(hook_exit: i32) -> Self {
            let tmp = crate::ci::TempGuard::new("validator");
            let repo = tmp.path().join("repo");
            std::fs::create_dir_all(repo.join("src")).unwrap();
            git(&repo, &["init", "-q", "-b", "main"]);
            std::fs::write(repo.join("src/x.py"), "def x(): return 1\n").unwrap();
            std::fs::create_dir_all(repo.join("vault/specs")).unwrap();
            let hook_cmd = if hook_exit == 0 {
                "true".into()
            } else {
                "false".to_string()
            };
            let spec = format!(
                "---\ntitle: demo\ndoc_type: spec\ngoal: keep x working\n\
                 files_in_scope:\n  - src/x.py\nverification_hooks:\n  - {{name: smoke, \
                 command: \"{hook_cmd}\", required: true, success_criteria: \"exit 0\", \
                 timeout_seconds: 30}}\n---\n"
            );
            std::fs::write(repo.join("vault/specs/2026-05-17_demo.md"), spec).unwrap();
            git(&repo, &["add", "."]);
            git(&repo, &["commit", "-q", "-m", "seed"]);

            let service =
                SessionService::new(SessionStorage::new(tmp.path().join("sessions")), &repo);
            Self {
                tmp,
                repo,
                service: Some(service),
            }
        }

        fn service(&self) -> &SessionService {
            self.service.as_ref().unwrap()
        }

        fn validator(&self) -> CiValidator {
            CiValidator::new(
                SessionService::new(
                    SessionStorage::new(self.tmp.path().join("sessions")),
                    &self.repo,
                ),
                VerificationRunner::new(self.repo.clone()),
                &self.repo,
            )
        }

        fn payload(&self, touched: &[&str]) -> ValidationInput {
            let diff = touched
                .iter()
                .map(|p| format!("--- a/{p}\n+++ b/{p}\n@@ -1 +1,2 @@\n x\n+new\n"))
                .collect::<Vec<_>>()
                .join("\n");
            ValidationInput::new(diff, &self.repo)
        }
    }

    #[test]
    fn matching_y_bloqueo_sin_sesion() {
        let fx = Fixture::new(0);
        let rec = fx
            .service()
            .open("2026-05-17_demo", "vault/specs/2026-05-17_demo.md", "")
            .unwrap();

        let v = fx.validator();

        // explicit match.
        let mut p = fx.payload(&["src/x.py"]);
        p.explicit_session_id = Some(rec.session_id.clone());
        let res = v.validate(&p);
        assert_eq!(res.session_match, SessionMatchKind::Explicit);
        assert!(res.matched_session.is_some());
        assert_eq!(res.exit_code, EXIT_PASS);
        assert!(res.scope_drift.is_empty());

        // sin match ⇒ blocked con blocker canónico.
        let res = v.validate(&fx.payload(&["src/x.py"]));
        assert_eq!(res.session_match, SessionMatchKind::NoneKind);
        assert_eq!(res.exit_code, EXIT_BLOCKED);
        assert!(res.blockers.iter().any(|b| b.contains("No Cortex Session")));
    }

    #[test]
    fn scope_drift_warn_y_unimplemented_block() {
        let fx = Fixture::new(0);
        let rec = fx
            .service()
            .open("2026-05-17_demo", "vault/specs/2026-05-17_demo.md", "")
            .unwrap();

        let v = fx.validator();

        // out-of-scope ⇒ warning + WARN.
        let mut p = fx.payload(&["src/x.py", "src/unexpected.py"]);
        p.explicit_session_id = Some(rec.session_id.clone());
        let res = v.validate(&p);
        assert!(res
            .scope_drift
            .iter()
            .any(|f| f.reason == DriftReason::OutOfScope));
        assert_eq!(res.exit_code, EXIT_WARN);

        // diff fuera de scope ⇒ unimplemented bloquea.
        let mut p2 = fx.payload(&["src/other.py"]);
        p2.explicit_session_id = Some(rec.session_id.clone());
        let res2 = v.validate(&p2);
        assert!(res2
            .scope_drift
            .iter()
            .any(|f| f.reason == DriftReason::Unimplemented));
        assert_eq!(res2.exit_code, EXIT_BLOCKED);
    }

    #[test]
    fn hook_requerido_fallido_bloquea() {
        let fx = Fixture::new(1); // smoke hace exit(1)
        let rec = fx
            .service()
            .open("2026-05-17_demo", "vault/specs/2026-05-17_demo.md", "")
            .unwrap();
        let mut p = fx.payload(&["src/x.py"]);
        p.explicit_session_id = Some(rec.session_id.clone());
        let res = fx.validator().validate(&p);
        assert_eq!(res.exit_code, EXIT_BLOCKED);
        assert!(res.blockers.iter().any(|b| b.contains("required hook")));
    }

    #[test]
    fn lifecycle_handoff_y_abandoned() {
        // HANDOFF ⇒ warning (WARN si no hay blockers).
        let fx = Fixture::new(0);
        let svc = fx.service();
        let rec = svc
            .open("2026-05-17_demo", "vault/specs/2026-05-17_demo.md", "")
            .unwrap();
        svc.close(
            &rec.session_id,
            SessionStatus::Handoff,
            SessionStatus::Handoff,
            None,
            vec![],
        )
        .unwrap();
        let mut p = fx.payload(&["src/x.py"]);
        p.explicit_session_id = Some(rec.session_id.clone());
        let res = fx.validator().validate(&p);
        assert!(res.warnings.iter().any(|w| w.contains("HANDOFF")));
        assert_eq!(res.exit_code, EXIT_WARN);

        // ABANDONED ⇒ blocker.
        let fx2 = Fixture::new(0);
        let svc2 = fx2.service();
        let rec2 = svc2
            .open("2026-05-17_demo", "vault/specs/2026-05-17_demo.md", "")
            .unwrap();
        svc2.close(
            &rec2.session_id,
            SessionStatus::Abandoned,
            SessionStatus::Abandoned,
            None,
            vec![],
        )
        .unwrap();
        let mut p2 = fx2.payload(&["src/x.py"]);
        p2.explicit_session_id = Some(rec2.session_id.clone());
        let res2 = fx2.validator().validate(&p2);
        assert!(res2.blockers.iter().any(|b| b.contains("ABANDONED")));
        assert_eq!(res2.exit_code, EXIT_BLOCKED);
    }

    #[test]
    fn parse_diff_dedup_y_borrados() {
        let diff = "--- a/src/x.py\n+++ b/src/x.py\n@@\n--- a/src/gone.py\n+++ /dev/null\n@@";
        let files = parse_files_from_diff(diff);
        assert_eq!(
            files,
            vec![PathBuf::from("src/x.py"), PathBuf::from("src/gone.py")]
        );
        // Sin duplicados aunque +++ repita tras ---.
        let diff2 = "+++ b/a.md\n--- a/a.md\n+++ b/b.md";
        assert_eq!(
            parse_files_from_diff(diff2),
            vec![PathBuf::from("a.md"), PathBuf::from("b.md")]
        );
    }

    #[test]
    fn json_dict_claves_estables() {
        let fx = Fixture::new(0);
        let rec = fx
            .service()
            .open("2026-05-17_demo", "vault/specs/2026-05-17_demo.md", "")
            .unwrap();
        let mut p = fx.payload(&["src/x.py"]);
        p.explicit_session_id = Some(rec.session_id.clone());
        let res = fx.validator().validate(&p);
        let json = res.to_json_string();
        for key in [
            "\"status\"",
            "\"exit_code\"",
            "\"session_match\"",
            "\"session_id\"",
            "\"files_in_diff\"",
            "\"scope_drift\"",
            "\"verification_results\"",
            "\"blockers\"",
            "\"warnings\"",
            "\"summary_text\"",
        ] {
            assert!(json.contains(key), "falta {key}");
        }
        assert!(json.starts_with("{\n  \"status\""));
    }
}
