use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

use cortex_enterprise::clock::FixedClock;
use cortex_enterprise::config::{build_enterprise_org_config, write_enterprise_config};
use cortex_enterprise::models::OrgProfile;
use cortex_enterprise::reporting::{
    DoctorBackend, DoctorCheckView, DoctorReportView, DoctorScope, EnterpriseReportingService,
    ReportingScope,
};

const TS: &str = "2026-08-25T12:00:00+00:00";

fn fixture_root(tag: &str) -> (tempfile::TempDir, PathBuf) {
    let tmp = tempfile::tempdir_in(std::env::temp_dir()).unwrap();
    let root = tmp.path().join(tag);
    std::fs::create_dir_all(&root).unwrap();
    std::fs::write(root.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    std::fs::create_dir_all(root.join("vault/specs")).unwrap();
    std::fs::write(root.join("vault/specs/spec.md"), "# Spec\n").unwrap();
    let cfg = build_enterprise_org_config("Acme", OrgProfile::SmallCompany, true, false).unwrap();
    write_enterprise_config(&root, &cfg, None).unwrap();
    std::fs::create_dir_all(root.join("vault-enterprise")).unwrap();
    std::fs::write(
        root.join("vault-enterprise/README.md"),
        "---\ntitle: E\ntags: [x]\n---\n\nE\n",
    )
    .unwrap();
    (tmp, root)
}

/// Snapshot estático con checks reales estilo doctor Python.
struct StaticBackend {
    report: DoctorReportView,
    calls: Arc<AtomicUsize>,
}

impl DoctorBackend for StaticBackend {
    fn run(
        &self,
        _root: &Path,
        _scope: DoctorScope,
    ) -> Result<DoctorReportView, cortex_enterprise::error::EnterpriseError> {
        self.calls.fetch_add(1, Ordering::SeqCst);
        Ok(self.report.clone())
    }
}

fn real_style_checks(root: &Path) -> Vec<DoctorCheckView> {
    vec![
        DoctorCheckView {
            name: "project_root".into(),
            ok: true,
            severity: "fail".into(),
            detail: root.display().to_string(),
        },
        DoctorCheckView {
            name: "vault_validation_errors".into(),
            ok: true,
            severity: "fail".into(),
            detail: "0 error(s) across 2 file(s)".into(),
        },
        DoctorCheckView {
            name: "vault_validation_warnings".into(),
            ok: false,
            severity: "warn".into(),
            detail: "2 warning(s) across 2 file(s)".into(),
        },
        DoctorCheckView {
            name: "enterprise_vault_validation_errors".into(),
            ok: true,
            severity: "fail".into(),
            detail: "0 error(s) across 1 file(s)".into(),
        },
        DoctorCheckView {
            name: "enterprise_vault_validation_warnings".into(),
            ok: true,
            severity: "warn".into(),
            detail: "0 warning(s) across 1 file(s)".into(),
        },
    ]
}

#[test]
fn all_scope_calls_doctor_once_and_reports_both_vaults() {
    let (tmp, root) = fixture_root("all");
    let calls = Arc::new(AtomicUsize::new(0));
    let backend = StaticBackend {
        report: DoctorReportView {
            project_root: root.clone(),
            checks: real_style_checks(&root),
            has_failures: false,
            has_warnings: false,
        },
        calls: calls.clone(),
    };
    let clk = FixedClock::parse(TS).unwrap();
    let service = EnterpriseReportingService::from_project_root(&root, None)
        .unwrap()
        .with_doctor_backend(backend)
        .with_clock(Arc::new(clk));
    let report = service.build_memory_report(ReportingScope::All).unwrap();

    assert_eq!(calls.load(Ordering::SeqCst), 1, "doctor se ejecuta UNA vez");
    assert_eq!(report.sources.len(), 2);
    assert_eq!(report.sources[0].scope, ReportingScope::Local);
    assert_eq!(report.sources[1].scope, ReportingScope::Enterprise);
    // Conteos extraídos del detail textual.
    assert_eq!(report.sources[0].validation_errors, 0);
    assert_eq!(report.sources[0].validation_warnings, 2);
    assert_eq!(report.sources[1].validation_errors, 0);
    assert_eq!(report.sources[1].markdown_files, 1);
    assert_eq!(report.generated_at, TS);
    assert_eq!(report.doctor["has_failures"], serde_json::json!(false));

    drop(tmp);
}

#[test]
fn default_backend_fails_explicitly() {
    let (_tmp, root) = fixture_root("def");
    let service = EnterpriseReportingService::from_project_root(&root, None).unwrap();
    let err = service
        .build_memory_report(ReportingScope::Local)
        .unwrap_err();
    assert_eq!(err.to_string(), "doctor backend unavailable until P12B-4");
}

#[test]
fn local_scope_uses_project_doctor_and_single_source() {
    let (tmp, root) = fixture_root("loc");
    let calls = Arc::new(AtomicUsize::new(0));
    let backend = StaticBackend {
        report: DoctorReportView {
            project_root: root.clone(),
            checks: real_style_checks(&root),
            has_failures: false,
            has_warnings: false,
        },
        calls: calls.clone(),
    };
    let service = EnterpriseReportingService::from_project_root(&root, None)
        .unwrap()
        .with_doctor_backend(backend);
    let report = service.build_memory_report(ReportingScope::Local).unwrap();
    assert_eq!(calls.load(Ordering::SeqCst), 1);
    assert_eq!(report.sources.len(), 1);
    assert!(!report.promotion.enabled, "promotion es enterprise-only");

    drop(tmp);
}

#[test]
fn promotion_disabled_reports_enabled_false_with_require_review() {
    let (tmp, root) = fixture_root("promo");
    let mut cfg = cortex_enterprise::config::load_enterprise_config(&root, true, None, None)
        .unwrap()
        .unwrap();
    cfg.promotion.enabled = false;
    write_enterprise_config(&root, &cfg, None).unwrap();

    let backend = StaticBackend {
        report: DoctorReportView {
            project_root: root.clone(),
            checks: vec![],
            has_failures: false,
            has_warnings: false,
        },
        calls: Arc::new(AtomicUsize::new(0)),
    };
    let service = EnterpriseReportingService::from_project_root(&root, None)
        .unwrap()
        .with_doctor_backend(backend);
    let report = service
        .build_memory_report(ReportingScope::Enterprise)
        .unwrap();
    assert!(!report.promotion.enabled);
    assert_eq!(
        report.promotion.require_review,
        cfg.promotion.require_review
    );

    drop(tmp);
}
