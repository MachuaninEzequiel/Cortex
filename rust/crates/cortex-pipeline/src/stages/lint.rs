//! Puerto de `stages/lint.py`.
use crate::domain::context::PipelineContext;
use crate::domain::types::{StageResult, StageStatus, StageType};
use crate::stages::run_command;

pub struct LintStage {
    pub command: Option<String>,
    pub block_on_failure: bool,
    pub timeout_s: u64,
}

impl Default for LintStage {
    fn default() -> Self {
        Self {
            command: None,
            block_on_failure: true,
            timeout_s: 120,
        }
    }
}

fn detect_command(ctx: &PipelineContext) -> Option<String> {
    let files = |ext: &str| ctx.changed_files.iter().any(|c| c.ends_with(ext));
    if files(".py") {
        Some("ruff check .".into())
    } else if files(".rs") {
        Some("cargo clippy -- -D warnings".into())
    } else {
        None
    }
}

impl crate::orchestrator::PipelineStage for LintStage {
    fn name(&self) -> &str {
        "Lint"
    }
    fn stage_type(&self) -> StageType {
        StageType::Lint
    }
    fn block_on_failure(&self) -> bool {
        self.block_on_failure
    }
    fn execute(&self, ctx: &mut PipelineContext) -> StageResult {
        let started = std::time::Instant::now();
        let Some(cmd) = self.command.clone().or_else(|| detect_command(ctx)) else {
            return StageResult {
                stage_type: StageType::Lint,
                stage_name: "Lint".into(),
                status: StageStatus::Skipped,
                message: "No lint command detected for this project type.".into(),
                artifacts: Default::default(),
                duration_ms: 0,
                timestamp: chrono::Utc::now(),
            };
        };
        let (code, stdout) = run_command(&cmd, self.timeout_s);
        let duration_ms = started.elapsed().as_millis() as i64;
        if code == 0 {
            return StageResult {
                stage_type: StageType::Lint,
                stage_name: "Lint".into(),
                status: StageStatus::Passed,
                message: "No lint errors found.".into(),
                artifacts: Default::default(),
                duration_ms,
                timestamp: chrono::Utc::now(),
            };
        }
        let error_lines = stdout
            .lines()
            .filter(|ln| ln.to_lowercase().contains("error") || ln.contains("E "))
            .count();
        let count = if error_lines > 0 {
            error_lines
        } else {
            stdout.matches('\n').count()
        };
        StageResult {
            stage_type: StageType::Lint,
            stage_name: "Lint".into(),
            status: StageStatus::Failed,
            message: format!("{count} lint issue(s) found."),
            artifacts: Default::default(),
            duration_ms,
            timestamp: chrono::Utc::now(),
        }
    }
}
