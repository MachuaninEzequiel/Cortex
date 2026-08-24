//! cortex-config — porteo del bloque de configuración de Cortex a serde.
//!
//! Obra 07 fase P1 (docs/transformacion/08-MIGRACION-TOTAL-RUST.md §4):
//! replica `cortex/core.py` (CortexConfig y bloques episodic/semantic/
//! retrieval/embedding/…) con la MISMA semántica de validación, defaults,
//! migraciones legacy (`episodic.embedding_*` → bloque `embedding:`) y
//! warnings. Los tests de `tests/unit/` Python que ejercitan config son LA
//! especificación hasta el cierre de la fase.
//!
//! Estado P0: scaffolding — este crate aún no expone modelos; entra en P1.

#![forbid(unsafe_code)]

/// Versión del esquema de config soportado por este crate.
pub const SCHEMA_VERSION: &str = "0.7.0";

#[cfg(test)]
mod tests {
    #[test]
    fn smoke_compila_y_expone_version_de_esquema() {
        assert!(!super::SCHEMA_VERSION.is_empty());
    }
}
