//! Pack de contexto (spec 07): canónicos + punteros. Fail-open ⇒ None.

use serde_json::{json, Map, Value};

use crate::catalog::Catalog;
use crate::purpose::Purpose;
use crate::request::JudgementRequest;
use crate::squeeze::{Candidate, ScoredCandidate};
use crate::JudgementClient;

pub const KEEP_BODY: f64 = 0.50;
pub const KEEP_PTR: f64 = 0.25;
pub const MAX_CANONICAL: usize = 2;
pub const MAX_POINTERS: usize = 6;
pub const MAX_RELATED_POINTERS: usize = 2;
pub const VALID_PACK_RELATIONS: &[&str] = &["wikilink", "implements", "constrains"];
#[allow(dead_code)]
pub const PACK_PROMPT_CHARS: usize = 1800;
const POINTER_LINE_CHARS: usize = 80;

/// Arista tipada del modelo de grafo nativo (spec 07 §5).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PackEdge {
    pub source: String,
    pub target: String,
    pub rel: String,
    pub line: Option<String>,
}

impl PackEdge {
    pub fn new(source: impl Into<String>, target: impl Into<String>, rel: impl Into<String>) -> Self {
        Self {
            source: source.into(),
            target: target.into(),
            rel: rel.into(),
            line: None,
        }
    }

    pub fn with_line(
        source: impl Into<String>,
        target: impl Into<String>,
        rel: impl Into<String>,
        line: impl Into<String>,
    ) -> Self {
        Self {
            source: source.into(),
            target: target.into(),
            rel: rel.into(),
            line: Some(line.into()),
        }
    }
}

#[derive(Debug, Clone)]
pub struct PackPointer {
    pub path: String,
    pub title: String,
    pub rel: String,
    pub line: String,
    pub noul: f64,
    pub original_index: usize,
}

#[derive(Debug, Clone)]
pub struct ContextPack {
    pub family: String,
    pub canonical: Vec<ScoredCandidate>,
    pub pointers: Vec<PackPointer>,
    pub dropped: usize,
}

struct DualScore {
    body: f64,
    ptr: f64,
}

/// Over-fetch del enricher cuando el purpose está on: max(max_items*2, 16).
pub fn pack_fetch_k(max_items: usize) -> usize {
    max_items.saturating_mul(2).max(16)
}

/// `None` = presenter nativo (off, 429, nadie pasa umbral).
pub fn pack_context(
    client: &dyn JudgementClient,
    catalog: &Catalog,
    query: &str,
    files: &[String],
    candidates: Vec<Candidate>,
    pinned_paths: &[String],
) -> Option<ContextPack> {
    pack_context_with_edges(client, catalog, query, files, candidates, pinned_paths, &[])
}

/// Pack con aristas tipadas del grafo nativo (spec 07 §5).
pub fn pack_context_with_edges(
    client: &dyn JudgementClient,
    catalog: &Catalog,
    query: &str,
    files: &[String],
    candidates: Vec<Candidate>,
    pinned_paths: &[String],
    edges: &[PackEdge],
) -> Option<ContextPack> {
    if candidates.is_empty() {
        return None;
    }
    if !client.enabled(Purpose::ContextPack) {
        return None;
    }

    let family = compass_family(client, catalog, query, files)?;
    let scores = dual_noul(client, catalog, query, files, &family, &candidates)?;
    assemble(candidates, scores, files, pinned_paths, family, edges)
}

fn goal_state(query: &str, files: &[String]) -> String {
    if files.is_empty() {
        query.to_string()
    } else {
        format!("{query}\nfiles: {}", files.join(", "))
    }
}

fn compass_family(
    client: &dyn JudgementClient,
    catalog: &Catalog,
    query: &str,
    files: &[String],
) -> Option<String> {
    let req = JudgementRequest::system_one(
        json!({
            "query": query,
            "goal": goal_state(query, files),
            "files": files,
        }),
        &catalog.model,
        catalog.compass_questions(),
    );
    let resp = client.evaluate(&req).ok()?;
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
        Some("other".into())
    } else {
        Some(choice.to_string())
    }
}

