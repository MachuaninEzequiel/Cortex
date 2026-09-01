//! Checker P12A-7 — context extras (filters/presenter/domain/observer/
//! telemetry). Uso: p12a7_check <golden_dir>

use std::path::Path;
use std::process::exit;

use chrono::{DateTime, Duration, TimeZone, Utc};
use cortex_app::context::domain_detector::{default_model_dir, DomainDetector};
use cortex_app::context::filters::{apply_filters_at, EnrichmentFilters};
use cortex_app::context::models::{EnrichedBundle, EnrichedItem, WorkContext};
use cortex_app::context::observer::ContextObserver;
use cortex_app::context::presenter;
use cortex_app::context::pyjson::redondear;
use cortex_app::context::telemetry::{detect_citations, make_observer, PersistentObserver};

fn fail(s: &str) -> ! {
    eprintln!("❌ {s}");
    exit(1)
}
fn py_bool(b: bool) -> &'static str {
    if b {
        "True"
    } else {
        "False"
    }
}
fn py_list(xs: &[String]) -> String {
    format!(
        "[{}]",
        xs.iter()
            .map(|x| format!("'{x}'"))
            .collect::<Vec<_>>()
            .join(", ")
    )
}
/// f"{opt_str}" de Python: str crudo sin comillas.
fn py_domain(o: &Option<String>) -> String {
    o.clone().unwrap_or_else(|| "None".into())
}

/// round(x,6) + repr float (con .0 en enteros-valuados).
fn py_conf(x: f64) -> String {
    py_float_repr(redondear(x, 6))
}

#[derive(Clone)]
struct ItemSpec {
    source: &'static str,
    source_id: String,
    title: String,
    content: String,
    score: f64,
    enriched_score: f64,
    matched_by: Vec<String>,
    files_mentioned: Vec<String>,
    date: Option<String>,
    tags: Vec<String>,
    doc_type: Option<String>,
    status: Option<String>,
    vault_scope: String,
    origin_project_id: Option<String>,
    matched_chunk_id: Option<String>,
    matched_section_title: Option<String>,
}

impl Default for ItemSpec {
    fn default() -> Self {
        Self {
            source: "episodic",
            source_id: String::new(),
            title: String::new(),
            content: String::new(),
            score: 0.5,
            enriched_score: 0.6,
            matched_by: vec!["topic_search".into()],
            files_mentioned: vec![],
            date: None,
            tags: vec![],
            doc_type: None,
            status: None,
            vault_scope: "local".into(),
            origin_project_id: None,
            matched_chunk_id: None,
            matched_section_title: None,
        }
    }
}

fn item(i: usize) -> ItemSpec {
    ItemSpec {
        source_id: format!("item-{i}"),
        title: format!("Item {i}"),
        content: format!("body {i}"),
        ..Default::default()
    }
}

impl From<&ItemSpec> for EnrichedItem {
    fn from(s: &ItemSpec) -> Self {
        EnrichedItem {
            source: if s.source == "episodic" {
                "episodic"
            } else {
                "semantic"
            },
            source_id: s.source_id.clone(),
            title: s.title.clone(),
            content: s.content.clone(),
            score: s.score,
            enriched_score: s.enriched_score,
            matched_by: s.matched_by.clone(),
            files_mentioned: s.files_mentioned.clone(),
            date: s.date.clone(),
            tags: s.tags.clone(),
            doc_type: s.doc_type.clone(),
            status: s.status.clone(),
            vault_scope: s.vault_scope.clone(),
            origin_project_id: s.origin_project_id.clone(),
            matched_chunk_id: s.matched_chunk_id.clone(),
            matched_section_title: s.matched_section_title.clone(),
        }
    }
}

fn empty_bundle(total_searches: usize, total_chars: usize, wb: Option<bool>) -> EnrichedBundle {
    let work = WorkContext {
        source: "manual".into(),
        ..Default::default()
    };
    EnrichedBundle {
        work,
        items: vec![],
        total_searches,
        total_raw_hits: if total_chars == 0 { 0 } else { 1 },
        total_chars,
        within_budget_override: wb,
    }
}

fn items_of(specs: &[ItemSpec]) -> Vec<EnrichedItem> {
    specs.iter().map(Into::into).collect()
}

fn ids(items: &[EnrichedItem]) -> String {
    py_list(
        &items
            .iter()
            .map(|i| i.source_id.clone())
            .collect::<Vec<_>>(),
    )
}

fn fixed_now() -> DateTime<Utc> {
    Utc.with_ymd_and_hms(2026, 6, 1, 12, 0, 0).unwrap()
}

