//! Fachada PyO3 del núcleo Rust de Cortex (`cortex_core._native`).
//!
//! REGLA DE DISEÑO (03-MIGRACION-RUST §R5.4 / riesgo R5): las APIs expuestas
//! acá son BATCH/GRUESAS — matrices completas por llamada, nunca loop-per-item
//! desde Python (el coste fijo FFI mata la ganancia si se llama fino).
//!
//! Este módulo SOLO adapta tipos: toda la lógica vive en `cortex-core`.

use numpy::prelude::*;
use numpy::{IntoPyArray, PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::path::Path;
use std::sync::Mutex;

use cortex_core::bm25::Bm25Index;
use cortex_core::store::VectorStore;
use cortex_core::webgraph;

#[cfg(feature = "onnx")]
use cortex_embed::onnx::OnnxEmbedder as RustOnnxEmbedder;

/// Versión del núcleo Rust (cortex-core).
#[pyfunction]
fn core_version() -> &'static str {
    cortex_core::VERSION
}

/// Scoring cosine BATCH: query `(dim,)` × matrix `(n, dim)` → scores `(n,)`.
///
/// API GRUESA (regla dura R5.4): una llamada procesa TODAS las filas con la
/// matriz contigua completa. Nunca llamar esto por-vector desde Python —
/// el coste fijo de FFI mataría la ganancia.
///
/// Paridad bit-a-bit con `_cosine_similarity` de Python: acumulación f64
/// secuencial + sqrt IEEE (ver cortex-core::scoring). dim paramétrica:
/// se valida contra el shape real de la matriz, falla RUIDOSA si no coincide.
#[pyfunction]
#[pyo3(signature = (query, matrix))]
fn cosine_scores<'py>(
    py: Python<'py>,
    query: PyReadonlyArray1<'py, f64>,
    matrix: PyReadonlyArray2<'py, f64>,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    if matrix.shape().len() != 2 || matrix.shape()[0] == 0 {
        return Err(PyValueError::new_err(format!(
            "matrix debe ser 2D no vacía, shape={:?}",
            matrix.shape()
        )));
    }
    let q = query
        .as_slice()
        .map_err(|e| PyValueError::new_err(format!("query debe ser contiguo: {e}")))?;
    let m = matrix
        .as_slice()
        .map_err(|e| PyValueError::new_err(format!("matrix debe ser C-contigua: {e}")))?;
    let dim = matrix.shape()[1];
    let scores = cortex_core::scoring::cosine_scores(q, m, dim)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok(scores.into_pyarray(py))
}

/// Store vectorial binario nativo (Gate G2) — log append-only schema v3.
///
/// API GRUESA: get_many/put_many/invalidate_many procesan lotes completos por
/// llamada. Los fingerprints son claves opacas calculadas en Python
/// (`cache_fingerprint`) → paridad de fingerprints por construcción.
#[pyclass]
struct NativeVectorStore {
    inner: Mutex<VectorStore>,
}

fn store_err(e: cortex_core::store::StoreError) -> PyErr {
    PyValueError::new_err(e.to_string())
}

#[pymethods]
impl NativeVectorStore {
    #[new]
    fn new(dir: &str, model_name: &str) -> PyResult<Self> {
        let st = VectorStore::open(Path::new(dir), model_name).map_err(store_err)?;
        Ok(Self {
            inner: Mutex::new(st),
        })
    }

    /// True si la carga conservó solo un prefijo válido (cola truncada/corrupta).
    #[getter]
    fn truncated_tail(&self) -> bool {
        self.inner.lock().expect("store lock").truncated_tail
    }

    /// Dimensión del store; None si aún no se guardó ningún vector.
    pub fn dim(&self) -> Option<usize> {
        self.inner.lock().expect("store lock").dim()
    }

    pub fn __len__(&self) -> usize {
        self.inner.lock().expect("store lock").len()
    }

