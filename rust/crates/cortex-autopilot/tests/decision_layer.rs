use std::sync::Arc;

use chrono::{DateTime, Utc};
use cortex_autopilot::config::load_autopilot_config;
use cortex_autopilot::detectors::AutopilotDetector;
use cortex_autopilot::detectors::{
    resolve_detectors, AmbiguousRequestDetector, CodeChangeDetector, DocsOnlyDetector,
    LargeRefactorDetector, NoopDetector, QuestionOnlyDetector, SecuritySensitiveDetector,
};
use cortex_autopilot::models::DetectionRequest;
use cortex_autopilot::policies::{
    AutopilotMode, AutopilotPolicy, EnforcementSeverity, PolicyEnforcer,
};
use cortex_autopilot::session_models::{Checkpoint, CheckpointSource, SessionRecord};
use cortex_workspace::WorkspaceLayout;

fn request(user: Option<&str>, files: &[&str]) -> DetectionRequest {
    DetectionRequest {
        user_request: user.map(str::to_string),
        changed_files: files.iter().map(|s| s.to_string()).collect(),
        git_diff_stat: None,
        session_state: None,
    }
}

fn checkpoint(ts: &str, artifacts: &[&str], verified: &[&str]) -> Checkpoint {
    Checkpoint {
        timestamp: DateTime::parse_from_rfc3339(ts)
            .unwrap()
            .with_timezone(&Utc),
        source: CheckpointSource::CortexSync,
        verified_claims: verified.iter().map(|s| s.to_string()).collect(),
        unverified_claims: vec![],
        artifacts_touched: artifacts.iter().map(|s| s.to_string()).collect(),
        note: String::new(),
    }
}

fn session_with(checkpoints: Vec<Checkpoint>) -> SessionRecord {
    let mut s = SessionRecord::minimal("2026-08-25_demo");
    s.checkpoints = checkpoints;
    s
}

// ── detectors ───────────────────────────────────────────────────────────

#[test]
fn detectors_match_python_results() {
    let code = CodeChangeDetector
        .detect(&request(None, &["a.rs", "b.rs"]))
        .unwrap();
    assert_eq!(code.task_type, "fast-code");
    assert_eq!(code.confidence, 0.7);
    assert_eq!(code.reason, "2 code files changed");

    // Solo los archivos con EXTENSIÓN de código cuentan (4 pasados, 1 .rs).
    let deep = CodeChangeDetector
        .detect(&request(None, &["a", "b", "c", "d.rs"]))
        .unwrap();
    assert_eq!(deep.task_type, "fast-code");
    assert_eq!(deep.reason, "1 code files changed");

    let docs = DocsOnlyDetector
        .detect(&request(None, &["a.md", "b.rst"]))
        .unwrap();
    assert_eq!(docs.task_type, "docs-only");
    assert_eq!(docs.reason, "Only documentation files changed (2)");

    let q = QuestionOnlyDetector
        .detect(&request(Some("how to test?"), &[]))
        .unwrap();
    assert_eq!(q.task_type, "question-only");
    assert_eq!(q.confidence, 0.75);

    let sec_file = SecuritySensitiveDetector
        .detect(&request(None, &["src/auth/login.py"]))
        .unwrap();
    assert_eq!(sec_file.task_type, "security");
    assert_eq!(sec_file.confidence, 0.8);

    let large = LargeRefactorDetector
        .detect(&request(None, &["1", "2", "3", "4", "5"]))
        .unwrap();
    assert_eq!(large.reason, "5 files changed — large scope");

    let amb = AmbiguousRequestDetector
        .detect(&request(Some("mejorar cosas"), &[]))
        .unwrap();
    assert_eq!(
        amb.reason,
        "Short request (2 words) with vague verb, no file references"
    );

    let noop = NoopDetector.detect(&request(None, &[])).unwrap();
    assert_eq!(noop.task_type, "noop");
}

#[test]
fn resolve_detectors_rules_match_python() {
    // Security override >0.5 gana aunque otro tenga más confianza.
    let all = cortex_autopilot::detectors::default_detectors();
    let res = resolve_detectors(&all, &request(Some("password hash"), &[]));
    assert_eq!(res.task_type, "security");

    // Ambiguous (0.7>0.6) bloquea antes del tie-break: "refactor" es verbo
    // vago, la petición es corta y no menciona archivos.
    let res = resolve_detectors(&all, &request(Some("refactor auth"), &["a.rs", "b.rs"]));
    assert_eq!(res.task_type, "ambiguous");

    // Sin candidatos >0.3: fallback al de mayor confianza (docs keyword).
    let only_noop: Vec<Box<dyn AutopilotDetector>> = vec![Box::new(NoopDetector)];
    let res = resolve_detectors(&only_noop, &request(None, &[]));
    assert_eq!(res.reason, "Noop fallback");
}

