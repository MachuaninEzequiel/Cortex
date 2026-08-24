//! Puerto mínimo de `cortex/handoff.py` — AgentHandoff sintético del
//! reconstructor (los campos que produce `_build_handoff`).

#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub struct ArtifactProduced {
    pub path: String,
    /// created | modified | deleted | renamed
    pub action: String,
    pub lines_changed: u64,
    pub lines_added: u64,
}

#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub struct AgentHandoff {
    pub agent: String,
    /// complete | partial | blocked
    pub status: String,
    pub verified_claims: Vec<String>,
    pub unverified_claims: Vec<String>,
    pub artifacts_produced: Vec<ArtifactProduced>,
    pub context_for_next: Vec<String>,
    pub suggested_adr: bool,
    pub suggested_adr_reason: String,
    pub suggested_context_terms: Vec<String>,
}
