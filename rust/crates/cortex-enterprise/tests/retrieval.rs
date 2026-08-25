use std::collections::BTreeMap;
use std::sync::Arc;

use cortex_enterprise::clock::FixedClock;
use cortex_enterprise::config::build_enterprise_org_config;
use cortex_enterprise::error::EnterpriseError;
use cortex_enterprise::retrieval::{
    EnterpriseRetrievalService, RetrievalScope, RetrievalSourceConfig,
};
use cortex_enterprise::sources::{
    EpisodicHit, EpisodicSource, SearchBackend, SemanticHit, SourceScope, VaultSource,
};

fn config_for(
    profile: cortex_enterprise::models::OrgProfile,
) -> cortex_enterprise::models::EnterpriseOrgConfig {
    build_enterprise_org_config("Acme", profile, true, false).unwrap()
}

struct DuplicateBackend;

impl SearchBackend for DuplicateBackend {
    fn search_vault(
        &mut self,
        source: &VaultSource,
        _query: &str,
        top_k: usize,
        _use_embeddings: bool,
    ) -> Result<Vec<SemanticHit>, EnterpriseError> {
        let _ = top_k;
        let hits = vec![SemanticHit::new(
            "runbook/auth.md",
            "Auth",
            "shared content",
            0.9,
        )];
        Ok(hits
            .into_iter()
            .map(|h| h.with_origin(source.scope, source.project_id.clone(), source.path.clone()))
            .collect())
    }

    fn search_episodic(
        &mut self,
        _source: &EpisodicSource,
        _query: &str,
        _top_k: usize,
        _use_embeddings: bool,
    ) -> Result<Vec<EpisodicHit>, EnterpriseError> {
        Ok(vec![])
    }
}

#[test]
fn all_scope_deduplicates_same_semantic_path_preferring_enterprise() {
    let config = config_for(cortex_enterprise::models::OrgProfile::MultiProjectTeam);
    let mut service = EnterpriseRetrievalService::new(
        config,
        "acme-project".to_string(),
        std::env::current_dir().unwrap(),
        std::env::current_dir().unwrap(),
        "vault".to_string(),
        ".memory/chroma".to_string(),
        "cortex_episodic".to_string(),
        None,
        DuplicateBackend,
    );
    let result = service
        .search("auth", RetrievalScope::All, 5, true, None)
        .unwrap();
    let semantic_unified: Vec<_> = result
        .unified_hits
        .iter()
        .filter(|h| h.source == "semantic")
        .collect();
    assert_eq!(semantic_unified.len(), 1, "misma ruta se deduplica");
    assert_eq!(
        semantic_unified[0].metadata["scope"], "enterprise",
        "gana el candidato enterprise para el objeto unificado"
    );
    // Breakdown cuenta el unificado.
    assert_eq!(result.source_breakdown["enterprise"], 1);
}

#[test]
fn local_scope_annotates_only_local_and_truncates() {
    let config = config_for(cortex_enterprise::models::OrgProfile::SmallCompany);
    let mut service = EnterpriseRetrievalService::new(
        config,
        "acme-project".to_string(),
        std::env::current_dir().unwrap(),
        std::env::current_dir().unwrap(),
        "vault".to_string(),
        ".memory/chroma".to_string(),
        "cortex_episodic".to_string(),
        None,
        LocalEpisodicBackend,
    );
    let result = service
        .search("auth", RetrievalScope::Local, 5, true, None)
        .unwrap();
    assert!(result
        .unified_hits
        .iter()
        .all(|h| h.metadata["scope"] == "local"));
    assert_eq!(result.semantic_hits.len(), 1);
    assert_eq!(result.episodic_hits.len(), 1);
    assert_eq!(result.source_breakdown["local"], 2);
    assert_eq!(result.source_breakdown["enterprise"], 0);
}

struct LocalEpisodicBackend;

impl SearchBackend for LocalEpisodicBackend {
    fn search_vault(
        &mut self,
        source: &VaultSource,
        _: &str,
        _: usize,
        _: bool,
    ) -> Result<Vec<SemanticHit>, EnterpriseError> {
        Ok(vec![SemanticHit::new("a.md", "A", "local", 0.9)
            .with_origin(
                source.scope,
                source.project_id.clone(),
                source.path.clone(),
            )])
    }
    fn search_episodic(
        &mut self,
        source: &EpisodicSource,
        _: &str,
        _: usize,
        _: bool,
    ) -> Result<Vec<EpisodicHit>, EnterpriseError> {
        let mut entry = cortex_app::episodic::MemoryEntry {
            id: format!("mem_{}", source.collection_name),
            content: "mem".into(),
            memory_type: "general".into(),
            tags: vec![],
            files: vec![],
            timestamp: "2026-08-25T00:00:00+00:00".into(),
            metadata: BTreeMap::new(),
        };
        // Metadata merge estilo MultiEpisodicReader.
        entry
            .metadata
            .insert("scope".into(), serde_json::json!(source.scope.as_str()));
        entry
            .metadata
            .insert("project_id".into(), serde_json::json!(source.project_id));
        entry
            .metadata
            .insert("origin_vault".into(), serde_json::json!(""));
        entry.metadata.insert(
            "origin_persist_dir".into(),
            serde_json::json!(source.persist_dir),
        );
        Ok(vec![EpisodicHit {
            entry,
            score: 0.9,
            origin_scope: source.scope,
            origin_project_id: source.project_id.clone(),
            origin_vault: String::new(),
            origin_persist_dir: source.persist_dir.clone(),
        }])
    }
}

