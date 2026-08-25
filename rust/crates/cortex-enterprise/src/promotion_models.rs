//! Puerto de `cortex.enterprise.promotion_models`: records append-only del
//! ciclo de promoción. El orden de campos serde = orden de declaración
//! Pydantic ⇒ `model_dump_json` byte-parity (compacto, unicode crudo).

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::clock::{default_now_string, Clock};
use crate::error::EnterpriseError;

macro_rules! string_status {
    ($name:ident { $($variant:ident => $value:literal),+ $(,)? }) => {
        #[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
        pub enum $name { $(#[serde(rename = $value)] $variant),+ }
        impl $name {
            pub fn as_str(self) -> &'static str { match self { $(Self::$variant => $value),+ } }
        }
        impl PartialEq<&str> for $name {
            fn eq(&self, other: &&str) -> bool { self.as_str() == *other }
        }
        impl std::fmt::Display for $name {
            fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                f.write_str(self.as_str())
            }
        }
    };
}

string_status!(PromotionStatus {
    Draft => "draft",
    Candidate => "candidate",
    Reviewed => "reviewed",
    Promoted => "promoted",
    Rejected => "rejected"
});
string_status!(PromotionDecisionType {
    Approve => "approve",
    Reject => "reject"
});
string_status!(PromotionEventKind {
    Candidate => "candidate",
    ReviewedEvent => "reviewed",
    Promoted => "promoted",
    RejectedEvent => "rejected"
});

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PromotionIssue {
    pub file: String,
    pub field: String,
    pub message: String,
    #[serde(default = "default_warning")]
    pub severity: String,
}
fn default_warning() -> String {
    "warning".to_string()
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PromotionCandidate {
    pub origin_id: String,
    pub doc_type: String,
    pub local_rel_path: String,
    pub local_abs_path: String,
    pub dest_rel_path: String,
    pub fingerprint: String,
    #[serde(default = "default_candidate")]
    pub status: String,
    #[serde(default)]
    pub issues: Vec<PromotionIssue>,
    #[serde(default)]
    pub metadata: BTreeMap<String, serde_json::Value>,
}
fn default_candidate() -> String {
    "candidate".to_string()
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PromotionDecision {
    pub decision: PromotionDecisionType,
    pub actor: String,
    #[serde(default = "default_now_string")]
    pub decided_at: String,
    #[serde(default)]
    pub reason: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PromotionRecordEvent {
    pub event: PromotionEventKind,
    #[serde(default = "default_now_string")]
    pub at: String,
    #[serde(default)]
    pub actor: Option<String>,
    #[serde(default)]
    pub payload: BTreeMap<String, serde_json::Value>,
}

/// Record append-only del ciclo de vida de un documento promotable.
/// `origin_id` es la clave de idempotencia (proyecto + ruta local);
/// `fingerprint` es el fingerprint normalizado del markdown fuente.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PromotionRecord {
    pub origin_id: String,
    pub local_rel_path: String,
    pub doc_type: String,
    pub dest_rel_path: String,
    pub fingerprint: String,
    pub status: PromotionStatus,
    #[serde(default = "default_now_string")]
    pub created_at: String,
    #[serde(default = "default_now_string")]
    pub updated_at: String,
    #[serde(default)]
    pub decision: Option<PromotionDecision>,
    #[serde(default)]
    pub events: Vec<PromotionRecordEvent>,
}

impl PromotionRecord {
    /// `touch()`: actualiza `updated_at` al instante del reloj.
    pub fn touch(&mut self, clock: &dyn Clock) {
        self.updated_at = crate::clock::isoformat_seconds(clock.now());
    }

    /// Serialización `model_dump_json()` (compacta).
    pub fn to_json_line(&self) -> Result<String, EnterpriseError> {
        serde_json::to_string(self).map_err(|e| EnterpriseError::Validation(e.to_string()))
    }
}
