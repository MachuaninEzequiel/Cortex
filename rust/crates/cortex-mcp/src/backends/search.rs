//! Backend nativo de la familia SEARCH (SearchBackend): motor keyword real
//! sobre los stores nativos (episódico `$contains` + BM25 semántico + fusión
//! RRF), igual que `cortex search` sin embeddings. Los embeddings
//! (cortex-embed en el MCP) quedan para el wiring P12 — el contrato del
//! oráculo en fixtures es keyword.

use crate::handlers_search::{
    EnrichedItemMirror, EnrichedMirror, RDoc, REntry, RHit, RetrievalMirror, SearchBackend,
    StructuralError,
};
use cortex_app::context::hybrid::{search_hybrid, UnifiedHit};
use cortex_app::episodic::{MemoryEntry, NativeEpisodicStore};
use cortex_app::semantic::{SemDoc, SemanticIndex};
use cortex_embed::onnx::OnnxEmbedder;
use std::path::{Path, PathBuf};

/// Escala RRF (mismo K que el kernel híbrido del CLI).
const RRF_K: f64 = 60.0;

/// Backend de producción: índice semántico del vault + store episódico.
pub struct NativeSearchBackend {
    semantic: SemanticIndex,
    episodic: Option<NativeEpisodicStore>,
    embedder: Option<OnnxEmbedder>,
    vault: PathBuf,
}

impl NativeSearchBackend {
    /// Abre el motor (espejo de `NativeMemory::open_with_embeddings(false)`):
    /// config del proyecto → vault → índice BM25 + store episódico.
    pub fn open(root: &std::path::Path) -> Result<Self, String> {
        let cfg = super::read_config_yaml(root);
        let vault = super::vault_path(root, &cfg);
        let semantic = SemanticIndex::build(&vault).map_err(|e| format!("semantic index: {e}"))?;
        let episodic = load_episodic(root, &cfg);
        // Modelo local (misma ruta que el CLI: cache de chroma). Sin
        // modelo ⇒ degrada a keyword, EXACTAMENTE como `cortex search`.
        let embedder = default_model_dir().and_then(|d| OnnxEmbedder::open(&d).ok());
        Ok(Self {
            semantic,
            episodic,
            embedder,
            vault,
        })
    }
}

/// Misma ruta del modelo que el CLI (`~/.cache/chroma/…/all-MiniLM-L6-v2/onnx`).
fn default_model_dir() -> Option<PathBuf> {
    let home = std::env::var_os("HOME").map(PathBuf::from)?;
    let dir = home.join(".cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx");
    (dir.join("model.onnx").exists()).then_some(dir)
}

impl SearchBackend for NativeSearchBackend {
    fn retrieve(
        &mut self,
        query: &str,
        top_k: usize,
        use_embeddings: bool,
    ) -> Result<RetrievalMirror, String> {
        // Ruta REAL con embeddings cuando el modelo local está disponible;
        // sin modelo degrada a keyword EXACTAMENTE como el CLI.
        if use_embeddings {
            if let (Some(store), Some(embedder)) = (&self.episodic, &mut self.embedder) {
                let (unified, _intent) =
                    search_hybrid(store, &self.semantic, embedder, query, top_k, true);
                return Ok(RetrievalMirror {
                    query: query.to_string(),
                    episodic_hits: unified
                        .iter()
                        .filter(|h| h.source == "episodic")
                        .take(top_k)
                        .map(|h| (rentry(h.entry.as_ref().expect("episodic")), h.score))
                        .collect(),
                    semantic_hits: unified
                        .iter()
                        .filter(|h| h.source == "semantic")
                        .take(top_k)
                        .map(|h| (rdoc(h.doc.expect("semantic")), h.score))
                        .collect(),
                    unified_hits: unified.into_iter().map(|h| rhit(&h)).collect(),
                });
            }
        }
        let ep: Vec<(MemoryEntry, f64)> = match &self.episodic {
            Some(store) => store
                .keyword_search(query, top_k * 3)
                .into_iter()
                .map(|e| (e.clone(), 1.0))
                .collect(),
            None => vec![],
        };
        let sem: Vec<(&SemDoc, f64)> = self.semantic.bm25_search(query, top_k * 3);
        let ep_refs: Vec<&(MemoryEntry, f64)> = ep.iter().collect();
        let unified = rrf_fuse(&ep_refs, &sem, top_k, 1.0, 1.0);
        Ok(RetrievalMirror {
            query: query.to_string(),
            episodic_hits: ep
                .iter()
                .take(top_k)
                .map(|(e, s)| (rentry(e), *s))
                .collect(),
            semantic_hits: sem.iter().take(top_k).map(|(d, s)| (rdoc(d), *s)).collect(),
            unified_hits: unified.into_iter().map(|h| rhit(&h)).collect(),
        })
    }

