//! Modelos del WebGraph — porteo de `cortex/webgraph/contracts.py`.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use serde_json::Value;

pub type WebGraphMode = String; // "semantic" | "episodic" | "hybrid"

/// Literales válidos de `WebGraphMode` (get_args en Python).
pub const WEBGRAPH_MODES: &[&str] = &["semantic", "episodic", "hybrid"];

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebGraphCapabilities {
    #[serde(default = "yes")]
    pub filters: bool,
    #[serde(default = "yes")]
    pub subgraph: bool,
    #[serde(default = "yes")]
    pub open_file: bool,
    #[serde(default = "yes")]
    pub relation_explanations: bool,
}

fn yes() -> bool {
    true
}

impl Default for WebGraphCapabilities {
    fn default() -> Self {
        Self {
            filters: true,
            subgraph: true,
            open_file: true,
            relation_explanations: true,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebGraphStats {
    #[serde(default)]
    pub node_count: i64,
    #[serde(default)]
    pub edge_count: i64,
    #[serde(default = "default_mode")]
    pub mode: String,
    #[serde(default)]
    pub truncated: bool,
}

fn default_mode() -> String {
    "hybrid".into()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebGraphNode {
    pub id: String,
    pub node_type: String,
    /// "semantic" | "episodic"
    pub source: String,
    pub label: String,
    #[serde(default)]
    pub summary: String,
    #[serde(default)]
    pub rel_path: Option<String>,
    #[serde(default)]
    pub memory_id: Option<String>,
    #[serde(default)]
    pub tags: Vec<String>,
    #[serde(default)]
    pub files: Vec<String>,
    #[serde(default)]
    pub timestamp: Option<String>,
    #[serde(default)]
    pub degree: i64,
    #[serde(default)]
    pub metadata: serde_json::Map<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebGraphEdge {
    pub id: String,
    pub source: String,
    pub target: String,
    pub edge_type: String,
    #[serde(default = "one")]
    pub weight: f64,
    #[serde(default)]
    pub evidence: Vec<String>,
}

fn one() -> f64 {
    1.0
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebGraphSnapshot {
    #[serde(default = "version")]
    pub version: String,
    pub fingerprint: String,
    /// ISO-8601 UTC con microsegundos (normalizado {{TS}} en el gate).
    #[serde(default)]
    pub generated_at: String,
    #[serde(default = "default_mode")]
    pub mode: String,
    pub stats: WebGraphStats,
    #[serde(default)]
    pub capabilities: WebGraphCapabilities,
    #[serde(default)]
    pub nodes: Vec<WebGraphNode>,
    #[serde(default)]
    pub edges: Vec<WebGraphEdge>,
}

fn version() -> String {
    "2.0".into()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebGraphNodeDetail {
    pub node: WebGraphNode,
    #[serde(default)]
    pub relations: Vec<WebGraphEdge>,
    #[serde(default)]
    pub neighbors: Vec<WebGraphNode>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SemanticRecord {
    pub node_id: String,
    pub node_type: String,
    pub title: String,
    pub summary: String,
    pub rel_path: String,
    pub abs_path: String,
    #[serde(default)]
    pub tags: Vec<String>,
    #[serde(default)]
    pub links: Vec<String>,
    #[serde(default)]
    pub content: String,
    #[serde(default)]
    pub embedding: Option<Vec<f64>>,
    #[serde(default)]
    pub metadata: serde_json::Map<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EpisodicRecord {
    pub node_id: String,
    pub node_type: String,
    pub label: String,
    pub summary: String,
    pub memory_id: String,
    #[serde(default)]
    pub tags: Vec<String>,
    #[serde(default)]
    pub files: Vec<String>,
    #[serde(default)]
    pub timestamp: Option<String>,
    #[serde(default)]
    pub content: String,
    #[serde(default)]
    pub metadata: serde_json::Map<String, Value>,
    #[serde(default)]
    pub embedding: Option<Vec<f64>>,
}
