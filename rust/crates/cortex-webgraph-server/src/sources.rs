//! Fuentes de records — porteo de `cortex/webgraph/semantic_source.py` y
//! `cortex/webgraph/episodic_source.py`.
//!
//! El lado nativo consume los motores ya gateados: el vault se recorre con
//! `cortex-app::semantic::SemanticIndex` (P2, orden sorted por rel_path) y la
//! memoria episódica llega como entradas `MemoryEntry` (P3/P12A-1, orden
//! canónico por id). El embedder es INYECTABLE para que el gate sea
//! determinista sin modelos ONNX (misma función pura en ambos lados).
//!
//! GAP documentado (no simulado): `origin_project_id`/`origin_scope` del
//! VaultReader federado no están en SemDoc nativo ⇒ metadata queda con
//! vault_scope="local"; la superficie federada real usa ids prefijados y no
//! depende de ese campo para el gate.

#![forbid(unsafe_code)]

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use serde_json::{json, Map, Value};

use crate::contracts::{EpisodicRecord, SemanticRecord};
use crate::style::{infer_doc_type_from_path, style_for_doc_type};

/// Embedder inyectable (texto → vector f64 determinista).
pub type EmbedFn = Arc<dyn Fn(&str) -> Vec<f64> + Send + Sync>;

/// `" ".join(text.split())` + truncado a 220 chars con "…" final.
pub fn normalize_summary(text: &str, max_chars: usize) -> String {
    let compact: Vec<&str> = text.split_whitespace().collect();
    let compact = compact.join(" ");
    let count = compact.chars().count();
    if count <= max_chars {
        return compact;
    }
    let head: String = compact.chars().take(max_chars - 1).collect();
    format!("{}\u{2026}", head.trim_end())
}

pub(crate) fn read_project_config(config_path: &Path) -> BTreeMap<String, serde_yaml::Value> {
    let Ok(text) = std::fs::read_to_string(config_path) else {
        return BTreeMap::new();
    };
    let Ok(value): Result<serde_yaml::Value, _> = serde_yaml::from_str(&text) else {
        return BTreeMap::new();
    };
    let mut out = BTreeMap::new();
    if let serde_yaml::Value::Mapping(map) = value {
        for (k, v) in map {
            if let serde_yaml::Value::String(key) = k {
                out.insert(key, v);
            }
        }
    }
    out
}

// ── SemanticSource ──────────────────────────────────────────────────────────

pub struct SemanticSource {
    pub vault_path: PathBuf,
    embedder: Option<EmbedFn>,
}

pub(crate) fn yaml_str(v: Option<&serde_yaml::Value>, default: &str) -> String {
    match v.and_then(|x| x.as_str()) {
        Some(s) => s.to_string(),
        None => default.to_string(),
    }
}

impl SemanticSource {
    /// Espejo del constructor: resuelve vault_path desde config/layout.
    pub fn new(
        config_path: &Path,
        layout: &cortex_workspace::WorkspaceLayout,
        vault_path: Option<PathBuf>,
        embedder: Option<EmbedFn>,
    ) -> SemanticSource {
        let cfg = read_project_config(config_path);
        let episodic_cfg = cfg.get("episodic");
        let semantic_cfg = cfg.get("semantic");
        let _ = episodic_cfg;
        let configured = yaml_str(semantic_cfg.and_then(|m| m.get("vault_path")), "vault");
        let vault = match vault_path {
            Some(p) => cortex_workspace::layout::resolve_lexical(&p),
            None => layout.resolve_workspace_relative(Path::new(&configured)),
        };
        Self {
            vault_path: vault,
            embedder,
        }
    }

