use chrono::{DateTime, Utc};
use cortex_enterprise::clock::FixedClock;
use cortex_enterprise::config::build_enterprise_org_config;
use cortex_enterprise::maintenance::{archive_violations, scan_retention_violations};
use cortex_enterprise::models::{OrgProfile, PromotableDocType, RetentionPolicy};
use cortex_enterprise::promotion_doctype::{
    list_pending_drafts, mark_as_accepted, mark_as_rejected, promote_note_doctype_aware,
    PromoteArgs,
};
use cortex_enterprise::review_knowledge::{approve_output, reject_output};
use cortex_workspace::WorkspaceLayout;
use std::fs;

const TS: &str = "2026-08-25T12:00:00+00:00";

fn clock() -> FixedClock {
    FixedClock::parse(TS).unwrap()
}

fn org_default() -> cortex_enterprise::models::EnterpriseOrgConfig {
    let mut cfg =
        build_enterprise_org_config("Acme Org", OrgProfile::SmallCompany, true, false).unwrap();
    // Sin teams ⇒ governance permisivo (back-compat), como en los tests Python.
    cfg.promotion.allowed_doc_types = vec![
        PromotableDocType::Spec,
        PromotableDocType::Decision,
        PromotableDocType::Runbook,
        PromotableDocType::Hu,
        PromotableDocType::Incident,
        PromotableDocType::Session,
    ];
    cfg
}

