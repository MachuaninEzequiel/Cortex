//! Tests de integración del `DocumentationStage` REAL (T4).
//!
//! Contrato (espejo del oráculo `cortex/pipeline/stages/documentation.py`):
//! - docs de agente presentes → PASSED + `has_agent_docs=true` (+ indexed N).
//! - sin docs → nota de sesión fallback vía persister nativo; PASSED por
//!   defecto (`block_on_failure=false`), FAILED si `block_on_failure=true`.
//! - sesión malformada / persister roto → ERROR "Documentation stage error:".
//! - PR context en memoria episódica nativa (paso 1, glue documentado).
//!
//! TDD: RED contra el stub (status Skipped), GREEN contra la implementación
//! real. Fixtures reales (vault + sesión gitless + spec en disco), nunca
//! mocks ni grep de source.

use std::fs;
use std::path::Path;

use cortex_app::pr::PRContext;
use cortex_app::session::service::SessionService;
use cortex_app::session::{
    SessionMode, SessionRecord, SessionStatus, SessionStorage, GITLESS_COMMIT_PLACEHOLDER,
};
use cortex_pipeline::domain::context::PipelineContext;
use cortex_pipeline::domain::types::StageStatus;
use cortex_pipeline::orchestrator::PipelineStage;
use cortex_pipeline::stages::documentation::DocumentationStage;
use cortex_workspace::WorkspaceLayout;

/// SHA 40-hex lowercase fijo (válido para `start_commit` no-gitless).
const COMMIT_SHA: &str = "feedfacefeedfacefeedfacefeedfacefeedface";

struct Fixture {
    _tmp: tempfile::TempDir,
    root: std::path::PathBuf,
    vault: std::path::PathBuf,
    service: SessionService,
}

fn spec_body() -> &'static str {
    "---\ntitle: PR spec\ngoal: Implement password reset flow\nfiles_in_scope:\n  - src/auth.py\nacceptance_criteria:\n  - Reset works\n---\n\n## Goal\n\nImplement password reset flow.\n"
}

/// Vault tmp + sesión gitless REAL + spec en disco (`record.spec_path`).
fn fixture() -> Fixture {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().to_path_buf();
    let vault = root.join("vault");
    fs::create_dir_all(vault.join("specs")).unwrap();

    let layout = WorkspaceLayout::from_repo_root(&root);
    let service = SessionService::new(
        SessionStorage::new(layout.sessions_dir()),
        &layout.repo_root,
    );

    let spec_path = vault.join("specs").join("pr-spec.md");
    fs::write(&spec_path, spec_body()).unwrap();

    let record = SessionRecord {
        session_id: "2026-08-25_docspr".into(),
        spec_path: spec_path.display().to_string(),
        spec_summary: "Implement password reset flow".into(),
        start_commit: GITLESS_COMMIT_PLACEHOLDER.into(),
        start_branch: "feature/pr-docs".into(),
        opened_at: "2026-08-25T12:00:00+00:00".into(),
        status: SessionStatus::Open,
        mode: SessionMode::Byo,
        ..Default::default()
    };
    service.save_new_record(&record).unwrap();

    Fixture {
        _tmp: tmp,
        root,
        vault,
        service,
    }
}

/// PipelineContext típico de CI (PR #42, branch feature/pr-docs).
fn ctx_of(f: &Fixture, changed: &[&str]) -> PipelineContext {
    let mut ctx = PipelineContext::new(&f.vault);
    ctx.pr_number = 42;
    ctx.pr_title = "Add password reset".into();
    ctx.pr_author = "dev1".into();
    ctx.source_branch = "feature/pr-docs".into();
    ctx.commit_sha = COMMIT_SHA.into();
    ctx.changed_files = changed.iter().map(|s| s.to_string()).collect();
    ctx
}

fn pr_ctx_with(changed: &[&str]) -> PRContext {
    PRContext {
        pr_number: 42,
        title: "Add password reset".into(),
        body: "refresh token".into(),
        author: "dev1".into(),
        source_branch: "feature/pr-docs".into(),
        commit_sha: COMMIT_SHA.into(),
        files_changed: changed.iter().map(|s| s.to_string()).collect(),
        ..Default::default()
    }
}

const DOCS_PRESENT: &[&str] = &["vault/specs/pr-spec.md"];
const NO_DOCS: &[&str] = &["src/auth.py"];

#[test]
fn docs_present_passed_con_has_agent_docs() {
    let f = fixture();
    let mut ctx = ctx_of(&f, DOCS_PRESENT);
    ctx.set_stage_output("Lint", "status", serde_json::json!("passed"));
    let stage = DocumentationStage::new(f.service).with_pr_ctx(pr_ctx_with(DOCS_PRESENT));

    let result = stage.execute(&mut ctx);

    assert_eq!(result.stage_name, "Documentation");
    assert_eq!(result.status, StageStatus::Passed);
    assert!(
        result
            .message
            .starts_with("Agent documentation found and indexed (1 docs)."),
        "{}",
        result.message
    );
    assert_eq!(result.artifacts["has_agent_docs"], serde_json::json!(true));
    assert_eq!(result.artifacts["indexed"], serde_json::json!(1));
}