    /// load_records: itera el índice nativo (sorted por rel) y proyecta.
    pub fn load_records(&self, include_embeddings: bool) -> Vec<SemanticRecord> {
        let index = match cortex_app::semantic::SemanticIndex::build(&self.vault_path) {
            Ok(idx) => idx,
            Err(_) => return Vec::new(),
        };
        let mut records = Vec::new();
        for doc in &index.docs {
            let rel_posix = doc.rel.replace('\\', "/");
            let node_type = semantic_node_type(&rel_posix, &doc.tags);
            let doc_type_slug = infer_doc_type_from_path(&rel_posix);
            let style = style_for_doc_type(doc_type_slug);
            let mut metadata = Map::new();
            metadata.insert("path".into(), json!(rel_posix));
            metadata.insert(
                "doc_type".into(),
                match doc_type_slug {
                    Some(s) => json!(s),
                    None => Value::Null,
                },
            );
            metadata.insert("vault_scope".into(), json!("local"));
            metadata.insert("color".into(), json!(style.color));
            metadata.insert("shape".into(), json!(style.shape));

            // Frontmatter lenient: ADR cross-refs (supersedes/superseded_by/
            // adr_number) re-parseados del archivo real.
            let abs_path = cortex_workspace::layout::resolve_lexical(Path::new(&doc.path));
            if let Some(fm) = parse_frontmatter_lenient(&abs_path) {
                for key in ["adr_number", "supersedes", "superseded_by"] {
                    if let Some(v) = fm.get(key) {
                        if !v.is_null() {
                            metadata.insert(key.into(), yaml_to_json(v));
                        }
                    }
                }
            }

            // Búsqueda de wikilinks [[...]] sobre el contenido crudo: el
            // parser nativo ya extrae links; usarlos tal cual.
            let embedding = if include_embeddings {
                let search_text = format!("{} {}", doc.title, doc.content).trim().to_string();
                Some(self.embed_text(&search_text))
            } else {
                None
            };

            records.push(SemanticRecord {
                node_id: format!("semantic:{rel_posix}"),
                node_type: node_type.into(),
                title: doc.title.clone(),
                summary: normalize_summary(&doc.content, 220),
                rel_path: rel_posix,
                abs_path: abs_path.to_string_lossy().to_string(),
                tags: doc.tags.clone(),
                links: doc.links.clone(),
                content: doc.content.clone(),
                embedding,
                metadata,
            });
        }
        records
    }

    fn embed_text(&self, text: &str) -> Vec<f64> {
        match &self.embedder {
            Some(f) => f(text),
            None => Vec::new(),
        }
    }
}

fn semantic_node_type(rel_path: &str, tags: &[String]) -> &'static str {
    let rel_lower = rel_path.to_lowercase();
    let tag_set: Vec<String> = tags.iter().map(|t| t.to_lowercase()).collect();
    if tag_set.iter().any(|t| t == "spec") || rel_lower.starts_with("specs/") {
        return "semantic_spec";
    }
    if tag_set.iter().any(|t| t == "session") || rel_lower.starts_with("sessions/") {
        return "semantic_session";
    }
    "semantic_doc"
}

/// parse_frontmatter_lenient: bloque YAML inicial "---\n...\n---".
pub fn parse_frontmatter_lenient(path: &Path) -> Option<serde_yaml::Mapping> {
    let text = std::fs::read_to_string(path).ok()?;
    let rest = text.strip_prefix("---\n")?;
    let end = rest.find("\n---")?;
    let block = &rest[..end];
    let value: serde_yaml::Value = serde_yaml::from_str(block).ok()?;
    match value {
        serde_yaml::Value::Mapping(m) => Some(m),
        _ => None,
    }
}

pub fn yaml_to_json(v: &serde_yaml::Value) -> Value {
    match v {
        serde_yaml::Value::Null => Value::Null,
        serde_yaml::Value::Bool(b) => json!(b),
        serde_yaml::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                json!(i)
            } else {
                json!(n.as_f64().unwrap_or(0.0))
            }
        }
        serde_yaml::Value::String(s) => json!(s),
        serde_yaml::Value::Sequence(seq) => Value::Array(seq.iter().map(yaml_to_json).collect()),
        serde_yaml::Value::Mapping(map) => {
            let mut m = Map::new();
            for (k, val) in map {
                let key = match k {
                    serde_yaml::Value::String(s) => s.clone(),
                    other => serde_yaml::to_string(other)
                        .unwrap_or_default()
                        .trim()
                        .to_string(),
                };
                m.insert(key, yaml_to_json(val));
            }
            Value::Object(m)
        }
        serde_yaml::Value::Tagged(t) => yaml_to_json(&t.value),
    }
}

