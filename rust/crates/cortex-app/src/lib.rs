//! cortex-app — capa de aplicación de Cortex (Obra 07).
//!
//! Acá vive el porteo de los servicios de aplicación Python:
//! sessions/quality-gates, documenter/reconstructor, ActionEngine,
//! ContextEnricher, retrieval híbrido (RRF sobre cortex-core) y setup.
//!
//! Contrato maestro: docs/transformacion/08-MIGRACION-TOTAL-RUST.md.
//! Cada componente entra por fases (P4-P7) con paridad conductual contra sus
//! tests Python originales (paridad-como-contrato). El binario `cortex` (clap)
//! y el brain consumen este crate; el MCP server (P9) lo expone vía rmcp.
//!
//! Estado: P0 scaffolding · P2a semantic (parser + BM25) · P3 episódica · P4
//! sessions/hooks/gates · P5 documenter+persister · **P7 context (este stream)**.

#![forbid(unsafe_code)]

pub mod ci;
pub mod context;
pub mod documenter;
pub mod episodic;
pub mod git;
pub mod security;
pub mod semantic;
pub mod session;

/// Identificación de build para parity logs y `--version`.
pub const BUILD_TAG: &str = concat!("cortex-app ", env!("CARGO_PKG_VERSION"));

#[cfg(test)]
mod tests {
    #[test]
    fn smoke_build_tag() {
        assert!(super::BUILD_TAG.starts_with("cortex-app "));
    }
}
