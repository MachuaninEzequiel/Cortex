//! Puerto mínimo de `cortex/handoff.py` — AgentHandoff sintético del
//! reconstructor (los campos que produce `_build_handoff`).

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct ArtifactProduced {
    pub path: String,
    /// created | modified | deleted | renamed
    pub action: String,
    #[serde(default)]
    pub lines_changed: u64,
    #[serde(default)]
    pub lines_added: u64,
}

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct AgentHandoff {
    pub agent: String,
    /// complete | partial | blocked
    #[serde(default = "default_partial")]
    pub status: String,
    #[serde(default)]
    pub verified_claims: Vec<String>,
    #[serde(default)]
    pub unverified_claims: Vec<String>,
    #[serde(default)]
    pub artifacts_produced: Vec<ArtifactProduced>,
    #[serde(default)]
    pub context_for_next: Vec<String>,
    #[serde(default)]
    pub suggested_adr: bool,
    #[serde(default)]
    pub suggested_adr_reason: String,
    #[serde(default)]
    pub suggested_context_terms: Vec<String>,
}

fn default_partial() -> String {
    "partial".into()
}
