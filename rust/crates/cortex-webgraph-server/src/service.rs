//! Porteo de `cortex/webgraph/service.py` — orquestación de snapshots.
//!
//! GAP explícito (P12B-3): `_append_enterprise_nodes` depende de
//! `cortex.enterprise.config` (crate cortex-enterprise, tarea P12B-3).
//! Mientras ese crate no exista, si el proyecto TIENE org.yaml se emite
//! warning por stderr y el snapshot queda SIN nodos enterprise (jamás se
//! finge paridad: el gate cubre proyectos sin org.yaml, que es el caso
//! donde Python tampoco agrega nada).

#![forbid(unsafe_code)]

use std::collections::{BTreeSet, HashMap, VecDeque};
use std::path::{Path, PathBuf};

use chrono::Utc;
use serde_json::json;

use crate::cache::WebGraphCache;
use crate::config::WebGraphConfig;
use crate::contracts::{
    WebGraphEdge, WebGraphMode, WebGraphNode, WebGraphNodeDetail, WebGraphSnapshot,
};
use crate::graph_builder::GraphBuilder;
use crate::sources::{EmbedFn, EpisodicSource, SemanticSource};
use cortex_workspace::WorkspaceLayout;

pub struct WebGraphService {
    pub project_root: PathBuf,
    pub config: WebGraphConfig,
    pub semantic_source: SemanticSource,
    pub episodic_source: EpisodicSource,
    pub cache: WebGraphCache,
}

impl WebGraphService {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        project_root: &Path,
        config: Option<WebGraphConfig>,
        vault_path: Option<PathBuf>,
        persist_dir: Option<PathBuf>,
        episodic_entries: Vec<cortex_app::episodic::MemoryEntry>,
        embedder: Option<EmbedFn>,
        workspace_layout: Option<WorkspaceLayout>,
    ) -> WebGraphService {
        let layout_owned;
        let layout: &WorkspaceLayout = if let Some(l) = workspace_layout {
            // Se mueve a un local para poder tomar referencia uniforme.
            layout_owned = l;
            &layout_owned
        } else {
            layout_owned = WorkspaceLayout::discover(project_root);
            &layout_owned
        };
        let config_path = layout.config_path();
        let cfg = config.unwrap_or_else(|| WebGraphConfig::load(Some(project_root), Some(layout)));
        let semantic =
            SemanticSource::new(&config_path, layout, vault_path.clone(), embedder.clone());
        let episodic = EpisodicSource::new(
            &config_path,
            layout,
            persist_dir.clone(),
            episodic_entries,
            embedder,
        );
        let cache = WebGraphCache::new(project_root, Some(layout));
        Self {
            project_root: project_root.to_path_buf(),
            config: cfg,
            semantic_source: semantic,
            episodic_source: episodic,
            cache,
        }
    }

    pub fn build_snapshot_by_mode(
        &self,
        mode: &str,
        use_cache: bool,
        scope: Option<&str>,
    ) -> WebGraphSnapshot {
        let _mode: WebGraphMode = mode.to_string();
        self.build_snapshot(mode, use_cache, scope)
    }

    pub fn build_snapshot(
        &self,
        mode: &str,
        use_cache: bool,
        scope: Option<&str>,
    ) -> WebGraphSnapshot {
        let fingerprint = self.cache.compute_fingerprint(
            &self.semantic_source.vault_path,
            &self.episodic_source.persist_dir,
            self.episodic_source.count(),
            self.episodic_source.cache_token(),
            &self.config.model_dump(),
        );
        if use_cache {
            if let Some(cached) = self.cache.load_snapshot(mode, &fingerprint, scope) {
                return cached;
            }
        }

        let include_embeddings = mode == "hybrid";
        let semantic_records = self.semantic_source.load_records(include_embeddings);
        let episodic_records = self.episodic_source.load_records(include_embeddings);
        let builder = GraphBuilder::new(self.config.clone());
        let generated_at = Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Micros, true);
        let mut snapshot = builder.build_snapshot(
            &fingerprint,
            mode,
            &generated_at,
            semantic_records,
            episodic_records,
        );

        // metadata: {"project_id": pid, "scope": "local", **node.metadata}
        let project_id = cortex_workspace::slugify(
            &self
                .project_root
                .file_name()
                .map(|s| s.to_string_lossy().to_string())
                .unwrap_or_default(),
            "project",
        );
        for node in &mut snapshot.nodes {
            let mut merged = serde_json::Map::new();
            merged.insert("project_id".into(), json!(project_id));
            merged.insert("scope".into(), json!("local"));
            for (k, v) in &node.metadata {
                merged.insert(k.clone(), v.clone());
            }
            node.metadata = merged;
        }

        snapshot = append_enterprise_nodes(snapshot, &self.project_root, &project_id);
        snapshot = filter_snapshot_by_scope(snapshot, scope);
        self.cache.store_snapshot(mode, &snapshot, scope);
        snapshot
    }

    pub fn get_node_detail(&self, node_id: &str, mode: &str) -> Option<WebGraphNodeDetail> {
        let snapshot = self.build_snapshot(mode, true, None);
        let nodes_by_id: HashMap<&str, &WebGraphNode> =
            snapshot.nodes.iter().map(|n| (n.id.as_str(), n)).collect();
        let node = nodes_by_id.get(node_id)?;
        let relations: Vec<WebGraphEdge> = snapshot
            .edges
            .iter()
            .filter(|e| e.source == node_id || e.target == node_id)
            .cloned()
            .collect();
        let neighbor_ids: BTreeSet<String> = relations
            .iter()
            .map(|e| {
                if e.source == node_id {
                    e.target.clone()
                } else {
                    e.source.clone()
                }
            })
            .collect();
        let neighbors: Vec<WebGraphNode> = neighbor_ids
            .iter()
            .filter_map(|id| nodes_by_id.get(id.as_str()).map(|n| (*n).clone()))
            .collect();
        Some(WebGraphNodeDetail {
            node: (*node).clone(),
            relations,
            neighbors,
        })
    }

    pub fn resolve_node_path(&self, node_id: &str, mode: &str) -> Option<PathBuf> {
        let detail = self.get_node_detail(node_id, mode)?;
        let rel_path = detail.node.rel_path?;
        if rel_path.is_empty() {
            return None;
        }
        Some(cortex_workspace::layout::resolve_lexical(
            &self.semantic_source.vault_path.join(rel_path),
        ))
    }

    pub fn get_subgraph(
        &self,
        node_id: &str,
        depth: i64,
        mode: &str,
        edge_types: Option<&BTreeSet<String>>,
    ) -> WebGraphSnapshot {
        let snapshot = self.build_snapshot(mode, true, None);
        let mut adjacency: HashMap<String, Vec<(String, String)>> = HashMap::new();
        for edge in &snapshot.edges {
            if let Some(types) = edge_types {
                if !types.contains(&edge.edge_type) {
                    continue;
                }
            }
            adjacency
                .entry(edge.source.clone())
                .or_default()
                .push((edge.target.clone(), edge.edge_type.clone()));
            adjacency
                .entry(edge.target.clone())
                .or_default()
                .push((edge.source.clone(), edge.edge_type.clone()));
        }

        let mut visited: BTreeSet<String> = BTreeSet::new();
        visited.insert(node_id.to_string());
        let mut queue: VecDeque<(String, i64)> = VecDeque::new();
        queue.push_back((node_id.to_string(), 0));
        while let Some((current, current_depth)) = queue.pop_front() {
            if current_depth >= depth {
                continue;
            }
            for (neighbor, _) in adjacency.get(&current).cloned().unwrap_or_default() {
                if visited.contains(&neighbor) {
                    continue;
                }
                visited.insert(neighbor.clone());
                queue.push_back((neighbor, current_depth + 1));
            }
        }

        let nodes: Vec<WebGraphNode> = snapshot
            .nodes
            .iter()
            .filter(|n| visited.contains(&n.id))
            .cloned()
            .collect();
        let edges: Vec<WebGraphEdge> = snapshot
            .edges
            .iter()
            .filter(|e| {
                visited.contains(&e.source)
                    && visited.contains(&e.target)
                    && edge_types.map(|t| t.contains(&e.edge_type)).unwrap_or(true)
            })
            .cloned()
            .collect();
        let mut out = snapshot;
        let node_count = nodes.len() as i64;
        let edge_count = edges.len() as i64;
        out.nodes = nodes;
        out.edges = edges;
        out.stats.node_count = node_count;
        out.stats.edge_count = edge_count;
        out
    }
}

