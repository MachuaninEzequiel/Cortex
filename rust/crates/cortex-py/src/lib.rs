//! Fachada PyO3 del núcleo Rust de Cortex (`cortex_core._native`).
//!
//! REGLA DE DISEÑO (03-MIGRACION-RUST §R5.4 / riesgo R5): las APIs expuestas
//! acá son BATCH/GRUESAS — matrices completas por llamada, nunca loop-per-item
//! desde Python (el coste fijo FFI mata la ganancia si se llama fino).
//!
//! Este módulo SOLO adapta tipos: toda la lógica vive en `cortex-core`.

use pyo3::prelude::*;

/// Versión del núcleo Rust (cortex-core).
#[pyfunction]
fn core_version() -> &'static str {
    cortex_core::VERSION
}

/// Módulo nativo. Se importa como `cortex_core._native`.
#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(core_version, m)?)?;
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
