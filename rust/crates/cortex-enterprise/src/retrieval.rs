//! Puerto de `cortex.enterprise.retrieval_service`: búsqueda multi-scope con
//! fusión RRF (k=60, rank desde 1, inserción estable) y pesos por scope.
//!
//! Paridad crítica replicada:
//! - `scores[key] += weight * 1/(k+rank)` en orden episódico-then-semántico;
//! - `ranked_keys = sorted(scores, reverse=True)` ESTABLE sobre el orden de
//!   primera inserción;
//! - preferencia enterprise SOLO para el objeto unificado
//!   (`existing is None or (existing.scope != 'enterprise' and this is)`);
//! - keys: `semantic:{path}` / `semantic:title:{title}` /
//!   `episodic:content:{primeros160-normalizados}` / `episodic:{id}`.

use std::collections::BTreeMap;
use std::path::PathBuf;

use cortex_app::episodic::MemoryEntry;

use crate::error::EnterpriseError;
use crate::models::EnterpriseOrgConfig;
pub use crate::models::RetrievalScope;
use crate::sources::{
    EpisodicHit, EpisodicSource, SearchBackend, SemanticHit, SourceScope, VaultSource,
};

const RRF_K: f64 = 60.0;

/// Pesos por scope (`RetrievalSourceConfig` Python).
#[derive(Debug, Clone, Copy)]
pub struct RetrievalSourceConfig {
    pub local_weight: f64,
    pub enterprise_weight: f64,
}

impl Default for RetrievalSourceConfig {
    fn default() -> Self {
        Self {
            local_weight: 1.0,
            enterprise_weight: 1.0,
        }
    }
}

/// Hit unificado post-fusión.
#[derive(Debug, Clone)]
pub struct UnifiedHit {
    pub source: String,
    pub score: f64,
    pub entry: Option<MemoryEntry>,
    pub doc: Option<SemanticHit>,
    pub metadata: serde_json::Map<String, serde_json::Value>,
}

/// Resultado espejo de `RetrievalResult`.
#[derive(Debug, Clone)]
pub struct RetrievalResult {
    pub query: String,
    pub episodic_hits: Vec<EpisodicHit>,
    pub semantic_hits: Vec<SemanticHit>,
    pub unified_hits: Vec<UnifiedHit>,
    pub source_breakdown: BTreeMap<String, usize>,
}

/// Servicio de retrieval enterprise genérico sobre el backend inyectado.
pub struct EnterpriseRetrievalService<B: SearchBackend> {
    config: EnterpriseOrgConfig,
    local_project_id: String,
    project_root: PathBuf,
    workspace_root: PathBuf,
    local_vault_path: String,
    local_episodic_dir: String,
    local_collection_name: String,
    source_config: RetrievalSourceConfig,
    backend: B,
}