    /// Enrich: contexto por keywords + archivos del vault (espejo funcional
    /// del oráculo: cada archivo/keyword aporta items con `matched_by`).
    fn enrich(
        &mut self,
        changed_files: Vec<String>,
        keywords: Vec<String>,
        pr_title: Option<String>,
        top_k: Option<usize>,
    ) -> Result<EnrichedMirror, String> {
        let top_k = top_k.unwrap_or(5);
        let mut items: Vec<EnrichedItemMirror> = Vec::new();
        let mut seen: Vec<String> = Vec::new();

        // 1. Keywords → retrieve por cada uno (episódico + semántico).
        for kw in &keywords {
            let ep: Vec<(MemoryEntry, f64)> = match &self.episodic {
                Some(store) => store
                    .keyword_search(kw, 6)
                    .into_iter()
                    .map(|e| (e.clone(), 1.0))
                    .collect(),
                None => vec![],
            };
            let sem: Vec<(&SemDoc, f64)> = self.semantic.bm25_search(kw, 6);
            let _ = rrf_fuse(&ep.iter().collect::<Vec<_>>(), &sem, 2, 1.0, 1.0);
            for (e, _) in ep {
                if seen.contains(&e.id) {
                    continue;
                }
                seen.push(e.id.clone());
                items.push(EnrichedItemMirror {
                    source: "episodic".into(),
                    title: first_line(&e.content),
                    content: truncate(&e.content, 400),
                    files_mentioned: e.files.clone(),
                    date_iso: Some(now_iso_date()),
                    matched_by: vec![kw.clone()],
                    tags: e.tags.clone(),
                    confidence: None,
                });
            }
            for (d, _s) in sem {
                if items
                    .iter()
                    .any(|i| i.title == d.title && i.source == "semantic")
                {
                    continue;
                }
                items.push(EnrichedItemMirror {
                    source: "semantic".into(),
                    title: d.title.clone(),
                    content: truncate(&d.content, 400),
                    files_mentioned: vec![],
                    date_iso: None,
                    matched_by: vec![kw.clone()],
                    tags: d.tags.clone(),
                    confidence: None,
                });
            }
        }

        // 2. Archivos del vault → item semántico (o lectura directa).
        for f in &changed_files {
            if let Some(item) = doc_item_for_path(&self.semantic, &self.vault, f) {
                if !items.iter().any(|i| i.title == item.title) {
                    items.push(item);
                }
            }
        }

        // 3. Título del PR → un hit episódico representativo.
        if let Some(t) = pr_title {
            if let Some(store) = &self.episodic {
                for e in store.keyword_search(&t, 3) {
                    if seen.contains(&e.id) {
                        continue;
                    }
                    items.push(EnrichedItemMirror {
                        source: "episodic".into(),
                        title: first_line(&e.content),
                        content: truncate(&e.content, 400),
                        files_mentioned: e.files.clone(),
                        date_iso: None,
                        matched_by: vec!["pr_title".into()],
                        tags: e.tags.clone(),
                        confidence: None,
                    });
                    break;
                }
            }
        }

        items.truncate(top_k * 3);
        let total = items.len();
        Ok(EnrichedMirror {
            items,
            total_items: total,
        })
    }

    fn enrich_structural(
        &mut self,
        query: &str,
        top_k: usize,
        scope: &str,
        doc_type: Vec<String>,
        exclude_doc_type: Vec<String>,
        status: Vec<String>,
        tag: Vec<String>,
        tag_any: Vec<String>,
        max_age_days: Option<i64>,
        project_id: Vec<String>,
        strict: bool,
    ) -> Result<EnrichedMirror, StructuralError> {
        // La ruta estructural aplica filtros en el handler; el motor de
        // fondo es el mismo retrieve con la consulta.
        let _ = (
            scope,
            doc_type,
            exclude_doc_type,
            status,
            tag,
            tag_any,
            max_age_days,
            project_id,
            strict,
        );
        self.enrich(vec![], vec![query.to_string()], None, Some(top_k))
            .map_err(StructuralError::Runtime)
    }
}

/// Loader del store episódico (espejo de `EpisodicLoad` del CLI).
fn load_episodic(root: &Path, cfg: &serde_yaml::Value) -> Option<NativeEpisodicStore> {
    let get = |key: &str, default: &str| -> String {
        cfg.get("episodic")
            .and_then(|m| m.get(key))
            .and_then(|v| v.as_str())
            .map(str::to_string)
            .unwrap_or_else(|| default.to_string())
    };
    let (persist_s, mode_s, value_s) = (
        get("persist_dir", "memory"),
        get("namespace_mode", "project"),
        get("namespace_value", ""),
    );
    let ns = cortex_workspace::EpisodicNamespaceCfg::new(&persist_s, &mode_s, &value_s);
    let layout = cortex_workspace::WorkspaceLayout::discover(root);
    let persist = cortex_workspace::resolve_episodic_persist_dir(&layout.workspace_root, &ns);
    for candidate in [
        persist.join("episodic_export.jsonl"),
        persist.join("memories.jsonl"),
    ] {
        if let Ok(store) = NativeEpisodicStore::load(&candidate) {
            return Some(store);
        }
    }
    None
}

