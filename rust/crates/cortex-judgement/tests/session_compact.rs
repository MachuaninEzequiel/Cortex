//! Tests de session_compact (P3): noul keep_call / keep_result, fail-open, default off.

use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Mutex;

use cortex_judgement::{
    build_handle, evaluate_session_compact, Catalog, ClientOptions, CompactCandidate,
    JudgementClient, JudgementError, JudgementRequest, JudgementResponse, Purpose,
    DEFAULT_PIN_LAST_N, KEEP_CALL, KEEP_RESULT, TRUNCATED_RESULT_MARKER,
};

struct ScriptClient {
    session_compact: bool,
    calls: Mutex<Vec<Result<JudgementResponse, JudgementError>>>,
    call_count: AtomicUsize,
}

impl ScriptClient {
    fn new(session_compact: bool, responses: Vec<Result<JudgementResponse, JudgementError>>) -> Self {
        Self {
            session_compact,
            calls: Mutex::new(responses),
            call_count: AtomicUsize::new(0),
        }
    }
}

impl JudgementClient for ScriptClient {
    fn enabled(&self, purpose: Purpose) -> bool {
        self.session_compact && matches!(purpose, Purpose::SessionCompact)
    }

    fn evaluate(&self, _request: &JudgementRequest) -> Result<JudgementResponse, JudgementError> {
        self.call_count.fetch_add(1, Ordering::SeqCst);
        let mut g = self.calls.lock().unwrap();
        if g.is_empty() {
            return Err(JudgementError::Http(429));
        }
        g.remove(0)
    }
}

#[test]
fn session_compact_off_returns_none_zero_http_calls() {
    let client = ScriptClient::new(false, vec![]);
    let catalog = Catalog::embedded().unwrap();
    let candidates = vec![CompactCandidate {
        id: "msg-1".into(),
        tool: "memory.search".into(),
        args: "query".into(),
        output: "results".into(),
    }];

    let res = evaluate_session_compact(&client, &catalog, &candidates);
    assert!(res.is_none(), "purpose off debe devolver None (fail-open)");
    assert_eq!(client.call_count.load(Ordering::SeqCst), 0);
}

#[test]
fn session_compact_429_fails_open_returns_none() {
    let client = ScriptClient::new(true, vec![Err(JudgementError::Http(429))]);
    let catalog = Catalog::embedded().unwrap();
    let candidates = vec![CompactCandidate {
        id: "msg-1".into(),
        tool: "memory.search".into(),
        args: "query".into(),
        output: "results".into(),
    }];

    let res = evaluate_session_compact(&client, &catalog, &candidates);
    assert!(res.is_none(), "429 debe fallar open (None, no error)");
    assert_eq!(client.call_count.load(Ordering::SeqCst), 1);
}

#[test]
fn session_compact_keeps_or_drops_according_to_thresholds() {
    let mut answers = serde_json::Map::new();
    // Item 1: keep_call 0.90, keep_result 0.15 (< 0.25 -> drop result)
    answers.insert("keep_call_1".into(), serde_json::json!({ "noul": 0.90 }));
    answers.insert("keep_result_1".into(), serde_json::json!({ "noul": 0.15 }));
    // Item 2: keep_call 0.10 (< 0.25 -> drop call), keep_result 0.85 (keep result)
    answers.insert("keep_call_2".into(), serde_json::json!({ "noul": 0.10 }));
    answers.insert("keep_result_2".into(), serde_json::json!({ "noul": 0.85 }));

    let client = ScriptClient::new(
        true,
        vec![Ok(JudgementResponse {
            model: "jev-1.13.0".into(),
            answers,
            usage: Default::default(),
            backend: "typesafe".into(),
        })],
    );
    let catalog = Catalog::embedded().unwrap();
    let candidates = vec![
        CompactCandidate {
            id: "1".into(),
            tool: "memory.search".into(),
            args: "authentication".into(),
            output: "200 lines of search results...".into(),
        },
        CompactCandidate {
            id: "2".into(),
            tool: "docs.related".into(),
            args: "architecture".into(),
            output: "Key architectural fact: RFC-1234".into(),
        },
    ];

    let decisions = evaluate_session_compact(&client, &catalog, &candidates).expect("evalúa ok");
    assert_eq!(decisions.len(), 2);

    assert_eq!(decisions[0].id, "1");
    assert!(decisions[0].should_keep_call());
    assert!(!decisions[0].should_keep_result()); // 0.15 < 0.25

    assert_eq!(decisions[1].id, "2");
    assert!(!decisions[1].should_keep_call()); // 0.10 < 0.25
    assert!(decisions[1].should_keep_result()); // 0.85 >= 0.25
}

#[test]
fn session_compact_build_handle_with_only_session_compact() {
    let mut opts = ClientOptions {
        enabled: true,
        provider: "typesafe".into(),
        session_compact: true,
        ..Default::default()
    };
    std::env::set_var("TYPESAFE_API_KEY", "dummy-key-for-test");
    opts.api_key_env = "TYPESAFE_API_KEY".into();

    let handle = build_handle(&opts);
    assert!(handle.is_some(), "session_compact: on debe activar el handle aun si otros purposes están off");
    assert!(handle.unwrap().client.enabled(Purpose::SessionCompact));
}

#[test]
fn constants_are_contractual() {
    assert_eq!(KEEP_CALL, 0.25);
    assert_eq!(KEEP_RESULT, 0.25);
    assert_eq!(DEFAULT_PIN_LAST_N, 4);
    assert_eq!(TRUNCATED_RESULT_MARKER, "[output truncated verbatim by session_compact]");
}