fn dual_noul(
    client: &dyn JudgementClient,
    catalog: &Catalog,
    query: &str,
    files: &[String],
    family: &str,
    hits: &[Candidate],
) -> Option<Vec<DualScore>> {
    let mut state_cands = Vec::with_capacity(hits.len());
    let mut ids = Vec::with_capacity(hits.len());
    for (i, hit) in hits.iter().enumerate() {
        let cid = format!("c{i}");
        let clipped: String = hit.text.chars().take(catalog.candidate_chars).collect();
        let mut item = Map::new();
        item.insert("id".into(), json!(cid));
        item.insert("path".into(), json!(hit.path));
        item.insert("title".into(), json!(hit.title));
        item.insert("text".into(), json!(clipped));
        state_cands.push(Value::Object(item));
        ids.push(cid);
    }
    let req = JudgementRequest::system_one(
        json!({
            "query": query,
            "goal": goal_state(query, files),
            "files": files,
            "family": family,
            "candidates": state_cands,
        }),
        &catalog.model,
        catalog.pack_noul_questions(query, family, &ids),
    );
    let resp = client.evaluate(&req).ok()?;
    Some(
        hits.iter()
            .enumerate()
            .map(|(i, _)| {
                let body = resp
                    .answers
                    .get(&format!("rel_c{i}_body"))
                    .and_then(|v| v.get("noul"))
                    .and_then(|v| v.as_f64())
                    .unwrap_or(0.0);
                let ptr = resp
                    .answers
                    .get(&format!("rel_c{i}_ptr"))
                    .and_then(|v| v.get("noul"))
                    .and_then(|v| v.as_f64())
                    .unwrap_or(0.0);
                DualScore { body, ptr }
            })
            .collect(),
    )
}

fn is_pinned(path: &str, pinned: &[String]) -> bool {
    pinned
        .iter()
        .any(|p| p == path || path.ends_with(p.as_str()) || p.ends_with(path))
}

fn clip_line(s: &str, n: usize) -> String {
    s.chars().take(n).collect()
}

fn path_matches(a: &str, b: &str) -> bool {
    if a.is_empty() || b.is_empty() {
        return false;
    }
    if a.eq_ignore_ascii_case(b) {
        return true;
    }
    let norm_a = a.replace('\\', "/").trim_start_matches("./").to_lowercase();
    let norm_b = b.replace('\\', "/").trim_start_matches("./").to_lowercase();
    if norm_a == norm_b {
        return true;
    }
    if norm_a.ends_with(&format!("/{norm_b}")) || norm_b.ends_with(&format!("/{norm_a}")) {
        return true;
    }
    let fname_a = norm_a.rsplit('/').next().unwrap_or(&norm_a);
    let fname_b = norm_b.rsplit('/').next().unwrap_or(&norm_b);
    if fname_a == fname_b {
        return true;
    }
    false
}