impl<B: SearchBackend> EnterpriseRetrievalService<B> {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        config: EnterpriseOrgConfig,
        local_project_id: String,
        project_root: PathBuf,
        workspace_root: PathBuf,
        local_vault_path: String,
        local_episodic_dir: String,
        local_collection_name: String,
        source_config: Option<RetrievalSourceConfig>,
        backend: B,
    ) -> Self {
        Self {
            config,
            local_project_id,
            project_root,
            workspace_root,
            local_vault_path,
            local_episodic_dir,
            local_collection_name,
            source_config: source_config.unwrap_or_default(),
            backend,
        }
    }

    /// `search`: fuentes por scope, lecturas multi-source, filtro por
    /// project_id y fusión RRF.
    pub fn search(
        &mut self,
        query: &str,
        scope: RetrievalScope,
        top_k: usize,
        use_embeddings: bool,
        project_id: Option<&str>,
    ) -> Result<RetrievalResult, EnterpriseError> {
        let vault_sources = self.build_vault_sources(scope);
        let episodic_sources = self.build_episodic_sources(scope);
        if scope == RetrievalScope::Enterprise
            && vault_sources.is_empty()
            && episodic_sources.is_empty()
        {
            return Err(EnterpriseError::Validation(
                "Enterprise scope requested but no enterprise sources are enabled \
                 (enterprise_semantic_enabled / enterprise_episodic_enabled)."
                    .to_string(),
            ));
        }

        // MultiVaultReader.search: TODOS los hits por fuente en orden.
        let mut semantic_hits = Vec::new();
        for source in &vault_sources {
            for hit in self
                .backend
                .search_vault(source, query, top_k, use_embeddings)?
            {
                semantic_hits.push(hit);
            }
        }
        let mut episodic_hits = Vec::new();
        for source in &episodic_sources {
            for hit in self
                .backend
                .search_episodic(source, query, top_k, use_embeddings)?
            {
                episodic_hits.push(hit);
            }
        }

        if let Some(project_id) = project_id {
            semantic_hits.retain(|h| h.origin_project_id == project_id);
            episodic_hits.retain(|h| h.origin_project_id == project_id);
        }

        let unified_hits = self.fuse_multi_scope(&episodic_hits, &semantic_hits, top_k);
        let source_breakdown = build_source_breakdown(&unified_hits);
        Ok(RetrievalResult {
            query: query.to_string(),
            episodic_hits: episodic_hits.into_iter().take(top_k).collect(),
            semantic_hits: semantic_hits.into_iter().take(top_k).collect(),
            unified_hits,
            source_breakdown,
        })
    }

    fn build_vault_sources(&self, scope: RetrievalScope) -> Vec<VaultSource> {
        let mut sources = Vec::new();
        if matches!(scope, RetrievalScope::Local | RetrievalScope::All) {
            sources.push(VaultSource {
                path: self.local_vault_path.clone(),
                scope: SourceScope::Local,
                project_id: self.local_project_id.clone(),
            });
        }
        if matches!(scope, RetrievalScope::Enterprise | RetrievalScope::All)
            && self.config.memory.enterprise_semantic_enabled
        {
            if let Some(vault) = self
                .config
                .resolve_enterprise_vault_path(&self.project_root, Some(&self.workspace_root))
            {
                sources.push(VaultSource {
                    path: vault.display().to_string(),
                    scope: SourceScope::Enterprise,
                    project_id: self.config.organization.slug.clone(),
                });
            }
        }
        sources
    }

    fn build_episodic_sources(&self, scope: RetrievalScope) -> Vec<EpisodicSource> {
        let mut sources = Vec::new();
        if matches!(scope, RetrievalScope::Local | RetrievalScope::All) {
            sources.push(EpisodicSource {
                persist_dir: self.local_episodic_dir.clone(),
                scope: SourceScope::Local,
                project_id: self.local_project_id.clone(),
                collection_name: self.local_collection_name.clone(),
            });
        }
        if matches!(scope, RetrievalScope::Enterprise | RetrievalScope::All)
            && self.config.memory.enterprise_episodic_enabled
        {
            if let Some(memory) = self
                .config
                .resolve_enterprise_memory_path(&self.project_root, Some(&self.workspace_root))
            {
                sources.push(EpisodicSource {
                    persist_dir: memory.display().to_string(),
                    scope: SourceScope::Enterprise,
                    project_id: self.config.organization.slug.clone(),
                    collection_name: format!("{}_enterprise", self.local_collection_name),
                });
            }
        }
        sources
    }

    /// `_fuse_multi_scope`.
    fn fuse_multi_scope(
        &self,
        episodic_hits: &[EpisodicHit],
        semantic_hits: &[SemanticHit],
        top_k: usize,
    ) -> Vec<UnifiedHit> {
        // scores + orden de primera inserción (dict de Python).
        let mut keys: Vec<String> = Vec::new();
        let mut scores: Vec<f64> = Vec::new();
        // unified_map: key → (source, entry/doc, metadata).
        let mut unified_order: Vec<String> = Vec::new();
        let mut unified: BTreeMap<String, UnifiedHit> = BTreeMap::new();

        let insert_key = |keys: &mut Vec<String>, scores: &mut Vec<f64>, key: String| -> usize {
            match keys.iter().position(|k| *k == key) {
                Some(i) => i,
                None => {
                    keys.push(key.clone());
                    scores.push(0.0);
                    keys.len() - 1
                }
            }
        };

        for (rank, hit) in episodic_hits.iter().enumerate() {
            let weight = self.scope_weight(hit.origin_scope);
            let key = episodic_key(hit);
            let i = insert_key(&mut keys, &mut scores, key.clone());
            scores[i] += weight * (1.0 / (RRF_K + rank as f64 + 1.0));

            let mut metadata = serde_json::Map::new();
            metadata.insert("scope".into(), serde_json::json!(hit.origin_scope.as_str()));
            metadata.insert(
                "project_id".into(),
                serde_json::json!(hit.origin_project_id),
            );
            metadata.insert("origin_vault".into(), serde_json::json!(hit.origin_vault));
            metadata.insert(
                "origin_persist_dir".into(),
                serde_json::json!(hit.origin_persist_dir),
            );
            let candidate = UnifiedHit {
                source: "episodic".into(),
                score: 0.0,
                entry: Some(hit.entry.clone()),
                doc: None,
                metadata,
            };
            unify_insert(&mut unified, &mut unified_order, key, candidate);
        }

        for (rank, doc) in semantic_hits.iter().enumerate() {
            let weight = self.scope_weight(doc.origin_scope);
            let key = semantic_key(doc);
            let i = insert_key(&mut keys, &mut scores, key.clone());
            scores[i] += weight * (1.0 / (RRF_K + rank as f64 + 1.0));

            let mut metadata = serde_json::Map::new();
            metadata.insert("scope".into(), serde_json::json!(doc.origin_scope.as_str()));
            metadata.insert(
                "project_id".into(),
                serde_json::json!(doc.origin_project_id),
            );
            metadata.insert("origin_vault".into(), serde_json::json!(doc.origin_vault));
            metadata.insert(
                "origin_persist_dir".into(),
                serde_json::json!(doc.origin_persist_dir),
            );
            let candidate = UnifiedHit {
                source: "semantic".into(),
                score: 0.0,
                entry: None,
                doc: Some(doc.clone()),
                metadata,
            };
            unify_insert(&mut unified, &mut unified_order, key, candidate);
        }

        // sorted(scores, reverse=True) estable sobre orden de inserción.
        let mut order: Vec<usize> = (0..keys.len()).collect();
        order.sort_by(|&a, &b| scores[b].total_cmp(&scores[a]));
        order.truncate(top_k);

        order
            .into_iter()
            .map(|i| {
                let mut hit = unified.get(&keys[i]).cloned().expect("unified presente");
                hit.score = scores[i];
                hit
            })
            .collect()
    }

    fn scope_weight(&self, scope: SourceScope) -> f64 {
        match scope {
            SourceScope::Enterprise => self.source_config.enterprise_weight,
            SourceScope::Local => self.source_config.local_weight,
        }
    }
}