/// Enterprise enrichment — ver GAP en docs del módulo. Con org.yaml presente
/// se declara la dependencia pendiente por stderr (fallo visible, no mudo).
fn append_enterprise_nodes(
    snapshot: WebGraphSnapshot,
    project_root: &Path,
    project_id: &str,
) -> WebGraphSnapshot {
    let layout = WorkspaceLayout::discover(project_root);
    let org_path = layout.org_config_path();
    if !org_path.exists() {
        return snapshot; // caso sin org.yaml: Python también devuelve igual.
    }
    eprintln!(
        "[cortex-webgraph] WARNING: org.yaml presente pero enterprise config \
         aún no portada (P12B-3): nodos enterprise omitidos (project_id={project_id})"
    );
    snapshot
}

fn filter_snapshot_by_scope(
    mut snapshot: WebGraphSnapshot,
    scope: Option<&str>,
) -> WebGraphSnapshot {
    let Some(scope) = scope else {
        return snapshot;
    };
    if scope == "all" {
        return snapshot;
    }
    if scope != "local" && scope != "enterprise" {
        return snapshot;
    }
    let allowed: BTreeSet<String> = snapshot
        .nodes
        .iter()
        .filter(|n| {
            n.metadata
                .get("scope")
                .and_then(|v| v.as_str())
                .unwrap_or("local")
                .trim()
                .to_lowercase()
                == scope
        })
        .map(|n| n.id.clone())
        .collect();
    let nodes: Vec<WebGraphNode> = snapshot
        .nodes
        .iter()
        .filter(|n| allowed.contains(&n.id))
        .cloned()
        .collect();
    let edges: Vec<WebGraphEdge> = snapshot
        .edges
        .iter()
        .filter(|e| allowed.contains(&e.source) && allowed.contains(&e.target))
        .cloned()
        .collect();
    let node_count = nodes.len() as i64;
    let edge_count = edges.len() as i64;
    snapshot.nodes = nodes;
    snapshot.edges = edges;
    snapshot.stats.node_count = node_count;
    snapshot.stats.edge_count = edge_count;
    snapshot
}
