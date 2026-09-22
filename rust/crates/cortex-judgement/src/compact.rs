//! Compactación de historial (P3, session_compact).
//! Tool results de Brain: noul keep_call / keep_result, pin últimos N, verbatim (no summary).
//! Fail-open ⇒ None / transcript intacto.

use crate::catalog::Catalog;
use crate::purpose::Purpose;
use crate::request::JudgementRequest;
use crate::JudgementClient;

pub const KEEP_CALL: f64 = 0.25;
pub const KEEP_RESULT: f64 = 0.25;
pub const DEFAULT_PIN_LAST_N: usize = 4;
pub const TRUNCATED_RESULT_MARKER: &str = "[output truncated verbatim by session_compact]";

#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct CompactCandidate {
    pub id: String,
    pub tool: String,
    pub args: String,
    pub output: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct CompactDecision {
    pub id: String,
    pub keep_call: f64,
    pub keep_result: f64,
}

impl CompactDecision {
    pub fn should_keep_call(&self) -> bool {
        self.keep_call >= KEEP_CALL
    }

    pub fn should_keep_result(&self) -> bool {
        self.keep_result >= KEEP_RESULT
    }
}

/// Evalúa en un solo batch HTTP los candidatos de tool call / result.
/// Fail-open: si el purpose está off o hay error (429, timeout), devuelve `None`.
pub fn evaluate_session_compact(
    client: &dyn JudgementClient,
    catalog: &Catalog,
    candidates: &[CompactCandidate],
) -> Option<Vec<CompactDecision>> {
    if candidates.is_empty() {
        return Some(Vec::new());
    }
    if !client.enabled(Purpose::SessionCompact) {
        return None;
    }

    let state_candidates: Vec<serde_json::Value> = candidates
        .iter()
        .map(|c| {
            let snippet = if c.output.chars().count() > 500 {
                let prefix: String = c.output.chars().take(500).collect();
                format!("{prefix}...")
            } else {
                c.output.clone()
            };
            serde_json::json!({
                "id": c.id,
                "tool": c.tool,
                "args": c.args,
                "snippet": snippet,
            })
        })
        .collect();

    let req = JudgementRequest::system_one(
        serde_json::json!({
            "candidates": state_candidates,
        }),
        &catalog.model,
        catalog.session_compact_questions(candidates),
    );

    let resp = client.evaluate(&req).ok()?;
    let mut decisions = Vec::with_capacity(candidates.len());
    for c in candidates {
        let call_key = format!("keep_call_{}", c.id);
        let result_key = format!("keep_result_{}", c.id);
        let keep_call = noul_value(resp.answers.get(&call_key));
        let keep_result = noul_value(resp.answers.get(&result_key));
        decisions.push(CompactDecision {
            id: c.id.clone(),
            keep_call,
            keep_result,
        });
    }
    Some(decisions)
}

fn noul_value(val: Option<&serde_json::Value>) -> f64 {
    let Some(v) = val else { return 0.0 };
    v.get("noul")
        .and_then(|n| n.as_f64())
        .or_else(|| v.as_f64())
        .unwrap_or(0.0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::error::JudgementError;
    use crate::request::JudgementResponse;
    use std::sync::atomic::{AtomicUsize, Ordering};

    struct MockClient {
        enabled: bool,
        eval_fn: Box<dyn Fn(&JudgementRequest) -> Result<JudgementResponse, JudgementError> + Send + Sync>,
        calls: AtomicUsize,
    }

    impl JudgementClient for MockClient {
        fn enabled(&self, purpose: Purpose) -> bool {
            self.enabled && matches!(purpose, Purpose::SessionCompact)
        }

        fn evaluate(&self, req: &JudgementRequest) -> Result<JudgementResponse, JudgementError> {
            self.calls.fetch_add(1, Ordering::SeqCst);
            (self.eval_fn)(req)
        }
    }

    #[test]
    fn disabled_returns_none_zero_calls() {
        let catalog = Catalog::embedded().unwrap();
        let client = MockClient {
            enabled: false,
            eval_fn: Box::new(|_| unreachable!()),
            calls: AtomicUsize::new(0),
        };
        let candidates = vec![CompactCandidate {
            id: "msg-1".into(),
            tool: "memory.search".into(),
            args: "jwt".into(),
            output: "some long output".into(),
        }];
        let res = evaluate_session_compact(&client, &catalog, &candidates);
        assert!(res.is_none());
        assert_eq!(client.calls.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn empty_candidates_returns_empty_zero_calls() {
        let catalog = Catalog::embedded().unwrap();
        let client = MockClient {
            enabled: true,
            eval_fn: Box::new(|_| unreachable!()),
            calls: AtomicUsize::new(0),
        };
        let res = evaluate_session_compact(&client, &catalog, &[]);
        assert_eq!(res, Some(Vec::new()));
        assert_eq!(client.calls.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn error_429_fails_open_returns_none() {
        let catalog = Catalog::embedded().unwrap();
        let client = MockClient {
            enabled: true,
            eval_fn: Box::new(|_| Err(JudgementError::Http(429))),
            calls: AtomicUsize::new(0),
        };
        let candidates = vec![CompactCandidate {
            id: "msg-1".into(),
            tool: "memory.search".into(),
            args: "jwt".into(),
            output: "output".into(),
        }];
        let res = evaluate_session_compact(&client, &catalog, &candidates);
        assert!(res.is_none(), "fail-open on 429 returns None");
        assert_eq!(client.calls.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn evaluates_candidates_and_parses_noul() {
        let catalog = Catalog::embedded().unwrap();
        let client = MockClient {
            enabled: true,
            eval_fn: Box::new(|req| {
                assert!(req.body.get("questions").is_some());
                let mut answers = serde_json::Map::new();
                // candidate 1: keep_call 0.90, keep_result 0.10 (drop result)
                answers.insert(
                    "keep_call_c1".into(),
                    serde_json::json!({ "noul": 0.90 }),
                );
                answers.insert(
                    "keep_result_c1".into(),
                    serde_json::json!({ "noul": 0.10 }),
                );
                // candidate 2: keep_call 0.10, keep_result 0.80
                answers.insert(
                    "keep_call_c2".into(),
                    serde_json::json!({ "noul": 0.10 }),
                );
                answers.insert(
                    "keep_result_c2".into(),
                    serde_json::json!({ "noul": 0.80 }),
                );
                Ok(JudgementResponse {
                    model: "jev-1.13.0".into(),
                    answers,
                    usage: Default::default(),
                    backend: "typesafe".into(),
                })
            }),
            calls: AtomicUsize::new(0),
        };
        let candidates = vec![
            CompactCandidate {
                id: "c1".into(),
                tool: "memory.search".into(),
                args: "auth".into(),
                output: "line 1\nline 2".into(),
            },
            CompactCandidate {
                id: "c2".into(),
                tool: "webgraph.serve".into(),
                args: "".into(),
                output: "ok".into(),
            },
        ];
        let decisions = evaluate_session_compact(&client, &catalog, &candidates).unwrap();
        assert_eq!(decisions.len(), 2);
        assert_eq!(decisions[0].id, "c1");
        assert!(decisions[0].should_keep_call());
        assert!(!decisions[0].should_keep_result()); // 0.10 < 0.25

        assert_eq!(decisions[1].id, "c2");
        assert!(!decisions[1].should_keep_call()); // 0.10 < 0.25
        assert!(decisions[1].should_keep_result()); // 0.80 >= 0.25
    }
}