#[test]
fn project_id_filter_keeps_matching_origins_only() {
    let config = config_for(cortex_enterprise::models::OrgProfile::MultiProjectTeam);
    let mut service = EnterpriseRetrievalService::new(
        config,
        "acme-project".to_string(),
        std::env::current_dir().unwrap(),
        std::env::current_dir().unwrap(),
        "vault".to_string(),
        ".memory/chroma".to_string(),
        "cortex_episodic".to_string(),
        None,
        FilterProbeBackend,
    );
    let result = service
        .search("policy", RetrievalScope::All, 5, true, Some("acme-project"))
        .unwrap();
    assert!(result
        .unified_hits
        .iter()
        .all(|h| h.metadata["project_id"] == "acme-project"));
}

/// Devuelve hits con project_ids distintos por scope para probar el filtro.
struct FilterProbeBackend;

impl SearchBackend for FilterProbeBackend {
    fn search_vault(
        &mut self,
        source: &VaultSource,
        _: &str,
        _: usize,
        _: bool,
    ) -> Result<Vec<SemanticHit>, EnterpriseError> {
        let project = match source.scope {
            SourceScope::Local => "acme-project",
            SourceScope::Enterprise => "acme-org",
        };
        Ok(vec![SemanticHit::new("doc.md", "Doc", "x", 0.9)
            .with_origin(
                source.scope,
                project.to_string(),
                source.path.clone(),
            )])
    }
    fn search_episodic(
        &mut self,
        _s: &EpisodicSource,
        _: &str,
        _: usize,
        _: bool,
    ) -> Result<Vec<EpisodicHit>, EnterpriseError> {
        Ok(vec![])
    }
}

#[test]
fn enterprise_scope_without_sources_fails_with_python_message() {
    let mut config = config_for(cortex_enterprise::models::OrgProfile::SmallCompany);
    config.memory.enterprise_semantic_enabled = false;
    config.memory.enterprise_episodic_enabled = false;
    let mut service = EnterpriseRetrievalService::new(
        config,
        "acme-project".to_string(),
        std::env::current_dir().unwrap(),
        std::env::current_dir().unwrap(),
        "vault".to_string(),
        ".memory/chroma".to_string(),
        "cortex_episodic".to_string(),
        None,
        DuplicateBackend,
    );
    let err = service
        .search("policy", RetrievalScope::Enterprise, 5, true, None)
        .unwrap_err();
    assert_eq!(
        err.to_string(),
        "Enterprise scope requested but no enterprise sources are enabled (enterprise_semantic_enabled / enterprise_episodic_enabled)."
    );
}

/// Pesos: con enterprise_weight=1.2 el hit enterprise supera al local aunque
/// compartan contenido; el orden de empates es estable (inserción).
#[test]
fn enterprise_weight_boosts_rank_and_ties_are_stable() {
    let config = config_for(cortex_enterprise::models::OrgProfile::MultiProjectTeam);
    let mut service = EnterpriseRetrievalService::new(
        config,
        "acme-project".to_string(),
        std::env::current_dir().unwrap(),
        std::env::current_dir().unwrap(),
        "vault".to_string(),
        ".memory/chroma".to_string(),
        "cortex_episodic".to_string(),
        Some(RetrievalSourceConfig {
            local_weight: 1.0,
            enterprise_weight: 1.2,
        }),
        WeightedBackend,
    );
    let result = service
        .search("q", RetrievalScope::All, 10, true, None)
        .unwrap();
    let scopes: Vec<&str> = result
        .unified_hits
        .iter()
        .map(|h| h.metadata["scope"].as_str().unwrap())
        .collect();
    // El semántico enterprise (peso 1.2·1/61) supera al local (1.0·1/61).
    let ent_pos = scopes.iter().position(|s| *s == "enterprise").unwrap();
    let loc_pos = scopes.iter().position(|s| *s == "local").unwrap();
    assert!(ent_pos < loc_pos);
}

struct WeightedBackend;

impl SearchBackend for WeightedBackend {
    fn search_vault(
        &mut self,
        source: &VaultSource,
        _: &str,
        _: usize,
        _: bool,
    ) -> Result<Vec<SemanticHit>, EnterpriseError> {
        let path = match source.scope {
            SourceScope::Local => "local.md",
            SourceScope::Enterprise => "enterprise.md",
        };
        Ok(vec![SemanticHit::new(path, "Same", "x", 0.9).with_origin(
            source.scope,
            source.project_id.clone(),
            source.path.clone(),
        )])
    }
    fn search_episodic(
        &mut self,
        _: &EpisodicSource,
        _: &str,
        _: usize,
        _: bool,
    ) -> Result<Vec<EpisodicHit>, EnterpriseError> {
        Ok(vec![])
    }
}

#[test]
fn clock_is_unused_but_available_for_future_native_glue() {
    // Guarda compatibilidad de interfaz con el resto del crate (Clock ya
    // usado por promoción); evita drift silencioso de imports compartidos.
    let clk = FixedClock::parse("2026-08-25T12:00:00+00:00").unwrap();
    let _ = Arc::new(clk);
}
