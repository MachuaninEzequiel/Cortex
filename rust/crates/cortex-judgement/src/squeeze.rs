//! Pipeline squeeze (espejo de TypeSafeAI/eval/squeeze.py).
//! Opera sobre candidatos JSON, no UnifiedHit.

use serde_json::{json, Map, Value};

use crate::catalog::Catalog;
use crate::error::JudgementError;
use crate::purpose::Purpose;
use crate::request::JudgementRequest;
use crate::JudgementClient;

#[derive(Debug, Clone)]
pub struct Candidate {
    pub id: String,
    pub path: String,
    pub title: String,
    pub text: String,
}

#[derive(Debug, Clone)]
pub struct ScoredCandidate {
    pub candidate: Candidate,
    pub noul: f64,
    pub original_index: usize,
}

/// Over-fetch nativo cuando el purpose está on: max(top_k*3, 30).
pub fn squeeze_fetch_k(top_k: usize, catalog: &Catalog) -> usize {
    (top_k.saturating_mul(3)).max(catalog.overfetch)
}

/// Compass + Noul títulos + Noul cuerpos + drop. Fail-open en cualquier call.
pub fn squeeze_search(
    client: &dyn JudgementClient,
    catalog: &Catalog,
    query: &str,
    candidates: Vec<Candidate>,
    top_k: usize,
) -> Vec<ScoredCandidate> {
    if candidates.is_empty() {
        return Vec::new();
    }
    if !client.enabled(Purpose::SearchSqueeze) {
        return native_trunc(candidates, top_k);
    }

    let family = compass_family(client, catalog, query);
    let stage1 = match noul_batch(client, catalog, query, &candidates, &family, false) {
        Ok(scored) => scored,
        Err(_) => return native_trunc(candidates, top_k),
    };

    let keep = catalog.stage2_keep.min(stage1.len());
    let top12_idx: Vec<usize> = stage1.iter().take(keep).map(|s| s.original_index).collect();
    let top12: Vec<Candidate> = top12_idx.iter().map(|&i| candidates[i].clone()).collect();

    let stage2 = match noul_batch(client, catalog, query, &top12, &family, true) {
        Ok(mut scored) => {
            for s in &mut scored {
                s.original_index = top12_idx[s.original_index];
            }
            scored
        }
        Err(_) => stage1,
    };

    apply_drop(stage2, &candidates, catalog, top_k)
}

fn compass_family(client: &dyn JudgementClient, catalog: &Catalog, query: &str) -> String {
    let req = JudgementRequest::system_one(
        json!({ "query": query }),
        &catalog.model,
        catalog.compass_questions(),
    );
    match client.evaluate(&req) {
        Ok(resp) => {
            let ans = resp.answers.get("family");
            let choice = ans
                .and_then(|v| v.get("choice"))
                .and_then(|v| v.as_str())
                .unwrap_or("other");
            let conf = ans
                .and_then(|v| v.get("confidence"))
                .and_then(|v| v.as_f64())
                .unwrap_or(0.0);
            if conf < catalog.compass_confidence_below {
                "other".into()
            } else {
                choice.to_string()
            }
        }
        Err(_) => "other".into(),
    }
}

fn noul_batch(
    client: &dyn JudgementClient,
    catalog: &Catalog,
    query: &str,
    hits: &[Candidate],
    family: &str,
    use_body: bool,
) -> Result<Vec<ScoredCandidate>, JudgementError> {
    let mut state_cands = Vec::with_capacity(hits.len());
    let mut ids = Vec::with_capacity(hits.len());
    for (i, hit) in hits.iter().enumerate() {
        let cid = format!("c{i}");
        let mut item = Map::new();
        item.insert("id".into(), json!(cid));
        item.insert("path".into(), json!(hit.path));
        item.insert("title".into(), json!(hit.title));
        if use_body {
            let clipped: String = hit.text.chars().take(catalog.candidate_chars).collect();
            item.insert("text".into(), json!(clipped));
        }
        state_cands.push(Value::Object(item));
        ids.push(cid);
    }
    let questions = catalog.noul_questions(query, family, &ids, use_body);
    let req = JudgementRequest::system_one(
        json!({
            "query": query,
            "family": family,
            "candidates": state_cands,
        }),
        &catalog.model,
        questions,
    );
    let resp = client.evaluate(&req)?;
    let mut scored: Vec<ScoredCandidate> = hits
        .iter()
        .enumerate()
        .map(|(i, hit)| {
            let key = format!("rel_c{i}");
            let noul = resp
                .answers
                .get(&key)
                .and_then(|v| v.get("noul"))
                .and_then(|v| v.as_f64())
                .unwrap_or(0.0);
            ScoredCandidate {
                candidate: hit.clone(),
                noul,
                original_index: i,
            }
        })
        .collect();
    scored.sort_by(|a, b| b.noul.total_cmp(&a.noul));
    Ok(scored)
}

fn apply_drop(
    scored: Vec<ScoredCandidate>,
    native: &[Candidate],
    catalog: &Catalog,
    top_k: usize,
) -> Vec<ScoredCandidate> {
    let passing: Vec<ScoredCandidate> = scored
        .iter()
        .filter(|s| s.noul >= catalog.drop_below)
        .cloned()
        .collect();
    if passing.is_empty() {
        return native_trunc(native.to_vec(), 3.min(top_k));
    }
    passing.into_iter().take(top_k).collect()
}

fn native_trunc(candidates: Vec<Candidate>, top_k: usize) -> Vec<ScoredCandidate> {
    candidates
        .into_iter()
        .enumerate()
        .take(top_k)
        .map(|(i, c)| ScoredCandidate {
            candidate: c,
            noul: 0.0,
            original_index: i,
        })
        .collect()
}

/// Rankea candidatos de promote. Fail-open: orden nativo, noul=0.
pub fn rank_promotion(
    client: &dyn JudgementClient,
    catalog: &Catalog,
    candidates: Vec<Candidate>,
) -> Vec<ScoredCandidate> {
    if candidates.is_empty() {
        return Vec::new();
    }
    let n = candidates.len();
    if !client.enabled(Purpose::Promotion) {
        return native_trunc(candidates, n);
    }
    let mut state_cands = Vec::with_capacity(candidates.len());
    let mut ids = Vec::with_capacity(candidates.len());
    for (i, hit) in candidates.iter().enumerate() {
        let cid = format!("c{i}");
        state_cands.push(json!({
            "id": cid,
            "path": hit.path,
            "title": hit.title,
        }));
        ids.push(cid);
    }
    let req = JudgementRequest::system_one(
        json!({ "candidates": state_cands }),
        &catalog.model,
        catalog.promotion_noul_questions(&ids),
    );
    match client.evaluate(&req) {
        Ok(resp) => {
            let mut scored: Vec<ScoredCandidate> = candidates
                .iter()
                .enumerate()
                .map(|(i, hit)| {
                    let key = format!("rel_c{i}");
                    let noul = resp
                        .answers
                        .get(&key)
                        .and_then(|v| v.get("noul"))
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0);
                    ScoredCandidate {
                        candidate: hit.clone(),
                        noul,
                        original_index: i,
                    }
                })
                .collect();
            scored.sort_by(|a, b| b.noul.total_cmp(&a.noul));
            scored
        }
        Err(_) => native_trunc(candidates, n),
    }
}
