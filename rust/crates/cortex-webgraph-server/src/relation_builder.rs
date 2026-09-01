//! Porteo de `cortex/webgraph/relation_builder.py` — edges explicables del
//! grafo híbrido.
//!
//! Los kernels O(n²) (vecinos semánticos + escaneo cross-source) se delegan
//! a `cortex-core::webgraph`, gateados bit-idénticos contra los loops
//! Python en G4. Este módulo porta la capa de construcción: wikilinks,
//! spec-links, supersedes tipados, el merge/dedupe de `_add_edge` y el
//! orden de inserción del dict Python (que define el orden del array JSON).

#![forbid(unsafe_code)]

use std::collections::BTreeSet;
use std::collections::HashMap;

use cortex_core::webgraph::semantic_neighbor_pairs;

use crate::config::WebGraphConfig;
use crate::contracts::{EpisodicRecord, SemanticRecord, WebGraphEdge};

const GENERIC_TAGS: &[&str] = &["general", "memory", "setup"];

pub fn slug(text: &str) -> String {
    // re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    let lower = text.to_lowercase();
    let mut out = String::new();
    let mut in_run = false;
    for ch in lower.chars() {
        if ch.is_ascii_lowercase() || ch.is_ascii_digit() {
            out.push(ch);
            in_run = false;
        } else if !in_run {
            out.push('-');
            in_run = true;
        }
    }
    out.trim_matches('-').to_string()
}

/// findall(r"[a-zA-Z0-9_]{3,}", text.lower()) → set.
fn tokenize(text: &str) -> BTreeSet<String> {
    let lower = text.to_lowercase();
    let mut set = BTreeSet::new();
    let chars: Vec<char> = lower.chars().collect();
    let mut cur = String::new();
    for &c in &chars {
        if c.is_ascii_alphanumeric() || c == '_' {
            cur.push(c);
        } else if !cur.is_empty() {
            if cur.chars().count() >= 3 {
                set.insert(std::mem::take(&mut cur));
            } else {
                cur.clear();
            }
        }
    }
    if cur.chars().count() >= 3 {
        set.insert(cur);
    }
    set
}

/// findall(r"[A-Za-z_][A-Za-z0-9_]{2,}") lowercase, sin stopwords.
fn identifier_tokens(text: &str) -> BTreeSet<String> {
    const STOP: &[&str] = &[
        "session",
        "specification",
        "changes",
        "files",
        "requirements",
    ];
    let chars: Vec<char> = text.chars().collect();
    let mut set = BTreeSet::new();
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];
        if c.is_ascii_alphabetic() || c == '_' {
            let mut tok = String::new();
            let mut j = i;
            while j < chars.len() {
                let cj = chars[j];
                if cj.is_ascii_alphanumeric() || cj == '_' {
                    tok.push(cj);
                    j += 1;
                } else {
                    break;
                }
            }
            if tok.chars().count() >= 3 {
                let low = tok.to_lowercase();
                if !STOP.contains(&low.as_str()) {
                    set.insert(low);
                }
            }
            i = j.max(i + 1);
        } else {
            i += 1;
        }
    }
    set
}

/// Clave canónica del dict Python: directional ⇒ (tipo, source, target);
/// resto ⇒ (tipo, min, max).
type EdgeKey = (String, String, String);

/// Mapa ordenado con semántica EXACTA de dict Python: asignar a una clave
/// existente PRESERVA su posición original de inserción; `into_values`
/// devuelve en orden de primera inserción.
#[derive(Default)]
struct OrderedEdges {
    map: HashMap<EdgeKey, WebGraphEdge>,
    order: Vec<EdgeKey>,
}

impl OrderedEdges {
    fn assign(&mut self, key: EdgeKey, edge: WebGraphEdge) {
        if !self.map.contains_key(&key) {
            self.order.push(key.clone());
        }
        self.map.insert(key, edge);
    }

    fn get_mut(&mut self, key: &EdgeKey) -> Option<&mut WebGraphEdge> {
        self.map.get_mut(key)
    }

    fn into_values_in_order(mut self) -> Vec<WebGraphEdge> {
        let map = &mut self.map;
        self.order.iter().filter_map(|k| map.remove(k)).collect()
    }
}

fn edge_key(edge_type: &str, source: &str, target: &str) -> EdgeKey {
    let directional =
        edge_type == "wikilink" || edge_type == "supersedes" || edge_type == "superseded_by";
    if directional {
        (
            edge_type.to_string(),
            source.to_string(),
            target.to_string(),
        )
    } else {
        let (lo, hi) = minmax(source, target);
        (edge_type.to_string(), lo, hi)
    }
}

fn minmax(a: &str, b: &str) -> (String, String) {
    if a <= b {
        (a.to_string(), b.to_string())
    } else {
        (b.to_string(), a.to_string())
    }
}

