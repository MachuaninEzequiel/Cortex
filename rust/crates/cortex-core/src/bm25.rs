//! BM25 sobre corpus en memoria (Gate G3) — réplica EXACTA de la semántica
//! de `VaultReader._bm25_search` + `_compute_idf` (Python).
//!
//! POR QUÉ CASERO Y NO TANTIVY (ver ADR-BM25.md):
//! El scorer Python cuenta SUBSTRINGS (`text.count(term)` sobre el texto
//! completo en minúsculas), no tokens de un analizador. Un índice invertido
//! como tantivy tokeniza y por construcción produce OTRO ranking. La regla
//! dura del programa es paridad ANTES que velocidad: ranking distinto = gate
//! inválido. La alternativa honesta es portar la misma aritmética a Rust,
//! donde el escaneo del corpus corre a velocidad nativa (memchr/two-way de
//! `str::match_indices`) en vez de bytecode interpretado.
//!
//! SEMÁNTICA REPLICAADA (bit a bit):
//! - tf = ocurrencias NO solapadas del término en `(title + " " + content)`
//!   ya en minúsculas — `str::match_indices` avanza igual que `str.count`.
//! - Búsqueda por BYTES UTF-8 == búsqueda por chars para patrones UTF-8 válidos
//!   (auto-sincronización: un patrón válido jamás matchea medio codepoint).
//! - idf proviene de Python (`_compute_idf`, f64) y se SNAPSHOT-ea al índice;
//!   término ausente o `idf == 0.0` se salta (paridad con `.get(term, 0.0)`).
//! - `doc_len`: tokens por espacio del texto bajado; default 1 si falta
//!   (paridad con `_doc_lengths.get(path, 1)`).
//! - Aritmética f64 con EL MISMO orden de operaciones que Python:
//!   `score += idf * (num / den)` acumulación secuencial (no Neumaier: el
//!   código Python usa `+=`, no `sum()`).
//! - Los scores salen alineados al ORDEN DE INSERCIÓN de los documentos —
//!   la fachada garantiza reconstruir el índice si el vault mutó (dirty).
//!
//! El texto EN MINÚSCULAS lo genera Python (`.lower()`): evita divergencias
//! Unicode entre runtimes; el coste O(corpus) se paga una vez por rebuild.

/// Índice BM25 in-memory: documentos + snapshot de IDF/avgdl.
///
/// API GRUESA: add/remove/search por lotes. La reconstrucción tras una
/// mutación del vault es completa y lazy (la dispara la primera query).
#[derive(Default)]
pub struct Bm25Index {
    /// Textos ya en minúsculas (generados por Python), paralelo a `paths`.
    texts: Vec<String>,
    paths: Vec<String>,
    doc_lens: Vec<u64>,
    idf: std::collections::HashMap<String, f64>,
    avgdl: f64,
}

impl Bm25Index {
    pub fn new() -> Self {
        Self::default()
    }

    /// Snapshot de IDF + avgdl. Se llama junto con el rebuild.
    pub fn set_stats(
        &mut self,
        idf_keys: &[String],
        idf_vals: &[f64],
        avgdl: f64,
    ) -> Result<(), String> {
        if idf_keys.len() != idf_vals.len() {
            return Err(format!(
                "set_stats: {} claves idf vs {} valores",
                idf_keys.len(),
                idf_vals.len()
            ));
        }
        self.idf = idf_keys
            .iter()
            .cloned()
            .zip(idf_vals.iter().copied())
            .collect();
        self.avgdl = avgdl;
        Ok(())
    }

    /// Agrega documentos por lote. `texts` debe venir YA en minúsculas.
    pub fn add_batch(
        &mut self,
        paths: &[String],
        texts: &[String],
        doc_lens: &[u64],
    ) -> Result<(), String> {
        if paths.len() != texts.len() || paths.len() != doc_lens.len() {
            return Err(format!(
                "add_batch: paths={} texts={} lens={} desalineados",
                paths.len(),
                texts.len(),
                doc_lens.len()
            ));
        }
        self.paths.extend_from_slice(paths);
        self.texts.extend_from_slice(texts);
        self.doc_lens.extend_from_slice(doc_lens);
        Ok(())
    }

