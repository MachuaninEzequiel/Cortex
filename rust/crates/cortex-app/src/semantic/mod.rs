//! Porteo del pipeline semántico de `cortex/semantic/` (Obra 07 fase P2).
//!
//! Paridad-como-contrato contra `VaultReader`:
//! - parser: `markdown_parser.py` (frontmatter, título fallback `.title()`,
//!   tags de frontmatter + hashtags inline con dedup ordenado, wiki-links).
//! - BM25 doc-level: `vault_reader._bm25_search` + `_compute_idf` — tf por
//!   SUBSTRING sobre `(title + " " + content).lower()`, idf =
//!   `ln((N-df+0.5)/(df+0.5)+1)`, k1=1.5 b=0.75, solo score>0, orden estable.
//!
//! El lado vectorial (chunker+routing+ort) entra en el mismo módulo (P2b).

pub mod chunker;
pub mod parser;
pub mod routing;

use std::collections::HashMap;
use std::path::{Path, PathBuf};

/// Chunk indexado con su vector de embedding (P2b).
#[derive(Debug, Clone)]
pub struct IndexedChunk {
    pub info: chunker::Chunk,
    pub embedding: Vec<f64>,
}

/// Documento semántico mínimo para ranking (espejo de SemanticDocument).
#[derive(Debug, Clone)]
pub struct SemDoc {
    /// Ruta absoluta tal como la emite el parser Python (`str(path)`).
    pub path: String,
    /// Ruta relativa al vault (clave del índice `_index`).
    pub rel: String,
    pub title: String,
    pub content: String,
    pub tags: Vec<String>,
    pub links: Vec<String>,
}

/// Índice documental con estadísticas BM25 pre-computadas.
pub struct SemanticIndex {
    /// Orden de inserción = iteración de archivos (afecta desempates estables).
    pub docs: Vec<SemDoc>,
    pub chunks: Vec<IndexedChunk>,
    by_rel: HashMap<String, usize>,
    doc_lengths: HashMap<String, usize>,
    idf: HashMap<String, f64>,
    avgdl: f64,
}

