//! Puerto de `cortex/retrieval/hybrid_search.py` — RRF cross-source con
//! pesos adaptativos por intención, consumiendo las nativas episódica
//! (P3) y semántica (P2b) de cortex-app.

use super::intent::{self, IntentResult};
use crate::episodic::MemoryEntry;
use crate::semantic::{SemDoc, SemanticIndex};
use cortex_embed::onnx::OnnxEmbedder;

/// Constante RRF estándar del paper.
const RRF_K: f64 = 60.0;

/// Hit unificado post-fusión (espejo de UnifiedHit en lo que consume el
/// enricher).
pub struct UnifiedHit<'a> {
    pub source: &'static str,
    /// Score fusionado RRF (el que consume el lado episódico).
    pub score: f64,
    /// Score CRUDO del SemanticDocument (VaultReader lo adjunta por doc);
    /// el oráculo usa ESTE para items semánticos (quirk fiel de
    /// `_unified_hit_to_enriched`: `score=hit.doc.score`, no `hit.score`).
    pub doc_score_raw: f64,
    /// Los hits de la estrategia entity_search son EpisodicHit en el
    /// oráculo y `_hit_to_enriched_item` los DESCARTA (sólo inflan
    /// total_raw_hits). Este flag replica ese drop.
    pub dropped: bool,
    pub entry: Option<MemoryEntry>,
    pub doc: Option<&'a SemDoc>,
    /// matched_chunk_id/section propagados por VaultReader cuando gana un
    /// chunk (siempre None para docs sin chunking).
    pub matched_chunk_id: Option<String>,
    pub matched_section_title: Option<String>,
}

/// Espejo de HybridSearch.search(query, top_k, use_embeddings=True):
/// 1. intent → pesos; 2. fetch_k = k*3 por fuente; 3. RRF fusion.
pub fn search_hybrid<'a>(
    episodic: &'a crate::episodic::NativeEpisodicStore,
    semantic: &'a SemanticIndex,
    embedder: &mut OnnxEmbedder,
    query: &str,
    top_k: usize,
    adaptive_weights: bool,
) -> (Vec<UnifiedHit<'a>>, IntentResult) {
    let intent_result = intent::detect(query);
    let (ep_w_base, sem_w_base) = if adaptive_weights {
        (intent_result.episodic_weight, intent_result.semantic_weight)
    } else {
        (1.0, 1.0)
    };

    let fetch_k = top_k * 3;

    // Embed una sola vez para ambas fuentes.
    let mut qv = embedder
        .embed_batch(std::slice::from_ref(&query.to_string()))
        .expect("embed del query");
    let Some(qvec) = qv.pop() else {
        return (Vec::new(), intent_result);
    };

    let episodic_hits = episodic.vector_search(&qvec, fetch_k);
    let semantic_hits = semantic.semantic_search_vec(&qvec, fetch_k);

    // ── fusión RRF: inserción episódica primero, luego semántica ──
    // fused_scores es dict de Python: orden de inserción observable en
    // desempates (sort estable reverse=True ⇒ primer insertado gana).
    let mut keys: Vec<String> = Vec::new();
    let mut scores: Vec<f64> = Vec::new();
    let find_or_insert = |keys: &mut Vec<String>, key: String| -> usize {
        match keys.iter().position(|k| *k == key) {
            Some(i) => i,
            None => {
                keys.push(key);
                keys.len() - 1
            }
        }
    };

    for (rank, (entry, _score_orig)) in episodic_hits.iter().enumerate() {
        let key = format!("episodic:{}", entry.id);
        let i = find_or_insert(&mut keys, key);
        if scores.len() <= i {
            scores.resize(i + 1, 0.0);
        }
        scores[i] += ep_w_base * (1.0 / (RRF_K + rank as f64 + 1.0));
    }
    for (rank, (doc, _score)) in semantic_hits.iter().enumerate() {
        let key = format!("semantic:{}", doc.path);
        let i = find_or_insert(&mut keys, key);
        if scores.len() <= i {
            scores.resize(i + 1, 0.0);
        }
        scores[i] += sem_w_base * (1.0 / (RRF_K + rank as f64 + 1.0));
    }

    // sorted(fused_scores, key=score, reverse=True) — estable.
    let mut order: Vec<usize> = (0..keys.len()).collect();
    order.sort_by(|&a, &b| scores[b].total_cmp(&scores[a]));
    order.truncate(top_k);

    let unified: Vec<UnifiedHit> = order
        .into_iter()
        .map(|i| {
            let key = &keys[i];
            if let Some(rest) = key.strip_prefix("episodic:") {
                let entry = episodic_hits
                    .iter()
                    .find(|(e, _)| e.id == rest)
                    .map(|(e, _)| (*e).clone());
                UnifiedHit {
                    source: "episodic",
                    score: scores[i],
                    doc_score_raw: 0.0,
                    dropped: false,
                    entry,
                    doc: None,
                    matched_chunk_id: None,
                    matched_section_title: None,
                }
            } else if let Some(path) = key.strip_prefix("semantic:") {
                let (doc, raw) = semantic_hits
                    .iter()
                    .find(|(d, _)| d.path == path)
                    .unwrap_or_else(|| fail_lookup(key));
                UnifiedHit {
                    source: "semantic",
                    score: scores[i],
                    doc_score_raw: *raw,
                    dropped: false,
                    entry: None,
                    doc: Some(doc),
                    matched_chunk_id: None,
                    matched_section_title: None,
                }
            } else {
                unreachable!("clave RRF desconocida");
            }
        })
        .collect();

    (unified, intent_result)
}

fn fail_lookup(_key: &str) -> ! {
    panic!("clave RRF sin hit correspondiente")
}
