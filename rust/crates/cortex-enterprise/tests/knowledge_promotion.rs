use std::fs;
use std::sync::Arc;

use cortex_enterprise::clock::FixedClock;
use cortex_enterprise::config::build_enterprise_org_config;
use cortex_enterprise::knowledge_promotion::{
    KnowledgePromotionService, PromotionPaths, PromotionRulesEngine,
};
use cortex_enterprise::models::{OrgProfile, PromotableDocType};

const TS: &str = "2026-08-25T12:00:00+00:00";

fn fixture_service(require_review: bool) -> (tempfile::TempDir, KnowledgePromotionService) {
    let tmp = tempfile::tempdir().unwrap();
    let project_root = tmp.path().join("acme-api");
    let local = project_root.join("vault");
    let enterprise = project_root.join("vault-enterprise");
    fs::create_dir_all(local.join("specs")).unwrap();
    fs::create_dir_all(&enterprise).unwrap();
    fs::write(
        local.join("specs/auth.md"),
        "---\ntitle: Auth\ntags: [spec]\n---\n\nInitial spec body\n",
    )
    .unwrap();
    let mut config =
        build_enterprise_org_config("Acme Org", OrgProfile::SmallCompany, true, false).unwrap();
    config.promotion.require_review = require_review;
    config.promotion.allowed_doc_types = vec![PromotableDocType::Spec];
    // La config vive en disco: discover_candidates la recarga en cada
    // llamada (contrato Python).
    cortex_enterprise::config::write_enterprise_config(&project_root, &config, None).unwrap();
    let paths = PromotionPaths {
        project_root: project_root.clone(),
        local_vault: local,
        enterprise_vault: enterprise.clone(),
        records_path: enterprise.join(".cortex/promotion/records.jsonl"),
    };
    let clock = Arc::new(FixedClock::parse(TS).unwrap());
    let service = KnowledgePromotionService::new(paths, config, clock);
    (tmp, service)
}

#[test]
fn reviewed_candidate_promotes_once_and_records_jsonl() {
    let (_tmp, mut svc) = fixture_service(true);
    let mut candidates = svc.discover_candidates().unwrap();
    assert_eq!(candidates.len(), 1);
    let selector = candidates.remove(0).origin_id;
    // Sin review previa no hay plan.
    assert!(svc.plan_promotion().unwrap().is_empty());

    let record = svc.review(&selector, true, "tester", Some("ok")).unwrap();
    assert_eq!(record.status, "reviewed");

    let plan = svc.plan_promotion().unwrap();
    assert_eq!(plan.len(), 1);

    let written = svc.apply_promotion(&plan, "tester").unwrap();
    assert_eq!(written.len(), 1);
    assert_eq!(written[0].status, "promoted");

    // Re-ejecutar es idempotente.
    assert!(svc.discover_candidates().unwrap().is_empty());
    assert!(svc.plan_promotion().unwrap().is_empty());
}

#[test]
fn jsonl_record_bytes_match_python_field_order() {
    let (_tmp, mut svc) = fixture_service(true);
    let candidate = svc.discover_candidates().unwrap().remove(0);
    let record = svc
        .review(&candidate.origin_id, true, "tester", Some("ok"))
        .unwrap();

    let line = fs::read_to_string(&svc.paths.records_path).unwrap();
    let line = line.lines().next().unwrap();
    let fp = &record.fingerprint;
    let ev_candidate = format!(
        "{{\"event\":\"candidate\",\"at\":\"{TS}\",\"actor\":null,\"payload\":{{\"fingerprint\":\"{fp}\"}}}}"
    );
    let ev_reviewed = format!(
        "{{\"event\":\"reviewed\",\"at\":\"{TS}\",\"actor\":\"tester\",\"payload\":{{\"reason\":\"ok\"}}}}"
    );
    let esperada = format!(
        "{{\"origin_id\":\"{o}\",\"local_rel_path\":\"specs/auth.md\",\"doc_type\":\"spec\",\
         \"dest_rel_path\":\"specs/acme-api/auth.md\",\"fingerprint\":\"{fp}\",\
         \"status\":\"reviewed\",\"created_at\":\"{TS}\",\"updated_at\":\"{TS}\",\
         \"decision\":{{\"decision\":\"approve\",\"actor\":\"tester\",\
         \"decided_at\":\"{TS}\",\"reason\":\"ok\"}},\
         \"events\":[{ev_candidate},{ev_reviewed}]}}",
        o = candidate.origin_id
    );
    assert_eq!(line, esperada);
}