/// dict.fromkeys preservando orden.
fn dedupe_keep_order(items: impl IntoIterator<Item = String>) -> Vec<String> {
    let mut seen = std::collections::HashSet::new();
    let mut out = Vec::new();
    for it in items {
        if seen.insert(it.clone()) {
            out.push(it);
        }
    }
    out
}

#[derive(Default)]
pub struct RelationBuilder {
    pub config: WebGraphConfig,
}

impl RelationBuilder {
    pub fn new(config: WebGraphConfig) -> Self {
        Self { config }
    }

    /// Orden de fases idéntico a build_edges; el dict define el orden final.
    pub fn build_edges(
        &self,
        semantic_records: &[SemanticRecord],
        episodic_records: &[EpisodicRecord],
    ) -> Vec<WebGraphEdge> {
        let mut edges = OrderedEdges::default();
        self.add_semantic_wikilinks(&mut edges, semantic_records);
        self.add_semantic_spec_links(&mut edges, semantic_records);
        self.add_supersedes_edges(&mut edges, semantic_records);
        self.add_cross_source_edges(&mut edges, semantic_records, episodic_records);
        if self.config.enable_semantic_neighbors {
            self.add_semantic_neighbors(&mut edges, semantic_records, episodic_records);
        }
        // list(edges.values()) ⇒ orden de primera inserción del dict.
        edges.into_values_in_order()
    }

    fn add_edge(
        &self,
        edges: &mut OrderedEdges,
        source: &str,
        target: &str,
        edge_type: &str,
        evidence: Vec<String>,
        weight: f64,
    ) {
        if source == target {
            return;
        }
        let key = edge_key(edge_type, source, target);
        match edges.get_mut(&key) {
            None => {
                edges.assign(
                    key,
                    WebGraphEdge {
                        id: format!("{edge_type}:{source}:{target}"),
                        source: source.to_string(),
                        target: target.to_string(),
                        edge_type: edge_type.to_string(),
                        weight,
                        evidence: dedupe_keep_order(evidence),
                    },
                );
            }
            Some(existing) => {
                let merged = dedupe_keep_order(existing.evidence.iter().cloned().chain(evidence));
                existing.evidence = merged;
                existing.weight = existing.weight.max(weight);
            }
        }
    }

    fn add_semantic_wikilinks(&self, edges: &mut OrderedEdges, records: &[SemanticRecord]) {
        let mut alias_index: HashMap<String, String> = HashMap::new();
        for record in records {
            let stem = record
                .rel_path
                .rsplit('/')
                .next()
                .unwrap_or("")
                .rsplit('.')
                .nth(1)
                .map(|_| {
                    record
                        .rel_path
                        .rsplit('/')
                        .next()
                        .unwrap_or("")
                        .rsplit_once('.')
                        .map(|(s, _)| s.to_string())
                        .unwrap_or_else(|| {
                            record.rel_path.rsplit('/').next().unwrap_or("").to_string()
                        })
                })
                .unwrap_or_else(|| record.rel_path.rsplit('/').next().unwrap_or("").to_string());
            alias_index.insert(record.rel_path.to_lowercase(), record.node_id.clone());
            alias_index.insert(stem.to_lowercase(), record.node_id.clone());
            alias_index.insert(slug(&record.title), record.node_id.clone());
        }
        for record in records {
            for link in &record.links {
                let target = link
                    .split('|')
                    .next()
                    .unwrap_or("")
                    .split('#')
                    .next()
                    .unwrap_or("")
                    .trim()
                    .to_lowercase();
                let target_id = alias_index
                    .get(&target)
                    .or_else(|| alias_index.get(&slug(&target)));
                if let Some(tid) = target_id {
                    self.add_edge(
                        edges,
                        &record.node_id,
                        tid,
                        "wikilink",
                        vec![link.clone()],
                        1.0,
                    );
                }
            }
        }
    }

    fn add_semantic_spec_links(&self, edges: &mut OrderedEdges, records: &[SemanticRecord]) {
        let specs: Vec<&SemanticRecord> = records
            .iter()
            .filter(|r| r.node_type == "semantic_spec")
            .collect();
        let mut spec_tokens_by_id: HashMap<&str, BTreeSet<String>> = HashMap::new();
        for spec in &specs {
            let mut tokens = tokenize(&spec.title);
            tokens.extend(tokenize(&spec.summary));
            spec_tokens_by_id.insert(&spec.node_id, tokens);
        }
        let sessions: Vec<&SemanticRecord> = records
            .iter()
            .filter(|r| r.node_type == "semantic_session")
            .collect();
        for session in sessions {
            let session_tokens = tokenize(&session.content);
            for spec in &specs {
                let overlap: Vec<String> = session_tokens
                    .intersection(&spec_tokens_by_id[spec.node_id.as_str()])
                    .cloned()
                    .collect();
                if overlap.len() >= 3 {
                    let mut sorted_overlap = overlap.clone();
                    sorted_overlap.sort();
                    let evidence = format!("shared tokens: {}", sorted_overlap[..4].join(", "));
                    self.add_edge(
                        edges,
                        &session.node_id,
                        &spec.node_id,
                        "same_spec_reference",
                        vec![evidence],
                        1.2,
                    );
                }
            }
        }
    }

