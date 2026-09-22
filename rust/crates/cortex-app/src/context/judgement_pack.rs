//! Adapter enricher → pack. El crate judgement no conoce EnrichedItem.

use std::path::Path;

use cortex_config::{JudgementConfig, JudgementProvider};
use cortex_judgement::{
    build_handle, pack_context_with_edges, Candidate, Catalog, ClientOptions, ContextPack,
    JudgementClient, JudgementHandle, PackEdge, Purpose,
};

use crate::semantic::SemanticIndex;
use super::models::{EnrichedBundle, EnrichedItem};
use super::presenter::{
    to_pack_compact, to_pack_markdown, ContextPackView, PackCanonicalView, PackPointerView,
};

pub fn client_options_from(
    cfg: &JudgementConfig,
    questions_override: Option<&Path>,
) -> ClientOptions {
    ClientOptions {
        enabled: cfg.enabled,
        provider: match cfg.provider {
            JudgementProvider::None => "none".into(),
            JudgementProvider::Typesafe => "typesafe".into(),
        },
        model: cfg.model.clone(),
        timeout_ms: cfg.timeout_ms,
        api_key_env: cfg.api_key_env.clone(),
        search_squeeze: cfg.purposes.search_squeeze == cortex_config::PurposeMode::On,
        promotion: cfg.purposes.promotion == cortex_config::PurposeMode::On,
        context_pack: cfg.purposes.context_pack == cortex_config::PurposeMode::On,
        utterance: cfg.purposes.utterance == cortex_config::PurposeMode::On,
        session_compact: cfg.purposes.session_compact == cortex_config::PurposeMode::On,
        model_routing: cfg.purposes.model_routing == cortex_config::PurposeMode::On,
        base_url: std::env::var("TYPESAFE_BASE_URL").ok(),
        questions_override: questions_override.map(|p| p.to_path_buf()),
    }
}

pub fn handle_from_config(
    cfg: &JudgementConfig,
    questions_override: Option<&Path>,
) -> Option<JudgementHandle> {
    build_handle(&client_options_from(cfg, questions_override))
}

pub fn item_path(item: &EnrichedItem) -> String {
    if item.source == "semantic" {
        item.source_id.clone()
    } else if let Some(f) = item.files_mentioned.first() {
        f.clone()
    } else {
        item.source_id.clone()
    }
}

pub fn bundle_to_candidates(bundle: &EnrichedBundle) -> Vec<Candidate> {
    bundle
        .items
        .iter()
        .enumerate()
        .map(|(i, it)| Candidate {
            id: format!("c{i}"),
            path: item_path(it),
            title: it.title.clone(),
            text: it.content.clone(),
        })
        .collect()
}

fn query_of(bundle: &EnrichedBundle) -> String {
    bundle
        .work
        .search_queries
        .first()
        .cloned()
        .or_else(|| bundle.work.pr_title.clone())
        .unwrap_or_default()
}

fn files_of(bundle: &EnrichedBundle) -> Vec<String> {
    let mut files = bundle.work.changed_files.clone();
    for f in &bundle.work.new_files {
        if !files.iter().any(|x| x == f) {
            files.push(f.clone());
        }
    }
    files
}

fn view_from_pack(pack: ContextPack, items: &[EnrichedItem]) -> ContextPackView {
    let canonical = pack
        .canonical
        .into_iter()
        .map(|s| {
            let src = items
                .get(s.original_index)
                .map(|it| it.source)
                .unwrap_or("semantic");
            PackCanonicalView {
                path: s.candidate.path,
                title: s.candidate.title,
                noul: s.noul,
                source: src,
                body: s.candidate.text,
            }
        })
        .collect();
    let pointers = pack
        .pointers
        .into_iter()
        .map(|p| PackPointerView {
            path: p.path,
            rel: p.rel,
            line: p.line,
        })
        .collect();
    ContextPackView {
        family: pack.family,
        canonical,
        pointers,
        dropped: pack.dropped,
    }
}

