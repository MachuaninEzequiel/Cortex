//! Puerto de `cortex.autopilot.config`: `autopilot.yaml` opcional con
//! defaults seguros.

use serde::{Deserialize, Serialize};

use cortex_workspace::WorkspaceLayout;

#[derive(Debug, Clone)]
pub struct ConfigError(pub String);

impl std::fmt::Display for ConfigError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}
impl std::error::Error for ConfigError {}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct AutopilotConfig {
    pub mode: String,
    pub default_budget_profile: String,
    pub auto_checkpoint_files: i64,
    pub auto_checkpoint_minutes: i64,
    pub max_event_jsonl_mb: i64,
    pub event_rotation_days: i64,
    pub enable_hooks: bool,
    pub ide_adapter: Option<String>,
}

impl Default for AutopilotConfig {
    fn default() -> Self {
        Self {
            mode: "assist".into(),
            default_budget_profile: "fast_code".into(),
            auto_checkpoint_files: 5,
            auto_checkpoint_minutes: 10,
            max_event_jsonl_mb: 5,
            event_rotation_days: 30,
            enable_hooks: false,
            ide_adapter: None,
        }
    }
}

/// `load_autopilot_config`: `{workspace_root}/autopilot.yaml` si existe;
/// error exacto "Failed to parse autopilot config: …" ante YAML roto.
pub fn load_autopilot_config(layout: &WorkspaceLayout) -> Result<AutopilotConfig, ConfigError> {
    let path = layout.workspace_root.join("autopilot.yaml");
    if !path.exists() {
        return Ok(AutopilotConfig::default());
    }
    let raw = std::fs::read_to_string(&path)
        .map_err(|e| ConfigError(format!("Failed to parse autopilot config: {e}")))?;
    let parsed: serde_yaml::Value = serde_yaml::from_str(&raw)
        .map_err(|e| ConfigError(format!("Failed to parse autopilot config: {e}")))?;
    // Python: `raw = safe_load() or {}`; no-dict ⇒ {} (defaults). Solo el
    // YAMLError genera ConfigError.
    match &parsed {
        serde_yaml::Value::Mapping(_) => serde_yaml::from_str::<AutopilotConfig>(&raw)
            .map_err(|e| ConfigError(format!("Failed to parse autopilot config: {e}"))),
        _ => Ok(AutopilotConfig::default()),
    }
}
