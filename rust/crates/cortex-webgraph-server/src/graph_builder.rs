//! Porteo de `cortex/webgraph/graph_builder.py`.

#![forbid(unsafe_code)]

use std::collections::HashMap;

use crate::config::WebGraphConfig;
use crate::contracts::{
    EpisodicRecord, SemanticRecord, WebGraphEdge, WebGraphNode, WebGraphSnapshot, WebGraphStats,
};
use crate::relation_builder::RelationBuilder;

pub struct GraphBuilder {
    pub config: WebGraphConfig,
}

impl GraphBuilder {
    pub fn new(config: WebGraphConfig) -> Self {
        Self { config }
    }

    pub fn build_snapshot(
        &self,
        fingerprint: &str,
        mode: &str,
        generated_at: &str,
        mut semantic_records: Vec<SemanticRecord>,
        mut episodic_records: Vec<EpisodicRecord>,
    ) -> WebGraphSnapshot {
        if mode == "semantic" {
            episodic_records.clear();
        } else if mode == "episodic" {
            semantic_records.clear();
        }
        let relation = RelationBuilder::new(self.config.clone());
        let edges = relation.build_edges(&semantic_records, &episodic_records);
        let nodes = Self::build_nodes(&semantic_records, &episodic_records, &edges);
        let visible: std::collections::HashSet<&str> =
            nodes.iter().map(|n| n.id.as_str()).collect();
        let filtered_edges: Vec<WebGraphEdge> = edges
            .into_iter()
            .filter(|e| visible.contains(e.source.as_str()) && visible.contains(e.target.as_str()))
            .collect();
        let stats = WebGraphStats {
            node_count: nodes.len() as i64,
            edge_count: filtered_edges.len() as i64,
            mode: mode.to_string(),
            truncated: false,
        };
        WebGraphSnapshot {
            version: "2.0".into(),
            fingerprint: fingerprint.to_string(),
            generated_at: generated_at.to_string(),
            mode: mode.to_string(),
            stats,
            capabilities: Default::default(),
            nodes,
            edges: filtered_edges,
        }
    }

    fn build_nodes(
        semantic_records: &[SemanticRecord],
        episodic_records: &[EpisodicRecord],
        edges: &[WebGraphEdge],
    ) -> Vec<WebGraphNode> {
        let mut degree_counter: HashMap<&str, i64> = HashMap::new();
        for edge in edges {
            *degree_counter.entry(edge.source.as_str()).or_insert(0) += 1;
            *degree_counter.entry(edge.target.as_str()).or_insert(0) += 1;
        }

        let mut nodes: Vec<WebGraphNode> = Vec::new();
        for s in semantic_records {
            // metadata + abs_path encima (campo legacy).
            let mut node_meta = s.metadata.clone();
            node_meta.insert("abs_path".into(), serde_json::json!(s.abs_path));
            nodes.push(WebGraphNode {
                id: s.node_id.clone(),
                node_type: s.node_type.clone(),
                source: "semantic".into(),
                label: s.title.clone(),
                summary: s.summary.clone(),
                rel_path: Some(s.rel_path.clone()),
                memory_id: None,
                tags: s.tags.clone(),
                files: vec![],
                timestamp: None,
                degree: degree_counter.get(s.node_id.as_str()).copied().unwrap_or(0),
                metadata: node_meta,
            });
        }
        for e in episodic_records {
            nodes.push(WebGraphNode {
                id: e.node_id.clone(),
                node_type: e.node_type.clone(),
                source: "episodic".into(),
                label: e.label.clone(),
                summary: e.summary.clone(),
                rel_path: None,
                memory_id: Some(e.memory_id.clone()),
                tags: e.tags.clone(),
                files: e.files.clone(),
                timestamp: e.timestamp.clone(),
                degree: degree_counter.get(e.node_id.as_str()).copied().unwrap_or(0),
                metadata: e.metadata.clone(),
            });
        }
        nodes.sort_by(|a, b| {
            (
                a.source.as_str(),
                a.node_type.as_str(),
                a.label.to_lowercase(),
            )
                .cmp(&(
                    b.source.as_str(),
                    b.node_type.as_str(),
                    b.label.to_lowercase(),
                ))
        });
        nodes
    }
}