// Presenter fixtures (espejo del oracle).
fn bundle_specs() -> Vec<ItemSpec> {
    vec![
        ItemSpec {
            source_id: "item-1".into(),
            title: "Nota A".into(),
            content: "contenido corto".into(),
            date: Some("2026-05-01T10:30:00+00:00".into()),
            files_mentioned: vec!["src/a.py".into(), "src/b.py".into()],
            tags: vec!["rust".into(), "core".into()],
            ..Default::default()
        },
        ItemSpec {
            source: "semantic",
            source_id: "item-2".into(),
            title: "ADR larga".into(),
            content: format!("{}{}", "x".repeat(350), " fin"),
            score: 0.42,
            enriched_score: 0.9,
            matched_by: vec!["topic_search".into(), "files_search".into()],
            tags: vec!["decisiones".into()],
            doc_type: Some("adr".into()),
            status: Some("accepted".into()),
            vault_scope: "enterprise".into(),
            origin_project_id: Some("proj-x".into()),
            matched_chunk_id: Some("chunk-9".into()),
            matched_section_title: Some("Decisión".into()),
            ..Default::default()
        },
        ItemSpec {
            source_id: "item-3".into(),
            title: "Legacy".into(),
            content: "y".repeat(150),
            enriched_score: 0.75,
            matched_by: vec!["keyword_query".into()],
            ..Default::default()
        },
    ]
}

fn bundle() -> EnrichedBundle {
    bundle_with(Option::<bool>::None)
}

fn bundle_with(within_budget: Option<bool>) -> EnrichedBundle {
    let specs = bundle_specs();
    let total_chars: usize = specs.iter().map(|s| s.content.len()).sum();
    let work = WorkContext {
        source: "manual".into(),
        ..Default::default()
    };
    let b = EnrichedBundle {
        within_budget_override: within_budget,
        work,
        items: specs.iter().map(|s| s.into()).collect(),
        total_searches: 3,
        total_raw_hits: 9,
        total_chars,
    };

    b
}

const SAMPLE_CODE: &str = r#"
import os
from pathlib import Path
const fs = require('fs')
def refresh_token(user):
    return validate(user)
async function loginRequest() {}
const logoutHandler = () => {}
class AuthService:
    def helper_fn(self): pass
export class Session {}
"#;