    /// Quita documentos por ruta exacta. Devuelve cuántos fueron quitados.
    pub fn remove_batch(&mut self, paths: &[String]) -> usize {
        let targets: std::collections::HashSet<&String> = paths.iter().collect();
        let antes = self.paths.len();
        let mut keep_texts = Vec::new();
        let mut keep_paths = Vec::new();
        let mut keep_lens = Vec::new();
        for ((p, t), l) in self
            .paths
            .drain(..)
            .zip(self.texts.drain(..))
            .zip(self.doc_lens.drain(..))
        {
            if targets.contains(&p) {
                continue;
            }
            keep_texts.push(t);
            keep_lens.push(l);
            keep_paths.push(p);
        }
        self.texts = keep_texts;
        self.paths = keep_paths;
        self.doc_lens = keep_lens;
        antes - self.paths.len()
    }

    pub fn clear(&mut self) {
        self.paths.clear();
        self.texts.clear();
        self.doc_lens.clear();
        self.idf.clear();
        self.avgdl = 0.0;
    }

    pub fn len(&self) -> usize {
        self.paths.len()
    }

    pub fn is_empty(&self) -> bool {
        self.paths.is_empty()
    }

    /// Scores BM25 de TODOS los documentos, alineados al orden interno.
    ///
    /// Paralelizado con rayon POR DOCUMENTO: cada score es independiente y
    /// `collect` preserva el orden → resultados bit-idénticos a la versión
    /// secuencial (mismo hilo de FLOPs f64 por documento).
    ///
    /// Réplica exacta del bucle Python:
    /// ```python
    /// idf = self._idf.get(term, 0.0)
    /// if idf == 0: continue
    /// tf = text.count(term)
    /// numerator = tf * (k1 + 1)
    /// denominator = tf + k1 * (1 - b + b * doc_len / avgdl)
    /// score += idf * (numerator / denominator)
    /// ```
    pub fn search(&self, terms: &[String], k1: f64, b: f64) -> Vec<f64> {
        use rayon::prelude::*;
        self.texts
            .par_iter()
            .zip(&self.doc_lens)
            .map(|(text, doc_len)| {
                let mut score = 0.0f64;
                for term in terms {
                    let idf = match self.idf.get(term) {
                        Some(v) => *v,
                        None => continue, // .get(term, 0.0) → skip
                    };
                    if idf == 0.0 {
                        continue;
                    }
                    let tf = count_nonoverlap(text, term) as f64;
                    let numerator = tf * (k1 + 1.0);
                    let denominator = tf + k1 * (1.0 - b + b * (*doc_len as f64) / self.avgdl);
                    score += idf * (numerator / denominator);
                }
                score
            })
            .collect()
    }

    /// Top-K documentos por score, con el MISMO desempate que Python:
    /// sort estable descendente sobre el orden de inserción ⇒ a igual score,
    /// gana el de índice menor. Devuelve (score, índice de documento).
    ///
    /// Supuesto documentado: scores finitos (inputs finitos, denominador > 0);
    /// `total_cmp` ordena NaN determinísticamente si algún día apareciera.
    pub fn top_k(&self, terms: &[String], k1: f64, b: f64, k: usize) -> Vec<(f64, u32)> {
        let scores = self.search(terms, k1, b);
        let mut orden: Vec<u32> = (0..scores.len() as u32)
            .filter(|&i| scores[i as usize] > 0.0)
            .collect();
        orden.sort_by(|&a, &b| {
            scores[b as usize]
                .total_cmp(&scores[a as usize])
                .then(a.cmp(&b))
        });
        orden.truncate(k);
        orden.into_iter().map(|i| (scores[i as usize], i)).collect()
    }
}