fn fixture_layout(tag: &str) -> (tempfile::TempDir, WorkspaceLayout) {
    let tmp = tempfile::tempdir_in(std::env::temp_dir()).unwrap();
    let root = tmp.path().join(tag);
    fs::create_dir_all(&root).unwrap();
    fs::write(root.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    let layout = WorkspaceLayout::discover(&root);
    (tmp, layout)
}

#[test]
fn adr_as_is_preserves_body_and_appends_audit() {
    let (_tmp, layout) = fixture_layout("adr");
    let vault = layout.enterprise_vault_path();
    fs::create_dir_all(&vault).unwrap();
    let source = layout.vault_path().join("decisions/DEC-x.md");
    fs::create_dir_all(source.parent().unwrap()).unwrap();
    fs::write(
        &source,
        "---\ndoc_type: decision\ntitle: Dec\nschema_version: 2\nstatus: published\nextra_key: keepme\n---\n\nBody line\n",
    )
    .unwrap();

    let result = promote_note_doctype_aware(PromoteArgs {
        source_path: &source,
        enterprise_vault_root: &vault,
        org: &org_default(),
        project_id: "api",
        actor: "tester",
        reason: Some("ok"),
        dry_run: false,
        clock: &clock(),
    })
    .unwrap();

    assert!(!result.summarized);
    assert_eq!(result.fingerprint.len(), 64);
    let bytes = fs::read_to_string(&result.target_path).unwrap();
    assert!(bytes.starts_with("---\n"));
    // Orden de claves del frontmatter enterprise.
    let expected_order = [
        "schema_version: 2",
        "doc_type: decision",
        "title: Dec",
        "status: published",
        "vault_scope: enterprise",
        "fingerprint:",
        "owner: tester",
        "team: admin",
        "classification: internal",
        "retention_days: 365",
        "extra_key: keepme",
        "audit_trail:",
    ];
    let mut last = 0usize;
    for needle in expected_order {
        let pos = bytes
            .find(needle)
            .unwrap_or_else(|| panic!("falta {needle}"));
        assert!(pos > last, "{needle} fuera de orden");
        last = pos;
    }
    // Audit trail con orden de claves Python.
    let audit_idx = bytes.find("- actor: tester").unwrap();
    let tail_end = (audit_idx + 160).min(bytes.len());
    let tail = &bytes[audit_idx..tail_end];
    let a_action = tail.find("action: promoted").unwrap();
    let a_ts = tail.find("timestamp:").unwrap();
    let a_reason = tail.find("reason: ok").unwrap();
    let a_mode = tail.find("promotion_mode: as-is").unwrap();
    assert!(a_action < a_ts && a_ts < a_reason && a_reason < a_mode);
}

#[test]
fn session_summarizes_and_runbook_becomes_draft() {
    let (_tmp, layout) = fixture_layout("sum");
    let vault = layout.enterprise_vault_path();
    fs::create_dir_all(&vault).unwrap();

    // SESSION summarize.
    let session = layout.vault_path().join("sessions/s.md");
    fs::create_dir_all(session.parent().unwrap()).unwrap();
    fs::write(
        &session,
        "---\ndoc_type: session\ntitle: Sprint\nstatus: active\n---\n\n## Key Decisions\n\nKeep Rust\n\n## Noise\n\nDrop me\n",
    )
    .unwrap();
    let result = promote_note_doctype_aware(PromoteArgs {
        source_path: &session,
        enterprise_vault_root: &vault,
        org: &org_default(),
        project_id: "api",
        actor: "tester",
        reason: None,
        dry_run: false,
        clock: &clock(),
    })
    .unwrap();
    assert!(result.summarized);
    let bytes = fs::read_to_string(&result.target_path).unwrap();
    assert!(bytes.contains("# Sprint\n"));
    assert!(bytes.contains("**Promoted session digest.** Full session lives at the source path."));
    assert!(bytes.contains("## Key Decisions\n\nKeep Rust"));
    assert!(!bytes.contains("Drop me"));
    assert!(bytes.contains("status: completed"));

    // RUNBOOK review-required.
    let runbook = layout.vault_path().join("runbooks/rb.md");
    fs::create_dir_all(runbook.parent().unwrap()).unwrap();
    fs::write(
        &runbook,
        "---\ndoc_type: runbook\ntitle: Deploy\n---\n\nSteps\n",
    )
    .unwrap();
    let result = promote_note_doctype_aware(PromoteArgs {
        source_path: &runbook,
        enterprise_vault_root: &vault,
        org: &org_default(),
        project_id: "api",
        actor: "tester",
        reason: None,
        dry_run: false,
        clock: &clock(),
    })
    .unwrap();
    assert!(!result.summarized);
    assert!(result.requires_review);
    let bytes = fs::read_to_string(&result.target_path).unwrap();
    assert!(bytes.contains("status: draft"));
}

#[test]
fn promotion_error_precedence_and_gates_match_python() {
    let (_tmp, layout) = fixture_layout("gates");
    let vault = layout.enterprise_vault_path();
    fs::create_dir_all(&vault).unwrap();
    let org = org_default();

    // Permisos ANTES que existencia de la fuente.
    let missing = layout.vault_path().join("specs/nope.md");
    let err = promote_note_doctype_aware(PromoteArgs {
        source_path: &missing,
        enterprise_vault_root: &vault,
        org: &org,
        project_id: "api",
        actor: "tester",
        reason: None,
        dry_run: false,
        clock: &clock(),
    })
    .unwrap_err();
    assert!(err.to_string().starts_with("source not found:"));

    // Actor sin permiso (con teams restrictivos).
    let mut restricted = org.clone();
    restricted.teams = vec![cortex_enterprise::models::TeamConfig {
        id: "eng".into(),
        members: vec![],
        can_promote: false,
        can_review: false,
    }];
    let err = promote_note_doctype_aware(PromoteArgs {
        source_path: &missing,
        enterprise_vault_root: &vault,
        org: &restricted,
        project_id: "api",
        actor: "intruder",
        reason: None,
        dry_run: false,
        clock: &clock(),
    })
    .unwrap_err();
    assert_eq!(
        err.to_string(),
        "actor 'intruder' (team=None) cannot promote"
    );

    // Incident low bloqueado; handoff no promovible; doc_type desconocido.
    let incident = layout.vault_path().join("incidents/inc.md");
    fs::create_dir_all(incident.parent().unwrap()).unwrap();
    fs::write(
        &incident,
        "---\ndoc_type: incident\ntitle: I\nseverity: low\n---\n\nB\n",
    )
    .unwrap();
    assert_eq!(
        promote_note_doctype_aware(PromoteArgs {
            source_path: &incident,
            enterprise_vault_root: &vault,
            org: &org,
            project_id: "api",
            actor: "tester",
            reason: None,
            dry_run: false,
            clock: &clock(),
        })
        .unwrap_err()
        .to_string(),
        "INCIDENT with severity=low is not promoted (gate by Fase 10)"
    );

    let handoff = layout.vault_path().join("handoffs/h.md");
    fs::create_dir_all(handoff.parent().unwrap()).unwrap();
    fs::write(&handoff, "---\ndoc_type: handoff\ntitle: H\n---\n\nB\n").unwrap();
    assert_eq!(
        promote_note_doctype_aware(PromoteArgs {
            source_path: &handoff,
            enterprise_vault_root: &vault,
            org: &org,
            project_id: "api",
            actor: "tester",
            reason: None,
            dry_run: false,
            clock: &clock(),
        })
        .unwrap_err()
        .to_string(),
        "'handoff' is not promotable (promotable=False in RouteSpec)"
    );

    let weird = layout.vault_path().join("specs/w.md");
    fs::create_dir_all(weird.parent().unwrap()).unwrap();
    fs::write(&weird, "---\ndoc_type: not-a-type\ntitle: W\n---\n\nB\n").unwrap();
    assert_eq!(
        promote_note_doctype_aware(PromoteArgs {
            source_path: &weird,
            enterprise_vault_root: &vault,
            org: &org,
            project_id: "api",
            actor: "tester",
            reason: None,
            dry_run: false,
            clock: &clock(),
        })
        .unwrap_err()
        .to_string(),
        "unknown doc_type 'not-a-type' in ".to_string() + &weird.display().to_string()
    );
}

#[test]
fn dry_run_writes_nothing_but_returns_result() {
    let (_tmp, layout) = fixture_layout("dry");
    let vault = layout.enterprise_vault_path();
    fs::create_dir_all(&vault).unwrap();
    let source = layout.vault_path().join("specs/dry.md");
    fs::create_dir_all(source.parent().unwrap()).unwrap();
    fs::write(&source, "---\ndoc_type: spec\ntitle: Dry\n---\n\nBody\n").unwrap();
    let result = promote_note_doctype_aware(PromoteArgs {
        source_path: &source,
        enterprise_vault_root: &vault,
        org: &org_default(),
        project_id: "api",
        actor: "tester",
        reason: None,
        dry_run: true,
        clock: &clock(),
    })
    .unwrap();
    assert!(!result.target_path.exists());
}

#[test]
fn approve_rejects_escape_from_enterprise_vault() {
    let (_tmp, layout) = fixture_layout("esc");
    let clk = clock();
    let err = approve_output(&layout, "../outside.md", "tester", "", &clk).unwrap_err();
    assert_eq!(
        err.to_string(),
        "Path escapes enterprise vault: ../outside.md"
    );
    let err = reject_output(&layout, "../outside.md", "tester", "why", false, &clk).unwrap_err();
    assert_eq!(
        err.to_string(),
        "Path escapes enterprise vault: ../outside.md"
    );
}

#[test]
fn accept_and_reject_mutations_match_python_semantics() {
    let (_tmp, layout) = fixture_layout("mut");
    let vault = layout.enterprise_vault_path();
    fs::create_dir_all(&vault).unwrap();
    let note = vault.join("notes/n.md");
    fs::create_dir_all(note.parent().unwrap()).unwrap();
    fs::write(
        &note,
        "---\ndoc_type: runbook\ntitle: N\nstatus: draft\n---\n\nBody\n",
    )
    .unwrap();

    // Non-draft rechaza aceptar.
    mark_as_accepted(&note, "rev", "", &clock()).unwrap();
    let bytes = fs::read_to_string(&note).unwrap();
    assert!(bytes.contains("status: accepted"));
    assert!(bytes.contains("actor: rev"));
    assert!(bytes.contains("action: accepted"));

    let err = mark_as_accepted(&note, "rev", "", &clock()).unwrap_err();
    assert!(err.to_string().starts_with(&format!(
        "cannot accept {}: status is 'accepted'",
        note.display()
    )));

    // Reject mueve a rejected/ y devuelve el nuevo path.
    fs::write(&note, "---\nstatus: draft\ntitle: N\n---\n\nBody\n").unwrap();
    let new_path = mark_as_rejected(&note, "rev", "dup", false, &clock())
        .unwrap()
        .expect("target");
    assert_eq!(new_path, vault.join("notes/rejected/n.md"));
    assert!(new_path.exists());
    assert!(!note.exists());
    let bytes = fs::read_to_string(&new_path).unwrap();
    assert!(bytes.contains("status: rejected"));
    assert!(bytes.contains("action: rejected"));

    // Reject con delete elimina sin dejar rastro reescrito.
    fs::create_dir_all(note.parent().unwrap()).unwrap();
    fs::write(&note, "---\nstatus: draft\ntitle: N\n---\n\nBody\n").unwrap();
    let gone = mark_as_rejected(&note, "rev", "del", true, &clock()).unwrap();
    assert!(gone.is_none());
    assert!(!note.exists());
}

#[test]
fn pending_drafts_filter_sort_and_skip_rejected() {
    let (_tmp, layout) = fixture_layout("pend");
    let vault = layout.enterprise_vault_path();
    fs::create_dir_all(vault.join("runbooks")).unwrap();
    fs::create_dir_all(vault.join("specs")).unwrap();
    fs::create_dir_all(vault.join("specs/rejected")).unwrap();
    fs::write(
        vault.join("runbooks/b.md"),
        "---\ndoc_type: runbook\nstatus: draft\ntitle: B\nowner: ana\n---\n\nB\n",
    )
    .unwrap();
    fs::write(
        vault.join("specs/a.md"),
        "---\ndoc_type: spec\nstatus: draft\ntitle: A\nowner: bob\n---\n\nB\n",
    )
    .unwrap();
    fs::write(
        vault.join("specs/published.md"),
        "---\nstatus: published\n---\n\nB\n",
    )
    .unwrap();
    fs::write(
        vault.join("specs/rejected/skip.md"),
        "---\ndoc_type: spec\nstatus: draft\n---\n\nB\n",
    )
    .unwrap();

    let all = list_pending_drafts(&vault, None);
    assert_eq!(
        // Orden por tupla (doc_type, path): "runbook" < "spec" alfabético,
        // idéntico al sort de Python.
        all.iter().map(|d| d.path.as_str()).collect::<Vec<_>>(),
        vec!["runbooks/b.md", "specs/a.md"]
    );

    let only_spec = list_pending_drafts(&vault, Some(&["spec".to_string()]));
    assert_eq!(only_spec.len(), 1);
    assert_eq!(only_spec[0].doc_type.as_deref(), Some("spec"));
}

#[test]
fn retention_boundary_is_inclusive() {
    let tmp = tempfile::tempdir().unwrap();
    fs::write(
        tmp.path().join("old.md"),
        "---\ndoc_type: hu\ncreated_at: '2026-08-24T00:00:00+00:00'\nretention_days: 1\n---\nBody\n",
    )
    .unwrap();
    let now: DateTime<Utc> = DateTime::parse_from_rfc3339("2026-08-25T00:00:00+00:00")
        .unwrap()
        .into();
    let hits = scan_retention_violations(tmp.path(), None, None, now);
    assert_eq!(hits.len(), 1);
    assert_eq!(hits[0].days_overdue, 0);
}

#[test]
fn retention_resolution_order_and_skips_match_python() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    fs::create_dir_all(root.join("_archived")).unwrap();
    fs::write(
        root.join("archived.md"),
        "---\ndoc_type: hu\ncreated_at: '2025-01-01T00:00:00+00:00'\n---\nB\n",
    )
    .unwrap();
    fs::write(
        root.join("_archived/deep.md"),
        "---\ndoc_type: hu\n---\nB\n",
    )
    .unwrap();
    fs::write(
        root.join("zero.md"),
        "---\ndoc_type: changelog\ncreated_at: '2020-01-01T00:00:00+00:00'\n---\nB\n",
    )
    .unwrap();
    fs::write(root.join("no-type.md"), "---\ntitle: X\n---\nB\n").unwrap();
    fs::write(
        root.join("explicit-wins.md"),
        "---\ndoc_type: hu\ncreated_at: '2025-01-01T00:00:00+00:00'\nretention_days: 99999\n---\nB\n",
    )
    .unwrap();
    fs::write(
        root.join("overdue.md"),
        "---\ndoc_type: hu\ncreated_at: '2024-06-01T00:00:00+00:00'\n---\nB\n",
    )
    .unwrap();

    let now: DateTime<Utc> = DateTime::parse_from_rfc3339("2026-08-25T00:00:00+00:00")
        .unwrap()
        .into();
    let org = org_default();
    let hits = scan_retention_violations(root, Some(&org), None, now);
    // Violan: overdue.md Y archived.md (está en la RAIZ; sólo el componente
    // de carpeta _archived/ se salta). hu=90 días por defecto; explicit-wins
    // no venció; changelog=0 nunca expira; no-type se salta.
    assert_eq!(
        hits.len(),
        2,
        "{:?}",
        hits.iter().map(|h| h.path.file_name()).collect::<Vec<_>>()
    );
    let names: Vec<_> = hits
        .iter()
        .map(|h| h.path.file_name().unwrap().to_string_lossy().to_string())
        .collect();
    assert!(names.contains(&"archived.md".to_string()));
    assert!(names.contains(&"overdue.md".to_string()));

    // defaults explícito pisa org.retention_defaults.
    let custom = RetentionPolicy {
        hu: 10_000,
        ..RetentionPolicy::default()
    };
    let hits = scan_retention_violations(root, Some(&org), Some(&custom), now);
    assert!(hits.is_empty());
}

#[test]
fn archive_moves_preserving_relative_paths() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    fs::create_dir_all(root.join("sub")).unwrap();
    let note = root.join("sub/n.md");
    fs::write(&note, "B\n").unwrap();

    let now: DateTime<Utc> = DateTime::parse_from_rfc3339("2026-08-25T00:00:00+00:00")
        .unwrap()
        .into();
    // n.md sin doc_type no genera violación; fabricamos una manual para probar el mover.
    let _unused = scan_retention_violations(root, None, None, now);
    let violations = vec![cortex_enterprise::maintenance::RetentionViolation {
        path: note.clone(),
        doc_type: Some("hu".into()),
        retention_days: 90,
        created_at: now,
        days_overdue: 5,
    }];
    let moved = archive_violations(&violations, root, false);
    assert_eq!(moved, vec![root.join("_archived/sub/n.md")]);
    assert!(!note.exists());
    assert!(root.join("_archived/sub/n.md").exists());

    // Dry-run devuelve plan sin mover.
    fs::copy(root.join("_archived/sub/n.md"), &note).unwrap();
    let planned = archive_violations(&violations, root, true);
    assert_eq!(planned, vec![root.join("_archived/sub/n.md")]);
    assert!(note.exists());
}
