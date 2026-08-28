//! Puerto de `cortex/ci/review_session.py` — sesiones de revisión CI (L3).
//!
//! Una review session usa la primitiva Session tal cual; los únicos bits
//! nuevos son `CheckpointSource.CI_BOT` y el modo inferido `CI_REVIEW`
//! cuando todos los checkpoints vienen del bot. Las sesiones de review NO
//! promueven el puntero activo (CI corre junto a la sesión del developer).

use crate::session::service::SessionService;
use crate::session::{CheckpointSource, SessionRecord, SessionStatus};

/// Abrir una review session fresca (sin tocar la sesión activa).
///
/// Sin `spec_path` se usa una referencia sintética `vault/specs/<id>.md`;
/// no necesita existir — las review sessions nunca invocan al documenter.
pub fn open_review_session(
    service: &SessionService,
    spec_id: &str,
    base_commit: &str,
    head_branch: &str,
    pr_number: Option<i64>,
    spec_path: Option<&str>,
) -> Result<SessionRecord, String> {
    let spec_path = spec_path
        .map(str::to_string)
        .unwrap_or_else(|| format!("vault/specs/{spec_id}.md"));
    let summary = match pr_number {
        Some(n) => format!("PR #{n} review"),
        None => format!("Review of {head_branch}"),
    };
    // No se puede usar service.open: setea start_commit=HEAD del checkout de
    // CI y promueve la sesión a activa. Review sessions necesitan un
    // base_commit explícito y no deben robar el puntero.
    let record = SessionRecord {
        session_id: service.make_unique_session_id(spec_id),
        spec_path,
        spec_summary: summary,
        start_commit: base_commit.to_string(),
        start_branch: head_branch.to_string(),
        opened_at: crate::session::service::now_iso(),
        ..Default::default()
    };
    service.save_new_record(&record)?;
    Ok(record)
}

fn hook_label(name: &str, passed: bool, exit_code: i64) -> String {
    // Espejo del f-string con !r de Python: repr ⇒ comillas simples.
    if passed {
        format!("hook '{name}' passed")
    } else {
        format!("hook '{name}' failed (exit {exit_code})")
    }
}

/// Agregar un checkpoint `CI_BOT` a la review session.
///
/// Con `validation_payload` (el dict JSON de `validate-pr --format json`),
/// los hooks que pasan pasan a verified_claims, warnings/blockers a
/// unverified_claims y files_in_diff a artifacts_touched.
#[allow(clippy::too_many_arguments)]
pub fn report_ci_checkpoint(
    service: &SessionService,
    session_id: &str,
    validation_payload: Option<&serde_json::Value>,
    manual_claims: &[String],
    manual_artifacts: &[String],
    note: &str,
) -> Result<SessionRecord, String> {
    let mut verified: Vec<String> = manual_claims.to_vec();
    let mut unverified: Vec<String> = Vec::new();
    let mut artifacts: Vec<String> = manual_artifacts.to_vec();
    let mut payload_note = note.to_string();

    if let Some(payload) = validation_payload {
        if let Some(hooks) = payload
            .get("verification_results")
            .and_then(|v| v.as_array())
        {
            for hook in hooks {
                let name = hook.get("name").and_then(|v| v.as_str()).unwrap_or("");
                let passed = hook
                    .get("passed")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(false);
                let code = hook
                    .get("exit_code")
                    .and_then(|v| v.as_i64())
                    .unwrap_or_default();
                let label = hook_label(name, passed, code);
                if passed {
                    verified.push(label);
                } else {
                    unverified.push(label);
                }
            }
        }
        for w in payload
            .get("warnings")
            .and_then(|v| v.as_array())
            .into_iter()
            .flatten()
        {
            unverified.push(match w.as_str() {
                Some(s) => s.to_string(),
                None => w.to_string(),
            });
        }
        for b in payload
            .get("blockers")
            .and_then(|v| v.as_array())
            .into_iter()
            .flatten()
        {
            let s = match b.as_str() {
                Some(s) => s.to_string(),
                None => b.to_string(),
            };
            unverified.push(format!("blocker: {s}"));
        }
        for f in payload
            .get("files_in_diff")
            .and_then(|v| v.as_array())
            .into_iter()
            .flatten()
        {
            artifacts.push(match f.as_str() {
                Some(s) => s.to_string(),
                None => f.to_string(),
            });
        }
        if payload_note.is_empty() {
            payload_note = payload
                .get("summary_text")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .trim()
                .to_string();
        }
    }

    service.checkpoint(
        session_id,
        CheckpointSource::CiBot,
        verified,
        unverified,
        artifacts,
        &payload_note,
        None, // ci-bot no emite fase (modo COMPOSED); ruling R7
    )
}

