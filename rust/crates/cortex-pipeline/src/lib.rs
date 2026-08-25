//! Puerto de `cortex.pipeline` (P12B-6): tipos, contexto, trait de stage,
//! orquestador con gates, stages subprocess y generador GitHub Actions.

pub mod domain;
pub mod orchestrator;
pub mod runners;
pub mod stages;

pub use domain::{
    context::PipelineContext,
    types::{PipelineReport, StageResult, StageStatus, StageType},
};
pub use orchestrator::{PipelineOrchestrator, PipelineStage};
