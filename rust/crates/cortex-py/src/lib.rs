//! Fachada PyO3 del núcleo Rust de Cortex (`cortex_core._native`).
//!
//! REGLA DE DISEÑO (03-MIGRACION-RUST §R5.4 / riesgo R5): las APIs expuestas
//! acá son BATCH/GRUESAS — matrices completas por llamada, nunca loop-per-item
//! desde Python (el coste fijo FFI mata la ganancia si se llama fino).
//!
//! Este módulo SOLO adapta tipos: toda la lógica vive en `cortex-core`.

use numpy::prelude::*;
use numpy::{IntoPyArray, PyArray1, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

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

/// Módulo nativo. Se importa como `cortex_core._native`.
#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(core_version, m)?)?;
    m.add_function(wrap_pyfunction!(cosine_scores, m)?)?;
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
