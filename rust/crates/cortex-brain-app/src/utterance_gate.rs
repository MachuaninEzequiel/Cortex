//! Portero (spec 09): un if al inicio del chat. No borra session/documenter.

use std::path::Path;

use cortex_app::session::service::SessionService;
use cortex_app::session::SessionStorage;
use cortex_judgement::{classify_utterance, Catalog, JudgementClient, JudgementHandle};
use cortex_workspace::WorkspaceLayout;

fn clip(s: &str, n: usize) -> String {
    s.chars().take(n).collect()
}

/// Abre sesión si Jev dice implement + needs_session y no hay activa.
/// 429 / off ⇒ no-op (Direct).
pub fn maybe_open_session_with(
    client: &dyn JudgementClient,
    catalog: &Catalog,
    service: &SessionService,
    text: &str,
) {
    let active = service.get_active().is_some();
    let Some(j) = classify_utterance(client, catalog, text, active, &[]) else {
        return;
    };
    if j.should_open_session(active) {
        let today = chrono::Utc::now().format("%Y-%m-%d");
        let session_id = format!("{today}_jev-work");
        let _ = service.open(&session_id, "", &clip(text, 120));
    }
}

pub fn maybe_open_session_for_project(project: &str, text: &str, handle: &JudgementHandle) {
    if project.trim().is_empty() {
        return;
    }
    let root = Path::new(project);
    let layout = WorkspaceLayout::discover(root);
    let service = SessionService::new(SessionStorage::new(layout.sessions_dir()), &layout.repo_root);
    maybe_open_session_with(&*handle.client, &handle.catalog, &service, text);
}

#[cfg(test)]
mod tests {
    use super::*;
    use cortex_judgement::{
        JudgementError, JudgementRequest, JudgementResponse, NullClient, Purpose,
    };
    use std::sync::Mutex;

    struct Script {
        calls: Mutex<Vec<JudgementResponse>>,
        on: bool,
    }
    impl JudgementClient for Script {
        fn enabled(&self, purpose: Purpose) -> bool {
            self.on && matches!(purpose, Purpose::Utterance)
        }
        fn evaluate(
            &self,
            _r: &JudgementRequest,
        ) -> Result<JudgementResponse, JudgementError> {
            let mut g = self.calls.lock().unwrap();
            if g.is_empty() {
                return Err(JudgementError::Http(429));
            }
            Ok(g.remove(0))
        }
    }

    fn work(choice: &str, session: f64) -> JudgementResponse {
        let mut answers = serde_json::Map::new();
        answers.insert(
            "work".into(),
            serde_json::json!({"choice": choice, "confidence": 0.95}),
        );
        answers.insert("needs_session".into(), serde_json::json!({"noul": session}));
        answers.insert("worth_remembering".into(), serde_json::json!({"noul": 0.0}));
        answers.insert("needs_finish".into(), serde_json::json!({"noul": 0.0}));
        JudgementResponse {
            model: "jev-1.13.0".into(),
            answers,
            usage: Default::default(),
            backend: "typesafe".into(),
        }
    }

    fn svc(dir: &Path) -> SessionService {
        let ses = dir.join(".cortex").join("sessions");
        std::fs::create_dir_all(&ses).unwrap();
        SessionService::new(SessionStorage::new(ses), dir)
    }

    #[test]
    fn question_does_not_open_session() {
        let tmp = tempfile::tempdir().unwrap();
        let service = svc(tmp.path());
        let catalog = Catalog::embedded().unwrap();
        let client = Script {
            calls: Mutex::new(vec![work("question", 0.05)]),
            on: true,
        };
        maybe_open_session_with(&client, &catalog, &service, "cómo funciona X");
        assert!(service.get_active().is_none());
    }

    #[test]
    fn implement_opens_session_when_none() {
        let tmp = tempfile::tempdir().unwrap();
        let service = svc(tmp.path());
        let catalog = Catalog::embedded().unwrap();
        let client = Script {
            calls: Mutex::new(vec![work("implement", 0.9)]),
            on: true,
        };
        maybe_open_session_with(&client, &catalog, &service, "arreglá Y");
        assert!(service.get_active().is_some());
    }

    #[test]
    fn http_429_does_not_open_session() {
        let tmp = tempfile::tempdir().unwrap();
        let service = svc(tmp.path());
        let catalog = Catalog::embedded().unwrap();
        let client = Script {
            calls: Mutex::new(vec![]),
            on: true,
        };
        maybe_open_session_with(&client, &catalog, &service, "arreglá Y");
        assert!(service.get_active().is_none());
    }

    #[test]
    fn direct_off_does_not_open_session() {
        let tmp = tempfile::tempdir().unwrap();
        let service = svc(tmp.path());
        let catalog = Catalog::embedded().unwrap();
        maybe_open_session_with(&NullClient, &catalog, &service, "arreglá Y");
        assert!(service.get_active().is_none());
    }
}