    fn add_supersedes_edges(&self, edges: &mut OrderedEdges, records: &[SemanticRecord]) {
        let mut adr_by_number: HashMap<i64, &String> = HashMap::new();
        for record in records {
            if let Some(n) = record.metadata.get("adr_number").and_then(|v| v.as_i64()) {
                if n > 0 {
                    adr_by_number.insert(n, &record.node_id);
                }
            }
        }
        let mut stem_index: HashMap<String, &String> = HashMap::new();
        for record in records {
            let stem = record
                .rel_path
                .rsplit('/')
                .next()
                .unwrap_or("")
                .rsplit_once('.')
                .map(|(s, _)| s)
                .unwrap_or(record.rel_path.rsplit('/').next().unwrap_or(""));
            stem_index.insert(stem.to_lowercase(), &record.node_id);
        }

        let resolve_target = |token: &str| -> Option<&String> {
            let reference = token.trim();
            if reference.is_empty() {
                return None;
            }
            let upper = reference.to_uppercase();
            if upper.starts_with("ADR-") {
                let num_part = upper.split_once('-').map(|x| x.1).unwrap_or("");
                let num = num_part.split('_').next().unwrap_or("");
                if let Ok(n) = num.parse::<i64>() {
                    if let Some(id) = adr_by_number.get(&n) {
                        return Some(id);
                    }
                }
            }
            stem_index.get(&reference.to_lowercase()).copied()
        };

        for record in records {
            if let Some(list) = record.metadata.get("supersedes") {
                for raw in value_list(list) {
                    if let Some(target_id) = resolve_target(&raw) {
                        self.add_edge(
                            edges,
                            &record.node_id,
                            target_id,
                            "supersedes",
                            vec![format!("supersedes: {raw}")],
                            1.5,
                        );
                    }
                }
            }
            if let Some(raw_sb) = record.metadata.get("superseded_by") {
                if raw_sb.is_null() {
                    continue;
                }
                let raw_str = scalar_to_string(raw_sb);
                if let Some(target_id) = resolve_target(&raw_str) {
                    self.add_edge(
                        edges,
                        &record.node_id,
                        target_id,
                        "superseded_by",
                        vec![format!("superseded_by: {raw_str}")],
                        1.4,
                    );
                }
            }
        }
    }

    fn add_cross_source_edges(
        &self,
        edges: &mut OrderedEdges,
        semantic_records: &[SemanticRecord],
        episodic_records: &[EpisodicRecord],
    ) {
        // Espejo EXACTO del loop pure-Python (`_add_cross_source_edges`):
        // pre-cómputo por registro + orden same_file ANTES de los pares de
        // cada episódico. El kernel G4 no se usa acá porque su formato de
        // evidence para same_spec_reference no fue validado contra la ruta
        // pura (los tests nativos no ejercitan ese tipo); paridad primero.
        let semantic_by_path: HashMap<String, &SemanticRecord> = semantic_records
            .iter()
            .map(|r| (r.rel_path.to_lowercase(), r))
            .collect();
        let ignored_tags: BTreeSet<String> = self
            .config
            .ignored_tags
            .iter()
            .map(|t| t.to_lowercase())
            .chain(GENERIC_TAGS.iter().map(|t| t.to_string()))
            .collect();

        let mut sem_tags: Vec<BTreeSet<String>> = Vec::new();
        let mut sem_entities: Vec<BTreeSet<String>> = Vec::new();
        let mut sem_tokens: Vec<BTreeSet<String>> = Vec::new();
        for record in semantic_records {
            sem_tags.push(
                record
                    .tags
                    .iter()
                    .map(|t| t.to_lowercase())
                    .filter(|t| !ignored_tags.contains(t))
                    .collect(),
            );
            sem_entities.push(identifier_tokens(&format!(
                "{} {}",
                record.title, record.content
            )));
            let mut toks = tokenize(&record.title);
            toks.extend(tokenize(&record.summary));
            sem_tokens.push(toks);
        }

        for episodic in episodic_records {
            let episodic_tags: BTreeSet<String> = episodic
                .tags
                .iter()
                .map(|t| t.to_lowercase())
                .filter(|t| !ignored_tags.contains(t))
                .collect();
            let episodic_entities = entities_from_metadata(episodic);
            let episodic_tokens = tokenize(&episodic.content);

            for file_ref in &episodic.files {
                if let Some(semantic) = semantic_by_path.get(&file_ref.to_lowercase()) {
                    self.add_edge(
                        edges,
                        &episodic.node_id,
                        &semantic.node_id,
                        "same_file_reference",
                        vec![file_ref.clone()],
                        1.3,
                    );
                }
            }

            for (s_idx, semantic) in semantic_records.iter().enumerate() {
                let shared_tags: Vec<String> = episodic_tags
                    .intersection(&sem_tags[s_idx])
                    .cloned()
                    .collect();
                if !shared_tags.is_empty() {
                    self.add_edge(
                        edges,
                        &episodic.node_id,
                        &semantic.node_id,
                        "shared_tag",
                        shared_tags.iter().take(3).cloned().collect(),
                        1.0,
                    );
                }

                let shared_entities: Vec<String> = episodic_entities
                    .intersection(&sem_entities[s_idx])
                    .cloned()
                    .collect();
                if !shared_entities.is_empty() {
                    self.add_edge(
                        edges,
                        &episodic.node_id,
                        &semantic.node_id,
                        "shared_entity",
                        shared_entities.iter().take(4).cloned().collect(),
                        1.1,
                    );
                }

                let overlap: BTreeSet<String> = episodic_tokens
                    .intersection(&sem_tokens[s_idx])
                    .cloned()
                    .collect();
                if semantic.node_type == "semantic_spec" && overlap.len() >= 3 {
                    let sorted_overlap: Vec<String> = overlap.into_iter().collect();
                    let evidence = format!(
                        "shared tokens: {}",
                        sorted_overlap[..4.min(sorted_overlap.len())].join(", ")
                    );
                    self.add_edge(
                        edges,
                        &episodic.node_id,
                        &semantic.node_id,
                        "same_spec_reference",
                        vec![evidence],
                        1.2,
                    );
                }
            }
        }
    }

