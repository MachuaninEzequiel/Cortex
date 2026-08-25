//! Puerto de `stages/security.py`: auditoría de dependencias.
use crate::domain::context::PipelineContext;
use crate::domain::types::{StageResult, StageStatus, StageType};
use crate::stages::run_command;

pub struct SecurityStage {
    pub command: Option<String>,
    pub block_on_failure: bool,
    pub timeout_s: u64,
}

impl Default for SecurityStage {
    fn default() -> Self {
        Self {
            command: None,
            block_on_failure: true,
            timeout_s: 300,
        }
    }
}

fn detect_command(ctx: &PipelineContext) -> Option<String> {
    if ctx.changed_files.iter().any(|c| c.ends_with(".py"))
        || std::path::Path::new("requirements.txt").exists()
        || std::path::Path::new("pyproject.toml").exists()
    {
        Some("pip-audit".into())
    } else if std::path::Path::new("Cargo.toml").exists() {
        Some("cargo audit".into())
    } else {
        None
    }
}

impl crate::orchestrator::PipelineStage for SecurityStage {
    fn name(&self) -> &str {
        "Security"
    }
    fn stage_type(&self) -> StageType {
        StageType::SecurityScan
    }
    fn block_on_failure(&self) -> bool {
        self.block_on_failure
    }
    fn execute(&self, ctx: &mut PipelineContext) -> StageResult {
        let started = std::time::Instant::now();
        let Some(cmd) = self.command.clone().or_else(|| detect_command(ctx)) else {
            return StageResult {
                stage_type: StageType::SecurityScan,
                stage_name: "Security".into(),
                status: StageStatus::Skipped,
                message: "No security audit command detected for this project type.".into(),
                artifacts: Default::default(),
                duration_ms: 0,
                timestamp: chrono::Utc::now(),
            };
        };
        let (code, stdout) = run_command(&cmd, self.timeout_s);
        let duration_ms = started.elapsed().as_millis() as i64;
        let vulnerabilities =
            stdout.matches("vulnerability").count() + stdout.matches("Vulnerability").count();
        StageResult {
            stage_type: StageType::SecurityScan,
            stage_name: "Security".into(),
            status: if code == 0 {
                StageStatus::Passed
            } else {
                StageStatus::Failed
            },
            message: format!("{vulnerabilities} vulnerability(ies) found."),
            artifacts: Default::default(),
            duration_ms,
            timestamp: chrono::Utc::now(),
        }
    }
}
