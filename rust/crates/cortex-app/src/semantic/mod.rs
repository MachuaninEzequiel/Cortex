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

/// Batch-embedder inyectable (espejo de `_embed_batch_with_cache`):
/// textos → vectores, uno por texto.
pub type EmbedBatchFn<'a> = &'a mut dyn FnMut(&[String]) -> Result<Vec<Vec<f64>>, String>;

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
        let mut idx = Self {
            docs,
            chunks: Vec::new(),
            by_rel,
            doc_lengths: HashMap::new(),
            idf: HashMap::new(),
            avgdl: 1.0,
        };
        idx.recompute_stats();
        Ok(idx)
    }

    /// Recalcula doc_lengths + avgdl + IDF desde `docs` — bloque compartido
    /// por `build()` (sync) e `index_file()` (`_compute_idf` tras cada
    /// escritura). Misma matemática que VaultReader.
    pub fn recompute_stats(&mut self) {
        self.doc_lengths = self
            .docs
            .iter()
            .map(|d| {
                (
                    d.rel.clone(),
                    format!("{} {}", d.title, d.content)
                        .split_whitespace()
                        .count(),
                )
            })
            .collect();
        let n_docs = self.docs.len().max(1) as f64;
        let mut df: HashMap<String, usize> = HashMap::new();
        for d in &self.docs {
            let text = format!("{} {}", d.title, d.content).to_lowercase();
            let mut seen: std::collections::HashSet<&str> = std::collections::HashSet::new();
            for word in text.split_whitespace() {
                if seen.insert(word) {
                    *df.entry(word.to_string()).or_insert(0) += 1;
                }
            }
        }
        self.idf = df
            .into_iter()
            .map(|(t, c)| {
                let v = ((n_docs - c as f64 + 0.5) / (c as f64 + 0.5) + 1.0).ln();
                (t, v)
            })
            .collect();
        let total: usize = self.doc_lengths.values().sum();
        self.avgdl = if self.docs.is_empty() {
            1.0
        } else {
            total as f64 / self.docs.len() as f64
        };
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
        let infos: Vec<chunker::Chunk> = self
            .docs
            .iter()
            .map(chunks_for_doc)
            .collect::<Vec<_>>()
            .concat();
        let texts: Vec<String> = infos.iter().map(|c| c.embedding_text()).collect();
        let vectors = embedder.embed_batch(&texts)?;
        self.chunks = infos
            .into_iter()
            .zip(vectors)
            .map(|(info, embedding)| IndexedChunk { info, embedding })
            .collect();
        Ok(self.chunks.len())
    }

    /// Puerto de `VaultReader.index_file` (P12A-1): re-parsea UN archivo del
    /// vault, upsertea el documento (posición de inserción preservada si ya
    /// existía, como el dict de Python), purga y regenera sus chunks,
    /// recalcula BM25 (lengths/avgdl/IDF completos) y embebe los chunks
    /// nuevos vía el batch-embedder provisto. Devuelve Ok(false) si el
    /// archivo no existe (mismo resultado que Python); los demás errores van
    /// como Err(msg) — estrictamente más informativo que el False+log de
    /// Python. La invalidación granular del vector-cache persistente no
    /// aplica: el índice nativo no tiene caché en disco.
    pub fn index_file(
        &mut self,
        vault: &Path,
        rel: &str,
        embed_batch: EmbedBatchFn<'_>,
    ) -> Result<bool, String> {
        let path =
            crate::security::resolve_safe(vault, Path::new(rel)).map_err(|e| e.to_string())?;
        if !path.exists() {
            return Ok(false);
        }
        let raw = std::fs::read_to_string(&path).map_err(|e| format!("index_file {}: {e}", rel))?;
        let parsed = parser::parse(&raw, &path);
        let doc = SemDoc {
            path: path.to_string_lossy().replace('\\', "/"),
            rel: rel.to_string(),
            title: parsed.title,
            content: parsed.content,
            tags: parsed.tags,
            links: parsed.links,
        };

        // Upsert: clave existente conserva posición; nueva va al final.
        match self.by_rel.get(rel) {
            Some(&i) => self.docs[i] = doc,
            None => {
                self.by_rel.insert(rel.to_string(), self.docs.len());
                self.docs.push(doc);
            }
        }

        // Purga + regeneración de chunks de este padre.
        let doc_ref = self.get_by_rel(rel).expect("recién insertado");
        let nuevos = chunks_for_doc(doc_ref);
        self.chunks.retain(|c| c.info.parent_path != rel);
        if !nuevos.is_empty() {
            let texts: Vec<String> = nuevos.iter().map(|c| c.embedding_text()).collect();
            let vectors = embed_batch(&texts)?;
            for (info, embedding) in nuevos.into_iter().zip(vectors) {
                self.chunks.push(IndexedChunk { info, embedding });
            }
        }

        // BM25: lengths + avgdl + IDF completos (`_compute_idf`).
        self.recompute_stats();
        Ok(true)
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

/// Chunks de un documento según routing — compartido por `sync`
/// (`attach_embeddings_with`) e `index_file`, para que ambos caminos
/// produzcan exactamente los mismos chunks.
fn chunks_for_doc(d: &SemDoc) -> Vec<chunker::Chunk> {
    let doc_type = routing::doc_type_from_rel(&d.rel).unwrap_or(routing::DocType::Glossary);
    let route = routing::route(doc_type);
    if !route.chunking_enabled {
        let title = if d.title.is_empty() {
            "(untitled)".to_string()
        } else {
            d.title.clone()
        };
        vec![chunker::single_chunk_public(
            &d.content, &title, doc_type, &d.tags, &d.rel,
        )]
    } else {
        chunker::chunk_document(&d.title, &d.content, doc_type, &d.tags, &d.rel, route)
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

#[cfg(test)]
mod tests {
    use super::*;

    fn vault_tmp(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("cortex_sem_{tag}_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(d.join("specs")).unwrap();
        d
    }

    fn escribir(d: &Path, rel: &str, contenido: &str) {
        let p = d.join(rel);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, contenido).unwrap();
    }

    #[test]
    fn index_file_incremental_igual_a_rebuild() {
        let d = vault_tmp("incr");
        escribir(&d, "glosario.md", "---\ntitle: Glosario\n---\n# Glosario\n\nLa memoria híbrida fusiona rankings con RRF y k=60.\n");
        escribir(&d, "specs/2026-06-01_foo.md", "---\ntitle: Spec foo\ndoc_type: spec\n---\nObjetivo: validar el gate de paridad del store episódico nativo.\n");
        escribir(
            &d,
            "nota.md",
            "# Nota\n\nTexto suelto sobre webgraph y rayon.\n",
        );

        let mut base = SemanticIndex::build(&d).unwrap();

        // Modificamos UN archivo en disco y reindexamos incrementalmente.
        escribir(&d, "specs/2026-06-01_foo.md", "---\ntitle: Spec foo v2\ndoc_type: spec\n---\nNuevo cuerpo: ahora habla del gate de paridad del workitem HU-1 y del cold start.\n");
        let ok = base.index_file(&d, "specs/2026-06-01_foo.md", &mut |_| {
            Ok(vec![vec![0.0; 4]; 3])
        });
        assert!(matches!(ok, Ok(true)), "{ok:?}");

        // Rebuild completo sobre el vault ya modificado.
        let full = SemanticIndex::build(&d).unwrap();

        // Mismos rankings bm25 incremental vs rebuild.
        for q in ["gate paridad", "cold start", "webgraph"] {
            let inc = base.bm25_search(q, 3);
            let reb = full.bm25_search(q, 3);
            let inc_rels: Vec<&str> = inc.iter().map(|(d, _)| d.rel.as_str()).collect();
            let reb_rels: Vec<&str> = reb.iter().map(|(d, _)| d.rel.as_str()).collect();
            assert_eq!(inc_rels, reb_rels, "query {q}");
        }
        // Y el documento reindexado refleja el nuevo título (upsert real).
        assert_eq!(
            base.get_by_rel("specs/2026-06-01_foo.md").unwrap().title,
            "Spec foo v2"
        );
        std::fs::remove_dir_all(&d).ok();
    }

    #[test]
    fn index_file_archivo_inexistente_false() {
        let d = vault_tmp("missing");
        escribir(&d, "nota.md", "# Nada\n");
        let mut idx = SemanticIndex::build(&d).unwrap();
        let r = idx.index_file(&d, "no_existe.md", &mut |_| Ok(vec![]));
        assert!(matches!(r, Ok(false)));
        std::fs::remove_dir_all(&d).ok();
    }

    #[test]
    fn index_file_archivo_nuevo_agrega_al_final() {
        let d = vault_tmp("nuevo");
        escribir(&d, "a.md", "---\ntitle: A\n---\nuno dos tres\n");
        let mut idx = SemanticIndex::build(&d).unwrap();
        escribir(&d, "sub/b.md", "---\ntitle: B\n---\ncuatro cinco seis\n");
        let ok = idx
            .index_file(&d, "sub/b.md", &mut |_| Ok(vec![vec![0.0; 2]]))
            .unwrap();
        assert!(ok);
        assert_eq!(idx.docs.len(), 2);
        assert_eq!(idx.get_by_rel("sub/b.md").unwrap().title, "B");
        std::fs::remove_dir_all(&d).ok();
    }
}