    fn add_semantic_neighbors(
        &self,
        edges: &mut OrderedEdges,
        semantic_records: &[SemanticRecord],
        episodic_records: &[EpisodicRecord],
    ) {
        // Ruta nativa vía kernel G4 (cortex_core::webgraph): su suma
        // compensada de Neumaier replica el fast-path float del builtin
        // sum() de CPython ≥3.12 que usa `_cosine_similarity` del oráculo.
        // NOTA: NO sustituir por fold(0.0, +) ingenuo — diverge 1 ULP en
        // varios pares (verificado empíricamente contra Python 3.12.14).
        let hybrid: Vec<EmbeddingOf> = semantic_records
            .iter()
            .map(|r| EmbeddingOf {
                id: &r.node_id,
                emb: r.embedding.as_deref(),
            })
            .chain(episodic_records.iter().map(|r| EmbeddingOf {
                id: &r.node_id,
                emb: r.embedding.as_deref(),
            }))
            .collect();
        if hybrid.len() > self.config.semantic_neighbor_max_nodes as usize {
            return;
        }
        let ids: Vec<String> = hybrid.iter().map(|h| h.id.to_string()).collect();
        let embeddings: Vec<Option<Vec<f64>>> =
            hybrid.iter().map(|h| h.emb.map(|v| v.to_vec())).collect();
        let pairs = semantic_neighbor_pairs(
            &ids,
            &embeddings,
            self.config.semantic_neighbor_threshold,
            self.config.semantic_neighbor_max_edges_per_node as usize,
        );
        for (i, j, score) in pairs {
            self.add_edge(
                edges,
                &ids[i],
                &ids[j],
                "semantic_neighbor",
                vec![format!("cosine={score:.3}")],
                score,
            );
        }
    }
}

struct EmbeddingOf<'a> {
    id: &'a str,
    emb: Option<&'a [f64]>,
}

// ── helpers ─────────────────────────────────────────────────────────────────

fn entities_from_metadata(record: &EpisodicRecord) -> BTreeSet<String> {
    let mut found = BTreeSet::new();
    if let Some(val @ serde_json::Value::Object(map)) = record.metadata.get("entities") {
        let _ = val;
        for (_k, values) in map {
            if let serde_json::Value::Array(list) = values {
                for value in list {
                    let text = scalar_to_string(value).trim().to_lowercase();
                    if !text.is_empty() {
                        found.insert(text);
                    }
                }
            }
        }
    }
    found
}

fn scalar_to_string(v: &serde_json::Value) -> String {
    match v {
        serde_json::Value::String(s) => s.clone(),
        serde_json::Value::Bool(b) => b.to_string(),
        serde_json::Value::Number(n) => n.to_string(),
        other => other.to_string(),
    }
}

fn value_list(v: &serde_json::Value) -> Vec<String> {
    match v {
        serde_json::Value::Array(items) => items.iter().map(scalar_to_string).collect(),
        serde_json::Value::Null => Vec::new(),
        other => vec![scalar_to_string(other)],
    }
}
