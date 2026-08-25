//! `PipelineContext` — contexto compartido entre stages.

use std::collections::BTreeMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Default)]
pub struct PipelineContext {
    pub vault_path: PathBuf,
    pub changed_files: Vec<String>,
    pub pr_number: i64,
    pub pr_title: String,
    pub pr_author: String,
    pub source_branch: String,
    pub target_branch: String,
    pub commit_sha: String,
    pub labels: Vec<String>,
    pub config: BTreeMap<String, serde_json::Value>,
    pub stage_outputs: BTreeMap<String, BTreeMap<String, serde_json::Value>>,
}

impl PipelineContext {
    pub fn new(vault_path: impl Into<PathBuf>) -> Self {
        Self {
            vault_path: vault_path.into(),
            ..Default::default()
        }
    }

    /// `set_stage_output(stage_name, key, value)` — crea dict al vuelo.
    pub fn set_stage_output(&mut self, stage_name: &str, key: &str, value: serde_json::Value) {
        self.stage_outputs
            .entry(stage_name.to_string())
            .or_default()
            .insert(key.to_string(), value);
    }
}