// ── config ──────────────────────────────────────────────────────────────

#[test]
fn config_defaults_and_parse_error_match_python() {
    let tmp = tempfile::tempdir().unwrap();
    let layout = WorkspaceLayout::discover(tmp.path());
    std::fs::create_dir_all(&layout.workspace_root).unwrap();
    let cfg = load_autopilot_config(&layout).unwrap();
    assert_eq!(cfg.mode, "assist");
    assert_eq!(cfg.default_budget_profile, "fast_code");
    assert!(!cfg.enable_hooks);

    std::fs::write(layout.workspace_root.join("autopilot.yaml"), "{[}\n").unwrap();
    let err = load_autopilot_config(&layout).unwrap_err();
    assert!(err
        .to_string()
        .starts_with("Failed to parse autopilot config: "));
}

// ── policies ────────────────────────────────────────────────────────────

const TS: &str = "2026-08-25T12:00:00+00:00";

fn fixed_clock() -> Arc<dyn cortex_enterprise::clock::Clock> {
    Arc::new(cortex_enterprise::clock::FixedClock::parse(TS).unwrap())
}

fn enforcer(mode: AutopilotMode) -> PolicyEnforcer {
    PolicyEnforcer::new(
        AutopilotPolicy::from_config_values(mode.as_str(), "fast_code", 5, 10, fixed_clock())
            .unwrap(),
    )
}

#[test]
fn policy_defaults_from_config_and_validation() {
    let p =
        AutopilotPolicy::from_config_values("assist", "fast_code", 5, 10, fixed_clock()).unwrap();
    assert_eq!(p.mode, AutopilotMode::Assist);
    assert!(!p.pre_commit_verification);
    assert!(p.out_of_scope_warning);

    // autopilot activa pre-commit; thresholds clamp a >=1.
    let p = AutopilotPolicy::from_config_values("autopilot", "fast_code", 0, 10, fixed_clock())
        .unwrap();
    assert!(p.pre_commit_verification);
    assert_eq!(p.auto_checkpoint_threshold_files, 1);

    // Typos caen a defaults seguros (nunca fallan en from_config).
    let p = AutopilotPolicy::from_config_values("auto", "nope", 5, 10, fixed_clock()).unwrap();
    assert_eq!(p.mode, AutopilotMode::Assist);
    assert_eq!(p.budget_profile, "fast_code");

    // Construcción directa SÍ valida (mensaje exacto de __post_init__).
    let err = AutopilotPolicy::new(
        AutopilotMode::Observe,
        "malo".into(),
        false,
        false,
        5,
        10,
        fixed_clock(),
    )
    .unwrap_err();
    assert_eq!(
        err.to_string(),
        "unknown budget_profile 'malo'; must be one of [\"deep_code\", \"docs_only\", \"fast_code\", \"finish_only\", \"question_only\"]"
    );

    let err = AutopilotPolicy::new(
        AutopilotMode::Observe,
        "fast_code".into(),
        false,
        false,
        0,
        10,
        fixed_clock(),
    )
    .unwrap_err();
    assert_eq!(
        err.to_string(),
        "auto_checkpoint_threshold_files must be >= 1, got 0"
    );
}

use cortex_enterprise::clock::{Clock, SystemClock};
#[allow(dead_code)]
fn system_clock() -> Arc<dyn Clock> {
    Arc::new(SystemClock)
}

#[test]
fn enforcer_hooks_match_python_texts() {
    // on_session_open: keyword de seguridad con summary.
    let e = enforcer(AutopilotMode::Assist);
    let mut s = session_with(vec![]);
    s.spec_summary = "rotate the jwt token".into();
    let results = e.on_session_open(&s, None);
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].severity, EnforcementSeverity::Warn);
    assert!(results[0]
        .reason
        .starts_with("Spec summary mentions security-sensitive terms"));
    assert!(results[0].allowed());

    // Observe ⇒ sin warnings.
    let obs = enforcer(AutopilotMode::Observe);
    assert!(obs.on_session_open(&s, None).is_empty());

    // on_checkpoint: drift fuera de scope.
    let cp = checkpoint("2026-08-25T11:59:00+00:00", &["out/x.md"], &[]);
    let results = e.on_checkpoint(&s, &cp, Some(&["in/a.md".to_string()]));
    assert!(results.iter().any(|r| r
        .reason
        .starts_with("Checkpoint touches files outside spec scope: [\"out/x.md\"]")));

    // on_pre_close: autopilot sin verificado ⇒ BLOCK.
    let ap = enforcer(AutopilotMode::Autopilot);
    let empty = session_with(vec![]);
    let results = ap.on_pre_close(&empty);
    assert_eq!(results[0].severity, EnforcementSeverity::Block);
    assert!(results[0]
        .reason
        .contains("requires at least one checkpoint with verified"));
    assert!(!results[0].allowed());
}