    /// Batch get: devuelve ``(matriz (n, dim) f32, presentes: list[bool])``.
    /// Filas ausentes van en cero con presente=False. Una llamada por lote.
    fn get_many<'py>(
        &self,
        py: Python<'py>,
        fingerprints: Vec<String>,
    ) -> PyResult<(Bound<'py, PyArray2<f32>>, Vec<bool>)> {
        let n = fingerprints.len();
        let dim = {
            let inner = self.inner.lock().expect("store lock");
            match inner.dim() {
                None => {
                    // Store vacío: todo miss sin error (paridad cache Python).
                    let empty = numpy::PyArray2::<f32>::zeros(py, (n, 0), false);
                    return Ok((empty, vec![false; n]));
                }
                Some(d) => d,
            }
        };

        let mut matrix = vec![0f32; n * dim];
        let mut present = vec![false; n];
        {
            let lock = self.inner.lock().expect("store lock");
            lock.get_many(&fingerprints, &mut matrix, &mut present)
                .map_err(store_err)?;
        }
        let arr = matrix
            .into_pyarray(py)
            .reshape([n, dim])
            .map_err(|e| PyValueError::new_err(format!("reshape del resultado falló: {e}")))?;
        Ok((arr, present))
    }

    /// Batch put transaccional: valida TODO antes de escribir nada.
    fn put_many(
        &self,
        fingerprints: Vec<String>,
        chunk_ids: Vec<String>,
        vectors: PyReadonlyArray2<f32>,
    ) -> PyResult<()> {
        if fingerprints.len() != chunk_ids.len() {
            return Err(PyValueError::new_err(format!(
                "put_many: {} fingerprints vs {} chunk_ids",
                fingerprints.len(),
                chunk_ids.len()
            )));
        }
        let dim = *vectors
            .shape()
            .get(1)
            .ok_or_else(|| PyValueError::new_err("vectors debe ser 2D"))?;
        let flat = vectors
            .as_slice()
            .map_err(|e| PyValueError::new_err(format!("vectors debe ser C-contigua: {e}")))?;
        self.inner
            .lock()
            .expect("store lock")
            .put_many(&fingerprints, &chunk_ids, flat, dim)
            .map_err(store_err)
    }

    /// Tombstones batch. Devuelve cuántos fueron invalidaciones nuevas.
    fn invalidate_many(&self, fingerprints: Vec<String>) -> PyResult<usize> {
        self.inner
            .lock()
            .expect("store lock")
            .invalidate_many(&fingerprints)
            .map_err(store_err)
    }

    /// fps vivos cuyo chunk_id está exactamente en el conjunto dado.
    fn fps_for_chunk_ids(&self, chunk_ids: Vec<String>) -> Vec<String> {
        self.inner
            .lock()
            .expect("store lock")
            .fps_for_chunk_ids(&chunk_ids)
    }

    /// fps vivos cuyo chunk_id empieza con el prefijo dado.
    fn fps_with_chunk_prefix(&self, prefix: &str) -> Vec<String> {
        self.inner
            .lock()
            .expect("store lock")
            .fps_with_chunk_prefix(prefix)
    }

    /// Export batch de metadatos: (fps, chunk_ids) de entradas vivas.
    fn entries_export(&self) -> (Vec<String>, Vec<String>) {
        self.inner.lock().expect("store lock").entries_export()
    }

    /// Compacta (tmp + rename atómico). Devuelve entradas finales.
    fn compact(&self) -> PyResult<usize> {
        self.inner
            .lock()
            .expect("store lock")
            .compact()
            .map_err(store_err)
    }
}

/// Índice BM25 nativo (Gate G3): corpus + snapshot IDF en memoria.
///
/// Los textos llegan YA en minúsculas desde Python (paridad Unicode); los
/// scores salen alineados al orden interno — la fachada reconstruye el índice
/// completo si el vault mutó (dirty flag).
#[pyclass]
struct NativeBm25Index {
    inner: Mutex<Bm25Index>,
}

