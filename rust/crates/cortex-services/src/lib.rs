//! Servicios de dominio portados en P12A-5/P12A-6.
//!
//! - [`spec`]: SpecService — validación, persistencia, index selectivo,
//!   apertura best-effort de Session y memoria episódica.
//! - [`note`]: NoteService — nota session con rollback transaccional.
//! - [`migration`]: migrador de bóvedas legacy → esquema canónico.

pub mod migration;
pub mod note;
pub mod spec;

use std::collections::BTreeMap;

use serde_json::Value;

/// Request común al store episódico (equivale a `EpisodicMemoryStore.add`).
#[derive(Debug, Clone, PartialEq)]
pub struct EpisodicRequest {
    pub content: String,
    pub memory_type: String,
    pub tags: Vec<String>,
    pub files: Vec<String>,
    pub extra_metadata: BTreeMap<String, Value>,
}

/// Puerto episódico con fallo observable.
pub trait EpisodicPort {
    fn add(&mut self, request: EpisodicRequest) -> Result<(), String>;
}

/// Puerto semántico con errores necesarios para rollback transaccional.
pub trait SemanticPort {
    fn index_file(&mut self, rel_path: &str) -> Result<bool, String>;
    fn sync(&mut self) -> Result<usize, String>;
}

/// Puerto opcional para abrir una Session tras crear una spec.
pub trait SessionOpener {
    fn open(
        &self,
        spec_id: &str,
        spec_path: &str,
        spec_summary: &str,
    ) -> Result<cortex_app::session::SessionRecord, String>;
}

impl SessionOpener for cortex_app::session::service::SessionService {
    fn open(
        &self,
        spec_id: &str,
        spec_path: &str,
        spec_summary: &str,
    ) -> Result<cortex_app::session::SessionRecord, String> {
        self.open(spec_id, spec_path, spec_summary)
    }
}

/// Persistencia común sobre `cortex_setup::writers::build_note`, incluyendo
/// idempotencia por fingerprint y DuplicateDocumentError del writer Python.
pub(crate) fn persist_note(
    req: &mut cortex_setup::writers::NoteRequest,
    vault: &std::path::Path,
    now: chrono::DateTime<chrono::Utc>,
) -> Result<std::path::PathBuf, String> {
    let outcome = cortex_setup::writers::build_note(req, vault, "local", None, None, now)?;
    if outcome.path.exists() {
        let existing = std::fs::read_to_string(&outcome.path).map_err(|e| e.to_string())?;
        let nuevo = fingerprint(&outcome.content).unwrap_or_default();
        let viejo = fingerprint(&existing).unwrap_or_default();
        if !nuevo.is_empty() && nuevo == viejo {
            return Ok(outcome.path);
        }
        return Err(format!(
            "Document already exists with different content: {}. Pass overwrite=True to replace, or choose a different title.",
            outcome.path.display()
        ));
    }
    if let Some(parent) = outcome.path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    std::fs::write(&outcome.path, outcome.content).map_err(|e| e.to_string())?;
    Ok(outcome.path)
}

fn fingerprint(md: &str) -> Option<String> {
    let rest = md.strip_prefix("---")?;
    let fin = rest.find("\n---")?;
    rest[..fin].lines().find_map(|line| {
        line.strip_prefix("fingerprint:")
            .map(|v| v.trim().trim_matches('"').trim_matches('\'').to_string())
    })
}