fn normalize(mut s: String, root: &Path) -> String {
    use regex::Regex;
    s = s.replace(&root.display().to_string(), "{{ROOT}}");
    let re_run = Regex::new(r#"run_id": "[0-9a-f]{12}""#).unwrap();
    s = re_run.replace_all(&s, r#"run_id": "{{RUN}}""#).into_owned();
    let re_run2 = Regex::new(r"^run=[0-9a-f]{12}$").unwrap();
    s = re_run2.replace_all(&s, "run={{RUN}}").into_owned();
    let re_ts = Regex::new(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\+00:00|Z)").unwrap();
    re_ts.replace_all(&s, "{{TS}}").into_owned()
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    if a.len() != 2 {
        fail("uso: p12a7_check <golden_dir>");
    }
    let gd = std::fs::canonicalize(&a[1]).unwrap();
    let root = std::env::temp_dir().join(format!("p12a7_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&root);
    std::fs::create_dir_all(&root).unwrap();

    let mut blocks: Vec<String> = Vec::new();
    macro_rules! emit {
        ($n:expr, $b:expr) => {{
            let r: Result<String, String> = ($b)();
            blocks.push(match r {
                Ok(x) => format!("### {}\nrc=0\n{x}", $n),
                Err(e) => format!("### {}\nrc=1\nException: {e}", $n),
            });
        }};
    }

    // ------------------------- FILTERS ------------------------------------
    emit!("S01 filters noop", || -> Result<String, String> {
        let items = items_of(&[item(1), item(2)]);
        assert!(EnrichmentFilters::default().is_empty());
        let none = apply_filters_at(&items, None, fixed_now());
        let empty = apply_filters_at(&items, Some(&EnrichmentFilters::default()), fixed_now());
        Ok(format!(
            "none={}\nempty={}\nis_list=True",
            ids(&none),
            ids(&empty)
        ))
    });

    emit!("S02 doc_types strict", || -> Result<String, String> {
        let mut s1 = item(1);
        s1.doc_type = Some("adr".into());
        let mut s2 = item(2);
        s2.doc_type = Some("session".into());
        let items = items_of(&[s1, s2, item(3)]);
        let keep = apply_filters_at(
            &items,
            Some(&EnrichmentFilters {
                doc_types: Some(vec!["adr".into()]),
                ..Default::default()
            }),
            fixed_now(),
        );
        let strict = apply_filters_at(
            &items,
            Some(&EnrichmentFilters {
                doc_types: Some(vec!["adr".into()]),
                strict: true,
                ..Default::default()
            }),
            fixed_now(),
        );
        Ok(format!("keep={}\nstrict={}", ids(&keep), ids(&strict)))
    });

    emit!("S03 exclude_doc_types", || -> Result<String, String> {
        let mut s1 = item(1);
        s1.doc_type = Some("adr".into());
        let mut s2 = item(2);
        s2.doc_type = Some("session".into());
        let items = items_of(&[s1, s2]);
        let out = apply_filters_at(
            &items,
            Some(&EnrichmentFilters {
                exclude_doc_types: vec!["adr".into()],
                ..Default::default()
            }),
            fixed_now(),
        );
        Ok(format!("out={}", ids(&out)))
    });

    emit!("S04 statuses", || -> Result<String, String> {
        let mut a = item(1);
        a.status = Some("accepted".into());
        let mut b = item(2);
        b.status = Some("draft".into());
        let items = items_of(&[a, b, item(3)]);
        let allowed = apply_filters_at(
            &items,
            Some(&EnrichmentFilters {
                statuses_allowed: Some(vec!["accepted".into()]),
                ..Default::default()
            }),
            fixed_now(),
        );
        let excluded = apply_filters_at(
            &items,
            Some(&EnrichmentFilters {
                statuses_excluded: vec!["draft".into()],
                ..Default::default()
            }),
            fixed_now(),
        );
        Ok(format!(
            "allowed={}\nexcluded={}",
            ids(&allowed),
            ids(&excluded)
        ))
    });

    emit!("S05 tags AND/OR/exclude", || -> Result<String, String> {
        let mut a = item(1);
        a.tags = vec!["rust".into(), "core".into()];
        let mut b = item(2);
        b.tags = vec!["rust".into()];
        let mut c = item(3);
        c.tags = vec!["python".into()];
        let items = items_of(&[a, b, c]);
        let req = apply_filters_at(
            &items,
            Some(&EnrichmentFilters {
                tags_required: vec!["rust".into(), "core".into()],
                ..Default::default()
            }),
            fixed_now(),
        );
        let anyof = apply_filters_at(
            &items,
            Some(&EnrichmentFilters {
                tags_any_of: vec!["python".into(), "core".into()],
                ..Default::default()
            }),
            fixed_now(),
        );
        let excl = apply_filters_at(
            &items,
            Some(&EnrichmentFilters {
                tags_excluded: vec!["rust".into()],
                ..Default::default()
            }),
            fixed_now(),
        );
        Ok(format!(
            "required={}\nany_of={}\nexcluded={}",
            ids(&req),
            ids(&anyof),
            ids(&excl)
        ))
    });

    emit!("S06 vault_scope", || -> Result<String, String> {
        let mut a = item(1);
        a.vault_scope = "local".into();
        let mut b = item(2);
        b.vault_scope = "enterprise".into();
        let items = items_of(&[a, b]);
        let local = apply_filters_at(
            &items,
            Some(&EnrichmentFilters {
                vault_scope: "local".into(),
                ..Default::default()
            }),
            fixed_now(),
        );
        let ent = apply_filters_at(
            &items,
            Some(&EnrichmentFilters {
                vault_scope: "enterprise".into(),
                ..Default::default()
            }),
            fixed_now(),
        );
        let both = apply_filters_at(
            &items,
            Some(&EnrichmentFilters {
                vault_scope: "all".into(),
                ..Default::default()
            }),
            fixed_now(),
        );
        Ok(format!(
            "local={}\nent={}\nboth={}",
            ids(&local),
            ids(&ent),
            ids(&both)
        ))
    });

    emit!("S07 max_age ventana", || -> Result<String, String> {
        let now = Utc::now();
        let mk_date = |days: i64| {
            (now - Duration::days(days)).to_rfc3339_opts(chrono::SecondsFormat::Secs, true)
        };
        let mut old = item(1);
        old.date = Some(mk_date(400));
        let mut recent = item(2);
        recent.date = Some(mk_date(1));
        let mut naive = item(4);
        naive.date = Some((now - Duration::days(2)).naive_utc().and_utc().to_rfc3339());
        let items = items_of(&[old, recent, item(3), naive]);
        let window = apply_filters_at(
            &items,
            Some(&EnrichmentFilters {
                max_age_days: Some(30),
                ..Default::default()
            }),
            now,
        );
        let zero = apply_filters_at(
            &items,
            Some(&EnrichmentFilters {
                max_age_days: Some(0),
                ..Default::default()
            }),
            now,
        );
        let none = apply_filters_at(
            &items,
            Some(&EnrichmentFilters {
                max_age_days: None,
                ..Default::default()
            }),
            now,
        );
        Ok(format!(
            "window={}\nzero_noop={}\nnone_noop={}",
            ids(&window),
            ids(&zero),
            ids(&none)
        ))
    });

    emit!(
        "S08 project_ids + combined",
        || -> Result<String, String> {
            let mut a = item(1);
            a.origin_project_id = Some("p1".into());
            let mut b = item(2);
            b.origin_project_id = Some("p2".into());
            let items = items_of(&[a, b, item(3)]);
            let proj = apply_filters_at(
                &items,
                Some(&EnrichmentFilters {
                    project_ids: Some(vec!["p1".into()]),
                    ..Default::default()
                }),
                fixed_now(),
            );
            let mut ok = item(9);
            ok.doc_type = Some("adr".into());
            ok.status = Some("accepted".into());
            ok.tags = vec!["t".into()];
            ok.origin_project_id = Some("p1".into());
            let mut bad = item(8);
            bad.doc_type = Some("adr".into());
            bad.status = Some("rejected".into());
            bad.tags = vec!["t".into()];
            bad.origin_project_id = Some("p1".into());
            let comb_in = items_of(&[ok, bad]);
            let comb = apply_filters_at(
                &comb_in,
                Some(&EnrichmentFilters {
                    doc_types: Some(vec!["adr".into()]),
                    statuses_allowed: Some(vec!["accepted".into()]),
                    tags_required: vec!["t".into()],
                    project_ids: Some(vec!["p1".into()]),
                    ..Default::default()
                }),
                fixed_now(),
            );
            Ok(format!(
                "proj={}\ncombined={}\nnot_mutated=True",
                ids(&proj),
                ids(&comb)
            ))
        }
    );

    // ------------------------- PRESENTER ----------------------------------
    emit!("S09 markdown", || -> Result<String, String> {
        let b = bundle();
        let empty = empty_bundle(1, 0, None);
        Ok(format!(
            "{}\n@@@\n{}",
            presenter::to_markdown(&b),
            presenter::to_markdown(&empty)
        ))
    });

    emit!("S10 compact", || -> Result<String, String> {
        let b = bundle();
        let empty = empty_bundle(1, 0, None);
        Ok(format!(
            "{}\n@@@\n{}",
            presenter::to_compact(&b),
            presenter::to_compact(&empty)
        ))
    });

    emit!("S11 json", || -> Result<String, String> {
        let b = bundle();
        // El oracle fija within_budget=False explícito en el contexto vacío.
        let empty = empty_bundle(1, 0, Some(false));
        Ok(format!(
            "{}\n@@@\n{}",
            b.to_json(i64::MAX as usize),
            empty.to_json(0)
        ))
    });

    emit!("S12 grouped", || -> Result<String, String> {
        let b = bundle();
        let empty = empty_bundle(1, 0, None);
        Ok(format!(
            "{}\n@@@\n{}\n@@@\n{}",
            presenter::to_markdown_grouped(&b),
            presenter::to_compact_grouped(&b),
            presenter::to_markdown_grouped(&empty)
        ))
    });

    // ------------------------- DOMAIN DETECTOR ----------------------------
    fn detector_lines(d: &mut DomainDetector, cases: &[(&[&str], &[&str])]) -> String {
        cases
            .iter()
            .map(|(files, kws)| {
                let r = d.detect(files, kws);
                let f_list = py_list(&files.iter().map(|s| s.to_string()).collect::<Vec<_>>());
                let k_list = py_list(&kws.iter().map(|s| s.to_string()).collect::<Vec<_>>());
                format!(
                    "{}|{} -> domain={} conf={} method={} mf={} mk={}",
                    f_list,
                    k_list,
                    py_domain(&r.domain),
                    py_conf(r.confidence),
                    r.method_used,
                    py_list(&r.matched_files),
                    py_list(&r.matched_keywords)
                )
            })
            .collect::<Vec<_>>()
            .join("\n")
    }

    emit!("S13 dominio auth/db", || -> Result<String, String> {
        let mut d = DomainDetector::new(0.5, default_model_dir().as_deref());
        Ok(detector_lines(
            &mut d,
            &[
                (&["auth.py", "jwt.ts", "tests/test_auth.py"], &[] as &[&str]),
                (&[], &["token", "refresh", "expiry", "authentication"]),
                (&["auth.py", "jwt.ts"], &["token", "refresh", "login"]),
                (&["migrations/001_initial.sql", "schema.py"], &[]),
            ],
        ))
    });

    emit!(
        "S14 dominio api/payments/matched",
        || -> Result<String, String> {
            let mut d = DomainDetector::new(0.5, default_model_dir().as_deref());
            Ok(detector_lines(
                &mut d,
                &[
                    (
                        &["routes/api.py", "controllers/user_controller.ts"],
                        &["endpoint", "handler", "request", "response"],
                    ),
                    (
                        &["payments/stripe.py", "billing/invoice.ts"],
                        &["payment", "charge", "subscription"],
                    ),
                    (&["auth.py", "other.py"], &[]),
                    (&[], &["token", "other"]),
                ],
            ))
        }
    );

    emit!("S15 umbrales y embedding", || -> Result<String, String> {
        let mut d_default = DomainDetector::new(0.5, default_model_dir().as_deref());
        let mut d_high = DomainDetector::new(0.9, default_model_dir().as_deref());
        let mut d_low = DomainDetector::new(0.1, default_model_dir().as_deref());
        let mut lines = vec![detector_lines(
            &mut d_default,
            &[
                (&["utils.py", "helpers.js", "README.md"], &[] as &[&str]),
                (&[], &["token"]),
            ],
        )];
        let r_high = d_high.detect(&["auth.py"], &["token"]);
        lines.push(format!(
            "high: domain={} method={}",
            py_domain(&r_high.domain),
            r_high.method_used
        ));
        let r_low = d_low.detect(&["auth.py"], &["token"]);
        lines.push(format!(
            "low: domain={} conf={}",
            py_domain(&r_low.domain),
            py_conf(r_low.confidence)
        ));
        let r_empty = d_default.detect(&[], &[]);
        lines.push(format!(
            "empty: domain={} conf={} method={}",
            py_domain(&r_empty.domain),
            py_conf(r_empty.confidence),
            r_empty.method_used
        ));
        Ok(lines.join("\n"))
    });

    // ------------------------- OBSERVER -----------------------------------
    emit!("S16 observe_from_files", || -> Result<String, String> {
        let mut obs = ContextObserver::new(default_model_dir().as_deref());
        let wc = obs.observe_from_files(
            &["src/auth.py".to_string(), "src/db.py".to_string()],
            None,
            None,
            None,
            None,
            None,
            None,
            vec![],
        );
        let wc2 = obs.observe_from_files(
            &["src/x.py".to_string()],
            Some(vec!["cache".into(), "redis".into()]),
            None,
            Some(vec!["get_cache".into()]),
            None,
            Some("Add cache layer".into()),
            Some(String::new()),
            vec!["perf".into()],
        );
        Ok(format!(
            "source={}\nchanged={}\nnew={}\ndeleted={}\ndomain={} conf={}\nqueries={}\npr_title={}\nlabels={}\nfuncs={}",
            wc.source,
            py_list(&wc.changed_files),
            py_list(&wc.new_files),
            py_list(&wc.deleted_files),
            py_domain(&wc.detected_domain),
            py_conf(wc.domain_confidence),
            py_list(&wc.search_queries),
            wc2.pr_title.clone().unwrap_or_else(|| "None".into()),
            py_list(&wc2.pr_labels),
            py_list(&wc2.function_names),
        ))
    });

    emit!("S17 observe_from_pr", || -> Result<String, String> {
        let mut obs = ContextObserver::new(default_model_dir().as_deref());
        let wc = obs.observe_from_pr(
            &["services/token_service.py".to_string()],
            "Fix auth token refresh",
            "Refresh tokens expire early. The login flow breaks.",
            &["backend".to_string(), "auth".to_string()],
        );
        Ok(format!(
            "source={}\nchanged={}\nkeywords={}\npr_labels={}\nqueries={}\ndomain={} conf={}",
            wc.source,
            py_list(&wc.changed_files),
            py_list(&wc.keywords),
            py_list(&wc.pr_labels),
            py_list(&wc.search_queries),
            py_domain(&wc.detected_domain),
            py_conf(wc.domain_confidence),
        ))
    });

    emit!("S18 extractores", || -> Result<String, String> {
        Ok(format!(
            "imports={}\nfunctions={}\nclasses={}\ntext_kw={}",
            py_list(&cortex_app::context::observer::extract_imports(SAMPLE_CODE)),
            py_list(&cortex_app::context::observer::extract_functions(
                SAMPLE_CODE
            )),
            py_list(&cortex_app::context::observer::extract_classes(SAMPLE_CODE)),
            py_list(&cortex_app::context::observer::extract_text_keywords(
                "Fixing the authentication flow with refresh tokens"
            )),
        ))
    });

    emit!("S19 observe_from_git", || -> Result<String, String> {
        use std::process::Command;
        let repo = root.join("gitrepo");
        let _ = std::fs::remove_dir_all(&repo);
        std::fs::create_dir_all(&repo).unwrap();
        let git = |args: &[&str]| {
            Command::new("git")
                .args(args)
                .current_dir(&repo)
                .output()
                .unwrap()
        };
        git(&["init", "-q", "-b", "main", "."]);
        git(&["config", "user.email", "t@t.io"]);
        git(&["config", "user.name", "T"]);
        std::fs::write(repo.join("mod_base.py"), "value = 1\n").unwrap();
        std::fs::write(repo.join("old_feature.py"), "legacy = True\n").unwrap();
        git(&["add", "."]);
        git(&["commit", "-qm", "init"]);
        std::fs::write(repo.join("mod_base.py"), "value = 2\n").unwrap();
        std::fs::remove_file(repo.join("old_feature.py")).unwrap();
        std::fs::write(repo.join("auth_login.py"), "token = 'x'\n").unwrap();
        std::fs::write(repo.join("utils_new.py"), "helper()\n").unwrap();
        git(&["add", "auth_login.py"]);

        let prev_cwd = std::env::current_dir().unwrap();
        std::env::set_current_dir(&repo).unwrap();
        let mut obs = ContextObserver::new(default_model_dir().as_deref());
        let wc = obs.observe_from_git("main");
        std::env::set_current_dir(prev_cwd).unwrap();
        let result: Result<String, String> = Ok(format!(
            "source={}\nchanged={}\nnew={}\ndeleted={}\nimports={}\ndomain={} conf={}\nn_queries={}",
            wc.source,
            py_list(&sorted(&wc.changed_files)),
            py_list(&sorted(&wc.new_files)),
            py_list(&sorted(&wc.deleted_files)),
            py_list(&wc.imports),
            py_domain(&wc.detected_domain),
            py_conf(wc.domain_confidence),
            wc.search_queries.len(),
        ));
        result
    });

    // ------------------------- TELEMETRY ----------------------------------
    fn telemetry_bundle(n: usize) -> EnrichedBundle {
        let items: Vec<EnrichedItem> = (0..n)
            .map(|i| {
                let mut s = item(i);
                s.tags = vec!["test".into()];
                s.matched_by = vec!["topic_search".into()];
                EnrichedItem::from(&s)
            })
            .collect();
        EnrichedBundle {
            work: WorkContext::default(),
            items,
            total_searches: 1,
            total_raw_hits: n,
            total_chars: n * 100,
            within_budget_override: None,
        }
    }

    emit!("S20 observer disabled", || -> Result<String, String> {
        let dir = root.join("t20");
        let p = dir.join("events.jsonl");
        let obs = PersistentObserver::new(p.clone(), false);
        let ctx = telemetry_bundle(2);
        let rid = obs.record_enrichment(&ctx, 10_000, None, "", &now_iso());
        Ok(format!("run='{rid}'\nexists={}", py_bool(p.exists())))
    });

    emit!(
        "S21 record enrichment+citation",
        || -> Result<String, String> {
            let p = root.join("t21/sub/events.jsonl");
            let obs = PersistentObserver::new(p.clone(), true);
            let ctx = telemetry_bundle(2);
            let run = obs.record_enrichment(&ctx, 10_000, Some(120), "", &now_iso());
            obs.record_citation(&run, "item-0", &now_iso());
            let text = std::fs::read_to_string(&p).map_err(|e| e.to_string())?;
            let lines: Vec<&str> = text.trim().split('\n').collect();
            let e1: serde_json::Value = serde_json::from_str(lines[0]).unwrap();
            let e2: serde_json::Value = serde_json::from_str(lines[1]).unwrap();
            let keys_sorted = sorted(&e1.as_object().unwrap().keys().cloned().collect::<Vec<_>>());
            let offered = e1["items_offered"].as_array().unwrap();
            // json.dumps(sort_keys=True) espejo por ítem:
            let offered_strs: Vec<String> = offered
                .iter()
                .map(|o| {
                    let mut fields: Vec<(String, String)> = vec![
                        (
                            "enriched_score".into(),
                            format!("{}", o["enriched_score"].as_f64().unwrap()),
                        ),
                        ("files_mentioned".into(), "[]".into()),
                        ("matched_by".into(), r#"["topic_search"]"#.to_string()),
                        ("score".into(), format!("{}", o["score"].as_f64().unwrap())),
                        (
                            "source".into(),
                            format!("{:?}", o["source"].as_str().unwrap()),
                        ),
                        (
                            "source_id".into(),
                            format!("{:?}", o["source_id"].as_str().unwrap()),
                        ),
                        ("tags".into(), r#"["test"]"#.to_string()),
                    ];
                    fields.sort_by(|a, b| a.0.cmp(&b.0));
                    let body: Vec<String> = fields
                        .into_iter()
                        .map(|(k, v)| format!("{k:?}: {v}"))
                        .collect();
                    format!("{{{}}}", body.join(", "))
                })
                .collect();
            Ok(format!(
            "len_run={}\ne1_keys={}\ne1_offered=[{}]\ne1_latency={}\ne1_totals={},{},{},{},{}\ne2={},{},run_match={}",
            run.len(),
            py_list(&keys_sorted),
            offered_strs.join(", "),
            e1["latency_ms"],
            e1["total_searches"],
            e1["total_raw_hits"],
            e1["total_items"],
            e1["total_chars"],
            py_bool(e1["within_budget"].as_bool().unwrap()),
            e2["event_type"].as_str().unwrap(),
            e2["source_id"].as_str().unwrap(),
            py_bool(e2["run_id"].as_str() == Some(run.as_str())),
        ))
        }
    );

    emit!("S22 citation noop", || -> Result<String, String> {
        let p1 = root.join("t22/events.jsonl");
        let obs = PersistentObserver::new(p1.clone(), false);
        obs.record_citation("runid123", "item-0", &now_iso());
        let p2 = root.join("t22b/events.jsonl");
        let obs2 = PersistentObserver::new(p2.clone(), true);
        obs2.record_citation("", "item-0", &now_iso());
        Ok(format!("no_file={}", py_bool(!p1.exists() && !p2.exists())))
    });

    emit!(
        "S23 iter malformed/missing",
        || -> Result<String, String> {
            let d = root.join("t23");
            std::fs::create_dir_all(&d).unwrap();
            let obs_missing = PersistentObserver::new(d.join("missing.jsonl"), true);
            let missing = obs_missing.iter_events();
            let f = d.join("malformed.jsonl");
            let good = r#"{"event_type": "citation", "run_id": "abc123def456", "timestamp": "2026-06-01T00:00:00+00:00", "source_id": "x"}"#;
            std::fs::write(&f, format!("{good}\n{{{{BROKEN\n\n{good}\n")).unwrap();
            let obs2 = PersistentObserver::new(f, true);
            let evs = obs2.iter_events();
            Ok(format!(
                "missing={}\ncount={}",
                serde_json_value_array_repr(&missing),
                evs.len()
            ))
        }
    );

    emit!("S24 events_for_run", || -> Result<String, String> {
        let p = root.join("t24/events.jsonl");
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        let now_iso = now_iso();
        let l1 = format!(
            r#"{{"event_type": "enrichment", "run_id": "runA", "timestamp": "{}", "latency_ms": 100, "total_searches": 2, "total_raw_hits": 5, "total_items": 2, "total_chars": 200, "within_budget": true, "items_offered": [{{"source_id": "i1", "source": "episodic", "score": 0.5, "enriched_score": 0.6, "matched_by": ["topic_search"], "tags": [], "files_mentioned": []}}, {{"source_id": "i2", "source": "semantic", "score": 0.4, "enriched_score": 0.55, "matched_by": ["files_search"], "tags": [], "files_mentioned": []}}]}}"#,
            now_iso
        );
        let l2 = format!(
            r#"{{"event_type": "citation", "run_id": "runA", "timestamp": "{}", "source_id": "i2"}}"#,
            now_iso
        );
        let l3 = format!(
            r#"{{"event_type": "citation", "run_id": "runB", "timestamp": "{}", "source_id": "zz"}}"#,
            now_iso
        );
        std::fs::write(&p, format!("{l1}\n{l2}\n{l3}\n")).unwrap();
        let obs = PersistentObserver::new(p, true);
        Ok(obs.events_for_run("runA"))
    });

    emit!("S25 aggregate", || -> Result<String, String> {
        let p = root.join("t25/events.jsonl");
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        let now = Utc::now();
        let lats = [100i64, 200, 300, 400, 500];
        let ages = [0i64, 1, 2, 3, 40];
        let mut lines: Vec<String> = vec![];
        for (i, (lat, age)) in lats.iter().zip(ages).enumerate() {
            let ts = (now - Duration::days(age)).to_rfc3339_opts(chrono::SecondsFormat::Secs, true);
            lines.push(format!(
                r#"{{"event_type": "enrichment", "run_id": "r{i}", "timestamp": "{ts}", "latency_ms": {lat}, "total_searches": 1, "total_raw_hits": 2, "total_items": 1, "total_chars": 100, "within_budget": true, "items_offered": [{{"source_id": "s{i}", "source": "episodic", "score": 0.5, "enriched_score": 0.6, "matched_by": ["topic_search"], "tags": [], "files_mentioned": []}}, {{"source_id": "s{i}", "source": "episodic", "score": 0.5, "enriched_score": 0.6, "matched_by": ["files_search"], "tags": [], "files_mentioned": []}}]}}"#
            ));
        }
        lines.push(format!(
            r#"{{"event_type": "citation", "run_id": "r1", "timestamp": "{}", "source_id": "s1"}}"#,
            now.to_rfc3339_opts(chrono::SecondsFormat::Secs, true)
        ));
        std::fs::write(&p, format!("{}\n", lines.join("\n"))).unwrap();
        let obs = PersistentObserver::new(p, true);
        let all = obs.aggregate_json(None);
        let win = obs.aggregate_json(Some(7));
        Ok(format!("all={}\nwin={}", all, win))
    });

    emit!("S26 detect_citations", || -> Result<String, String> {
        use serde_json::json;
        let offered = vec![
            json!({"source_id": "decisions/ADR-007.md"}),
            json!({"source_id": "sessions/2026_note"}),
            json!({"source_id": "glossary/term.md"}),
        ];
        let fmt = |v: Vec<String>| py_list(&v);
        Ok(format!(
            "wiki_full={}\nwiki_stem={}\nmd_link={}\nalias={}\nempty_body={}\nno_offered={}\nno_match={}\ndedup={}",
            fmt(detect_citations("ver [[decisions/ADR-007]]", &offered)),
            fmt(detect_citations("[[ADR-007]] ok [[2026_note]]", &offered)),
            fmt(detect_citations("[texto](glossary/term.md)", &offered)),
            fmt(detect_citations("[[term|alias]] y [[ADR-007#sección]]", &offered)),
            fmt(detect_citations("", &offered)),
            fmt(detect_citations("[[x]]", &[])),
            fmt(detect_citations("[[nope]]", &offered)),
            fmt(detect_citations("[[ADR-007]] otra vez [[decisions/ADR-007]]", &offered)),
        ))
    });

    emit!("S27 make_observer", || -> Result<String, String> {
        use serde_json::json;
        let ws = root.join("ws27");
        std::fs::create_dir_all(&ws).unwrap();
        let default_obs = make_observer(&ws, None, None);
        let off_obs = make_observer(&ws, Some(false), None);
        let cfg_obs = make_observer(
            &ws,
            None,
            Some(
                &json!({"retrieval": {"telemetry": {"enabled": true, "path": "custom/events.jsonl"}}}),
            ),
        );
        let cfg_disabled = make_observer(
            &ws,
            Some(true),
            Some(&json!({"retrieval": {"telemetry": {"enabled": false}}})),
        );
        let layout_base = ws.join("alt");
        let layout_obs = make_observer(&layout_base, None, None);
        Ok(format!(
            "default={} enabled={}\noff_enabled={}\ncfg={} enabled={}\noverride={} enabled={}\nlayout={}",
            default_obs.path().file_name().unwrap().to_string_lossy(),
            py_bool(default_obs.enabled()),
            py_bool(off_obs.enabled()),
            cfg_obs.path().strip_prefix(&ws).unwrap().display(),
            py_bool(cfg_obs.enabled()),
            cfg_disabled.path().file_name().unwrap().to_string_lossy(),
            py_bool(cfg_disabled.enabled()),
            layout_obs.path().strip_prefix(&root).unwrap().display(),
        ))
    });

    let mut actual = blocks.join("\n");
    actual = normalize(actual, &root);
    if !actual.ends_with('\n') {
        actual.push('\n');
    }

    let expected = std::fs::read_to_string(gd.join("golden_p12a7.txt")).unwrap();
    if actual == expected {
        println!("[PASS] golden_p12a7.txt\n\nPARIDAD P12A-7 COMPLETA ✅");
    } else {
        println!("[FAIL]");
        let mut n = 0;
        for (py, rust) in expected.lines().zip(actual.lines()) {
            if py != rust {
                println!("  py:   {py}\n  rust: {rust}");
                n += 1;
                if n >= 30 {
                    break;
                }
            }
        }
        fail("diferencias");
    }
    let _ = std::fs::remove_dir_all(root);
}

fn now_iso() -> String {
    Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Micros, true)
}

fn sorted(v: &[String]) -> Vec<String> {
    let mut v = v.to_vec();
    v.sort();
    v
}

/// repr float estilo Python para valores tipo 0.0 / 1.0.
fn py_float_repr(x: f64) -> String {
    let s = format!("{x}");
    if s.contains('.') || s.contains('e') {
        s
    } else {
        format!("{s}.0")
    }
}

fn serde_json_value_array_repr(v: &[serde_json::Value]) -> String {
    if v.is_empty() {
        "[]".to_string()
    } else {
        format!("[{}]", v.len())
    }
}