pub fn extract_stem(path: &str) -> &str {
    let name = path.rsplit(['/', '\\']).next().unwrap_or(path);
    match name.rfind('.') {
        Some(idx) if idx > 0 => &name[..idx],
        _ => name,
    }
}

pub fn is_code_file(path: &str) -> bool {
    let lower = path.to_lowercase();
    lower.ends_with(".rs")
        || lower.ends_with(".ts")
        || lower.ends_with(".tsx")
        || lower.ends_with(".js")
        || lower.ends_with(".jsx")
        || lower.ends_with(".py")
        || lower.ends_with(".go")
        || lower.ends_with(".c")
        || lower.ends_with(".cpp")
        || lower.ends_with(".h")
        || lower.ends_with(".hpp")
        || lower.ends_with(".java")
        || lower.ends_with(".sh")
}

pub fn is_doc_file(path: &str) -> bool {
    let lower = path.to_lowercase();
    lower.ends_with(".md")
        || lower.ends_with(".markdown")
        || lower.ends_with(".txt")
        || lower.contains("/vault/")
        || lower.starts_with("vault/")
        || lower.contains("/specs/")
        || lower.starts_with("specs/")
        || lower.contains("/docs/")
        || lower.starts_with("docs/")
}

fn is_generic_stem(stem: &str) -> bool {
    matches!(
        stem,
        "mod"
            | "lib"
            | "main"
            | "index"
            | "types"
            | "models"
            | "test"
            | "tests"
            | "utils"
            | "common"
    )
}

fn parse_wiki_links(body: &str) -> Vec<String> {
    let mut links = Vec::new();
    let chars: Vec<char> = body.chars().collect();
    let mut i = 0;
    while i + 1 < chars.len() {
        if chars[i] == '[' && chars[i + 1] == '[' {
            let start = i + 2;
            let mut j = start;
            while j + 1 < chars.len() && !(chars[j] == ']' && chars[j + 1] == ']') {
                j += 1;
            }
            if j + 1 < chars.len() {
                let inside: String = chars[start..j].iter().collect();
                let clean = inside
                    .split('|')
                    .next()
                    .unwrap_or("")
                    .split('#')
                    .next()
                    .unwrap_or("")
                    .trim()
                    .to_string();
                if !clean.is_empty() {
                    links.push(clean);
                }
                i = j + 2;
                continue;
            }
        }
        i += 1;
    }
    links
}

