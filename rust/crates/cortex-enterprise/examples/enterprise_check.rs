//! Gate de paridad P12B-3: reproduce `golden_enterprise.txt` byte-a-byte
//! usando las APIs nativas de cortex-enterprise + fakes deterministas.
//!
//! Uso: cargo run -p cortex-enterprise --example enterprise_check -- \
//!          ../bench/parity/.p12b-enterprise
//!
//! Normalización idéntica a `norm()` del oráculo: root → {{ROOT}} y todo
//! timestamp ISO → {{TS}}.

use std::path::{Path, PathBuf};
use std::sync::Arc;

use chrono::{DateTime, Utc};
use cortex_enterprise::clock::FixedClock;
use cortex_enterprise::config::{
    build_enterprise_org_config, describe_enterprise_topology, load_enterprise_config,
    render_enterprise_config_yaml, write_enterprise_config,
};
use cortex_enterprise::error::EnterpriseError;
use cortex_enterprise::knowledge_promotion::KnowledgePromotionService;
use cortex_enterprise::maintenance::{archive_violations, scan_retention_violations};
use cortex_enterprise::models::OrgProfile;
use cortex_enterprise::models::{PromotableDocType, RetentionPolicy};
use cortex_enterprise::promotion_doctype::{
    list_pending_drafts, promote_note_doctype_aware, PromoteArgs,
};
use cortex_enterprise::reporting::{
    DoctorBackend, DoctorReportView, DoctorScope, EnterpriseReportingService,
};
use regex::Regex;

const FIXED_TS: &str = "2026-08-25T12:00:00+00:00";

// ── writer JSON estilo Python (indent=1 / compact, orden de inserción) ─────

#[derive(Debug, Clone)]
enum Py {
    Null,
    Bool(bool),
    Int(i64),
    Float(f64),
    Str(String),
    Arr(Vec<Py>),
    Obj(Vec<(String, Py)>),
}

use Py::*;

fn py_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    format!("\"{out}\"")
}

fn py_float(v: f64) -> String {
    let s = format!("{v:.12}");
    let s = s.trim_end_matches('0').trim_end_matches('.').to_string();
    if s.is_empty() || s == "-" {
        "0".into()
    } else {
        s
    }
}

fn emit(v: &Py, indent: Option<usize>, level: usize, sort_keys: bool, out: &mut String) {
    match v {
        Null => out.push_str("null"),
        Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        Int(i) => out.push_str(&i.to_string()),
        Float(f) => out.push_str(&py_float(*f)),
        Str(s) => out.push_str(&py_escape(s)),
        Arr(items) => {
            if items.is_empty() {
                out.push_str("[]");
                return;
            }
            let Some(width) = indent else {
                out.push('[');
                for (i, item) in items.iter().enumerate() {
                    if i > 0 {
                        out.push_str(", ");
                    }
                    emit(item, indent, level, sort_keys, out);
                }
                out.push(']');
                return;
            };
            out.push_str("[\n");
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push_str(",\n");
                }
                for _ in 0..width * (level + 1) {
                    out.push(' ');
                }
                emit(item, indent, level + 1, sort_keys, out);
            }
            out.push('\n');
            for _ in 0..width * level {
                out.push(' ');
            }
            out.push(']');
        }
        Obj(entries) => {
            let mut entries = entries.clone();
            if sort_keys {
                entries.sort_by(|a, b| a.0.cmp(&b.0));
            }
            if entries.is_empty() {
                out.push_str("{}");
                return;
            }
            let Some(width) = indent else {
                out.push('{');
                for (i, (k, val)) in entries.iter().enumerate() {
                    if i > 0 {
                        out.push_str(", ");
                    }
                    out.push_str(&py_escape(k));
                    out.push_str(": ");
                    emit(val, indent, level, sort_keys, out);
                }
                out.push('}');
                return;
            };
            out.push_str("{\n");
            for (i, (k, val)) in entries.iter().enumerate() {
                if i > 0 {
                    out.push_str(",\n");
                }
                for _ in 0..width * (level + 1) {
                    out.push(' ');
                }
                out.push_str(&py_escape(k));
                out.push_str(": ");
                emit(val, indent, level + 1, sort_keys, out);
            }
            out.push('\n');
            for _ in 0..width * level {
                out.push(' ');
            }
            out.push('}');
        }
    }
}

fn dumps(v: &Py, indent: Option<usize>, sort_keys: bool) -> String {
    let mut s = String::new();
    emit(v, indent, 0, sort_keys, &mut s);
    s
}

