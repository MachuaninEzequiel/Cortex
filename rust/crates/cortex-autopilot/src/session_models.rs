//! Subconjunto mínimo y fiel de `cortex.session.models` consumido por la
//! capa de decisión (SessionStatus/CheckpointSource/Checkpoint/Record).
//! Campos no usados por policies/lifecycle quedan fuera por diseño; el
//! motor completo de sesiones es territorio futuro.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

macro_rules! str_enum {
    ($name:ident { $($v:ident => $s:literal),+ $(,)? }) => {
        #[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
        pub enum $name { $(#[serde(rename = $s)] $v),+ }
        impl $name {
            pub fn as_str(self) -> &'static str { match self { $(Self::$v => $s),+ } }
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

str_enum!(SessionStatus {
    Open => "open",
    Closed => "closed",
    Handoff => "handoff",
    Abandoned => "abandoned"
});

str_enum!(CheckpointSource {
    CortexSync => "cortex-sync",
    CortexSddwork => "cortex-SDDwork",
    CortexCodeExplorer => "cortex-code-explorer",
    CortexCodeImplementer => "cortex-code-implementer",
    CortexCodeDesigner => "cortex-code-designer",
    UserSkill => "user-skill",
    IdeHook => "ide-hook",
    Manual => "manual",
    CiBot => "ci-bot"
});

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Checkpoint {
    pub timestamp: DateTime<Utc>,
    pub source: CheckpointSource,
    #[serde(default)]
    pub verified_claims: Vec<String>,
    #[serde(default)]
    pub unverified_claims: Vec<String>,
    #[serde(default)]
    pub artifacts_touched: Vec<String>,
    #[serde(default)]
    pub note: String,
}

/// Subconjunto de `SessionRecord` usado por la capa de decisión.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SessionRecord {
    pub session_id: String,
    #[serde(default)]
    pub spec_path: String,
    #[serde(default)]
    pub spec_summary: String,
    #[serde(default)]
    pub start_commit: String,
    #[serde(default)]
    pub start_branch: String,
    pub opened_at: DateTime<Utc>,
    #[serde(default = "default_status")]
    pub status: SessionStatus,
    #[serde(default)]
    pub checkpoints: Vec<Checkpoint>,
    #[serde(default)]
    pub closed_at: Option<DateTime<Utc>>,
    #[serde(default)]
    pub end_commit: Option<String>,
}

fn default_status() -> SessionStatus {
    SessionStatus::Open
}

impl SessionRecord {
    /// Fixture/constructor mínimo para la capa de decisión.
    pub fn minimal(session_id: &str) -> Self {
        Self {
            session_id: session_id.to_string(),
            spec_path: String::new(),
            spec_summary: String::new(),
            start_commit: String::new(),
            start_branch: String::new(),
            opened_at: Utc::now(),
            status: SessionStatus::Open,
            checkpoints: vec![],
            closed_at: None,
            end_commit: None,
        }
    }

    /// Invariante lifecycle: OPEN sin campos de cierre; terminal con ellos
    /// (defensa ante edición manual, como el doctor Python).
    pub fn lifecycle_violation(&self) -> Option<&'static str> {
        let has_close = self.closed_at.is_some() || self.end_commit.is_some();
        match self.status {
            SessionStatus::Open if has_close => Some("OPEN with close-time fields set"),
            s if s != SessionStatus::Open && !has_close => {
                Some("terminal but missing close-time fields")
            }
            _ => None,
        }
    }
}