/// Extrae aristas nativas {wikilink, implements, constrains} del bundle (spec 07 §3.2 y §5).
pub fn extract_edges_from_bundle(bundle: &EnrichedBundle) -> Vec<PackEdge> {
    let mut edges = Vec::new();
    let items = &bundle.items;

    // 1. wikilink: enlaces [[wiki]] presentes en el contenido
    for item in items {
        let src_path = item_path(item);
        let links = parse_wiki_links(&item.content);
        for link in links {
            let link_low = link.to_lowercase();
            for other in items {
                let other_path = item_path(other);
                if other_path == src_path {
                    continue;
                }
                let other_low = other_path.to_lowercase();
                let other_stem = extract_stem(&other_path).to_lowercase();
                if other_low == link_low
                    || other_low.ends_with(&format!("/{link_low}"))
                    || other_low.ends_with(&format!("/{link_low}.md"))
                    || other.title.eq_ignore_ascii_case(&link)
                    || other_stem == link_low
                {
                    edges.push(PackEdge::with_line(
                        &src_path,
                        &other_path,
                        "wikilink",
                        &other.title,
                    ));
                    break;
                }
            }
        }
    }

    // 2. implements: path de código ↔ ficha nativa del mismo módulo (heurística de path)
    let mut code_paths: Vec<String> = Vec::new();
    for f in &bundle.work.changed_files {
        code_paths.push(f.clone());
    }
    for f in &bundle.work.new_files {
        if !code_paths.contains(f) {
            code_paths.push(f.clone());
        }
    }
    for item in items {
        let p = item_path(item);
        if is_code_file(&p) && !code_paths.contains(&p) {
            code_paths.push(p);
        }
    }

    for code_path in &code_paths {
        let code_stem = extract_stem(code_path).to_lowercase();
        if code_stem.is_empty() || is_generic_stem(&code_stem) {
            continue;
        }
        for item in items {
            let doc_path = item_path(item);
            if doc_path == *code_path {
                continue;
            }
            if is_doc_file(&doc_path) || item.source == "semantic" {
                let doc_stem = extract_stem(&doc_path).to_lowercase();
                let title_stem = item.title.to_lowercase().replace([' ', '-'], "_");
                if doc_stem == code_stem || title_stem == code_stem {
                    edges.push(PackEdge::with_line(
                        code_path,
                        &doc_path,
                        "implements",
                        &item.title,
                    ));
                }
            }
        }
    }

    // 3. constrains: ADR / decision / spec vinculado al canónico
    for item in items {
        let is_adr = item.doc_type.as_deref() == Some("adr")
            || item.doc_type.as_deref() == Some("decision")
            || item.source_id.to_uppercase().contains("ADR-")
            || item.title.to_uppercase().contains("ADR-");
        if !is_adr {
            continue;
        }
        let adr_path = item_path(item);
        for other in items {
            let other_path = item_path(other);
            if other_path == adr_path {
                continue;
            }
            let other_stem = extract_stem(&other_path).to_lowercase();
            let mentioned = item.files_mentioned.iter().any(|f| {
                f == &other_path || f.ends_with(&other_path) || other_path.ends_with(f)
            });
            let content_match = !other_stem.is_empty()
                && !is_generic_stem(&other_stem)
                && item.content.to_lowercase().contains(&other_stem);

            if mentioned || content_match {
                edges.push(PackEdge::with_line(
                    &adr_path,
                    &other_path,
                    "constrains",
                    &item.title,
                ));
            }
        }
    }

    // Deduplicate
    let mut seen = std::collections::HashSet::new();
    edges.retain(|e| seen.insert((e.source.clone(), e.target.clone(), e.rel.clone())));
    edges
}

/// Carga aristas cacheadas del webgraph si existen en disco (.cortex/webgraph/cache/).
pub fn load_cached_webgraph_edges(root: &Path) -> Vec<PackEdge> {
    let mut edges = Vec::new();
    let candidates = [
        root.join(".cortex").join("webgraph").join("cache").join("snapshot-hybrid.json"),
        root.join(".cortex").join("webgraph").join("cache").join("snapshot-semantic.json"),
    ];

    for path in &candidates {
        if !path.exists() {
            continue;
        }
        let Ok(content) = std::fs::read_to_string(path) else {
            continue;
        };
        let Ok(val) = serde_json::from_str::<serde_json::Value>(&content) else {
            continue;
        };
        let Some(arr) = val.get("edges").and_then(|v| v.as_array()) else {
            continue;
        };
        for e in arr {
            let raw_type = e.get("edge_type").and_then(|v| v.as_str()).unwrap_or("");
            let rel = match raw_type {
                "wikilink" => "wikilink",
                "implements" => "implements",
                "constrains" | "same_spec_reference" | "supersedes" | "superseded_by" => {
                    "constrains"
                }
                _ => continue,
            };
            let source = e.get("source").and_then(|v| v.as_str()).unwrap_or("");
            let target = e.get("target").and_then(|v| v.as_str()).unwrap_or("");
            if source.is_empty() || target.is_empty() || source == target {
                continue;
            }
            let line = e
                .get("evidence")
                .and_then(|v| v.as_array())
                .and_then(|a| a.first())
                .and_then(|v| v.as_str())
                .map(String::from);
            edges.push(PackEdge {
                source: source.into(),
                target: target.into(),
                rel: rel.into(),
                line,
            });
        }
        if !edges.is_empty() {
            break;
        }
    }
    edges
}