#[test]
fn no_docs_genera_fallback_passed() {
    let f = fixture();
    let mut ctx = ctx_of(&f, NO_DOCS);
    let stage = DocumentationStage::new(f.service).with_pr_ctx(pr_ctx_with(NO_DOCS));

    let result = stage.execute(&mut ctx);

    assert_eq!(result.status, StageStatus::Passed);
    assert!(
        result
            .message
            .starts_with("No agent docs found. Fallback generated: "),
        "{}",
        result.message
    );
    assert_eq!(result.artifacts["has_agent_docs"], serde_json::json!(false));
    let fallback = result.artifacts["fallback_path"].as_str().unwrap();
    assert!(
        Path::new(fallback).is_file(),
        "fallback note no existe: {fallback}"
    );
    assert!(
        fallback.starts_with(&f.vault.display().to_string()),
        "fallback fuera del vault: {fallback}"
    );
}

#[test]
fn no_docs_con_block_on_failure_failed() {
    let f = fixture();
    let mut ctx = ctx_of(&f, NO_DOCS);
    let stage = DocumentationStage::new(f.service)
        .with_pr_ctx(pr_ctx_with(NO_DOCS))
        .with_block_on_failure(true);

    let result = stage.execute(&mut ctx);

    assert_eq!(result.status, StageStatus::Failed);
    assert!(
        result
            .message
            .starts_with("No agent docs found. Fallback generated: "),
        "{}",
        result.message
    );
    assert_eq!(result.artifacts["has_agent_docs"], serde_json::json!(false));
}

#[test]
fn sin_pr_ctx_fallback_skipped() {
    let f = fixture();
    let mut ctx = ctx_of(&f, NO_DOCS);
    let stage = DocumentationStage::new(f.service);

    let result = stage.execute(&mut ctx);

    assert_eq!(result.status, StageStatus::Passed);
    assert_eq!(
        result.message,
        "No agent docs found. Fallback generation skipped."
    );
    assert_eq!(result.artifacts["has_agent_docs"], serde_json::json!(false));
    assert_eq!(result.artifacts["fallback_path"], serde_json::Value::Null);
}

#[test]
fn sesion_malformada_error() {
    let f = fixture();
    // Sesión NO gitless (start_commit real) sin repo git detrás ⇒ el
    // `reconstruct_git` del persister falla ⇒ ERROR del stage.
    let spec_path = f.vault.join("specs").join("pr-spec.md");
    let record = SessionRecord {
        session_id: "2026-08-25_gitpr".into(),
        spec_path: spec_path.display().to_string(),
        spec_summary: "Implement password reset flow".into(),
        start_commit: COMMIT_SHA.into(),
        start_branch: "feature/pr-docs".into(),
        opened_at: "2026-08-25T12:00:00+00:00".into(),
        status: SessionStatus::Open,
        mode: SessionMode::Byo,
        ..Default::default()
    };
    f.service.save_new_record(&record).unwrap();

    let mut ctx = ctx_of(&f, NO_DOCS);
    let stage = DocumentationStage::new(f.service).with_pr_ctx(pr_ctx_with(NO_DOCS));

    let result = stage.execute(&mut ctx);

    assert_eq!(result.status, StageStatus::Error);
    assert!(
        result.message.starts_with("Documentation stage error: "),
        "{}",
        result.message
    );
    assert!(result.artifacts["error"].is_string());
}

#[test]
fn store_pr_context_escribe_memoria_episodica() {
    let f = fixture();
    let mut ctx = ctx_of(&f, DOCS_PRESENT);
    ctx.set_stage_output("Lint", "status", serde_json::json!("passed"));
    ctx.set_stage_output("Tests", "status", serde_json::json!("passed"));
    ctx.set_stage_output(
        "Security Audit",
        "status",
        serde_json::json!("failed: 2 high"),
    );

    let memory_jsonl = f.root.join("memory").join("episodic_export.jsonl");
    fs::create_dir_all(memory_jsonl.parent().unwrap()).unwrap();
    fs::write(&memory_jsonl, "").unwrap();

    let stage = DocumentationStage::new(f.service)
        .with_pr_ctx(pr_ctx_with(DOCS_PRESENT))
        .with_memory_jsonl(&memory_jsonl);

    let result = stage.execute(&mut ctx);
    assert_eq!(result.status, StageStatus::Passed);

    // La fila episódica se persistió vía el glue nativo (PRService →
    // NativeEpisodicStore JSONL).
    let store = cortex_app::episodic::NativeEpisodicStore::load(&memory_jsonl).unwrap();
    assert_eq!(store.count(), 1, "falta la memoria PR en el JSONL");
    let entry = &store.rows[0].entry;
    assert_eq!(entry.memory_type, "pr");
    assert_eq!(entry.tags, vec!["pr", "dev1"]);
    assert!(entry
        .content
        .starts_with("PR #42: Add password reset by dev1 (feature/pr-docs -> main)"));
    assert!(entry.content.contains("\nLint: passed"));
    assert!(entry.content.contains("\nAudit: failed: 2 high"));
    assert!(entry.content.contains("\nTests: passed"));
}