impl SemanticIndex {
    /// Replica `sync()` en la parte que BM25 necesita (P2a): parse + lengths +
    /// IDF + avgdl. Los archivos se recorren en orden sorted por rel_path
    /// (determinismo Rust; los empates flotantes son measure-zero).
    pub fn build(vault: &Path) -> Result<Self, String> {
        let mut files: Vec<PathBuf> = Vec::new();
        collect_md(vault, &mut files)?;
        files.sort();

        let mut docs = Vec::with_capacity(files.len());
        let mut by_rel = HashMap::new();
        for path in &files {
            let raw =
                std::fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))?;
            let parsed = parser::parse(&raw, path);
            let rel = path
                .strip_prefix(vault)
                .expect("strip_prefix")
                .to_string_lossy()
                .replace('\\', "/");
            by_rel.insert(rel.clone(), docs.len());
            docs.push(SemDoc {
                path: path.to_string_lossy().replace('\\', "/"),
                rel,
                title: parsed.title,
                content: parsed.content,
                tags: parsed.tags,
                links: parsed.links,
            });
        }

        // doc_lengths + IDF + avgdl (idéntico a sync()).
        let mut doc_lengths: HashMap<String, usize> = HashMap::new();
        for d in &docs {
            let len = format!("{} {}", d.title, d.content)
                .split_whitespace()
                .count();
            doc_lengths.insert(d.rel.clone(), len);
        }
        let n_docs = docs.len().max(1) as f64;
        let mut df: HashMap<String, usize> = HashMap::new();
        for d in &docs {
            let text = format!("{} {}", d.title, d.content).to_lowercase();
            let mut seen: std::collections::HashSet<&str> = std::collections::HashSet::new();
            for word in text.split_whitespace() {
                if seen.insert(word) {
                    *df.entry(word.to_string()).or_insert(0) += 1;
                }
            }
        }
        let idf: HashMap<String, f64> = df
            .into_iter()
            .map(|(t, c)| {
                let v = ((n_docs - c as f64 + 0.5) / (c as f64 + 0.5) + 1.0).ln();
                (t, v)
            })
            .collect();
        let total: usize = doc_lengths.values().sum();
        let avgdl = if docs.is_empty() {
            1.0
        } else {
            total as f64 / docs.len() as f64
        };

        Ok(Self {
            docs,
            chunks: Vec::new(),
            by_rel,
            doc_lengths,
            idf,
            avgdl,
        })
    }

    /// P2b: construye chunks (routing+chunker) y embebe en un solo lote
    /// vía cortex-embed (ort). Replica la parte vectorial de `sync()`.
    pub fn attach_embeddings(&mut self, model_dir: &Path) -> Result<usize, String> {
        let mut emb = cortex_embed::onnx::OnnxEmbedder::open(model_dir)?;
        self.attach_embeddings_with(&mut emb)
    }

    pub fn attach_embeddings_with(
        &mut self,
        embedder: &mut cortex_embed::onnx::OnnxEmbedder,
    ) -> Result<usize, String> {
        let mut infos: Vec<chunker::Chunk> = Vec::new();
        for d in &self.docs {
            let doc_type = routing::doc_type_from_rel(&d.rel).unwrap_or(routing::DocType::Glossary);
            let route = routing::route(doc_type);
            if !route.chunking_enabled {
                let title = if d.title.is_empty() {
                    "(untitled)".to_string()
                } else {
                    d.title.clone()
                };
                infos.push(chunker::single_chunk_public(
                    &d.content, &title, doc_type, &d.tags, &d.rel,
                ));
            } else {
                infos.extend(chunker::chunk_document(
                    &d.title, &d.content, doc_type, &d.tags, &d.rel, route,
                ));
            }
        }
        let texts: Vec<String> = infos.iter().map(|c| c.embedding_text()).collect();
        let vectors = embedder.embed_batch(&texts)?;
        self.chunks = infos
            .into_iter()
            .zip(vectors)
            .map(|(info, embedding)| IndexedChunk { info, embedding })
            .collect();
        Ok(self.chunks.len())
    }

    /// Búsqueda semántica: coseno por chunk (>0), max por padre (primer máximo
    /// gana), orden estable descendente — puerto 1:1 de `VaultReader.search`.
    pub fn semantic_search(
        &self,
        query: &str,
        top_k: usize,
        embedder: &mut cortex_embed::onnx::OnnxEmbedder,
    ) -> Vec<(&SemDoc, f64)> {
        let mut qvec = embedder
            .embed_batch(std::slice::from_ref(&query.to_string()))
            .expect("embed del query");
        let Some(q) = qvec.pop() else {
            return Vec::new();
        };
        self.semantic_search_vec(&q, top_k)
    }

    /// Variante con vector pre-calculado.
    pub fn semantic_search_vec(&self, qvec: &[f64], top_k: usize) -> Vec<(&SemDoc, f64)> {
        // best_per_doc con orden de primera aparición; `score > cur` conserva
        // el PRIMER máximo — idéntico al dict de Python + comparación estricta.
        let mut best: HashMap<&str, f64> = HashMap::new();
        let mut order: Vec<&str> = Vec::new();
        for ch in &self.chunks {
            let score = cosine(qvec, &ch.embedding);
            if score <= 0.0 {
                continue;
            }
            let parent = ch.info.parent_path.as_str();
            match best.get(parent) {
                None => {
                    order.push(parent);
                    best.insert(parent, score);
                }
                Some(&cur) if score > cur => {
                    best.insert(parent, score);
                }
                _ => {}
            }
        }
        let mut scored: Vec<(&SemDoc, f64)> = Vec::new();
        for parent in order {
            let Some(doc) = self.get_by_rel(parent) else {
                continue;
            };
            let score = best[parent];
            scored.push((doc, score));
        }
        scored.sort_by(|a, b| b.1.total_cmp(&a.1));
        scored.truncate(top_k);
        scored
    }

    /// Puerto de `_bm25_search` (k1=1.5, b=0.75 fijos como en Python).
    pub fn bm25_search(&self, query: &str, top_k: usize) -> Vec<(&SemDoc, f64)> {
        const K1: f64 = 1.5;
        const B: f64 = 0.75;
        let lower = query.to_lowercase();
        let terms: Vec<&str> = lower.split_whitespace().collect();
        if terms.is_empty() {
            return vec![];
        }

        let mut scored: Vec<(&SemDoc, f64)> = Vec::new();
        for d in &self.docs {
            let text = format!("{} {}", d.title, d.content).to_lowercase();
            let doc_len = self.doc_lengths.get(&d.rel).copied().unwrap_or(1);
            let mut score = 0.0f64;
            for term in &terms {
                let idf = self.idf.get(*term).copied().unwrap_or(0.0);
                if idf == 0.0 {
                    continue;
                }
                let tf = text.matches(term).count() as f64;
                let numerator = tf * (K1 + 1.0);
                let denominator = tf + K1 * (1.0 - B + B * doc_len as f64 / self.avgdl);
                score += idf * (numerator / denominator);
            }
            if score > 0.0 {
                scored.push((d, score));
            }
        }
        // Python: sorted(key=..., reverse=True) — estable ⇒ a igual score gana
        // el orden de inserción. Rust sort_by es estable también.
        scored.sort_by(|a, b| b.1.total_cmp(&a.1));
        scored.truncate(top_k);
        scored
    }

    pub fn get_by_rel(&self, rel: &str) -> Option<&SemDoc> {
        self.by_rel.get(rel).map(|&i| &self.docs[i])
    }
}

fn collect_md(dir: &Path, out: &mut Vec<PathBuf>) -> Result<(), String> {
    let rd = std::fs::read_dir(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
    for entry in rd {
        let p = entry.map_err(|e| e.to_string())?.path();
        if p.is_dir() {
            collect_md(&p, out)?;
        } else if p.extension().and_then(|e| e.to_str()) == Some("md") {
            out.push(p);
        }
    }
    Ok(())
}

/// Coseno naive (suma secuencial izquierda→derecha) — espejo exacto de
/// `_cosine_similarity` de VaultReader (ruta default, sin Neumaier).
fn cosine(a: &[f64], b: &[f64]) -> f64 {
    let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f64 = a.iter().map(|x| x * x).sum::<f64>().sqrt();
    let norm_b: f64 = b.iter().map(|x| x * x).sum::<f64>().sqrt();
    if norm_a == 0.0 || norm_b == 0.0 {
        return 0.0;
    }
    dot / (norm_a * norm_b)
}