/// Extrae aristas combinando bundle, SemanticIndex opcional y snapshot en disco.
pub fn extract_edges_with_semantic(
    bundle: &EnrichedBundle,
    semantic: Option<&SemanticIndex>,
    project_root: Option<&Path>,
) -> Vec<PackEdge> {
    let mut edges = extract_edges_from_bundle(bundle);

    if let Some(idx) = semantic {
        for doc in &idx.docs {
            // wikilinks de SemDoc.links
            for link in &doc.links {
                let link_low = link.to_lowercase();
                if let Some(target) = idx.docs.iter().find(|d| {
                    d.rel.to_lowercase() == link_low
                        || d.rel.to_lowercase().ends_with(&format!("/{link_low}"))
                        || d.rel.to_lowercase().ends_with(&format!("/{link_low}.md"))
                        || d.title.eq_ignore_ascii_case(link)
                }) {
                    edges.push(PackEdge::with_line(&doc.rel, &target.rel, "wikilink", &target.title));
                }
            }

            // implements entre changed_files y SemDoc
            for f in &bundle.work.changed_files {
                let f_stem = extract_stem(f).to_lowercase();
                if !f_stem.is_empty() && !is_generic_stem(&f_stem) {
                    let d_stem = extract_stem(&doc.rel).to_lowercase();
                    if d_stem == f_stem {
                        edges.push(PackEdge::with_line(f, &doc.rel, "implements", &doc.title));
                    }
                }
            }

            // constrains desde ADRs
            if doc.rel.to_uppercase().contains("ADR-") || doc.title.to_uppercase().contains("ADR-") {
                for f in &bundle.work.changed_files {
                    let f_stem = extract_stem(f).to_lowercase();
                    if !f_stem.is_empty() && !is_generic_stem(&f_stem) && doc.content.to_lowercase().contains(&f_stem) {
                        edges.push(PackEdge::with_line(&doc.rel, f, "constrains", &doc.title));
                    }
                }
            }
        }
    }

    if let Some(root) = project_root {
        let cached = load_cached_webgraph_edges(root);
        edges.extend(cached);
    }

    let mut seen = std::collections::HashSet::new();
    edges.retain(|e| seen.insert((e.source.clone(), e.target.clone(), e.rel.clone())));
    edges
}

pub fn try_pack_view(
    client: &dyn JudgementClient,
    catalog: &Catalog,
    bundle: &EnrichedBundle,
) -> Option<ContextPackView> {
    try_pack_view_with_semantic(client, catalog, bundle, None, None)
}

pub fn try_pack_view_with_semantic(
    client: &dyn JudgementClient,
    catalog: &Catalog,
    bundle: &EnrichedBundle,
    semantic: Option<&SemanticIndex>,
    project_root: Option<&Path>,
) -> Option<ContextPackView> {
    if !client.enabled(Purpose::ContextPack) {
        return None;
    }
    let edges = extract_edges_with_semantic(bundle, semantic, project_root);
    let pack = pack_context_with_edges(
        client,
        catalog,
        &query_of(bundle),
        &files_of(bundle),
        bundle_to_candidates(bundle),
        &files_of(bundle),
        &edges,
    )?;
    Some(view_from_pack(pack, &bundle.items))
}

pub fn try_pack_view_with_edges(
    client: &dyn JudgementClient,
    catalog: &Catalog,
    bundle: &EnrichedBundle,
    edges: &[PackEdge],
) -> Option<ContextPackView> {
    if !client.enabled(Purpose::ContextPack) {
        return None;
    }
    let pack = pack_context_with_edges(
        client,
        catalog,
        &query_of(bundle),
        &files_of(bundle),
        bundle_to_candidates(bundle),
        &files_of(bundle),
        edges,
    )?;
    Some(view_from_pack(pack, &bundle.items))
}

/// Compact para el agente; markdown verbose para humano (`--expand` no mete dropped).
pub fn format_pack(
    handle: &JudgementHandle,
    bundle: &EnrichedBundle,
    compact: bool,
    expand: bool,
) -> Option<String> {
    format_pack_with_semantic(handle, bundle, compact, expand, None, None)
}

