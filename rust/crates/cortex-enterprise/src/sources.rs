//! Puerto de `cortex.enterprise.sources`: lectores multi-vault y
//! multi-episódico. Los tipos son owned y anotan origen (scope/project/
//! vault/persist_dir) exactamente como los `model_copy(update=…)` de Python.

use crate::error::EnterpriseError;
use cortex_app::episodic::MemoryEntry;

/// Scope de origen de un hit.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SourceScope {
    Local,
    Enterprise,
}

impl SourceScope {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Local => "local",
            Self::Enterprise => "enterprise",
        }
    }
}

/// Espejo de `VaultSource`.
#[derive(Debug, Clone)]
pub struct VaultSource {
    pub path: String,
    pub scope: SourceScope,
    pub project_id: String,
}

/// Espejo de `EpisodicSource`.
#[derive(Debug, Clone)]
pub struct EpisodicSource {
    pub persist_dir: String,
    pub scope: SourceScope,
    pub project_id: String,
    pub collection_name: String,
}

/// SemanticDocument anotado con origen.
#[derive(Debug, Clone)]
pub struct SemanticHit {
    pub path: String,
    pub title: String,
    pub content: String,
    pub score: f64,
    pub origin_scope: SourceScope,
    pub origin_project_id: String,
    pub origin_vault: String,
    pub origin_persist_dir: String,
}

impl SemanticHit {
    pub fn new(
        path: impl Into<String>,
        title: impl Into<String>,
        content: impl Into<String>,
        score: f64,
    ) -> Self {
        Self {
            path: path.into(),
            title: title.into(),
            content: content.into(),
            score,
            origin_scope: SourceScope::Local,
            origin_project_id: String::new(),
            origin_vault: String::new(),
            origin_persist_dir: String::new(),
        }
    }

    /// Anota origen (equivalente al `model_copy(update={origin_*})`).
    pub fn with_origin(mut self, scope: SourceScope, project_id: String, vault: String) -> Self {
        self.origin_scope = scope;
        self.origin_project_id = project_id;
        self.origin_vault = vault;
        self
    }
}

/// `EpisodicHit` con entry + origen.
#[derive(Debug, Clone)]
pub struct EpisodicHit {
    pub entry: MemoryEntry,
    pub score: f64,
    pub origin_scope: SourceScope,
    pub origin_project_id: String,
    pub origin_vault: String,
    pub origin_persist_dir: String,
}

/// Backend de búsqueda inyectable por fuente (seam de testabilidad; el
/// adapter nativo vive en `retrieval::native`).
pub trait SearchBackend: Send {
    fn search_vault(
        &mut self,
        source: &VaultSource,
        query: &str,
        top_k: usize,
        use_embeddings: bool,
    ) -> Result<Vec<SemanticHit>, EnterpriseError>;
    fn search_episodic(
        &mut self,
        source: &EpisodicSource,
        query: &str,
        top_k: usize,
        use_embeddings: bool,
    ) -> Result<Vec<EpisodicHit>, EnterpriseError>;
}
