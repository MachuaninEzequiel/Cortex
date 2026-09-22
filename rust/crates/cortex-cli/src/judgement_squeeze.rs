//! Adapter search/context: UnifiedHit ↔ JSON de Jev. El crate judgement
//! no conoce UnifiedHit.

use std::path::Path;

use cortex_app::context::hybrid::UnifiedHit;
use cortex_app::context::judgement_pack::client_options_from;
use cortex_config::JudgementConfig;
use cortex_judgement::{
    build_handle, squeeze_search, Candidate, ClientOptions, JudgementHandle, ScoredCandidate,
};

use crate::memory_cmds::{display_path_episodic, display_title_episodic};

pub fn options_from_config(
    cfg: &JudgementConfig,
    questions_override: Option<&Path>,
) -> ClientOptions {
    client_options_from(cfg, questions_override)
}

pub fn handle_from_yaml(
    raw: &serde_yaml::Value,
    questions_override: Option<&Path>,
) -> Option<JudgementHandle> {
    let cfg: JudgementConfig = raw
        .get("judgement")
        .cloned()
        .and_then(|v| serde_yaml::from_value(v).ok())
        .unwrap_or_default();
    build_handle(&options_from_config(&cfg, questions_override))
}

pub fn questions_override_path(workspace_root: &Path, repo_root: &Path) -> std::path::PathBuf {
    let ws = workspace_root.join("judgement").join("questions.yaml");
    if ws.exists() {
        ws
    } else {
        repo_root
            .join(".cortex")
            .join("judgement")
            .join("questions.yaml")
    }
}

/// Reordena hits nativos. Fail-open lo resuelve squeeze_search.
pub fn squeeze_unified<'a>(
    handle: &JudgementHandle,
    query: &str,
    hits: Vec<UnifiedHit<'a>>,
    top_k: usize,
) -> (Vec<UnifiedHit<'a>>, Vec<Option<f64>>) {
    let candidates: Vec<Candidate> = hits
        .iter()
        .enumerate()
        .map(|(i, h)| hit_to_candidate(i, h))
        .collect();
    let scored = squeeze_search(&*handle.client, &handle.catalog, query, candidates, top_k);
    reorder_hits(hits, &scored)
}

fn hit_to_candidate(i: usize, hit: &UnifiedHit<'_>) -> Candidate {
    if hit.source == "episodic" {
        let e = hit.entry.as_ref().expect("episodic");
        Candidate {
            id: format!("c{i}"),
            path: display_path_episodic(e),
            title: display_title_episodic(e),
            text: e.content.clone(),
        }
    } else {
        let d = hit.doc.expect("semantic");
        Candidate {
            id: format!("c{i}"),
            path: d.path.clone(),
            title: d.title.clone(),
            text: d.content.clone(),
        }
    }
}

fn reorder_hits<'a>(
    hits: Vec<UnifiedHit<'a>>,
    scored: &[ScoredCandidate],
) -> (Vec<UnifiedHit<'a>>, Vec<Option<f64>>) {
    let mut out = Vec::with_capacity(scored.len());
    let mut nouls = Vec::with_capacity(scored.len());
    for s in scored {
        if let Some(h) = hits.get(s.original_index) {
            // UnifiedHit no es Clone (lifetime + &SemDoc). Reconstruimos
            // moviendo no se puede; copiamos campos.
            out.push(copy_hit(h));
            nouls.push(if s.noul > 0.0 { Some(s.noul) } else { None });
        }
    }
    (out, nouls)
}

fn copy_hit<'a>(h: &UnifiedHit<'a>) -> UnifiedHit<'a> {
    UnifiedHit {
        source: h.source,
        score: h.score,
        doc_score_raw: h.doc_score_raw,
        dropped: h.dropped,
        entry: h.entry.clone(),
        doc: h.doc,
        matched_chunk_id: h.matched_chunk_id.clone(),
        matched_section_title: h.matched_section_title.clone(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use cortex_config::{JudgementProvider, PurposeMode};

    #[test]
    fn omitted_config_does_not_build_handle() {
        let raw: serde_yaml::Value =
            serde_yaml::from_str("semantic:\n  vault_path: vault\n").unwrap();
        std::env::remove_var("TYPESAFE_API_KEY");
        assert!(handle_from_yaml(&raw, None).is_none());
    }

    #[test]
    fn purpose_off_does_not_build_handle() {
        let raw: serde_yaml::Value = serde_yaml::from_str(
            "judgement:\n  enabled: true\n  provider: typesafe\n  purposes:\n    search_squeeze: off\n",
        )
        .unwrap();
        std::env::set_var("TYPESAFE_API_KEY", "x");
        assert!(handle_from_yaml(&raw, None).is_none());
        std::env::remove_var("TYPESAFE_API_KEY");
    }

    #[test]
    fn options_search_squeeze_on() {
        let cfg = JudgementConfig {
            enabled: true,
            provider: JudgementProvider::Typesafe,
            purposes: cortex_config::JudgementPurposes {
                search_squeeze: PurposeMode::On,
                ..Default::default()
            },
            ..JudgementConfig::default()
        };
        let opts = options_from_config(&cfg, None);
        assert!(opts.search_squeeze);
        assert_eq!(opts.provider, "typesafe");
    }

    #[test]
    fn options_utterance_on() {
        let cfg = JudgementConfig {
            enabled: true,
            provider: JudgementProvider::Typesafe,
            purposes: cortex_config::JudgementPurposes {
                utterance: PurposeMode::On,
                ..Default::default()
            },
            ..JudgementConfig::default()
        };
        let opts = options_from_config(&cfg, None);
        assert!(opts.utterance);
        assert_eq!(opts.provider, "typesafe");
    }
}
