//! Porteo de `cortex/handoff.py` — schema estructurado de handoff entre
//! agentes (contrato YAML legacy, deprecado a favor de SessionRecord pero
//! vigente para IDEs sin checkpoints).
//!
//! Paridad: `to_yaml` produce EXACTAMENTE los bytes de
//! `yaml.safe_dump(model_dump(mode="json"), sort_keys=False,
//! allow_unicode=True)` (ver `pyyaml` para el porqué del emisor propio).
//! `from_yaml` valida como pydantic: raíz mapping obligatoria, Literals
//! estrictos en agent/status/action, defaults idénticos; los campos
//! desconocidos se IGNORAN (pydantic default).

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};

use crate::pyyaml::{to_pyyaml_string, Node};

/// Agente productor canónico (Literal de pydantic).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AgentName {
    #[serde(rename = "cortex-sync")]
    CortexSync,
    #[serde(rename = "cortex-SDDwork")]
    CortexSddwork,
    #[serde(rename = "cortex-code-explorer")]
    CortexCodeExplorer,
    #[serde(rename = "cortex-code-implementer")]
    CortexCodeImplementer,
    #[serde(rename = "cortex-documenter")]
    CortexDocumenter,
    #[serde(rename = "cortex-security-auditor")]
    CortexSecurityAuditor,
    #[serde(rename = "cortex-test-verifier")]
    CortexTestVerifier,
}

impl AgentName {
    pub fn as_str(&self) -> &'static str {
        match self {
            AgentName::CortexSync => "cortex-sync",
            AgentName::CortexSddwork => "cortex-SDDwork",
            AgentName::CortexCodeExplorer => "cortex-code-explorer",
            AgentName::CortexCodeImplementer => "cortex-code-implementer",
            AgentName::CortexDocumenter => "cortex-documenter",
            AgentName::CortexSecurityAuditor => "cortex-security-auditor",
            AgentName::CortexTestVerifier => "cortex-test-verifier",
        }
    }
}

/// Estado de completitud (Literal de pydantic).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum HandoffStatus {
    #[serde(rename = "complete")]
    Complete,
    #[serde(rename = "partial")]
    Partial,
    #[serde(rename = "blocked")]
    Blocked,
}

impl HandoffStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            HandoffStatus::Complete => "complete",
            HandoffStatus::Partial => "partial",
            HandoffStatus::Blocked => "blocked",
        }
    }
}

/// Acción sobre un artefacto producido (Literal de pydantic).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ArtifactAction {
    #[serde(rename = "created")]
    Created,
    #[serde(rename = "modified")]
    Modified,
    #[serde(rename = "deleted")]
    Deleted,
    #[serde(rename = "renamed")]
    Renamed,
}

impl ArtifactAction {
    pub fn as_str(&self) -> &'static str {
        match self {
            ArtifactAction::Created => "created",
            ArtifactAction::Modified => "modified",
            ArtifactAction::Deleted => "deleted",
            ArtifactAction::Renamed => "renamed",
        }
    }
}

/// Archivo producido/tocado por un agente durante su corrida.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ArtifactProduced {
    pub path: String,
    pub action: ArtifactAction,
    #[serde(default)]
    pub lines_changed: i64,
    #[serde(default)]
    pub lines_added: i64,
}

/// Handoff estructurado que emite todo subagente al completar.
///
/// Anclas estrictas (`agent` y `status`); el resto con defaults pydantic.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AgentHandoff {
    pub agent: AgentName,
    pub status: HandoffStatus,
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

impl AgentHandoff {
    /// Serializa a YAML byte-parity con `yaml.safe_dump(sort_keys=False,
    /// allow_unicode=True)` sobre `model_dump(mode="json")`.
    pub fn to_yaml(&self) -> String {
        let node = Node::Map(vec![
            ("agent".into(), Node::s(self.agent.as_str())),
            ("status".into(), Node::s(self.status.as_str())),
            (
                "verified_claims".into(),
                Node::Seq(self.verified_claims.iter().map(Node::s).collect()),
            ),
            (
                "unverified_claims".into(),
                Node::Seq(self.unverified_claims.iter().map(Node::s).collect()),
            ),
            (
                "artifacts_produced".into(),
                Node::Seq(
                    self.artifacts_produced
                        .iter()
                        .map(|a| {
                            Node::Map(vec![
                                ("path".into(), Node::s(a.path.clone())),
                                ("action".into(), Node::s(a.action.as_str())),
                                ("lines_changed".into(), Node::Int(a.lines_changed)),
                                ("lines_added".into(), Node::Int(a.lines_added)),
                            ])
                        })
                        .collect(),
                ),
            ),
            (
                "context_for_next".into(),
                Node::Seq(self.context_for_next.iter().map(Node::s).collect()),
            ),
            ("suggested_adr".into(), Node::Bool(self.suggested_adr)),
            (
                "suggested_adr_reason".into(),
                Node::s(self.suggested_adr_reason.clone()),
            ),
            (
                "suggested_context_terms".into(),
                Node::Seq(self.suggested_context_terms.iter().map(Node::s).collect()),
            ),
        ]);
        to_pyyaml_string(&node)
    }

    /// Parsea y valida un YAML de handoff.
    ///
    /// Errores equivalentes al contrato Python:
    /// - raíz no-mapping ⇒ `"Handoff YAML must be a mapping at the root"`.
    /// - violación de schema (Literals/required) ⇒ mensaje descriptivo.
    pub fn from_yaml(text: &str) -> Result<AgentHandoff, String> {
        let data: serde_yaml::Value =
            serde_yaml::from_str(text).map_err(|e| format!("YAML inválido: {e}"))?;
        if !data.is_mapping() {
            return Err("Handoff YAML must be a mapping at the root".into());
        }
        serde_yaml::from_value(data).map_err(|e| format!("Handoff inválido: {e}"))
    }
}
