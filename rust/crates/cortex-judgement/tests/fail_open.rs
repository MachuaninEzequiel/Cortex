//! Fail-open: 429 / error de evaluate no vacía el ranking nativo.

use std::io::{Read, Write};
use std::net::TcpListener;
use std::sync::Mutex;

use cortex_judgement::{
    squeeze_search, Candidate, Catalog, JudgementClient, JudgementError, JudgementRequest,
    JudgementResponse, Purpose, TypesafeClient,
};

struct ScriptClient {
    calls: Mutex<Vec<Result<JudgementResponse, JudgementError>>>,
}

impl ScriptClient {
    fn new(calls: Vec<Result<JudgementResponse, JudgementError>>) -> Self {
        Self {
            calls: Mutex::new(calls),
        }
    }
}

impl JudgementClient for ScriptClient {
    fn enabled(&self, purpose: Purpose) -> bool {
        matches!(purpose, Purpose::SearchSqueeze | Purpose::Promotion)
    }
    fn evaluate(&self, _request: &JudgementRequest) -> Result<JudgementResponse, JudgementError> {
        let mut g = self.calls.lock().unwrap();
        if g.is_empty() {
            return Err(JudgementError::Http(429));
        }
        g.remove(0)
    }
}

fn cands() -> Vec<Candidate> {
    vec![
        Candidate {
            id: "0".into(),
            path: "sessions.rs.md".into(),
            title: "sessions".into(),
            text: "mcp sessions backend".into(),
        },
        Candidate {
            id: "1".into(),
            path: "verification.md".into(),
            title: "verification".into(),
            text: "checkpoint verification".into(),
        },
        Candidate {
            id: "2".into(),
            path: "other.md".into(),
            title: "other".into(),
            text: "unrelated".into(),
        },
    ]
}

fn noul_resp(pairs: &[(&str, f64)]) -> JudgementResponse {
    let mut answers = serde_json::Map::new();
    for (k, n) in pairs {
        answers.insert((*k).into(), serde_json::json!({ "noul": n }));
    }
    JudgementResponse {
        model: "jev-1.13.0".into(),
        answers,
        usage: Default::default(),
        backend: "typesafe".into(),
    }
}

#[test]
fn stage1_429_returns_native_order_truncated() {
    let catalog = Catalog::embedded().unwrap();
    let client = ScriptClient::new(vec![
        Ok(JudgementResponse {
            model: "jev-1.13.0".into(),
            answers: {
                let mut m = serde_json::Map::new();
                m.insert(
                    "family".into(),
                    serde_json::json!({"choice": "session", "confidence": 1.0}),
                );
                m
            },
            usage: Default::default(),
            backend: "typesafe".into(),
        }),
        Err(JudgementError::Http(429)),
    ]);
    let out = squeeze_search(&client, &catalog, "checkpoint verification", cands(), 2);
    assert_eq!(out.len(), 2);
    assert_eq!(out[0].candidate.path, "sessions.rs.md");
    assert_eq!(out[1].candidate.path, "verification.md");
}

#[test]
fn successful_noul_reorders_and_drops_low() {
    let catalog = Catalog::embedded().unwrap();
    let client = ScriptClient::new(vec![
        Ok(JudgementResponse {
            model: "jev-1.13.0".into(),
            answers: {
                let mut m = serde_json::Map::new();
                m.insert(
                    "family".into(),
                    serde_json::json!({"choice": "session", "confidence": 1.0}),
                );
                m
            },
            usage: Default::default(),
            backend: "typesafe".into(),
        }),
        Ok(noul_resp(&[
            ("rel_c0", 0.1),
            ("rel_c1", 0.9),
            ("rel_c2", 0.05),
        ])),
        Ok(noul_resp(&[("rel_c0", 0.95), ("rel_c1", 0.1)])),
    ]);
    let out = squeeze_search(&client, &catalog, "checkpoint verification", cands(), 5);
    assert!(!out.is_empty());
    assert_eq!(out[0].candidate.path, "verification.md");
    assert!(out.iter().all(|s| s.noul >= catalog.drop_below));
}

