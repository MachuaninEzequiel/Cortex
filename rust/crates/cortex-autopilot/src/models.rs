//! Puerto de `cortex.autopilot.models`: vocabulario de la capa de decisión.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct DetectionRequest {
    pub user_request: Option<String>,
    #[serde(default)]
    pub changed_files: Vec<String>,
    pub git_diff_stat: Option<String>,
    /// Bolsa libre de metadata (sin tipar, como Python Any | None).
    pub session_state: Option<serde_json::Value>,
}

pub const TASK_TYPES: &[&str] = &[
    "question-only",
    "docs-only",
    "fast-code",
    "deep-code",
    "security",
    "ambiguous",
    "noop",
];

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DetectionResult {
    pub task_type: String,
    #[serde(default)]
    pub confidence: f64,
    #[serde(default)]
    pub reason: String,
    #[serde(default = "default_complexity")]
    pub suggested_complexity: String,
}

fn default_complexity() -> String {
    "none".to_string()
}

impl DetectionResult {
    pub fn noop(reason: impl Into<String>) -> Self {
        Self {
            task_type: "noop".into(),
            confidence: 0.0,
            reason: reason.into(),
            suggested_complexity: "none".into(),
        }
    }
}
