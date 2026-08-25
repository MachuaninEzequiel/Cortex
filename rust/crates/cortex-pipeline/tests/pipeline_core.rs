use cortex_pipeline::{PipelineContext, PipelineOrchestrator, StageResult, StageStatus, StageType};

struct FakeStage {
    name: &'static str,
    t: StageType,
    ok: bool,
    block: bool,
}
impl cortex_pipeline::PipelineStage for FakeStage {
    fn name(&self) -> &str {
        self.name
    }
    fn stage_type(&self) -> StageType {
        self.t
    }
    fn block_on_failure(&self) -> bool {
        self.block
    }
    fn execute(&self, _ctx: &mut PipelineContext) -> StageResult {
        StageResult {
            stage_type: self.t,
            stage_name: self.name.into(),
            status: if self.ok {
                StageStatus::Passed
            } else {
                StageStatus::Failed
            },
            message: String::new(),
            artifacts: Default::default(),
            duration_ms: 1234,
            timestamp: chrono::Utc::now(),
        }
    }
}

fn stages(specs: &[(bool, bool)]) -> Vec<Box<dyn cortex_pipeline::PipelineStage>> {
    specs
        .iter()
        .map(|(ok, block)| {
            Box::new(FakeStage {
                name: if *ok { "Tests" } else { "Lint" },
                t: if *ok {
                    StageType::Test
                } else {
                    StageType::Lint
                },
                ok: *ok,
                block: *block,
            }) as Box<dyn cortex_pipeline::PipelineStage>
        })
        .collect()
}

#[test]
fn all_pass_flow() {
    let mut ctx = PipelineContext::new("vault");
    let report = PipelineOrchestrator::new(stages(&[(true, true)])).run(&mut ctx);
    assert!(report.passed());
    assert_eq!(report.results[0].status.value(), "passed");
    assert_eq!(report.summary(), "Pipeline PASSED in 1.2s — [✅ Tests]");
}

#[test]
fn blocking_failure_skips_remaining() {
    let mut ctx = PipelineContext::new("vault");
    let report = PipelineOrchestrator::new(stages(&[(false, true), (true, true)])).run(&mut ctx);
    assert!(!report.passed());
    assert_eq!(report.results[1].status.value(), "skipped");
    assert_eq!(
        report.results[1].message,
        "Skipped due to earlier gate failure."
    );
}

#[test]
fn non_blocking_failure_continues() {
    let mut ctx = PipelineContext::new("vault");
    let report = PipelineOrchestrator::new(stages(&[(false, false), (true, true)])).run(&mut ctx);
    assert_eq!(report.results[0].status.value(), "failed");
    assert_eq!(report.results[1].status.value(), "passed");
}

#[test]
fn markdown_table_renders() {
    let mut ctx = PipelineContext::new("vault");
    let report = PipelineOrchestrator::new(stages(&[(true, true)])).run(&mut ctx);
    let md = report.to_markdown();
    assert!(md.contains("| ✅ Tests | passed | 1.2s | - |"));
    assert!(md.contains("**✅ All gates passed** — Total: 1.2s"));
}
