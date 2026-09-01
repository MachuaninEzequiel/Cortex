//! `PipelineOrchestrator` — ejecuta stages en orden y aplica gates.
//! Semántica exacta de Python: tras cada execute se registra el output;
//! si un stage falla con block_on_failure y abort_early ⇒ los RESTANTES
//! se marcan SKIPPED ("Skipped due to earlier gate failure.").

use crate::domain::context::PipelineContext;
use crate::domain::types::{PipelineReport, StageResult, StageStatus};
use std::time::Instant;

pub trait PipelineStage {
    fn name(&self) -> &str;
    fn stage_type(&self) -> StageTypeAlias;
    fn block_on_failure(&self) -> bool;
    fn execute(&self, ctx: &mut PipelineContext) -> StageResult;
}

pub type StageTypeAlias = crate::domain::types::StageType;

pub struct PipelineOrchestrator {
    stages: Vec<Box<dyn PipelineStage>>,
    abort_early: bool,
}

impl PipelineOrchestrator {
    pub fn new(stages: Vec<Box<dyn PipelineStage>>) -> Self {
        Self {
            stages,
            abort_early: true,
        }
    }

    pub fn with_abort_early(mut self, abort_early: bool) -> Self {
        self.abort_early = abort_early;
        self
    }

    pub fn run(&self, ctx: &mut PipelineContext) -> PipelineReport {
        let started_at = chrono::Utc::now();
        let mut results: Vec<StageResult> = Vec::new();
        let mut aborted = false;

        for stage in &self.stages {
            if aborted {
                results.push(StageResult {
                    stage_type: stage.stage_type(),
                    stage_name: stage.name().to_string(),
                    status: StageStatus::Skipped,
                    message: "Skipped due to earlier gate failure.".into(),
                    artifacts: Default::default(),
                    duration_ms: 0,
                    timestamp: chrono::Utc::now(),
                });
                continue;
            }
            let _start = Instant::now();
            let result = stage.execute(ctx);
            ctx.set_stage_output(
                stage.name(),
                "status",
                serde_json::json!(result.status.value()),
            );
            if !result.passed() && stage.block_on_failure() && self.abort_early {
                eprintln!("🚨 Gate failed: {}. Aborting pipeline.", stage.name());
                aborted = true;
            }
            results.push(result);
        }

        PipelineReport {
            results,
            started_at,
            ended_at: chrono::Utc::now(),
        }
    }
}