pub fn format_pack_with_semantic(
    handle: &JudgementHandle,
    bundle: &EnrichedBundle,
    compact: bool,
    expand: bool,
    semantic: Option<&SemanticIndex>,
    project_root: Option<&Path>,
) -> Option<String> {
    let view = try_pack_view_with_semantic(&*handle.client, &handle.catalog, bundle, semantic, project_root)?;
    Some(if compact {
        to_pack_compact(&view, expand)
    } else {
        to_pack_markdown(&view, expand)
    })
}

pub fn format_pack_with_edges(
    handle: &JudgementHandle,
    bundle: &EnrichedBundle,
    edges: &[PackEdge],
    compact: bool,
    expand: bool,
) -> Option<String> {
    let view = try_pack_view_with_edges(&*handle.client, &handle.catalog, bundle, edges)?;
    Some(if compact {
        to_pack_compact(&view, expand)
    } else {
        to_pack_markdown(&view, expand)
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::context::models::{EnrichedItem, WorkContext};
    use crate::context::presenter::to_compact;
    use cortex_judgement::{
        JudgementError, JudgementRequest, JudgementResponse, NullClient, Purpose,
    };
    use std::sync::Mutex;

    fn item(path: &str, title: &str, body: &str) -> EnrichedItem {
        EnrichedItem {
            source: "semantic",
            source_id: path.into(),
            title: title.into(),
            content: body.into(),
            score: 0.5,
            enriched_score: 0.6,
            matched_by: vec!["topic_search".into()],
            files_mentioned: vec![],
            date: None,
            tags: vec![],
            doc_type: None,
            status: None,
            vault_scope: "local".into(),
            origin_project_id: None,
            matched_chunk_id: None,
            matched_section_title: None,
        }
    }

    fn bundle() -> EnrichedBundle {
        EnrichedBundle {
            work: WorkContext {
                search_queries: vec!["checkpoint verification".into()],
                ..Default::default()
            },
            items: vec![
                item("sessions.rs.md", "sessions", "mcp sessions backend"),
                item(
                    "verification.md",
                    "verification",
                    "checkpoint verification quality gates",
                ),
                item("other.md", "other", "unrelated"),
            ],
            total_searches: 4,
            total_raw_hits: 32,
            total_chars: 900,
            within_budget_override: None,
        }
    }

    #[test]
    fn omitted_client_keeps_compact_identical() {
        let b = bundle();
        let catalog = Catalog::embedded().unwrap();
        assert!(try_pack_view(&NullClient, &catalog, &b).is_none());
        let compact = to_compact(&b);
        assert!(compact.contains("## 🧠 Cortex Context"));
        assert!(compact.contains("Matched by:"));
    }

    struct Boom;
    impl JudgementClient for Boom {
        fn enabled(&self, purpose: Purpose) -> bool {
            matches!(purpose, Purpose::ContextPack)
        }
        fn evaluate(
            &self,
            _request: &JudgementRequest,
        ) -> Result<JudgementResponse, JudgementError> {
            Err(JudgementError::Http(429))
        }
    }

    #[test]
    fn fail_open_429_returns_none() {
        let catalog = Catalog::embedded().unwrap();
        assert!(try_pack_view(&Boom, &catalog, &bundle()).is_none());
    }

    struct Script {
        calls: Mutex<Vec<JudgementResponse>>,
    }
    impl JudgementClient for Script {
        fn enabled(&self, purpose: Purpose) -> bool {
            matches!(purpose, Purpose::ContextPack)
        }
        fn evaluate(
            &self,
            _request: &JudgementRequest,
        ) -> Result<JudgementResponse, JudgementError> {
            let mut g = self.calls.lock().unwrap();
            if g.is_empty() {
                return Err(JudgementError::Http(429));
            }
            Ok(g.remove(0))
        }
    }

    fn family() -> JudgementResponse {
        let mut answers = serde_json::Map::new();
        answers.insert(
            "family".into(),
            serde_json::json!({"choice": "session", "confidence": 1.0}),
        );
        JudgementResponse {
            model: "jev-1.13.0".into(),
            answers,
            usage: Default::default(),
            backend: "typesafe".into(),
        }
    }

    fn dual() -> JudgementResponse {
        let mut answers = serde_json::Map::new();
        for (k, n) in [
            ("rel_c0_body", 0.10),
            ("rel_c0_ptr", 0.40),
            ("rel_c1_body", 0.92),
            ("rel_c1_ptr", 0.95),
            ("rel_c2_body", 0.05),
            ("rel_c2_ptr", 0.10),
        ] {
            answers.insert(k.into(), serde_json::json!({ "noul": n }));
        }
        JudgementResponse {
            model: "jev-1.13.0".into(),
            answers,
            usage: Default::default(),
            backend: "typesafe".into(),
        }
    }

    #[test]
    fn pack_view_canonical_is_verification_not_wrapper() {
        let catalog = Catalog::embedded().unwrap();
        let client = Script {
            calls: Mutex::new(vec![family(), dual()]),
        };
        let view = try_pack_view(&client, &catalog, &bundle()).unwrap();
        assert_eq!(view.canonical[0].path, "verification.md");
        assert_ne!(view.canonical[0].path, "sessions.rs.md");
        let text = to_pack_compact(&view, false);
        assert!(text.starts_with("## Context pack"));
        assert!(!text.contains("Matched by:"));
        assert!(!text.contains("4 searches"));
        assert!(text.chars().count() <= 1800);
    }

    #[test]
    fn extract_edges_from_bundle_detects_wikilink_implements_and_constrains() {
        let mut b = bundle();
        // Add a code file to work
        b.work.changed_files = vec!["src/auth.rs".into()];
        // Modify items: item 0 has wikilink to item 1; item 1 is auth.md (implements); item 2 is ADR-001 (constrains)
        b.items = vec![
            item("specs/overview.md", "overview", "See [[auth.md]] for details."),
            item("vault/auth.md", "auth", "Authentication specification"),
            item("vault/adr/ADR-001.md", "ADR-001 Auth Engine", "Decisions on auth and overview"),
        ];
        b.items[2].doc_type = Some("adr".into());

        let edges = extract_edges_from_bundle(&b);
        let edge_rels: Vec<(&str, &str, &str)> = edges
            .iter()
            .map(|e| (e.source.as_str(), e.target.as_str(), e.rel.as_str()))
            .collect();

        assert!(
            edge_rels.iter().any(|(s, t, r)| *r == "wikilink" && s.contains("overview") && t.contains("auth")),
            "wikilink detected from [[auth.md]]: {edge_rels:?}"
        );
        assert!(
            edge_rels.iter().any(|(s, t, r)| *r == "implements" && s.contains("src/auth.rs") && t.contains("auth.md")),
            "implements detected between src/auth.rs and auth.md: {edge_rels:?}"
        );
        assert!(
            edge_rels.iter().any(|(s, _t, r)| *r == "constrains" && s.contains("ADR-001")),
            "constrains detected from ADR-001: {edge_rels:?}"
        );
    }

    #[test]
    fn pack_view_with_typed_edges_renders_in_pointers() {
        let catalog = Catalog::embedded().unwrap();
        let client = Script {
            calls: Mutex::new(vec![family(), dual()]),
        };
        let b = bundle();
        let edges = vec![
            PackEdge::new("verification.md", "sessions.rs.md", "implements"),
        ];
        let view = try_pack_view_with_edges(&client, &catalog, &b, &edges).unwrap();
        assert_eq!(view.canonical[0].path, "verification.md");
        assert_eq!(view.pointers[0].path, "sessions.rs.md");
        assert_eq!(view.pointers[0].rel, "implements");

        let text = to_pack_compact(&view, false);
        assert!(text.contains("- sessions.rs.md  — implements — "));
    }
}
