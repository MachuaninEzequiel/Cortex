//! cortex-setup — Obra 07 P8 (stream B)
//!
//! Porteo de la capa de setup/documentación de Cortex a Rust con
//! paridad-como-contrato contra el código Python:
//!
//! - [`jinja`]: entorno minijinja que replica el env jinja2 de
//!   `cortex/documentation/templates_engine.py` (trim_blocks, lstrip_blocks,
//!   keep_trailing_newline) sobre LAS PLANTILLAS REALES `.md.j2`.
//! - [`yaml`]: dumper que replica byte-a-byte `yaml.safe_dump(data,
//!   default_flow_style=False, allow_unicode=True, sort_keys=False)` de
//!   PyYAML para los tipos de datos que produce el frontmatter canónico.
//! - [`slug`]: réplica de `cortex.documentation.common.slugify`.
//! - [`fingerprint`]: SHA-256 hex igual que `compute_fingerprint`.
//!
//! Los módulos restantes (writers canónicos, setup templates, IDE
//! adapters, session hooks) se agregan por commits atómicos dentro de P8.

pub mod detector;
pub mod doc_type;
pub mod fingerprint;
pub mod jinja;
pub mod routing;
pub mod setup_templates;
pub mod setup_templates_gen;
pub mod slug;
pub mod writers;
pub mod yaml;

/// Rutas de las plantillas canónicas reales (fuente Python, solo lectura).
pub const PY_TEMPLATES_DIR: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../cortex/documentation/templates"
);
