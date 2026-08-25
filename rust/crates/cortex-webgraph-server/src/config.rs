//! Porteo de `cortex/webgraph/config.py` — WebGraphConfig.

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use cortex_workspace::WorkspaceLayout;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebGraphConfig {
    #[serde(default = "def_host")]
    pub server_host: String,
    #[serde(default = "def_port")]
    pub server_port: i64,
    #[serde(default = "yes")]
    pub auto_open_browser: bool,
    #[serde(default = "def_mode")]
    pub default_mode: String,
    #[serde(default = "def_threshold")]
    pub semantic_neighbor_threshold: f64,
    #[serde(default = "def_max_edges")]
    pub semantic_neighbor_max_edges_per_node: i64,
    #[serde(default = "def_max_nodes")]
    pub semantic_neighbor_max_nodes: i64,
    #[serde(default = "yes")]
    pub enable_semantic_neighbors: bool,
    #[serde(default = "def_depth")]
    pub max_subgraph_depth: i64,
    #[serde(default = "def_ignored_tags")]
    pub ignored_tags: Vec<String>,
}

fn def_host() -> String {
    "127.0.0.1".into()
}
fn def_port() -> i64 {
    8765
}
fn yes() -> bool {
    true
}
fn def_mode() -> String {
    "hybrid".into()
}
fn def_threshold() -> f64 {
    0.82
}
fn def_max_edges() -> i64 {
    2
}
fn def_max_nodes() -> i64 {
    220
}
fn def_depth() -> i64 {
    2
}
fn def_ignored_tags() -> Vec<String> {
    vec!["general".into()]
}

impl Default for WebGraphConfig {
    fn default() -> Self {
        Self {
            server_host: def_host(),
            server_port: def_port(),
            auto_open_browser: true,
            default_mode: def_mode(),
            semantic_neighbor_threshold: def_threshold(),
            semantic_neighbor_max_edges_per_node: def_max_edges(),
            semantic_neighbor_max_nodes: def_max_nodes(),
            enable_semantic_neighbors: true,
            max_subgraph_depth: def_depth(),
            ignored_tags: def_ignored_tags(),
        }
    }
}

impl WebGraphConfig {
    /// default_path: usa layout si hay; si no, legacy bajo project_root.
    pub fn default_path(
        project_root: Option<&Path>,
        workspace_layout: Option<&WorkspaceLayout>,
    ) -> PathBuf {
        if let Some(layout) = workspace_layout {
            return layout.webgraph_config_path();
        }
        let root = project_root
            .map(Path::to_path_buf)
            .unwrap_or_else(|| std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")));
        root.join(".cortex").join("webgraph").join("config.yaml")
    }

    /// load: YAML del path o defaults. Claves desconocidas se IGNORAN.
    pub fn load(
        project_root: Option<&Path>,
        workspace_layout: Option<&WorkspaceLayout>,
    ) -> WebGraphConfig {
        let path = Self::default_path(project_root, workspace_layout);
        if !path.exists() {
            return Self::default();
        }
        let Ok(text) = std::fs::read_to_string(&path) else {
            return Self::default();
        };
        let data: serde_yaml::Value =
            serde_yaml::from_str(&text).unwrap_or(serde_yaml::Value::Null);
        let data = match data {
            serde_yaml::Value::Mapping(_) => data,
            _ => serde_yaml::Value::Mapping(Default::default()),
        };
        serde_yaml::from_value(data).unwrap_or_default()
    }

    /// Payload canónico para fingerprint (model_dump de pydantic).
    pub fn model_dump(&self) -> serde_json::Value {
        serde_json::json!({
            "server_host": self.server_host,
            "server_port": self.server_port,
            "auto_open_browser": self.auto_open_browser,
            "default_mode": self.default_mode,
            "semantic_neighbor_threshold": self.semantic_neighbor_threshold,
            "semantic_neighbor_max_edges_per_node": self.semantic_neighbor_max_edges_per_node,
            "semantic_neighbor_max_nodes": self.semantic_neighbor_max_nodes,
            "enable_semantic_neighbors": self.enable_semantic_neighbors,
            "max_subgraph_depth": self.max_subgraph_depth,
            "ignored_tags": self.ignored_tags,
        })
    }
}
