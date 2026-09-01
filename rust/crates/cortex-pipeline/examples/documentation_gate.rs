//! Checker del segmento `### DOCUMENTATION` del gate `pipeline_golden_p12b.py`
//! (T4): corre el `DocumentationStage` REAL sobre un fixture (vault + sesión
//! gitless + spec) y emite el `StageResult` CONGELADO — timestamp fijo y
//! `duration_ms` 0 — como una línea JSON que el gate normaliza ({{ROOT}},
//! {{ID}}) y congela en el golden.
//!
//! Uso:
//!   documentation_gate <root> <fixed_ts> <block:0|1> <changed_csv> [pr_ctx:0|1]
//!
//! `root` debe contener (layout v2): `.cortex/workspace.yaml`, `.cortex/vault/`
//! (con la spec referenciada por la sesión) y `.cortex/sessions/*.yaml`
//! (sesión gitless con `start_branch` == branch del PR). Determinista: el
//! fixture vive FUERA del repo (gitless real), ids de sesión fijos,
//! memory_jsonl ausente (memoria best-effort no entra al StageResult).

use std::path::Path;

use cortex_app::pr::PRContext;
use cortex_app::session::service::SessionService;
use cortex_app::session::SessionStorage;
use cortex_pipeline::domain::context::PipelineContext;
use cortex_pipeline::domain::types::{StageResult, StageStatus};
use cortex_pipeline::orchestrator::PipelineStage;
use cortex_pipeline::stages::documentation::DocumentationStage;
use cortex_workspace::WorkspaceLayout;
use serde_json::json;

const FIXED_COMMIT: &str = "feedfacefeedfacefeedfacefeedfacefeedface";
const FIXED_BRANCH: &str = "feature/pr-docs";

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let root = Path::new(&args[1]);
    let fixed_ts = &args[2];
    let block = args[3] == "1";
    let changed: Vec<String> = args
        .get(4)
        .map(|csv| {
            csv.split(',')
                .map(str::trim)
                .filter(|s| !s.is_empty())
                .map(String::from)
                .collect()
        })
        .unwrap_or_default();
    let with_pr = args.get(5).map(|s| s == "1").unwrap_or(true);

    let layout = WorkspaceLayout::from_repo_root(root);
    let vault = layout.vault_path();
    let service = SessionService::new(
        SessionStorage::new(layout.sessions_dir()),
        &layout.repo_root,
    );

    let mut ctx = PipelineContext::new(&vault);
    ctx.pr_number = 42;
    ctx.pr_title = "Add password reset".into();
    ctx.pr_author = "dev1".into();
    ctx.source_branch = FIXED_BRANCH.into();
    ctx.commit_sha = FIXED_COMMIT.into();
    ctx.changed_files = changed.clone();

    let mut stage = DocumentationStage::new(service).with_block_on_failure(block);
    if with_pr {
        stage = stage.with_pr_ctx(PRContext {
            pr_number: 42,
            title: "Add password reset".into(),
            body: String::new(),
            author: "dev1".into(),
            source_branch: FIXED_BRANCH.into(),
            commit_sha: FIXED_COMMIT.into(),
            files_changed: changed,
            ..Default::default()
        });
    }

    let mut result = stage.execute(&mut ctx);
    // Congela timestamp (reloj fijo del gate) y duration_ms.
    let ts = chrono::DateTime::parse_from_rfc3339(fixed_ts)
        .expect("fixed_ts ISO-8601")
        .with_timezone(&chrono::Utc);
    result.timestamp = ts;
    result.duration_ms = 0;
    assert_ne!(
        result.status,
        StageStatus::Skipped,
        "stage no debe quedar stub"
    );

    println!("{}", freeze_line(&result));
}

/// Línea JSON canónica con los campos que el golden congela.
fn freeze_line(r: &StageResult) -> String {
    json!({
        "stage_name": r.stage_name,
        "status": r.status.value(),
        "message": r.message,
        "artifacts": r.artifacts,
        "duration_ms": r.duration_ms,
        "timestamp": r.timestamp.to_rfc3339_opts(chrono::SecondsFormat::Secs, true),
    })
    .to_string()
}