/// Fusión RRF (replica del kernel del CLI en el path keyword; el kernel
/// híbrido con embeddings espera modelo — P12).
fn rrf_fuse<'a>(
    ep: &'a [&'a (MemoryEntry, f64)],
    sem: &[(&'a SemDoc, f64)],
    top_k: usize,
    ep_w: f64,
    sem_w: f64,
) -> Vec<UnifiedHit<'a>> {
    let mut keys: Vec<String> = Vec::new();
    let mut scores: Vec<f64> = Vec::new();
    let mut entries: Vec<Option<&'a MemoryEntry>> = Vec::new();
    let mut docs: Vec<Option<&'a SemDoc>> = Vec::new();
    let find_or_insert = |keys: &mut Vec<String>, key: String| -> usize {
        match keys.iter().position(|k| *k == key) {
            Some(i) => i,
            None => {
                keys.push(key);
                keys.len() - 1
            }
        }
    };
    for (rank, pair) in ep.iter().enumerate() {
        let (entry, _) = *pair;
        let key = format!("episodic:{}", entry.id);
        let i = find_or_insert(&mut keys, key);
        while scores.len() <= i {
            scores.push(0.0);
            entries.push(None);
            docs.push(None);
        }
        scores[i] += ep_w * (1.0 / (RRF_K + rank as f64 + 1.0));
        entries[i] = Some(entry);
    }
    for (rank, (d, _)) in sem.iter().enumerate() {
        let key = format!("semantic:{}", d.path);
        let i = find_or_insert(&mut keys, key);
        while scores.len() <= i {
            scores.push(0.0);
            entries.push(None);
            docs.push(None);
        }
        scores[i] += sem_w * (1.0 / (RRF_K + rank as f64 + 1.0));
        docs[i] = Some(d);
    }
    let mut order: Vec<usize> = (0..scores.len()).collect();
    order.sort_by(|&a, &b| {
        scores[b]
            .partial_cmp(&scores[a])
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    order
        .into_iter()
        .take(top_k)
        .map(|i| UnifiedHit {
            source: if entries[i].is_some() {
                "episodic"
            } else {
                "semantic"
            },
            score: scores[i],
            doc_score_raw: 0.0,
            dropped: false,
            entry: entries[i].cloned(),
            doc: docs[i],
            matched_chunk_id: None,
            matched_section_title: None,
        })
        .collect()
}

fn rentry(e: &MemoryEntry) -> REntry {
    REntry {
        id: e.id.clone(),
        content: e.content.clone(),
        memory_type: e.memory_type.clone(),
        tags: e.tags.clone(),
        files: e.files.clone(),
        confidence: None,
    }
}

fn rdoc(d: &SemDoc) -> RDoc {
    RDoc {
        path: d.path.clone(),
        title: d.title.clone(),
        content: d.content.clone(),
    }
}

fn rhit(h: &UnifiedHit<'_>) -> RHit {
    RHit {
        source: h.source.to_string(),
        score: h.score,
        entry: h.entry.as_ref().map(rentry),
        doc: h.doc.map(rdoc),
    }
}

/// Item semántico para un path relativo del vault (doc del índice o lectura
/// directa del archivo como fallback).
fn doc_item_for_path(
    semantic: &SemanticIndex,
    vault: &Path,
    rel: &str,
) -> Option<EnrichedItemMirror> {
    let (title, content, tags) = if let Some(d) = semantic.get_by_rel(rel) {
        (d.title.clone(), d.content.clone(), d.tags.clone())
    } else {
        let text = std::fs::read_to_string(vault.join(rel)).ok()?;
        (first_line(&text), text, Vec::new())
    };
    Some(EnrichedItemMirror {
        source: "semantic".into(),
        title,
        content: truncate(&content, 400),
        files_mentioned: vec![],
        date_iso: None,
        matched_by: vec![format!("file:{rel}")],
        tags,
        confidence: None,
    })
}

fn first_line(s: &str) -> String {
    s.lines()
        .find(|l| !l.trim().is_empty())
        .map(|l| l.trim_matches('#').trim().to_string())
        .unwrap_or_else(|| "Untitled".to_string())
}

fn truncate(s: &str, n: usize) -> String {
    s.chars().take(n).collect()
}

fn now_iso_date() -> String {
    chrono::Utc::now().format("%Y-%m-%d").to_string()
}
