//! Portero utterance (spec 09): question no abre sesión; implement sí; 429 fail-open.

use std::sync::Mutex;

use cortex_judgement::{
    allow_remember, classify_utterance, Catalog, JudgementClient, JudgementError, JudgementRequest,
    JudgementResponse, NullClient, Purpose, WorkKind,
};

struct Script {
    calls: Mutex<Vec<Result<JudgementResponse, JudgementError>>>,
    on: bool,
}

impl Script {
    fn on(calls: Vec<Result<JudgementResponse, JudgementError>>) -> Self {
        Self {
            calls: Mutex::new(calls),
            on: true,
        }
    }
}

impl JudgementClient for Script {
    fn enabled(&self, purpose: Purpose) -> bool {
        self.on && matches!(purpose, Purpose::Utterance)
    }
    fn evaluate(&self, _request: &JudgementRequest) -> Result<JudgementResponse, JudgementError> {
        let mut g = self.calls.lock().unwrap();
        if g.is_empty() {
            return Err(JudgementError::Http(429));
        }
        g.remove(0)
    }
}

fn resp_work(choice: &str, conf: f64, session: f64, remember: f64, finish: f64) -> JudgementResponse {
    let mut answers = serde_json::Map::new();
    answers.insert(
        "work".into(),
        serde_json::json!({"choice": choice, "confidence": conf}),
    );
    answers.insert("needs_session".into(), serde_json::json!({"noul": session}));
    answers.insert(
        "worth_remembering".into(),
        serde_json::json!({"noul": remember}),
    );
    answers.insert("needs_finish".into(), serde_json::json!({"noul": finish}));
    JudgementResponse {
        model: "jev-1.13.0".into(),
        answers,
        usage: Default::default(),
        backend: "typesafe".into(),
    }
}

#[test]
fn utterance_off_returns_none() {
    let catalog = Catalog::embedded().unwrap();
    assert!(classify_utterance(&NullClient, &catalog, "cómo funciona X", false, &[]).is_none());
}

#[test]
fn question_does_not_open_session_nor_remember() {
    let catalog = Catalog::embedded().unwrap();
    let client = Script::on(vec![Ok(resp_work("question", 0.95, 0.05, 0.05, 0.0))]);
    let j = classify_utterance(
        &client,
        &catalog,
        "cómo funciona el checkpoint verification",
        false,
        &[],
    )
    .unwrap();
    assert_eq!(j.work, WorkKind::Question);
    assert!(!j.should_open_session(false));
    assert!(!j.should_remember());
}

#[test]
fn implement_without_session_opens() {
    let catalog = Catalog::embedded().unwrap();
    let client = Script::on(vec![Ok(resp_work("implement", 0.9, 0.88, 0.7, 0.1))]);
    let j = classify_utterance(
        &client,
        &catalog,
        "arreglá el gate que deja pasar checkpoints vacíos",
        false,
        &[],
    )
    .unwrap();
    assert_eq!(j.work, WorkKind::Implement);
    assert!(j.should_open_session(false));
    assert!(!j.should_open_session(true), "ya hay sesión ⇒ no abrir otra");
    assert!(j.should_remember());
}

#[test]
fn utterance_429_returns_none() {
    let catalog = Catalog::embedded().unwrap();
    let client = Script::on(vec![Err(JudgementError::Http(429))]);
    assert!(
        classify_utterance(&client, &catalog, "arreglá Y", false, &[]).is_none(),
        "429 ⇒ no inventar sesión"
    );
}

#[test]
fn low_confidence_is_question() {
    let catalog = Catalog::embedded().unwrap();
    let client = Script::on(vec![Ok(resp_work("implement", 0.3, 0.9, 0.9, 0.0))]);
    let j = classify_utterance(&client, &catalog, "tal vez?", false, &[]).unwrap();
    assert_eq!(j.work, WorkKind::Question);
    assert!(!j.should_open_session(false));
}

#[test]
fn worth_remembering_low_skips() {
    let catalog = Catalog::embedded().unwrap();
    let client = Script::on(vec![Ok(resp_work("implement", 0.9, 0.8, 0.1, 0.0))]);
    let j = classify_utterance(&client, &catalog, "arreglá Y", false, &[]).unwrap();
    assert!(!j.should_remember());
}

#[test]
fn payload_has_state_and_questions() {
    struct Cap {
        inner: Script,
        captured: Mutex<Vec<JudgementRequest>>,
    }
    impl JudgementClient for Cap {
        fn enabled(&self, p: Purpose) -> bool {
            self.inner.enabled(p)
        }
        fn evaluate(&self, r: &JudgementRequest) -> Result<JudgementResponse, JudgementError> {
            self.captured.lock().unwrap().push(r.clone());
            self.inner.evaluate(r)
        }
    }
    let catalog = Catalog::embedded().unwrap();
    let cap = Cap {
        inner: Script::on(vec![Ok(resp_work("question", 1.0, 0.0, 0.0, 0.0))]),
        captured: Mutex::new(Vec::new()),
    };
    let _ = classify_utterance(&cap, &catalog, "cómo funciona X", false, &["a.rs".into()]);
    let req = &cap.captured.lock().unwrap()[0];
    assert!(req.body.get("state").is_some());
    assert!(req.body.get("questions").is_some());
    assert!(req.body["questions"].get("work").is_some());
    assert!(req.body["questions"].get("needs_session").is_some());
    assert!(req.body["questions"].get("worth_remembering").is_some());
    assert!(req.body["state"]["files"].is_array());
}

#[test]
fn allow_remember_fail_open_and_question() {
    let catalog = Catalog::embedded().unwrap();
    assert!(allow_remember(&NullClient, &catalog, "cómo funciona X", &[]));
    let q = Script::on(vec![Ok(resp_work("question", 0.99, 0.0, 0.0, 0.0))]);
    assert!(!allow_remember(&q, &catalog, "cómo funciona X", &[]));
    let boom = Script::on(vec![Err(JudgementError::Http(429))]);
    assert!(allow_remember(&boom, &catalog, "arreglá Y", &[]));
    let low = Script::on(vec![Ok(resp_work("implement", 0.9, 0.8, 0.1, 0.0))]);
    assert!(!allow_remember(&low, &catalog, "arreglá Y", &[]));
}