#[test]
fn all_below_threshold_keeps_top3_native() {
    let catalog = Catalog::embedded().unwrap();
    let client = ScriptClient::new(vec![
        Ok(JudgementResponse {
            model: "jev-1.13.0".into(),
            answers: {
                let mut m = serde_json::Map::new();
                m.insert(
                    "family".into(),
                    serde_json::json!({"choice": "other", "confidence": 1.0}),
                );
                m
            },
            usage: Default::default(),
            backend: "typesafe".into(),
        }),
        Ok(noul_resp(&[
            ("rel_c0", 0.01),
            ("rel_c1", 0.02),
            ("rel_c2", 0.03),
        ])),
        Ok(noul_resp(&[
            ("rel_c0", 0.03),
            ("rel_c1", 0.02),
            ("rel_c2", 0.01),
        ])),
    ]);
    let out = squeeze_search(&client, &catalog, "q", cands(), 5);
    assert_eq!(out.len(), 3);
    assert_eq!(out[0].candidate.path, "sessions.rs.md");
}

fn serve_status(status: u16, body: &'static str) -> String {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    std::thread::spawn(move || {
        for _ in 0..4 {
            let Ok((mut s, _)) = listener.accept() else {
                break;
            };
            let mut buf = [0u8; 2048];
            let _ = s.read(&mut buf);
            let resp = format!(
                "HTTP/1.1 {status} X\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
                body.len()
            );
            let _ = s.write_all(resp.as_bytes());
        }
    });
    format!("http://{addr}")
}

#[test]
fn typesafe_client_429_is_http_error_after_retry() {
    let url = serve_status(429, "{\"error\":\"rate\"}");
    let client = TypesafeClient::new(
        &url,
        "k".into(),
        "jev-1.13.0".into(),
        800,
        true,
        false,
        false,
        false,
        false,
        false,
    );
    let req = JudgementRequest::system_one(
        serde_json::json!({"query": "q"}),
        "jev-1.13.0",
        serde_json::json!({"family": {"type": "choice"}}),
    );
    let err = client.evaluate(&req).unwrap_err();
    assert_eq!(err, JudgementError::Http(429));
}

#[test]
fn disabled_client_skips() {
    assert!(!cortex_judgement::NullClient.enabled(Purpose::SearchSqueeze));
}

#[test]
fn build_handle_none_without_key() {
    let mut opts = cortex_judgement::ClientOptions::default();
    opts.enabled = true;
    opts.provider = "typesafe".into();
    opts.search_squeeze = true;
    opts.api_key_env = "CORTEX_JUDGEMENT_TEST_NO_KEY".into();
    std::env::remove_var("CORTEX_JUDGEMENT_TEST_NO_KEY");
    assert!(cortex_judgement::build_handle(&opts).is_none());
    assert_eq!(
        cortex_judgement::status(&opts),
        cortex_judgement::JudgementStatus::Degraded
    );
}

#[test]
fn build_handle_with_only_utterance() {
    let mut opts = cortex_judgement::ClientOptions::default();
    opts.enabled = true;
    opts.provider = "typesafe".into();
    opts.utterance = true;
    opts.api_key_env = "CORTEX_JUDGEMENT_TEST_UTT_KEY".into();
    std::env::set_var("CORTEX_JUDGEMENT_TEST_UTT_KEY", "x");
    assert!(cortex_judgement::build_handle(&opts).is_some());
    std::env::remove_var("CORTEX_JUDGEMENT_TEST_UTT_KEY");
}

#[test]
fn build_handle_with_only_context_pack() {
    let mut opts = cortex_judgement::ClientOptions::default();
    opts.enabled = true;
    opts.provider = "typesafe".into();
    opts.context_pack = true;
    opts.api_key_env = "CORTEX_JUDGEMENT_TEST_PACK_KEY".into();
    std::env::set_var("CORTEX_JUDGEMENT_TEST_PACK_KEY", "x");
    assert!(cortex_judgement::build_handle(&opts).is_some());
    std::env::remove_var("CORTEX_JUDGEMENT_TEST_PACK_KEY");
}

#[test]
fn resolve_api_key_prefers_env() {
    std::env::set_var("CORTEX_JUDGEMENT_TEST_KEY", "from-env");
    let v = cortex_judgement::resolve_api_key("CORTEX_JUDGEMENT_TEST_KEY").unwrap();
    assert_eq!(v, "from-env");
    std::env::remove_var("CORTEX_JUDGEMENT_TEST_KEY");
}