#[pymethods]
impl NativeBm25Index {
    #[new]
    fn new() -> Self {
        Self {
            inner: Mutex::new(Bm25Index::new()),
        }
    }

    /// Snapshot de IDF (claves+valores alineados) y avgdl.
    fn set_stats(&self, idf_keys: Vec<String>, idf_vals: Vec<f64>, avgdl: f64) -> PyResult<()> {
        self.inner
            .lock()
            .expect("bm25 lock")
            .set_stats(&idf_keys, &idf_vals, avgdl)
            .map_err(PyValueError::new_err)
    }

    /// Agrega documentos por lote; textos YA en minúsculas.
    fn add_batch(
        &self,
        paths: Vec<String>,
        texts: Vec<String>,
        doc_lens: Vec<u64>,
    ) -> PyResult<()> {
        self.inner
            .lock()
            .expect("bm25 lock")
            .add_batch(&paths, &texts, &doc_lens)
            .map_err(PyValueError::new_err)
    }

    fn remove_batch(&self, paths: Vec<String>) -> usize {
        self.inner.lock().expect("bm25 lock").remove_batch(&paths)
    }

    fn clear(&self) {
        self.inner.lock().expect("bm25 lock").clear();
    }

    fn __len__(&self) -> usize {
        self.inner.lock().expect("bm25 lock").len()
    }

    /// Scores de todo el corpus para UNA query — API GRUESA por query.
    /// Réplica bit a bit del loop `+= idf * (num/den)` de `_bm25_search`.
    fn search<'py>(
        &self,
        py: Python<'py>,
        terms: Vec<String>,
        k1: f64,
        b: f64,
    ) -> PyResult<Bound<'py, PyArray1<f64>>> {
        let scores = self.inner.lock().expect("bm25 lock").search(&terms, k1, b);
        Ok(scores.into_pyarray(py))
    }

    /// Top-K directo con desempate idéntico al sort estable de Python:
    /// devuelve `[(score, índice_de_documento)]` en orden final. Evita cruzar
    /// al Python una lista de N scores para re-filtrarla y re-ordenarla ahí.
    fn top_k(&self, terms: Vec<String>, k1: f64, b: f64, k: usize) -> Vec<(f64, u32)> {
        self.inner
            .lock()
            .expect("bm25 lock")
            .top_k(&terms, k1, b, k)
    }
}

/// Pares `semantic_neighbor` del webgraph (Gate G4) — API GRUESA: UNA llamada
/// procesa las O(n²) comparaciones con rayon. Réplica exacta de la semántica
/// del relation builder Python (desempates, orden de emisión, umbrales).
#[pyfunction]
fn semantic_neighbor_pairs(
    ids: Vec<String>,
    embeddings: Vec<Option<Vec<f64>>>,
    threshold: f64,
    max_edges_per_node: usize,
) -> Vec<(usize, usize, f64)> {
    webgraph::semantic_neighbor_pairs(&ids, &embeddings, threshold, max_edges_per_node)
}

/// Escaneo cross-source COMPLETO (Gate G4): genera los edges finales con el
/// merge/dedupe de `_add_edge` ya aplicado EN RUST (incluye same_file_reference
/// intercalado antes de los pares de cada episódico). Devuelve tuplas
/// `(id, source, target, edge_type, weight, evidence)` en orden de inserción.
type BuiltEdgeTuples = Vec<(String, String, String, String, f64, Vec<String>)>;