fn assemble(
    candidates: Vec<Candidate>,
    scores: Vec<DualScore>,
    files: &[String],
    pinned_paths: &[String],
    family: String,
    edges: &[PackEdge],
) -> Option<ContextPack> {
    let n = candidates.len();
    let mut order: Vec<usize> = (0..n).collect();
    order.sort_by(|&a, &b| scores[b].body.total_cmp(&scores[a].body));

    let max_can = if files.is_empty() { 1 } else { MAX_CANONICAL };
    let mut canonical = Vec::new();
    let mut used = vec![false; n];
    for idx in &order {
        if canonical.len() >= max_can {
            break;
        }
        if scores[*idx].body >= KEEP_BODY {
            canonical.push(ScoredCandidate {
                candidate: candidates[*idx].clone(),
                noul: scores[*idx].body,
                original_index: *idx,
            });
            used[*idx] = true;
        }
    }

    // Spec 07 §5: Vecindario de los canónicos después del noul.
    // Solo aristas tipadas: wikilink | implements | constrains.
    let mut validated_neighbors: Vec<(String, String, Option<String>)> = Vec::new();
    let mut seen_neighbors: std::collections::HashSet<String> = std::collections::HashSet::new();
    for can in &canonical {
        seen_neighbors.insert(can.candidate.path.to_lowercase());
    }

    for edge in edges {
        let rel = edge.rel.trim().to_lowercase();
        if !VALID_PACK_RELATIONS.contains(&rel.as_str()) {
            continue;
        }

        let mut matched_neighbor = None;
        for can in &canonical {
            if path_matches(&can.candidate.path, &edge.source) {
                if !path_matches(&can.candidate.path, &edge.target) {
                    matched_neighbor = Some(edge.target.clone());
                    break;
                }
            } else if path_matches(&can.candidate.path, &edge.target) {
                if !path_matches(&can.candidate.path, &edge.source) {
                    matched_neighbor = Some(edge.source.clone());
                    break;
                }
            }
        }

        if let Some(neigh) = matched_neighbor {
            let key = neigh.to_lowercase();
            if !seen_neighbors.contains(&key) {
                seen_neighbors.insert(key);
                validated_neighbors.push((neigh, rel, edge.line.clone()));
            }
        }
    }

    let has_validated_edges = !validated_neighbors.is_empty();
    let mut pointers = Vec::new();
    let mut pointer_paths: std::collections::HashSet<String> = std::collections::HashSet::new();

    // 1. Agregar aristas validadas desde canónicos (hasta MAX_POINTERS)
    for (neigh_path, rel, edge_line) in validated_neighbors {
        if pointers.len() >= MAX_POINTERS {
            break;
        }
        let cand_idx = candidates.iter().position(|c| path_matches(&c.path, &neigh_path));
        if let Some(idx) = cand_idx {
            used[idx] = true;
            let line = edge_line.unwrap_or_else(|| clip_line(&candidates[idx].title, POINTER_LINE_CHARS));
            pointer_paths.insert(candidates[idx].path.to_lowercase());
            pointers.push(PackPointer {
                path: candidates[idx].path.clone(),
                title: candidates[idx].title.clone(),
                rel,
                line,
                noul: scores[idx].ptr,
                original_index: idx,
            });
        } else {
            let title = edge_line.clone().unwrap_or_else(|| neigh_path.clone());
            let line = clip_line(&title, POINTER_LINE_CHARS);
            pointer_paths.insert(neigh_path.to_lowercase());
            pointers.push(PackPointer {
                path: neigh_path,
                title,
                rel,
                line,
                noul: 1.0,
                original_index: usize::MAX,
            });
        }
    }

    // 2. Candidatos con keep_ptr >= 0.25 (fallback related)
    // Spec 07 §3.2: "fallback si no hay tipo; máx 2 related por pack"
    // Spec 07 §5: "si no hay índice de grafo / no hay aristas tipadas: fail-open a punteros noul-only"
    let max_related = if has_validated_edges {
        MAX_RELATED_POINTERS
    } else {
        MAX_POINTERS
    };
    let mut related_count = 0;

    let mut ptr_order: Vec<usize> = (0..n).collect();
    ptr_order.sort_by(|&a, &b| scores[b].ptr.total_cmp(&scores[a].ptr));

    for idx in ptr_order {
        if pointers.len() >= MAX_POINTERS {
            break;
        }
        if used[idx] {
            continue;
        }
        let pin = is_pinned(&candidates[idx].path, pinned_paths);
        if scores[idx].ptr >= KEEP_PTR || pin {
            if !pin && related_count >= max_related {
                continue;
            }
            let key = candidates[idx].path.to_lowercase();
            if !pointer_paths.contains(&key) {
                pointer_paths.insert(key);
                pointers.push(PackPointer {
                    path: candidates[idx].path.clone(),
                    title: candidates[idx].title.clone(),
                    rel: "related".into(),
                    line: clip_line(&candidates[idx].title, POINTER_LINE_CHARS),
                    noul: scores[idx].ptr,
                    original_index: idx,
                });
                used[idx] = true;
                if !pin {
                    related_count += 1;
                }
            }
        }
    }

    // 3. Pin nunca dropped (§3.1.b)
    for (idx, cand) in candidates.iter().enumerate() {
        if pointers.len() >= MAX_POINTERS {
            break;
        }
        if used[idx] {
            continue;
        }
        let key = cand.path.to_lowercase();
        if is_pinned(&cand.path, pinned_paths) && !pointer_paths.contains(&key) {
            pointer_paths.insert(key);
            pointers.push(PackPointer {
                path: cand.path.clone(),
                title: cand.title.clone(),
                rel: "related".into(),
                line: clip_line(&cand.title, POINTER_LINE_CHARS),
                noul: scores[idx].ptr,
                original_index: idx,
            });
            used[idx] = true;
        }
    }

    if canonical.is_empty() && pointers.is_empty() {
        return None;
    }

    let dropped = used.iter().filter(|u| !**u).count();
    Some(ContextPack {
        family,
        canonical,
        pointers,
        dropped,
    })
}