/// Ocurrencias NO solapadas de `needle` en `haystack` — idéntico a `str.count`.
/// `match_indices` entrega matches sucesivos avanzando más allá de cada uno.
fn count_nonoverlap(haystack: &str, needle: &str) -> usize {
    if needle.is_empty() {
        return 0; // los términos nunca son vacíos (split de Python), defensa.
    }
    haystack.match_indices(needle).count()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn idx(docs: &[(&str, &str, u64)], idf: &[(&str, f64)], avgdl: f64) -> Bm25Index {
        let mut ix = Bm25Index::new();
        ix.add_batch(
            &docs.iter().map(|d| d.0.to_string()).collect::<Vec<_>>(),
            &docs.iter().map(|d| d.1.to_string()).collect::<Vec<_>>(),
            &docs.iter().map(|d| d.2).collect::<Vec<_>>(),
        )
        .unwrap();
        ix.set_stats(
            &idf.iter().map(|t| t.0.to_string()).collect::<Vec<_>>(),
            &idf.iter().map(|t| t.1).collect::<Vec<_>>(),
            avgdl,
        )
        .unwrap();
        ix
    }

    #[test]
    fn count_substring_no_overlap_igual_que_python() {
        // str.count cuenta no-solapados de izquierda a derecha.
        assert_eq!(count_nonoverlap("aaaa", "aa"), 2);
        assert_eq!(count_nonoverlap("abcabc", "abc"), 2);
        assert_eq!(count_nonoverlap("auth authentic", "auth"), 2);
        assert_eq!(count_nonoverlap("xyz", "auth"), 0);
        // UTF-8: búsqueda por bytes == por chars para patrones válidos.
        assert_eq!(count_nonoverlap("ñandú ñandú", "ñandú"), 2);
        assert_eq!(count_nonoverlap("mimimi", "mi"), 3);
    }

    /// Réplica EXACTA del loop Python para tests de paridad.
    fn python_reference(
        text: &str,
        doc_len: u64,
        terms: &[&str],
        idf: &std::collections::HashMap<String, f64>,
        avgdl: f64,
        k1: f64,
        b: f64,
    ) -> f64 {
        let mut score = 0.0;
        for term in terms {
            let idf = *idf.get(*term).unwrap_or(&0.0);
            if idf == 0.0 {
                continue;
            }
            let tf = text.matches(*term).count() as f64;
            let numerator = tf * (k1 + 1.0);
            let denominator = tf + k1 * (1.0 - b + b * doc_len as f64 / avgdl);
            score += idf * (numerator / denominator);
        }
        score
    }

    #[test]
    fn paridad_bit_exacta_contra_python() {
        let docs = vec![
            ("a.md", "login auth middleware token refresh", 6),
            ("b.md", "rest api endpoints json payload", 5),
            ("c.md", "stripe payments integration webhook", 5),
            ("d.md", "authentication authentication oauth", 3),
        ];
        let idf_pairs: Vec<(&str, f64)> = [
            ("auth", 0.731),
            ("api", 1.2039),
            ("token", 0.9808),
            ("inexistente", 1.5),
            ("comun", 0.0), // idf 0 ⇒ término saltado
        ]
        .into_iter()
        .collect();
        let idf_map: std::collections::HashMap<String, f64> =
            idf_pairs.iter().map(|(k, v)| (k.to_string(), *v)).collect();

        let ix = idx(&docs, &idf_pairs, 4.75);
        let terms: Vec<String> = ["auth", "api", "token", "inexistente", "comun"]
            .iter()
            .map(|s| s.to_string())
            .collect();
        let scores = ix.search(&terms, 1.5, 0.75);

        for (i, d) in docs.iter().enumerate() {
            let ref_score = python_reference(
                d.1,
                d.2,
                &["auth", "api", "token", "inexistente", "comun"],
                &idf_map,
                4.75,
                1.5,
                0.75,
            );
            assert_eq!(scores[i], ref_score, "doc {}", d.0);
        }
    }

    #[test]
    fn terminos_faltantes_y_idf_cero_se_saltan() {
        let docs = vec![("a.md", "contenido", 1)];
        let ix = idx(&docs, &[("presente", 2.0)], 1.0);
        let terms: Vec<String> = ["presente", "ausente"]
            .iter()
            .map(|s| s.to_string())
            .collect();
        let scores = ix.search(&terms, 1.5, 0.75);
        assert_eq!(scores.len(), 1);
        // "ausente" no está en el mapa idf ⇒ skipped; solo aporta "presente".
        let esperado = {
            let tf = 0.0f64; // "presente" no aparece en el texto
            let num = tf * 2.5;
            let den = tf + 1.5 * (1.0 - 0.75 + 0.75 * 1.0);
            2.0 * (num / den)
        };
        assert_eq!(scores[0], esperado);
    }

    #[test]
    fn doc_len_default_y_rebuild() {
        let mut ix = Bm25Index::new();
        ix.add_batch(&["a".into()], &["texto texto".into()], &[2])
            .unwrap();
        ix.set_stats(&["texto".to_string()], &[1.0], 2.0).unwrap();
        assert_eq!(ix.len(), 1);
        assert_eq!(ix.remove_batch(&["a".into()]), 1);
        assert!(ix.is_empty());
        ix.clear();
        assert_eq!(ix.len(), 0);
    }
}
