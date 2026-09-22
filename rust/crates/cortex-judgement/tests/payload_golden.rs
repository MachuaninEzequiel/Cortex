//! El JSON a TypeSafe tiene keys `state` / `questions`. Independiente del SDK Python.

use cortex_judgement::{Catalog, JudgementRequest};
use serde_json::Value;

#[test]
fn compass_payload_has_state_and_questions() {
    let catalog = Catalog::embedded().unwrap();
    let req = JudgementRequest::system_one(
        serde_json::json!({ "query": "how does session checkpoint verification work" }),
        &catalog.model,
        catalog.compass_questions(),
    );
    let body = &req.body;
    assert!(body.get("state").is_some(), "keys state/questions: {body}");
    assert!(body.get("questions").is_some(), "{body}");
    assert_eq!(body["model"], "jev-1.13.0");
    assert_eq!(
        body["questions"]["family"]["type"], "choice",
        "compass es Choice"
    );
    assert_eq!(
        body["questions"]["family"]["instructions"]["question"],
        "Which Cortex subsystem is this query primarily about?"
    );
    assert!(body["questions"]["family"]["criteria"]
        .get("session")
        .is_some());
}

#[test]
fn noul_payload_candidates_and_rel_ids() {
    let catalog = Catalog::embedded().unwrap();
    let ids = vec!["c0".into(), "c1".into()];
    let questions = catalog.noul_questions("q", "session", &ids, false);
    let req = JudgementRequest::system_one(
        serde_json::json!({
            "query": "q",
            "family": "session",
            "candidates": [
                {"id": "c0", "path": "a.md", "title": "A"},
                {"id": "c1", "path": "b.md", "title": "B"}
            ]
        }),
        &catalog.model,
        questions,
    );
    let body = &req.body;
    assert!(body.get("state").is_some());
    assert!(body.get("questions").is_some());
    let cands = body["state"]["candidates"].as_array().unwrap();
    assert_eq!(cands.len(), 2);
    assert!(cands[0].get("text").is_none(), "stage1 no manda text");
    let q = &body["questions"];
    assert_eq!(q["rel_c0"]["type"], "noul");
    let instr = q["rel_c0"]["instructions"].as_str().unwrap();
    assert!(instr.contains("`title` + `path`"));
    assert!(instr.contains("actual mechanism"));
}

#[test]
fn noul_body_stage_includes_text_inspect() {
    let catalog = Catalog::embedded().unwrap();
    let q: Value = catalog.noul_question("q", "retrieval", "c0", true);
    let instr = q["instructions"].as_str().unwrap();
    assert!(instr.contains("`title` + `text`"));
}