/// Cerrar la review session en estado terminal (audit-only, sin documenter).
///
/// Con `reason`, se registra como checkpoint MANUAL final para que el audit
/// log tenga la justificación.
pub fn close_review_session(
    service: &SessionService,
    session_id: &str,
    status: SessionStatus,
    reason: &str,
) -> Result<SessionRecord, String> {
    if !status.is_terminal() {
        return Err(format!(
            "status must be CLOSED / HANDOFF / ABANDONED, got {:?}",
            status.as_str()
        ));
    }
    if !reason.is_empty() {
        service.checkpoint(
            session_id,
            CheckpointSource::Manual,
            vec![],
            vec![],
            vec![],
            &format!("close reason: {reason}"),
            None,
        )?;
    }
    service.close(session_id, status, status, None, vec![])
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::session::{SessionMode, SessionStorage};
    use std::path::Path;

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
        assert!(out.status.success());
    }

    fn fixture() -> (crate::ci::TempGuard, SessionService) {
        let tmp = crate::ci::TempGuard::new("review");
        let repo = tmp.path().join("repo");
        std::fs::create_dir_all(&repo).unwrap();
        git(&repo, &["init", "-q", "-b", "main"]);
        std::fs::write(repo.join("x.txt"), "x\n").unwrap();
        git(&repo, &["add", "."]);
        git(&repo, &["commit", "-q", "-m", "seed"]);
        let svc = SessionService::new(SessionStorage::new(tmp.path().join("sessions")), &repo);
        (tmp, svc)
    }

    fn payload_json() -> serde_json::Value {
        serde_json::json!({
            "verification_results": [
                {"name": "tests", "passed": true, "exit_code": 0},
                {"name": "lint", "passed": false, "exit_code": 1},
            ],
            "warnings": ["out-of-scope file: src/y.py"],
            "blockers": [],
            "files_in_diff": ["src/x.py", "src/y.py"],
            "summary_text": "session=… status=warn",
        })
    }

    #[test]
    fn abre_con_base_commit_y_no_promueve_activo() {
        let (_tmp, svc) = fixture();
        let rec = open_review_session(
            &svc,
            "2026-05-17_pr-42-review",
            &"a".repeat(40),
            "feature/x",
            Some(42),
            None,
        )
        .unwrap();
        assert_eq!(rec.start_commit, "a".repeat(40));
        assert_eq!(rec.start_branch, "feature/x");
        assert!(rec.spec_summary.contains("PR #42 review"));
        assert_eq!(rec.spec_path, "vault/specs/2026-05-17_pr-42-review.md");

        // Puntero activo intacto (no había ninguno).
        assert!(svc.get_active().is_none());

        // Summary sin PR ⇒ "Review of <branch>".
        let rec2 = open_review_session(
            &svc,
            "2026-05-17_pr-99-review",
            &"b".repeat(40),
            "feature/y",
            None,
            None,
        )
        .unwrap();
        assert!(rec2.spec_summary.contains("Review of feature/y"));
    }

    #[test]
    fn checkpoint_desde_payload_y_manual() {
        let (_tmp, svc) = fixture();
        let rec = open_review_session(
            &svc,
            "2026-05-17_pr-1-review",
            &"c".repeat(40),
            "feature/z",
            Some(1),
            None,
        )
        .unwrap();
        let updated =
            report_ci_checkpoint(&svc, &rec.session_id, Some(&payload_json()), &[], &[], "")
                .unwrap();
        assert_eq!(updated.checkpoints.len(), 1);
        let cp = &updated.checkpoints[0];
        assert_eq!(cp.source, CheckpointSource::CiBot);
        assert!(cp.verified_claims.iter().any(|c| c.contains("tests")));
        assert!(cp.unverified_claims.iter().any(|c| c.contains("lint")));
        assert!(cp.artifacts_touched.contains(&"src/y.py".to_string()));
        assert_eq!(cp.note.trim(), "session=… status=warn");

        // Manual only.
        let updated2 = report_ci_checkpoint(
            &svc,
            &rec.session_id,
            None,
            &["manual claim".to_string()],
            &["src/x.py".to_string()],
            "initial review",
        )
        .unwrap();
        let cp2 = updated2.checkpoints.last().unwrap();
        assert_eq!(cp2.verified_claims, vec!["manual claim"]);
        assert_eq!(cp2.artifacts_touched, vec!["src/x.py"]);
        assert_eq!(cp2.note, "initial review");
    }

    #[test]
    fn cierre_ci_review_observed_e_invalido() {
        let (_tmp, svc) = fixture();

        // Todos los checkpoints CI_BOT ⇒ modo CI_REVIEW al cerrar.
        let rec = open_review_session(
            &svc,
            "2026-05-17_pr-3-review",
            &"e".repeat(40),
            "feature/v",
            Some(3),
            None,
        )
        .unwrap();
        report_ci_checkpoint(
            &svc,
            &rec.session_id,
            None,
            &["x".to_string()],
            &["src/x.py".to_string()],
            "",
        )
        .unwrap();
        let closed =
            close_review_session(&svc, &rec.session_id, SessionStatus::Closed, "").unwrap();
        assert_eq!(closed.status, SessionStatus::Closed);
        assert_eq!(closed.mode, SessionMode::CiReview);

        // close con reason ⇒ checkpoint MANUAL mezcla fuentes ⇒ OBSERVED.
        let rec2 = open_review_session(
            &svc,
            "2026-05-17_pr-4-review",
            &"f".repeat(40),
            "feature/u",
            Some(4),
            None,
        )
        .unwrap();
        let closed2 = close_review_session(
            &svc,
            &rec2.session_id,
            SessionStatus::Handoff,
            "hooks failed",
        )
        .unwrap();
        assert_eq!(closed2.mode, SessionMode::Observed);
        assert!(closed2
            .checkpoints
            .iter()
            .any(|c| c.note.contains("hooks failed")));

        // Status inválido (no terminal) ⇒ error.
        let rec3 = open_review_session(
            &svc,
            "2026-05-17_pr-5-review",
            &"0".repeat(40),
            "feature/q",
            Some(5),
            None,
        )
        .unwrap();
        assert!(close_review_session(&svc, &rec3.session_id, SessionStatus::Open, "").is_err());
    }
}