/// Regla de reemplazo del objeto unificado.
fn unify_insert(
    unified: &mut BTreeMap<String, UnifiedHit>,
    _order: &mut Vec<String>,
    key: String,
    candidate: UnifiedHit,
) {
    match unified.get(&key) {
        None => {
            unified.insert(key, candidate);
        }
        Some(existing) => {
            let existing_is_ent =
                existing.metadata.get("scope").and_then(|s| s.as_str()) == Some("enterprise");
            let cand_is_ent =
                candidate.metadata.get("scope").and_then(|s| s.as_str()) == Some("enterprise");
            if !existing_is_ent && cand_is_ent {
                unified.insert(key, candidate);
            }
        }
    }
}

fn semantic_key(doc: &SemanticHit) -> String {
    let path = doc.path.trim().to_lowercase();
    let title = doc.title.trim().to_lowercase();
    if !path.is_empty() {
        format!("semantic:{path}")
    } else {
        format!("semantic:title:{title}")
    }
}

fn episodic_key(hit: &EpisodicHit) -> String {
    let content = hit
        .entry
        .content
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ");
    let content = content.trim().to_lowercase();
    if content.is_empty() {
        format!("episodic:{}", hit.entry.id)
    } else {
        format!("episodic:content:{}", &content[..content.len().min(160)])
    }
}

fn build_source_breakdown(unified_hits: &[UnifiedHit]) -> BTreeMap<String, usize> {
    let mut breakdown = BTreeMap::from([("local".to_string(), 0), ("enterprise".to_string(), 0)]);
    for hit in unified_hits {
        let scope = hit
            .metadata
            .get("scope")
            .and_then(|s| s.as_str())
            .unwrap_or("local")
            .to_string();
        *breakdown.entry(scope).or_insert(0) += 1;
    }
    breakdown
}
