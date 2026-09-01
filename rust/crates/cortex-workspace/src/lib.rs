//! Porteo de los módulos de workspace de Cortex a Rust nativo.
//!
//! Obra 07 fase **P12B-1** (stream B, dual-stream §7 de
//! `docs/transformacion/09-DEUDA-MIGRACION-PYTHON.md`). Piezas:
//!
//! - [`layout`] — `cortex/workspace/layout.py`: `WorkspaceLayout` con
//!   discovery legacy/nuevo (`discover`) y TODAS las propiedades de rutas.
//! - [`handoff`] — `cortex/handoff.py`: schema `AgentHandoff` (contrato YAML
//!   legacy entre agentes) con serialización byte-parity vs PyYAML.
//! - [`git_policy`] — `cortex/git_policy.py`: patrones/snippet de `.gitignore`
//!   por layout y chequeo de contenido.
//! - [`skills`] — `cortex/skills/__init__.py`: instalación del bundle de
//!   skills Obsidian embebido en el binario (`include_str!`, sin deps).
//! - [`runtime_context`] — `cortex/runtime_context.py`: slugify, detección
//!   git (branch/toplevel) y resolución del directorio episódico por
//!   namespace (project/branch/custom).
//! - [`pyyaml`] — emisor YAML compatible byte-a-byte con `yaml.safe_dump`
//!   (PyYAML), necesario porque `serde_yaml` NO replica el formato de
//!   PyYAML (folding a 80 columnas, quoting de indicadores, indentless
//!   sequences). Ver contrato en el módulo.
//!
//! Contrato general P12B-1: paridad conductual contra el oráculo
//! `bench/parity/workspace_golden_p12b.py` (build/verify) + checker Rust
//! `examples/workspace_check.rs`. Los tests Python (`tests/unit/workspace`,
//! `tests/unit/handoff.py`, `tests/unit/runtime_context.py`,
//! `tests/unit/skills`) son LA especificación.
//!
//! Nota sobre `resolve_safe`: pertenece al stream A (cortex-app,
//! `cortex/security/paths.py`); este crate NO lo duplica — quien necesite
//! resolución segura consume `cortex_app::security`.

#![forbid(unsafe_code)]

pub mod git_policy;
pub mod handoff;
pub mod layout;
pub mod pyyaml;
pub mod runtime_context;
pub mod skills;

pub use git_policy::{
    gitignore_contains, recommended_gitignore_snippet, LEGACY_GITIGNORE_PATTERNS,
    NEW_LAYOUT_GITIGNORE_PATTERNS, RECOMMENDED_GITIGNORE_PATTERNS,
};
pub use handoff::{AgentHandoff, AgentName, ArtifactAction, ArtifactProduced, HandoffStatus};
pub use layout::WorkspaceLayout;
pub use runtime_context::{
    detect_git_branch, detect_git_repo_path, resolve_episodic_persist_dir, slugify,
    EpisodicNamespaceCfg,
};
pub use skills::{install_skills, SKILL_NAMES};