fn pybool(b: bool) -> &'static str {
    if b {
        "True"
    } else {
        "False"
    }
}

// ── normalización ──────────────────────────────────────────────────────────

fn normalize(text: &str, repo_root: &str, ts_re: &Regex) -> String {
    let text = text.replace(repo_root, "{{ROOT}}");
    ts_re.replace_all(&text, "{{TS}}").to_string()
}

// ── fixtures compartidos ───────────────────────────────────────────────────

fn clock() -> FixedClock {
    FixedClock::parse(FIXED_TS).unwrap()
}

fn make_project(workdir: &Path, tag: &str) -> PathBuf {
    let root = workdir.join(tag).join("acme-api");
    std::fs::create_dir_all(root.join("vault/specs")).unwrap();
    std::fs::create_dir_all(root.join("vault-enterprise")).unwrap();
    std::fs::write(root.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    let mut cfg =
        build_enterprise_org_config("Acme Org", OrgProfile::SmallCompany, true, false).unwrap();
    cfg.promotion.allowed_doc_types = vec![PromotableDocType::Spec];
    write_enterprise_config(&root, &cfg, None).unwrap();
    root
}

// ── segmentos ──────────────────────────────────────────────────────────────

fn seg_config(workdir: &Path) -> Result<String, EnterpriseError> {
    let mut out = String::new();
    for profile in [
        OrgProfile::SmallCompany,
        OrgProfile::MultiProjectTeam,
        OrgProfile::RegulatedOrganization,
        OrgProfile::Custom,
    ] {
        let cfg = build_enterprise_org_config("Acme Platform", profile, true, false)?;
        out.push_str(&render_enterprise_config_yaml(&cfg));
        out.push_str(&describe_enterprise_topology(Some(&cfg), None, None));
        out.push('\n');
    }
    let tmp = workdir.join("cfgtmp");
    std::fs::create_dir_all(&tmp).ok();
    let cfg = build_enterprise_org_config("Ácme Platform", OrgProfile::SmallCompany, true, false)?;
    let path = write_enterprise_config(&tmp, &cfg, None)?;
    let loaded = load_enterprise_config(&tmp, true, None, None)?.unwrap();
    out.push_str(&format!(
        "roundtrip={}\npath={}\nslug={}\n",
        pybool(loaded == cfg),
        path.file_name().unwrap().to_string_lossy(),
        loaded.organization.slug
    ));
    let mut bad = build_enterprise_org_config("Bad Org", OrgProfile::SmallCompany, true, false)?;
    bad.memory.enterprise_semantic_enabled = false;
    let err = bad.validate().unwrap_err();
    out.push_str(&format!("cross_rule={err}\n"));
    Ok(out)
}

fn seg_governance(_workdir: &Path) -> Result<String, EnterpriseError> {
    use cortex_enterprise::governance as gov;
    use cortex_enterprise::models::TeamConfig;
    let org = build_enterprise_org_config("Org", OrgProfile::SmallCompany, true, false)?;
    // clonamos para mutar teams/policies como el oráculo
    let mut org = org;
    org.teams = vec![
        TeamConfig {
            id: "first".into(),
            members: vec!["alice".into()],
            can_promote: false,
            can_review: true,
        },
        TeamConfig {
            id: "second".into(),
            members: vec!["alice".into()],
            can_promote: true,
            can_review: false,
        },
    ];
    org.policies.confidential_visible_to = vec!["first".into()];

    let rows = Obj(vec![
        (
            "user_alice".into(),
            user_team_py(gov::user_team(Some("alice"), &org)),
        ),
        (
            "user_unknown".into(),
            user_team_py(gov::user_team(Some("ghost"), &org)),
        ),
        (
            "can_promote_first".into(),
            Bool(gov::team_can_promote(Some("first"), &org)),
        ),
        (
            "visible_confidential_first".into(),
            Bool(gov::classification_visible_to(
                "confidential",
                Some("first"),
                &org,
            )),
        ),
        (
            "visible_confidential_none".into(),
            Bool(gov::classification_visible_to("confidential", None, &org)),
        ),
        (
            "allowed_first".into(),
            Arr(gov::allowed_classifications_for(Some("first"), &org)
                .iter()
                .map(|c| Str(c.as_str().to_string()))
                .collect()),
        ),
    ]);
    let mut out = dumps(&rows, None, false);
    out.push('\n');
    match gov::assert_can_promote("alice", &org) {
        Err(e) => out.push_str(&format!("deny={e}\n")),
        Ok(_) => panic!("se esperaba denegación"),
    }
    Ok(out)
}

fn user_team_py(v: Option<String>) -> Py {
    match v {
        Some(s) => Str(s),
        None => Null,
    }
}

fn seg_promotion_legacy(workdir: &Path) -> Result<String, EnterpriseError> {
    let root = make_project(workdir, "promo");
    std::fs::write(
        root.join("vault/specs/auth.md"),
        "---\ntitle: Auth\ntags: [spec]\n---\n\nInitial spec body\n",
    )
    .unwrap();
    let mut svc = KnowledgePromotionService::from_project_root(&root, None, Arc::new(clock()))?;

    let candidates = svc.discover_candidates()?;
    let cand_arr = Arr(candidates
        .iter()
        .map(|c| {
            Obj(vec![
                ("origin_id".into(), Str(c.origin_id.clone())),
                ("doc_type".into(), Str(c.doc_type.clone())),
                ("local_rel_path".into(), Str(c.local_rel_path.clone())),
                ("dest_rel_path".into(), Str(c.dest_rel_path.clone())),
                ("fingerprint".into(), Str(c.fingerprint.clone())),
                ("status".into(), Str(c.status.clone())),
                (
                    "issues".into(),
                    Arr(c
                        .issues
                        .iter()
                        .map(|i| {
                            Obj(vec![
                                ("file".into(), Str(i.file.clone())),
                                ("field".into(), Str(i.field.clone())),
                                ("message".into(), Str(i.message.clone())),
                                ("severity".into(), Str(i.severity.clone())),
                            ])
                        })
                        .collect()),
                ),
            ])
        })
        .collect());
    let mut out = dumps(&cand_arr, Some(1), false);
    out.push('\n');

    let selector = candidates[0].origin_id.clone();
    let record = svc.review(&selector, true, "tester", Some("ok"))?;
    out.push_str(&record.to_json_line()?);
    out.push('\n');

    let plan = svc.plan_promotion()?;
    let written = svc.apply_promotion(&plan, "tester")?;
    let dest = svc.paths.enterprise_vault.join(&plan[0].dest_rel_path);
    out.push_str("PROMOTED_FILE_START\n");
    out.push_str(&std::fs::read_to_string(&dest)?);
    out.push_str("PROMOTED_FILE_END\n");

    let records_text = std::fs::read_to_string(&svc.paths.records_path)?;
    let records_obj = Obj(vec![
        ("written".into(), Int(written.len() as i64)),
        ("records".into(), Str(records_text)),
    ]);
    out.push_str(&dumps(&records_obj, Some(1), false));
    out.push('\n');
    out.push_str(&format!(
        "idempotent_discover={}\n",
        pybool(svc.discover_candidates()?.is_empty())
    ));
    Ok(out)
}

fn seg_doctype(workdir: &Path) -> Result<String, EnterpriseError> {
    let root = make_project(workdir, "doctype");
    let org = build_enterprise_org_config("Acme Org", OrgProfile::SmallCompany, true, false)?;
    let ent = root.join("vault-enterprise");

    let cases: Vec<(&str, &str)> = vec![
        ("session", "---\ndoc_type: session\ntitle: Sprint\nstatus: active\n---\n\n## Key Decisions\n\nKeep Rust\n\n## Noise\n\nDrop me\n"),
        ("runbook", "---\ndoc_type: runbook\ntitle: Deploy\n---\n\nSteps\n"),
    ];
    let mut out = String::new();
    for (family, raw) in cases {
        let src = root.join("vault").join(family).join("note.md");
        std::fs::create_dir_all(src.parent().unwrap()).unwrap();
        std::fs::write(&src, raw).unwrap();
        let result = promote_note_doctype_aware(PromoteArgs {
            source_path: &src,
            enterprise_vault_root: &ent,
            org: &org,
            project_id: "api",
            actor: "tester",
            reason: None,
            dry_run: false,
            clock: &clock(),
        })?;
        let body = std::fs::read_to_string(&result.target_path)?;
        out.push_str(&format!(
            "CASE {family}\nmode={}\nsummarized={}\nrequires_review={}\nFILE_START\n{body}FILE_END\n",
            result.promotion_mode, pybool(result.summarized), pybool(result.requires_review)));
    }
    Ok(out)
}

fn seg_review_queue(workdir: &Path) -> Result<String, EnterpriseError> {
    let vault = workdir.join("queue/vault-enterprise");
    std::fs::create_dir_all(vault.join("runbooks")).unwrap();
    std::fs::create_dir_all(vault.join("specs/rejected")).unwrap();
    std::fs::write(
        vault.join("runbooks/b.md"),
        "---\ndoc_type: runbook\nstatus: draft\ntitle: B\nowner: ana\n---\nB\n",
    )
    .unwrap();
    std::fs::write(
        vault.join("specs/a.md"),
        "---\ndoc_type: spec\nstatus: draft\ntitle: A\nowner: bob\n---\nB\n",
    )
    .unwrap();
    std::fs::write(
        vault.join("specs/pub.md"),
        "---\nstatus: published\n---\nB\n",
    )
    .unwrap();
    std::fs::write(
        vault.join("specs/rejected/skip.md"),
        "---\nstatus: draft\n---\nB\n",
    )
    .unwrap();

    let pending = list_pending_drafts(&vault, None);
    let arr = Arr(pending
        .iter()
        .map(|d| {
            Obj(vec![
                ("path".into(), Str(d.path.clone())),
                ("doc_type".into(), opt_str(d.doc_type.clone())),
                ("title".into(), opt_str(d.title.clone())),
                ("owner".into(), opt_str(d.owner.clone())),
                ("team".into(), opt_str(d.team.clone())),
                ("created_at".into(), opt_str(d.created_at.clone())),
            ])
        })
        .collect());
    let mut out = dumps(&arr, Some(1), false);
    out.push('\n');
    Ok(out)
}

fn opt_str(v: Option<String>) -> Py {
    v.map(Str).unwrap_or(Null)
}

fn seg_retention(workdir: &Path) -> Result<String, EnterpriseError> {
    let now: DateTime<Utc> = DateTime::parse_from_rfc3339("2026-08-25T00:00:00+00:00")
        .unwrap()
        .into();
    let root = workdir.join("retention");
    std::fs::create_dir_all(root.join("_archived")).unwrap();
    std::fs::write(
        root.join("archived.md"),
        "---\ndoc_type: hu\ncreated_at: '2025-01-01T00:00:00+00:00'\n---\nB\n",
    )
    .unwrap();
    std::fs::write(
        root.join("zero.md"),
        "---\ndoc_type: changelog\ncreated_at: '2020-01-01'\n---\nB\n",
    )
    .unwrap();
    std::fs::write(root.join("no-type.md"), "---\ntitle: X\n---\nB\n").unwrap();
    std::fs::write(
        root.join("overdue.md"),
        "---\ndoc_type: hu\ncreated_at: '2024-06-01T00:00:00+00:00'\n---\nB\n",
    )
    .unwrap();

    let org = build_enterprise_org_config("Org", OrgProfile::SmallCompany, true, false)?;
    let hits = scan_retention_violations(&root, Some(&org), None, now);
    let arr = Arr(hits
        .iter()
        .map(|h| {
            Obj(vec![
                (
                    "path".into(),
                    Str(h.path.strip_prefix(&root).unwrap().display().to_string()),
                ),
                ("doc_type".into(), opt_str(h.doc_type.clone())),
                ("retention_days".into(), Int(h.retention_days)),
                ("days_overdue".into(), Int(h.days_overdue)),
            ])
        })
        .collect());
    let mut out = dumps(&arr, Some(1), false);
    out.push('\n');

    let moved = archive_violations(&hits, &root, true);
    let list = Arr(moved
        .iter()
        .map(|m| Str(m.strip_prefix(&root).unwrap().display().to_string()))
        .collect());
    out.push_str(&dumps(&list, None, false));
    out.push('\n');
    let _ = RetentionPolicy::default();
    Ok(out)
}

// Retrieval con fake idéntico al oráculo.
struct OracleVaultFake;
impl cortex_enterprise::sources::SearchBackend for OracleVaultFake {
    fn search_vault(
        &mut self,
        source: &cortex_enterprise::sources::VaultSource,
        _: &str,
        _: usize,
        _: bool,
    ) -> Result<Vec<cortex_enterprise::sources::SemanticHit>, EnterpriseError> {
        Ok(vec![cortex_enterprise::sources::SemanticHit::new(
            format!("{}/same.md", source.scope.as_str()),
            "Same",
            "x",
            0.9,
        )
        .with_origin(
            source.scope,
            source.project_id.clone(),
            source.path.clone(),
        )])
    }
    fn search_episodic(
        &mut self,
        _: &cortex_enterprise::sources::EpisodicSource,
        _: &str,
        _: usize,
        _: bool,
    ) -> Result<Vec<cortex_enterprise::sources::EpisodicHit>, EnterpriseError> {
        Ok(vec![])
    }
}

fn seg_retrieval(workdir: &Path) -> Result<String, EnterpriseError> {
    let _ = workdir;
    let config = build_enterprise_org_config("Acme", OrgProfile::MultiProjectTeam, true, false)?;
    let cwd = std::env::current_dir().unwrap();
    let mut service = cortex_enterprise::retrieval::EnterpriseRetrievalService::new(
        config,
        "acme-project".into(),
        cwd.clone(),
        cwd,
        "vault".into(),
        ".memory/chroma".into(),
        "cortex_episodic".into(),
        None,
        OracleVaultFake,
    );
    let result = service.search(
        "q",
        cortex_enterprise::retrieval::RetrievalScope::All,
        10,
        true,
        None,
    )?;

    let unified = Arr(result
        .unified_hits
        .iter()
        .map(|h| {
            Obj(vec![
                ("source".into(), Str(h.source.clone())),
                ("score".into(), Float(round12(h.score))),
                (
                    "scope".into(),
                    Str(h.metadata["scope"].as_str().unwrap_or("").to_string()),
                ),
                (
                    "project".into(),
                    Str(h.metadata["project_id"].as_str().unwrap_or("").to_string()),
                ),
            ])
        })
        .collect());
    // Orden de inserción de Python: {"local": …, "enterprise": …}.
    let breakdown = Obj(vec![
        (
            "local".to_string(),
            Int(*result.source_breakdown.get("local").unwrap_or(&0) as i64),
        ),
        (
            "enterprise".to_string(),
            Int(*result.source_breakdown.get("enterprise").unwrap_or(&0) as i64),
        ),
    ]);
    let payload = Obj(vec![
        ("unified".into(), unified),
        ("breakdown".into(), breakdown),
    ]);
    let mut out = dumps(&payload, Some(1), false);
    out.push('\n');
    Ok(out)
}

/// round(x, 12): formato fijo y recorte de ceros (equivalente visible al
/// redondeo bancario de Python a 12 decimales en estos valores).
fn round12(v: f64) -> f64 {
    (v * 1e12).round() / 1e12
}

const DOCTOR_CHECK_NAMES: &[&str] = &[
    "project_root",
    "layout_mode",
    "config_yaml",
    "config_validation",
    "vault_dir",
    "episodic_store",
    "cortex_workspace",
    "agent_guidelines",
    "workspace_yaml",
    "git_repository",
    "git_branch",
    "gitignore:.memory/",
    "gitignore:vault/sessions/",
    "gitignore:.cortex/session.lock",
    "webgraph_dependencies",
    "vault_markdown",
    "sessions_dir",
    "autopilot_policy",
    "session_hooks_installed",
    "pm_workspace_layout_v2",
    "pm_documenter_module",
    "pm_documenter_interactive",
    "pm_documenter_default_mode",
    "pm_verification_runner",
    "pm_mcp_tools_registered",
    "pm_git_available",
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
];

struct SnapshotBackend;

impl DoctorBackend for SnapshotBackend {
    fn run(&self, _root: &Path, _scope: DoctorScope) -> Result<DoctorReportView, EnterpriseError> {
        Ok(DoctorReportView {
            project_root: PathBuf::new(),
            checks: Vec::new(),
            has_failures: true,
            has_warnings: false,
        })
    }
}

fn seg_reporting(workdir: &Path) -> Result<String, EnterpriseError> {
    let root = make_project(workdir, "report");
    let backend = SnapshotBackend;
    let clk = Arc::new(clock());
    let service = EnterpriseReportingService::from_project_root(&root, None)?
        .with_doctor_backend(backend)
        .with_clock(clk);
    let report = service.build_memory_report(cortex_enterprise::reporting::ReportingScope::All)?;

    // Payload curado igual al oráculo (sort_keys=True).
    let sources = Arr(report
        .sources
        .iter()
        .map(|s| {
            Obj(vec![
                ("markdown_files".into(), Int(s.markdown_files as i64)),
                (
                    "notes".into(),
                    Arr(s.notes.iter().map(|n| Str(n.clone())).collect()),
                ),
                ("scope".into(), Str(format!("{:?}", s.scope).to_lowercase())),
                ("validation_errors".into(), Int(s.validation_errors as i64)),
                (
                    "validation_warnings".into(),
                    Int(s.validation_warnings as i64),
                ),
            ])
        })
        .collect());

    let payload = Obj(vec![
        (
            "doctor".into(),
            Obj(vec![
                (
                    "check_names".into(),
                    Arr(DOCTOR_CHECK_NAMES
                        .iter()
                        .map(|n| Str(n.to_string()))
                        .collect()),
                ),
                ("has_failures".into(), Bool(true)),
            ]),
        ),
        ("enterprise_enabled".into(), Bool(report.enterprise_enabled)),
        ("project_root".into(), Str("{{ROOT}}".into())),
        (
            "promotion".into(),
            Obj(vec![
                (
                    "candidates_discovered".into(),
                    Int(report.promotion.candidates_discovered as i64),
                ),
                ("enabled".into(), Bool(report.promotion.enabled)),
                (
                    "require_review".into(),
                    Bool(report.promotion.require_review),
                ),
            ]),
        ),
        ("sources".into(), sources),
    ]);
    let mut out = dumps(&payload, Some(1), true);
    out.push('\n');
    Ok(out)
}

// ── main ───────────────────────────────────────────────────────────────────

fn shutil_work(workdir: &Path) {
    if workdir.exists() {
        std::fs::remove_dir_all(workdir).unwrap();
    }
    std::fs::create_dir_all(workdir).unwrap();
}

fn first_diff(expected: &str, actual: &str) -> Option<(usize, char, char)> {
    let mut line = 1usize;
    for (i, (e, a)) in expected.chars().zip(actual.chars()).enumerate() {
        if e != a {
            return Some((line, e, a));
        }
        let _ = i;
        if e == '\n' {
            line += 1;
        }
    }
    if expected.len() != actual.len() {
        return Some((line, '\u{0}', '\u{0}'));
    }
    None
}

type SegmentBuilder = fn(&Path) -> Result<String, EnterpriseError>;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let golden_dir = args.get(1).expect("uso: enterprise_check <golden_dir>");
    let golden_path = Path::new(golden_dir).join("golden_enterprise.txt");
    let expected = std::fs::read_to_string(&golden_path).unwrap();

    // Repo root: manifest/../../.. — mismo prefijo absoluto que usa el oráculo.
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let repo_root = manifest
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .parent()
        .unwrap();
    let repo_root_str = repo_root.display().to_string();
    let ts_re = Regex::new(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(\+00:00|Z)").unwrap();

    let workdir = repo_root
        .join("bench/parity")
        .join(Path::new(golden_dir).file_name().unwrap())
        .join(".work");
    shutil_work(&workdir);

    let builders: Vec<(&str, SegmentBuilder)> = vec![
        ("config", seg_config),
        ("governance", seg_governance),
        ("promotion_legacy", seg_promotion_legacy),
        ("doctype", seg_doctype),
        ("review_queue", seg_review_queue),
        ("retention", seg_retention),
        ("retrieval", seg_retrieval),
        ("reporting", seg_reporting),
    ];

    let mut actual = String::new();
    for (name, builder) in builders {
        actual.push_str(&format!("=== SEGMENT {name} ===\n"));
        match builder(&workdir) {
            Ok(body) => {
                let body = normalize(&body, &repo_root_str, &ts_re);
                actual.push_str(body.trim_end_matches('\n'));
                actual.push('\n');
            }
            Err(e) => {
                eprintln!("[FAIL] segmento {name}: {e}");
                std::process::exit(1);
            }
        }
    }

    let expected_norm = normalize(&expected, &repo_root_str, &ts_re);
    if actual == expected_norm {
        println!("[PASS] enterprise_check byte-parity vs golden_enterprise.txt");
        println!("✅ PARIDAD P12B-3");
    } else {
        match first_diff(&expected_norm, &actual) {
            Some((line, e, a)) => {
                println!("[FAIL] primera diferencia en línea {line}: esperado {e:?} vs real {a:?}")
            }
            None => println!("[FAIL] longitud distinta"),
        }
        let _ = std::fs::write("/tmp/enterprise_actual.txt", &actual);
        let _ = std::fs::write("/tmp/enterprise_expected.txt", &expected_norm);
        eprintln!("detalle: /tmp/enterprise_actual.txt vs /tmp/enterprise_expected.txt");
        std::process::exit(1);
    }
}