// ── EpisodicSource ──────────────────────────────────────────────────────────

pub struct EpisodicSource {
    pub persist_dir: PathBuf,
    pub entries: Vec<cortex_app::episodic::MemoryEntry>,
    embedder: Option<EmbedFn>,
}

impl EpisodicSource {
    pub fn new(
        config_path: &Path,
        layout: &cortex_workspace::WorkspaceLayout,
        persist_dir: Option<PathBuf>,
        entries: Vec<cortex_app::episodic::MemoryEntry>,
        embedder: Option<EmbedFn>,
    ) -> EpisodicSource {
        let cfg = read_project_config(config_path);
        let resolved = match persist_dir {
            Some(p) => cortex_workspace::layout::resolve_lexical(&p),
            None => {
                // resolve_episodic_persist_dir(workspace_root, episodic_cfg)
                let get = |key: &str| -> String {
                    yaml_str(cfg.get("episodic").and_then(|m| m.get(key)), "")
                };
                let persist_dir_cfg = boxed_or_default(&get("persist_dir"), "memory").to_string();
                let mode_cfg = get("namespace_mode");
                let value_cfg = get("namespace_value");
                let ns = cortex_workspace::EpisodicNamespaceCfg::new(
                    &persist_dir_cfg,
                    &mode_cfg,
                    &value_cfg,
                );
                cortex_workspace::resolve_episodic_persist_dir(&layout.workspace_root, &ns)
            }
        };
        Self {
            persist_dir: resolved,
            entries,
            embedder,
        }
    }

    pub fn count(&self) -> usize {
        self.entries.len()
    }

    /// cache_token análogo al store (constante por proceso en el gate).
    pub fn cache_token(&self) -> i64 {
        self.entries.len() as i64 * 31 + 7
    }

    pub fn load_records(&self, include_embeddings: bool) -> Vec<EpisodicRecord> {
        let mut records = Vec::new();
        for entry in &self.entries {
            let mut metadata: Map<String, Value> = entry
                .metadata
                .iter()
                .map(|(k, v)| (k.clone(), v.clone()))
                .collect();
            metadata
                .entry("doc_type".to_string())
                .or_insert_with(|| json!("episodic"));
            let first_line = entry.content.lines().next().unwrap_or("");
            let label_trunc: String = first_line.chars().take(120).collect();
            let label = if label_trunc.is_empty() {
                entry.id.clone()
            } else {
                label_trunc
            };
            let embedding = if include_embeddings {
                Some(self.embed_text(&entry.content))
            } else {
                None
            };
            records.push(EpisodicRecord {
                node_id: format!("episodic:{}", entry.id),
                node_type: episodic_node_type(&entry.memory_type).into(),
                label,
                summary: normalize_summary(&entry.content, 220),
                memory_id: entry.id.clone(),
                tags: entry.tags.clone(),
                files: entry.files.iter().map(|f| f.replace('\\', "/")).collect(),
                timestamp: Some(entry.timestamp.clone()),
                content: entry.content.clone(),
                metadata,
                embedding,
            });
        }
        records
    }

    fn embed_text(&self, text: &str) -> Vec<f64> {
        match &self.embedder {
            Some(f) => f(text),
            None => Vec::new(),
        }
    }
}

pub(crate) fn boxed_or_default<'a>(v: &'a str, default: &'a str) -> &'a str {
    if v.is_empty() {
        default
    } else {
        v
    }
}

fn episodic_node_type(memory_type: &str) -> &'static str {
    match memory_type.trim().to_lowercase().as_str() {
        "spec" => "episodic_spec",
        "session" => "episodic_session",
        _ => "episodic_general",
    }
}