#[test]
fn sessions_and_cortex_metadata_are_not_promotable_by_default() {
    let (_tmp, mut svc) = fixture_service(true);
    fs::create_dir_all(svc.paths.local_vault.join("sessions")).unwrap();
    fs::write(
        svc.paths.local_vault.join("sessions/2026-01-01_s.md"),
        "---\ntitle: S\n---\n\nBody\n",
    )
    .unwrap();
    fs::create_dir_all(svc.paths.local_vault.join(".cortex")).unwrap();
    fs::write(
        svc.paths.local_vault.join(".cortex/internal.md"),
        "---\ntitle: X\n---\n\nSecret\n",
    )
    .unwrap();
    let candidates = svc.discover_candidates().unwrap();
    assert_eq!(candidates.len(), 1, "sólo specs/auth.md es candidato");
    assert_eq!(candidates[0].local_rel_path, "specs/auth.md");
    let _ = &mut svc;
}

#[test]
fn fingerprint_normalizes_crlf_and_strips_body_edges() {
    let raw = "---\ntitle: A\n---\n\r\nHola\r\nmundo\r\n";
    let fp_a = cortex_enterprise::frontmatter::normalized_markdown_fingerprint(raw);
    let fp_b = cortex_enterprise::frontmatter::normalized_markdown_fingerprint(
        "---\ntitle: A\n---\n\nHola\nmundo\n",
    );
    assert_eq!(fp_a, fp_b);
    assert_eq!(fp_a.len(), 64);
}

#[test]
fn invalid_jsonl_lines_are_skipped_silently() {
    let (_tmp, svc) = fixture_service(true);
    fs::create_dir_all(svc.paths.records_path.parent().unwrap()).unwrap();
    fs::write(
        &svc.paths.records_path,
        "{not-json}\n{\"origin_id\":\"x\",\"status\":\"impossible-status\"}\n",
    )
    .unwrap();
    let latest = svc.repo.load_latest_by_origin_id().unwrap();
    assert!(latest.is_empty(), "líneas inválidas se descartan");
}

#[test]
fn content_change_requires_new_review() {
    let (_tmp, mut svc) = fixture_service(true);
    let candidate = svc.discover_candidates().unwrap().remove(0);
    svc.review(&candidate.origin_id, true, "tester", None)
        .unwrap();
    let plan = svc.plan_promotion().unwrap();
    svc.apply_promotion(&plan, "tester").unwrap();

    fs::write(
        svc.paths.local_vault.join("specs/auth.md"),
        "---\ntitle: Auth\ntags: [spec]\n---\n\nChanged spec body\n",
    )
    .unwrap();
    let candidates = svc.discover_candidates().unwrap();
    assert_eq!(candidates.len(), 1, "candidato reaparece tras cambio");
    assert!(
        svc.plan_promotion().unwrap().is_empty(),
        "no se promueve sin nueva review"
    );
}

#[test]
fn validation_error_blocks_review() {
    let (_tmp, mut svc) = fixture_service(true);
    fs::remove_file(svc.paths.local_vault.join("specs/auth.md")).unwrap();
    fs::write(
        svc.paths.local_vault.join("specs/bad.md"),
        "---\n: bad yaml\n---\n\nBody\n",
    )
    .unwrap();
    let candidate = svc.discover_candidates().unwrap().remove(0);
    assert!(candidate.issues.iter().any(|i| i.severity == "error"));

    let err = svc
        .review(&candidate.local_rel_path, true, "tester", None)
        .unwrap_err();
    assert_eq!(
        err.to_string(),
        "Cannot review a document with validation errors."
    );
}

#[test]
fn unknown_selector_reports_python_message() {
    let (_tmp, mut svc) = fixture_service(true);
    let err = svc.review("missing.md", true, "tester", None).unwrap_err();
    assert_eq!(
        err.to_string(),
        "No candidate found for selector: missing.md"
    );
}

#[test]
fn rules_engine_messages_match_python() {
    let allowed: std::collections::HashSet<String> =
        ["spec"].iter().map(|s| s.to_string()).collect();
    let engine = PromotionRulesEngine::new(allowed);
    assert_eq!(
        engine.is_promotable(".cortex/x.md"),
        (false, "internal cortex metadata".to_string())
    );
    assert_eq!(
        engine.is_promotable("docs/a.md"),
        (
            false,
            "unknown doc family (not under a recognized vault folder)".to_string()
        )
    );
    assert_eq!(
        engine.is_promotable("sessions/s.md"),
        (
            false,
            "sessions excluded by default (not enabled in org promotion.allowed_doc_types)"
                .to_string()
        )
    );
    assert_eq!(
        engine.is_promotable("incidents/i.md"),
        (
            false,
            "doc_type 'incident' not allowed by org promotion.allowed_doc_types".to_string()
        )
    );
    assert_eq!(
        engine.is_promotable("specs/a.md"),
        (true, "allowed".to_string())
    );
}
