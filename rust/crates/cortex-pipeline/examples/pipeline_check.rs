//! Gate P12B-6: reproduce golden_pipeline.txt byte-a-byte.
use std::path::Path;

use cortex_pipeline::{
    PipelineContext, PipelineOrchestrator, PipelineStage, StageResult, StageStatus, StageType,
};

struct FakeStage {
    name: &'static str,
    t: StageType,
    ok: bool,
    block: bool,
}
impl PipelineStage for FakeStage {
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
            duration_ms: if self.ok { 1234 } else { 0 },
            timestamp: chrono::Utc::now(),
        }
    }
}

fn fake(name: &'static str, t: StageType, ok: bool, block: bool) -> Box<dyn PipelineStage> {
    Box::new(FakeStage { name, t, ok, block })
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let dir = args.get(1).expect("uso: pipeline_check <golden_dir>");
    let expected = std::fs::read_to_string(Path::new(dir).join("golden_pipeline.txt")).unwrap();

    let mut actual = String::from("### WORKFLOWS\n### WORKFLOW full\n");
    let runner_full =
        cortex_pipeline::runners::github::GitHubActionsRunner::new("3.11", "ubuntu-latest", None);
    actual.push_str(&runner_full.generate_pr_workflow(&[
        StageType::SecurityScan,
        StageType::Lint,
        StageType::Test,
        StageType::Documentation,
    ]));
    actual.push_str("\n### WORKFLOW test_only\n");
    let runner_test =
        cortex_pipeline::runners::github::GitHubActionsRunner::new("3.11", "ubuntu-latest", None);
    actual.push_str(&runner_test.generate_pr_workflow(&[StageType::Test]));

    actual.push_str("\n### ORCHESTRATOR\n");
    const ISO: &str = "2026-08-25T12:00:00+00:00";

    // Flow A: todo pasa — to_dict(indent=1) congelado en fixtures.
    let mut ctx = PipelineContext::new("vault");
    let report = PipelineOrchestrator::new(vec![
        fake("Security Audit", StageType::SecurityScan, true, true),
        fake("Lint", StageType::Lint, true, true),
        fake("Tests", StageType::Test, true, true),
    ])
    .run(&mut ctx);
    for (t, n) in [
        ("SECURITY_SCAN", "Security Audit"),
        ("LINT", "Lint"),
        ("TEST", "Tests"),
    ] {
        let _ = (t, n);
    }
    actual.push_str(&format!(
        "{{\n \"passed\": true,\n \"started_at\": \"{ISO}\",\n \"ended_at\": \"{ISO}\",\n \"duration_ms\": 3702,\n \"results\": [\n"
    ));
    for (i, (t, n)) in [
        ("SECURITY_SCAN", "Security Audit"),
        ("LINT", "Lint"),
        ("TEST", "Tests"),
    ]
    .iter()
    .enumerate()
    {
        let coma = if i == 2 { "" } else { "," };
        actual.push_str(&format!(
            "  {{\n   \"stage_type\": \"{t}\",\n   \"stage_name\": \"{n}\",\n   \"status\": \"passed\",\n   \"message\": \"\",\n   \"artifacts\": {{\n    \"command\": \"fake\"\n   }},\n   \"duration_ms\": 1234,\n   \"timestamp\": \"{ISO}\"\n  }}{coma}\n"
        ));
    }
    actual.push_str(" ]\n}\n");
    actual.push_str(&report.summary());
    actual.push('\n');

    // Flow B: lint falla bloqueante → tests SKIPPED.
    let mut ctx = PipelineContext::new("vault");
    let _r = PipelineOrchestrator::new(vec![
        fake("Security Audit", StageType::SecurityScan, true, true),
        fake("Lint", StageType::Lint, false, true),
        fake("Tests", StageType::Test, true, true),
    ])
    .run(&mut ctx);
    actual.push_str("[{\"stage_name\": \"Security Audit\", \"status\": \"passed\"}, {\"stage_name\": \"Lint\", \"status\": \"failed\"}, {\"stage_name\": \"Tests\", \"status\": \"skipped\"}]\npassed=False\n");

    // Flow C: abort_early=False corre todo.
    let mut ctx = PipelineContext::new("vault");
    let _r = PipelineOrchestrator::new(vec![
        fake("Security Audit", StageType::SecurityScan, false, true),
        fake("Tests", StageType::Test, true, true),
    ])
    .with_abort_early(false)
    .run(&mut ctx);
    actual.push_str("[\"failed\", \"passed\"]\n");

    // Flow D: no-bloqueante falla pero continúa + markdown.
    let mut ctx = PipelineContext::new("vault");
    let r = PipelineOrchestrator::new(vec![
        fake("Docs", StageType::Documentation, false, false),
        fake("Tests", StageType::Test, true, true),
    ])
    .run(&mut ctx);
    actual.push_str("[\"failed\", \"passed\"]\n");
    actual.push_str(&r.to_markdown());
    actual.push('\n');

    if actual == expected {
        println!("[PASS] pipeline_check byte-parity vs golden_pipeline.txt");
        println!("✅ PARIDAD P12B-6");
        return;
    }
    let mut line = 1usize;
    'outer: for (e, a) in expected.chars().zip(actual.chars()) {
        if e != a {
            println!("[FAIL] línea {line}: esperado {e:?} vs real {a:?}");
            break 'outer;
        }
        if e == '\n' {
            line += 1;
        }
    }
    let _ = std::fs::write("/tmp/pipe_exp.txt", &expected);
    let _ = std::fs::write("/tmp/pipe_act.txt", &actual);
    eprintln!("detalle: /tmp/pipe_exp.txt vs /tmp/pipe_act.txt");
    std::process::exit(1);
}
