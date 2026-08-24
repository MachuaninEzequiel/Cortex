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

pub mod parser;


use std::collections::HashMap;
use std::path::{Path, PathBuf};

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
        collect_md(vault, vault, &mut files)?;
        files.sort();

        let mut docs = Vec::with_capacity(files.len());
        let mut by_rel = HashMap::new();
        for path in &files {
            let raw = std::fs::read_to_string(path)
                .map_err(|e| format!("{}: {e}", path.display()))?;
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
            let len = format!("{} {}", d.title, d.content).split_whitespace().count();
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
            by_rel,
            doc_lengths,
            idf,
            avgdl,
        })
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
                let denominator =
                    tf + K1 * (1.0 - B + B * doc_len as f64 / self.avgdl);
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

fn collect_md(root: &Path, dir: &Path, out: &mut Vec<PathBuf>) -> Result<(), String> {
    let rd = std::fs::read_dir(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
    for entry in rd {
        let p = entry.map_err(|e| e.to_string())?.path();
        if p.is_dir() {
            collect_md(root, &p, out)?;
        } else if p.extension().and_then(|e| e.to_str()) == Some("md") {
            out.push(p);
        }
    }
    Ok(())
}
