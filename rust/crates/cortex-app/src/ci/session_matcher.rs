//! Puerto de `cortex/ci/session_matcher.py` — encontrar la Session de un PR.
//!
//! Prioridad intencional: explicit > base_commit > head_branch > none.

use crate::session::service::SessionMatchKind;
use crate::session::{SessionRecord, SessionStorage};

pub fn find_session_for_pr(
    storage: &SessionStorage,
    explicit_session_id: Option<&str>,
    base_commit: Option<&str>,
    head_branch: Option<&str>,
) -> (Option<SessionRecord>, SessionMatchKind) {
    if let Some(id) = explicit_session_id.filter(|s| !s.is_empty()) {
        // Fallo de carga ⇒ "none" en vez de crash (BLE001 del oráculo).
        return match storage.load(id) {
            Ok(record) => (Some(record), SessionMatchKind::Explicit),
            Err(_) => (None, SessionMatchKind::NoneKind),
        };
    }

    let Ok(records) = storage.list_all() else {
        return (None, SessionMatchKind::NoneKind);
    };

    if let Some(base) = base_commit.filter(|s| !s.is_empty()) {
        for record in &records {
            if record.start_commit == base {
                return (Some(record.clone()), SessionMatchKind::ByCommit);
            }
        }
    }

    if let Some(branch) = head_branch.filter(|s| !s.is_empty()) {
        for record in &records {
            if record.start_branch == branch {
                return (Some(record.clone()), SessionMatchKind::ByBranch);
            }
        }
    }

    (None, SessionMatchKind::NoneKind)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::session::service::SessionService;

    use crate::ci::TempGuard;
    use std::path::Path;

    fn service_with(storage_root: &Path, repo_root: &Path) -> SessionService {
        SessionService::new(SessionStorage::new(storage_root.to_path_buf()), repo_root)
    }

    #[test]
    fn prioridad_explicit_commit_branch_none() {
        let tmp = TempGuard::new("matcher");
        let repo = tmp.path().join("repo");
        std::fs::create_dir_all(&repo).unwrap();
        for args in [
            vec!["init", "-q", "-b", "main"],
            vec!["config", "user.email", "t@x.com"],
            vec!["config", "user.name", "T"],
            vec!["add", "."],
            vec!["commit", "-q", "--allow-empty", "-m", "seed"],
        ] {
            assert!(std::process::Command::new("git")
                .args(&args)
                .current_dir(&repo)
                .output()
                .unwrap()
                .status
                .success());
        }
        let svc = service_with(&tmp.path().join("sessions"), &repo);

        let rec = svc
            .open("2026-05-17_demo", "vault/specs/2026-05-17_demo.md", "")
            .unwrap();

        let storage = SessionStorage::new(tmp.path().join("sessions"));

        // explicit existente gana siempre.
        let (r, k) = find_session_for_pr(&storage, Some(&rec.session_id), Some("zz"), Some("zz"));
        assert_eq!(k, SessionMatchKind::Explicit);
        assert_eq!(r.unwrap().session_id, rec.session_id);

        // by_commit: start_commit == HEAD del repo abierto.
        let head = rec.start_commit.clone();
        let (r, k) = find_session_for_pr(&storage, None, Some(&head), Some("otra"));
        assert_eq!(k, SessionMatchKind::ByCommit);
        assert_eq!(r.unwrap().session_id, rec.session_id);

        // by_branch.
        let (r, k) = find_session_for_pr(&storage, None, None, Some(rec.start_branch.as_str()));
        assert_eq!(k, SessionMatchKind::ByBranch);
        assert_eq!(r.unwrap().session_id, rec.session_id);

        // explicit inexistente ⇒ none (no crash).
        let (r, k) = find_session_for_pr(&storage, Some("2026-01-01_faltante"), None, None);
        assert_eq!(k, SessionMatchKind::NoneKind);
        assert!(r.is_none());

        // nada ⇒ none; gitless placeholder no matchea commits reales.
        assert_eq!(
            find_session_for_pr(&storage, None, None, None).1,
            SessionMatchKind::NoneKind
        );
    }
}