#[pyfunction]
#[allow(clippy::too_many_arguments)]
fn cross_source_build(
    epi_ids: Vec<String>,
    epi_files_targets: Vec<Vec<(String, String)>>,
    epi_tags: Vec<Vec<String>>,
    epi_entities: Vec<Vec<String>>,
    epi_tokens: Vec<Vec<String>>,
    sem_ids: Vec<String>,
    sem_tags: Vec<Vec<String>>,
    sem_entities: Vec<Vec<String>>,
    sem_tokens: Vec<Vec<String>>,
    sem_is_spec: Vec<bool>,
) -> PyResult<BuiltEdgeTuples> {
    let n_epi = epi_ids.len();
    if epi_files_targets.len() != n_epi
        || epi_tags.len() != n_epi
        || epi_entities.len() != n_epi
        || epi_tokens.len() != n_epi
    {
        return Err(PyValueError::new_err(
            "cross_source_build: listas epis\u{f3}dicas desalineadas",
        ));
    }
    let n_sem = sem_ids.len();
    if sem_tags.len() != n_sem
        || sem_entities.len() != n_sem
        || sem_tokens.len() != n_sem
        || sem_is_spec.len() != n_sem
    {
        return Err(PyValueError::new_err(
            "cross_source_build: listas sem\u{e1}nticas desalineadas",
        ));
    }
    Ok(webgraph::cross_source_build(
        &epi_ids,
        &epi_files_targets,
        &epi_tags,
        &epi_entities,
        &epi_tokens,
        &sem_ids,
        &sem_tags,
        &sem_entities,
        &sem_tokens,
        &sem_is_spec,
    )
    .into_iter()
    .map(|e| (e.id, e.source, e.target, e.edge_type, e.weight, e.evidence))
    .collect())
}

/// Embedder ONNX productivo (Gate G5-integración): all-MiniLM-L6-v2 sobre
/// los artefactos chroma cacheados. Paridad demostrada cos=1.0 vs OnnxEmbedder
/// (ADR-EMBEDDINGS.md). dim paramétrica, sale del modelo.
#[cfg(feature = "onnx")]
#[pyclass]
struct NativeEmbedder {
    inner: Mutex<RustOnnxEmbedder>,
}

#[cfg(feature = "onnx")]
#[pymethods]
impl NativeEmbedder {
    /// `model_dir` contiene tokenizer.json + model.onnx (layout de cache chroma).
    /// `intra_threads`: None = default ORT (1-4 recomendado para queries cortas).
    #[new]
    #[pyo3(signature = (model_dir, intra_threads = None))]
    fn new(model_dir: &str, intra_threads: Option<usize>) -> PyResult<Self> {
        let emb = RustOnnxEmbedder::open_with_threads(Path::new(model_dir), intra_threads)
            .map_err(PyValueError::new_err)?;
        Ok(Self {
            inner: Mutex::new(emb),
        })
    }

    /// Dimensión del modelo; None hasta la primera inferencia.
    fn dim(&self) -> Option<usize> {
        self.inner.lock().expect("embedder lock").dim()
    }

    fn embed(&self, text: String) -> Vec<f64> {
        self.embed_batch(vec![text]).pop().unwrap_or_default()
    }

    /// API GRUESA: un lote completo por llamada (sub-lotes internos de 32,
    /// igual que chroma).
    fn embed_batch(&self, texts: Vec<String>) -> Vec<Vec<f64>> {
        self.inner
            .lock()
            .expect("embedder lock")
            .embed_batch(&texts)
            .unwrap_or_else(|e| panic!("NativeEmbedder.embed_batch falló: {e}"))
    }
}

/// Módulo nativo. Se importa como `cortex_core._native`.
#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(core_version, m)?)?;
    m.add_function(wrap_pyfunction!(cosine_scores, m)?)?;
    m.add_function(wrap_pyfunction!(semantic_neighbor_pairs, m)?)?;
    m.add_function(wrap_pyfunction!(cross_source_build, m)?)?;
    m.add_class::<NativeVectorStore>()?;
    m.add_class::<NativeBm25Index>()?;
    #[cfg(feature = "onnx")]
    m.add_class::<NativeEmbedder>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::core_version;

    #[test]
    fn smoke_version_coherente_con_core() {
        assert_eq!(core_version(), cortex_core::VERSION);
    }
}
