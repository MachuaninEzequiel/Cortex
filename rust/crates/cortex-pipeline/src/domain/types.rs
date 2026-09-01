//! Puertos de `cortex.pipeline.domain.types` y `context`.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StageType {
    SecurityScan,
    Lint,
    Test,
    Documentation,
    Build,
    Deploy,
}

impl StageType {
    /// `StageType.name` de Python (nombre del miembro del enum).
    pub fn py_name(self) -> &'static str {
        match self {
            Self::SecurityScan => "SECURITY_SCAN",
            Self::Lint => "LINT",
            Self::Test => "TEST",
            Self::Documentation => "DOCUMENTATION",
            Self::Build => "BUILD",
            Self::Deploy => "DEPLOY",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StageStatus {
    Passed,
    Failed,
    Skipped,
    Error,
}

impl StageStatus {
    pub fn value(self) -> &'static str {
        match self {
            Self::Passed => "passed",
            Self::Failed => "failed",
            Self::Skipped => "skipped",
            Self::Error => "error",
        }
    }
    pub fn icon(self) -> &'static str {
        match self {
            Self::Passed => "✅",
            Self::Failed => "❌",
            Self::Skipped => "⏭️",
            Self::Error => "💥",
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct StageResult {
    pub stage_type: StageType,
    pub stage_name: String,
    pub status: StageStatus,
    pub message: String,
    pub artifacts: BTreeMap<String, serde_json::Value>,
    pub duration_ms: i64,
    pub timestamp: DateTime<Utc>,
}

impl StageResult {
    pub fn passed(&self) -> bool {
        self.status == StageStatus::Passed
    }
    pub fn failed(&self) -> bool {
        matches!(self.status, StageStatus::Failed | StageStatus::Error)
    }

    /// `to_dict` en orden Python.
    pub fn to_dict(&self) -> BTreeMap<String, serde_json::Value> {
        let mut out = BTreeMap::new();
        // Orden de inserción Python se pierde en BTreeMap; el gate usa el
        // writer ordenado del checker. Aquí solo completitud importa.
        out.insert(
            "stage_type".into(),
            serde_json::json!(self.stage_type.py_name()),
        );
        out.insert("stage_name".into(), serde_json::json!(self.stage_name));
        out.insert("status".into(), serde_json::json!(self.status.value()));
        out.insert("message".into(), serde_json::json!(self.message));
        out.insert(
            "artifacts".into(),
            serde_json::to_value(&self.artifacts).unwrap_or_default(),
        );
        out.insert("duration_ms".into(), serde_json::json!(self.duration_ms));
        out.insert(
            "timestamp".into(),
            serde_json::json!(self
                .timestamp
                .to_rfc3339_opts(chrono::SecondsFormat::Secs, true)),
        );
        out
    }
}

#[derive(Debug, Clone)]
pub struct PipelineReport {
    pub results: Vec<StageResult>,
    pub started_at: DateTime<Utc>,
    pub ended_at: DateTime<Utc>,
}

impl PipelineReport {
    pub fn passed(&self) -> bool {
        self.results
            .iter()
            .all(|r| r.passed() || r.status == StageStatus::Skipped)
    }
    pub fn total_duration_ms(&self) -> i64 {
        self.results.iter().map(|r| r.duration_ms).sum()
    }
    /// `summary()` — un línea para logs.
    pub fn summary(&self) -> String {
        let overall = if self.passed() { "PASSED" } else { "FAILED" };
        let icons: Vec<String> = self
            .results
            .iter()
            .map(|r| format!("[{} {}]", r.status.icon(), r.stage_name))
            .collect();
        format!(
            "Pipeline {overall} in {:.1}s — {}",
            self.total_duration_ms() as f64 / 1000.0,
            icons.join(" ")
        )
    }
    /// `to_markdown()` — tabla para PR comments.
    pub fn to_markdown(&self) -> String {
        let mut lines = vec![
            "## 🧠 Cortex Pipeline Report".to_string(),
            String::new(),
            "| Stage | Status | Duration | Message |".to_string(),
            "|-------|--------|----------|---------|".to_string(),
        ];
        for r in &self.results {
            lines.push(format!(
                "| {} {} | {} | {:.1}s | {} |",
                r.status.icon(),
                r.stage_name,
                r.status.value(),
                r.duration_ms as f64 / 1000.0,
                if r.message.is_empty() {
                    "-"
                } else {
                    &r.message
                }
            ));
        }
        lines.push(String::new());
        let overall = if self.passed() {
            "✅ All gates passed"
        } else {
            "❌ Pipeline failed"
        };
        lines.push(format!(
            "**{overall}** — Total: {:.1}s",
            self.total_duration_ms() as f64 / 1000.0
        ));
        lines.join("\n")
    }
}

// Serialize simple para artefactos.
impl Serialize for StageStatus {
    fn serialize<S: serde::Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.serialize_str(self.value())
    }
}
impl<'de> Deserialize<'de> for StageStatus {
    fn deserialize<D: serde::Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        let s = String::deserialize(d)?;
        Ok(match s.as_str() {
            "passed" => Self::Passed,
            "failed" => Self::Failed,
            "skipped" => Self::Skipped,
            _ => Self::Error,
        })
    }
}
