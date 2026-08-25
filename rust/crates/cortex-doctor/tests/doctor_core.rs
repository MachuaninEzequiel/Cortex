use std::fs;
use std::path::PathBuf;

use cortex_doctor::doctor::{run_doctor, DoctorScope};
use cortex_enterprise::config::{build_enterprise_org_config, write_enterprise_config};

fn fixture(tag: &str, new_layout: bool) -> (tempfile::TempDir, PathBuf) {
    let tmp = tempfile::tempdir_in(std::env::temp_dir()).unwrap();
    let root = tmp.path().join(tag);
    fs::create_dir_all(&root).unwrap();
    fs::write(root.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    fs::create_dir_all(root.join("vault/specs")).unwrap();
    fs::write(
        root.join("vault/specs/spec.md"),
        "---\ntitle: Spec\ntags: [spec]\n---\n\n# Spec\n\nHello\n",
    )
    .unwrap();
    if new_layout {
        fs::create_dir_all(root.join(".cortex")).unwrap();
        fs::write(
            root.join(".cortex/workspace.yaml"),
            "layout_version: 2\nprojects: []\n",
        )
        .unwrap();
        let _ = PathBuf::new();
    }
    (tmp, root)
}

#[test]
fn core_portable_checks_order_and_details_match_python() {
    let (_tmp, root) = fixture("core", false);
    let report = run_doctor(&root, DoctorScope::Project).unwrap();

    assert_eq!(report.project_root, root);
    // gitignore:.memory/ ausente ⇒ fail ⇒ has_failures=true (igual que
    // el doctor Python en este fixture).
    assert!(report.has_failures(), "{report:?}");

    let names: Vec<&str> = report.checks.iter().map(|c| c.name.as_str()).collect();
    let esperados_prefix = [
        "project_root",
        "layout_mode",
        "config_yaml",
        "config_validation",
        "vault_dir",
        "episodic_store",
        "cortex_workspace",
        "agent_guidelines",
    ];
    assert_eq!(&names[..esperados_prefix.len()], &esperados_prefix);

    let by_name = |n: &str| {
        report
            .checks
            .iter()
            .find(|c| c.name == n)
            .unwrap_or_else(|| panic!("falta {n}"))
    };
    let c = by_name("project_root");
    assert!(c.ok && c.severity == "fail" && c.detail == root.display().to_string());

    let lm = by_name("layout_mode");
    assert_eq!(
        lm.detail,
        format!("legacy (workspace_root={})", root.display())
    );

    let cv = by_name("config_validation");
    assert!(cv.ok && cv.severity == "info");
    assert_eq!(cv.detail, "config.yaml is valid");

    let es = by_name("episodic_store");
    assert_eq!(es.severity, "fail", "sin GITHUB_ACTIONS es fail");
    assert!(
        es.detail.ends_with("memory"),
        "resolve_episodic_persist_dir default"
    );

    // Gitignore legacy presente con severidades correctas.
    let gi_memory = by_name("gitignore:.memory/");
    assert_eq!(gi_memory.severity, "fail");
    assert_eq!(gi_memory.detail, ".memory/");
}

#[test]
fn missing_root_returns_only_two_checks() {
    let tmp = tempfile::tempdir_in(std::env::temp_dir()).unwrap();
    let root = tmp.path().join("nope");
    let report = run_doctor(&root, DoctorScope::Project).unwrap();
    assert_eq!(report.checks.len(), 2);
    assert_eq!(report.checks[0].name, "project_root");
    assert!(!report.checks[0].ok);
    assert_eq!(report.checks[1].name, "layout_mode");
}

#[test]
fn new_layout_uses_new_gitignore_patterns_and_workspace_yaml_info() {
    let (_tmp, root) = fixture("newl", true);
    let report = run_doctor(&root, DoctorScope::Project).unwrap();
    let names: Vec<&str> = report.checks.iter().map(|c| c.name.as_str()).collect();
    assert!(names.contains(&"workspace_layout_version"));
    assert!(!names.contains(&"workspace_yaml"));
    let lv = report
        .checks
        .iter()
        .find(|c| c.name == "workspace_layout_version")
        .unwrap();
    assert_eq!(lv.detail, "layout_version=2");
    assert!(names.contains(&"gitignore:.cortex/memory/"));
}

#[test]
fn enterprise_scope_requires_org_yaml_and_validates_full_block() {
    let (_tmp, root) = fixture("ent", false);
    let cfg = build_enterprise_org_config(
        "Acme Org",
        cortex_enterprise::models::OrgProfile::SmallCompany,
        true,
        false,
    )
    .unwrap();
    write_enterprise_config(&root, &cfg, None).unwrap();
    // vault-enterprise VACÍO: emite enterprise_vault_markdown (semántica
    // Python: ese check solo aparece sin markdown).
    fs::create_dir_all(root.join("vault-enterprise")).unwrap();

    let report = run_doctor(&root, DoctorScope::Enterprise).unwrap();
    let names: Vec<&str> = report.checks.iter().map(|c| c.name.as_str()).collect();
    for esperado in [
        "enterprise_config",
        "enterprise_config_validation",
        "enterprise_topology",
        "enterprise_vault_dir",
        "enterprise_vault_markdown",
        "enterprise_promotion_allowed_doc_types",
        "enterprise_promotion_dir",
        "enterprise_promotion_records_presence",
        "enterprise_branch_isolation_alignment",
        "enterprise_retrieval_scope",
    ] {
        assert!(names.contains(&esperado), "falta {esperado}");
    }
    let topo = report
        .checks
        .iter()
        .find(|c| c.name == "enterprise_topology")
        .unwrap();
    assert!(topo.detail.starts_with("profile=small-company"));
    // records.jsonl no existe aún → warn.
    let rec = report
        .checks
        .iter()
        .find(|c| c.name == "enterprise_promotion_records_presence")
        .unwrap();
    assert!(!rec.ok && rec.severity == "warn");
}

#[test]
fn native_backend_implements_reporting_seam() {
    use cortex_doctor::native::NativeDoctorBackend;
    use cortex_enterprise::reporting::{DoctorBackend, ReportingScope};

    let (_tmp, root) = fixture("seam", false);
    write_enterprise_config(
        &root,
        &build_enterprise_org_config(
            "Acme Org",
            cortex_enterprise::models::OrgProfile::SmallCompany,
            true,
            false,
        )
        .unwrap(),
        None,
    )
    .unwrap();
    fs::create_dir_all(root.join("vault-enterprise")).unwrap();

    let backend = NativeDoctorBackend::new();
    let view = backend
        .run(&root, cortex_enterprise::reporting::DoctorScope::Enterprise)
        .unwrap();
    assert!(view.checks.iter().any(|c| c.name == "enterprise_config"));

    // Mapeo de scopes.
    let service =
        cortex_enterprise::reporting::EnterpriseReportingService::from_project_root(&root, None)
            .unwrap()
            .with_doctor_backend(NativeDoctorBackend::new());
    let payload = service.build_memory_report(ReportingScope::Local).unwrap();
    assert!(payload.doctor["checks"]
        .as_array()
        .unwrap()
        .iter()
        .all(|c| c["name"] != "enterprise_config"));
}
