//! cortex-core — dominio puro de Cortex en Rust (Obra 03, migración incremental).
//!
//! REGLA DE ORO: este crate NO depende de `pyo3` ni de ninguna capa de bindings.
//! Debe compilar y testear 100% offline como librería nativa. La fachada Python
//! vive exclusivamente en `cortex-py` (`cortex_core._native`, APIs batch/gruesas).
//!
//! Módulos previstos — se portean UN GATE POR VEZ (HANDOFF §TAREA-RUST R4):
//! - `scoring`:  scoring vectorial batch cosine → Gate G1
//! - `store`:    store binario schema v2, dim paramétrica, falla ruidosa → Gate G2
//! - `bm25`:     índice invertido / BM25 (tantivy-vs-casero con ADR) → Gate G3
//! - `webgraph`: vecinos semánticos O(n²) con rayon → Gate G4
//!
//! Invariantes que ya rigen desde el esqueleto:
//! - `dim` de vectores = parámetro SIEMPRE (lección vector_cache.py:41).
//! - Paridad ANTES que velocidad: resultado distinto = gate inválido.

/// Versión del núcleo nativo (reportada por `cortex_core._native.core_version()`).
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

pub mod bm25;
pub mod scoring;
pub mod store;
pub mod webgraph;

#[cfg(test)]
mod tests {
    use super::VERSION;

    #[test]
    fn smoke_version() {
        assert!(!VERSION.is_empty());
        assert_eq!(VERSION, "0.1.0");
    }
}
