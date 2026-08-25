//! Puerto parcial de `stages/documentation.py`: sin AgentMemory nativo ⇒
//! stub contractual (patrón P6/P9).
use crate::domain::context::PipelineContext;
use crate::domain::types::{StageResult, StageStatus, StageType};

pub struct DocumentationStage;

impl crate::orchestrator::PipelineStage for DocumentationStage {
    fn name(&self) -> &str {
        "Documentation"
    }
    fn stage_type(&self) -> StageType {
        StageType::Documentation
    }
    fn block_on_failure(&self) -> bool {
        false
    }
    fn execute(&self, _ctx: &mut PipelineContext) -> StageResult {
        StageResult {
            stage_type: StageType::Documentation,
            stage_name: "Documentation".into(),
            status: StageStatus::Skipped,
            message: "backend no nativo aún (cortex.core.AgentMemory)".into(),
            artifacts: Default::default(),
            duration_ms: 0,
            timestamp: chrono::Utc::now(),
        }
    }
}
