//! Porteo de `cortex/webgraph/federation.py` — grafo federado multi-proyecto.

#![forbid(unsafe_code)]

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use chrono::Utc;

use crate::contracts::{
    WebGraphEdge, WebGraphNode, WebGraphNodeDetail, WebGraphSnapshot, WebGraphStats,
};
use crate::service::WebGraphService;
use crate::sources::EmbedFn;
use cortex_workspace::WorkspaceLayout;

#[derive(Debug, Clone)]
pub struct WorkspaceProject {
    pub project_id: String,
    pub root: PathBuf,
    pub vault_path: Option<PathBuf>,
    pub memory_path: Option<PathBuf>,
}

pub fn default_workspace_file(
    project_root: Option<&Path>,
    workspace_layout: Option<&WorkspaceLayout>,
) -> PathBuf {
    if let Some(layout) = workspace_layout {
        return layout.webgraph_workspace_path();
    }
    let root = project_root
        .map(Path::to_path_buf)
        .unwrap_or_else(|| std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")));
    root.join(".cortex").join("webgraph").join("workspace.yaml")
}

pub fn resolve_workspace_file(
    workspace_file: Option<&str>,
    project_root: Option<&Path>,
    workspace_layout: Option<&WorkspaceLayout>,
) -> Option<PathBuf> {
    if let Some(f) = workspace_file {
        return Some(cortex_workspace::layout::resolve_lexical(&PathBuf::from(
            expanduser(f),
        )));
    }
    let default_path = default_workspace_file(project_root, workspace_layout);
    if default_path.exists() {
        return Some(cortex_workspace::layout::resolve_lexical(&default_path));
    }
    None
}

fn expanduser(s: &str) -> String {
    match s.strip_prefix("~/") {
        Some(rest) => {
            if let Ok(home) = std::env::var("HOME") {
                format!("{home}/{rest}")
            } else {
                s.to_string()
            }
        }
        None => s.to_string(),
    }
}

/// write_workspace_file con yaml.safe_dump(sort_keys=False) byte-parity vía
/// emisor PyYAML de cortex-workspace.
pub fn write_workspace_file(workspace_file: &Path, projects: &[WorkspaceProject]) -> PathBuf {
    use cortex_workspace::pyyaml::{to_pyyaml_string, Node};
    let items: Vec<Node> = projects
        .iter()
        .map(|p| {
            let mut fields = vec![
                ("id".to_string(), Node::s(p.project_id.clone())),
                (
                    "root".to_string(),
                    Node::s(p.root.to_string_lossy().replace('\\', "/")),
                ),
            ];
            if let Some(v) = &p.vault_path {
                fields.push((
                    "vault".into(),
                    Node::s(v.to_string_lossy().replace('\\', "/")),
                ));
            }
            if let Some(m) = &p.memory_path {
                fields.push((
                    "memory".into(),
                    Node::s(m.to_string_lossy().replace('\\', "/")),
                ));
            }
            Node::Map(fields)
        })
        .collect();
    let doc = Node::Map(vec![("projects".into(), Node::Seq(items))]);
    if let Some(parent) = workspace_file.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    std::fs::write(workspace_file, to_pyyaml_string(&doc)).expect("workspace.yaml");
    workspace_file.to_path_buf()
}

pub fn load_workspace_projects(workspace_file: &Path) -> Vec<WorkspaceProject> {
    let Ok(text) = std::fs::read_to_string(workspace_file) else {
        return Vec::new();
    };
    let Ok(payload): Result<serde_yaml::Value, _> = serde_yaml::from_str(&text) else {
        return Vec::new();
    };
    let projects = payload.get("projects");
    let Some(serde_yaml::Value::Sequence(items)) = projects else {
        return Vec::new();
    };
    let mut loaded = Vec::new();
    for item in items {
        let serde_yaml::Value::Mapping(map) = item else {
            continue;
        };
        let get_str = |key: &str| -> String {
            map.get(serde_yaml::Value::String(key.into()))
                .map(|v| match v {
                    serde_yaml::Value::String(s) => s.clone(),
                    other => serde_yaml::to_string(other)
                        .unwrap_or_default()
                        .trim()
                        .to_string(),
                })
                .unwrap_or_default()
                .trim()
                .to_string()
        };
        let project_id = get_str("id");
        let root_raw = get_str("root");
        if project_id.is_empty() || root_raw.is_empty() {
            continue;
        }
        let root = cortex_workspace::layout::resolve_lexical(&PathBuf::from(expanduser(&root_raw)));
        let vault_raw = get_str("vault");
        let memory_raw = get_str("memory");
        loaded.push(WorkspaceProject {
            project_id,
            vault_path: resolve_optional_project_path(&root, &vault_raw),
            memory_path: resolve_optional_project_path(&root, &memory_raw),
            root,
        });
    }
    loaded
}

fn resolve_optional_project_path(project_root: &Path, value: &str) -> Option<PathBuf> {
    if value.is_empty() {
        return None;
    }
    let expanded = expanduser(value);
    let path = PathBuf::from(expanded);
    let path = if path.is_absolute() {
        path
    } else {
        project_root.join(path)
    };
    Some(cortex_workspace::layout::resolve_lexical(&path))
}

pub struct FederatedWebGraphService {
    pub workspace_file: PathBuf,
    pub projects: Vec<WorkspaceProject>,
    pub services: HashMap<String, WebGraphService>,
}

impl FederatedWebGraphService {
    pub fn new(workspace_file: &Path, embedder: Option<EmbedFn>) -> Self {
        let workspace_file = cortex_workspace::layout::resolve_lexical(workspace_file);
        let projects = load_workspace_projects(&workspace_file);
        let mut services = HashMap::new();
        for project in &projects {
            services.insert(
                project.project_id.clone(),
                WebGraphService::new(
                    &project.root,
                    None,
                    project.vault_path.clone(),
                    project.memory_path.clone(),
                    load_episodic_entries_for(&project.root, &project.memory_path),
                    embedder.clone(),
                    None,
                ),
            );
        }
        Self {
            workspace_file,
            projects,
            services,
        }
    }

    pub fn build_snapshot(
        &self,
        mode: &str,
        use_cache: bool,
        scope: Option<&str>,
    ) -> WebGraphSnapshot {
        // Orden de proyectos == orden del YAML (dict Python por project_id).
        let mut nodes: Vec<WebGraphNode> = Vec::new();
        let mut edges: Vec<WebGraphEdge> = Vec::new();
        let mut fingerprints: Vec<String> = Vec::new();

        for project in &self.projects {
            let Some(service) = self.services.get(&project.project_id) else {
                continue;
            };
            let snapshot = service.build_snapshot(mode, use_cache, scope);
            fingerprints.push(format!("{}:{}", project.project_id, snapshot.fingerprint));
            for mut node in snapshot.nodes {
                node.id = prefixed(&project.project_id, &node.id);
                node.metadata
                    .insert("project_id".into(), serde_json::json!(project.project_id));
                nodes.push(node);
            }
            for mut edge in snapshot.edges {
                edge.id = prefixed(&project.project_id, &edge.id);
                edge.source = prefixed(&project.project_id, &edge.source);
                edge.target = prefixed(&project.project_id, &edge.target);
                edges.push(edge);
            }
        }

        let mut sorted_fps = fingerprints.clone();
        sorted_fps.sort();
        use sha2::{Digest, Sha256};
        let digest = Sha256::digest(sorted_fps.join("|").as_bytes());
        let fingerprint: String = digest.iter().map(|b| format!("{b:02x}")).collect();

        let generated_at = Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Micros, true);
        WebGraphSnapshot {
            version: "2.0".into(),
            fingerprint,
            generated_at,
            mode: mode.to_string(),
            stats: WebGraphStats {
                node_count: nodes.len() as i64,
                edge_count: edges.len() as i64,
                mode: mode.to_string(),
                truncated: false,
            },
            capabilities: Default::default(),
            nodes,
            edges,
        }
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
        let neighbor_ids: std::collections::BTreeSet<String> = relations
            .iter()
            .map(|e| {
                if e.source == node_id {
                    e.target.clone()
                } else {
                    e.source.clone()
                }
            })
            .collect();
        let neighbors = neighbor_ids
            .iter()
            .filter_map(|id| nodes_by_id.get(id.as_str()).map(|n| (*n).clone()))
            .collect();
        Some(WebGraphNodeDetail {
            node: (*node).clone(),
            relations,
            neighbors,
        })
    }

    pub fn get_subgraph(
        &self,
        node_id: &str,
        depth: i64,
        mode: &str,
        edge_types: Option<&std::collections::BTreeSet<String>>,
    ) -> WebGraphSnapshot {
        let snapshot = self.build_snapshot(mode, true, None);
        if depth <= 0 {
            let mut empty = snapshot;
            empty.nodes.clear();
            empty.edges.clear();
            empty.stats.node_count = 0;
            empty.stats.edge_count = 0;
            return empty;
        }
        let mut adjacency: HashMap<String, std::collections::BTreeSet<String>> = HashMap::new();
        for edge in &snapshot.edges {
            if let Some(types) = edge_types {
                if !types.contains(&edge.edge_type) {
                    continue;
                }
            }
            adjacency
                .entry(edge.source.clone())
                .or_default()
                .insert(edge.target.clone());
            adjacency
                .entry(edge.target.clone())
                .or_default()
                .insert(edge.source.clone());
        }

        let mut frontier: std::collections::BTreeSet<String> =
            [node_id.to_string()].into_iter().collect();
        let mut visited = frontier.clone();
        for _ in 0..depth {
            let mut new_frontier = std::collections::BTreeSet::new();
            for current in &frontier {
                for neighbor in adjacency.get(current).cloned().unwrap_or_default() {
                    if !visited.contains(&neighbor) {
                        visited.insert(neighbor.clone());
                        new_frontier.insert(neighbor);
                    }
                }
            }
            frontier = new_frontier;
            if frontier.is_empty() {
                break;
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
        out.stats.node_count = nodes.len() as i64;
        out.stats.edge_count = edges.len() as i64;
        out.nodes = nodes;
        out.edges = edges;
        out
    }

    pub fn resolve_node_path(&self, node_id: &str, mode: &str) -> Option<PathBuf> {
        let (project_id, raw_id) = split_prefixed(node_id);
        self.services
            .get(&project_id)?
            .resolve_node_path(&raw_id, mode)
    }
}

fn load_episodic_entries_for(
    project_root: &Path,
    memory_path: &Option<PathBuf>,
) -> Vec<cortex_app::episodic::MemoryEntry> {
    // En federación la memoria por proyecto se resuelve como en
    // EpisodicSource Python: path declarado en workspace.yaml, o si no el
    // default por config (`resolve_episodic_persist_dir`, persist_dir
    // "memory" bajo workspace_root). Sin export ⇒ vacío.
    let dir: PathBuf = match memory_path {
        Some(p) => p.clone(),
        None => {
            let layout = WorkspaceLayout::discover(project_root);
            let cfg = crate::sources::read_project_config(&layout.config_path());
            let get = |key: &str| -> String {
                crate::sources::yaml_str(cfg.get("episodic").and_then(|m| m.get(key)), "")
            };
            let persist_cfg =
                crate::sources::boxed_or_default(&get("persist_dir"), "memory").to_string();
            let mode_cfg = get("namespace_mode");
            let value_cfg = get("namespace_value");
            let ns =
                cortex_workspace::EpisodicNamespaceCfg::new(&persist_cfg, &mode_cfg, &value_cfg);
            cortex_workspace::resolve_episodic_persist_dir(&layout.workspace_root, &ns)
        }
    };
    let jsonl = dir.join("episodic_export.jsonl");
    if !jsonl.exists() {
        return Vec::new();
    }
    cortex_app::episodic::NativeEpisodicStore::load(&jsonl)
        .map(|store| store.entries_sorted_by_id().into_iter().cloned().collect())
        .unwrap_or_default()
}

pub(crate) fn prefixed(project_id: &str, item_id: &str) -> String {
    format!("{project_id}::{item_id}")
}

pub(crate) fn split_prefixed(value: &str) -> (String, String) {
    match value.split_once("::") {
        Some((a, b)) => (a.to_string(), b.to_string()),
        None => (String::new(), value.to_string()),
    }
}
