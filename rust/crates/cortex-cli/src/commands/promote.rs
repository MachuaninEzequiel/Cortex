//! `cortex promote-knowledge` — puerto de cli/main.py::promote_knowledge.

use std::path::Path;

use clap::Parser;

use crate::paths::{expand_user, python_resolve};
use crate::pyjson::{Num, PyVal};

#[derive(Parser, Debug)]
#[command(
    name = "promote-knowledge",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct PromoteArgs {
    /// Absolute path to the target project root (where .cortex/org.yaml lives).
    #[arg(long)]
    pub project_root: Option<String>,

    /// Dry-run by default. Use --apply to execute promotion.
    #[arg(long, overrides_with = "apply", default_value_t = true)]
    pub dry_run: bool,

    /// Use --apply to execute promotion.
    #[arg(long)]
    pub apply: bool,

    /// Actor name for audit records (default: current OS user).
    #[arg(long)]
    pub actor: Option<String>,

    /// Output raw JSON payload (plan + results).
    #[arg(long)]
    pub json: bool,
}

pub fn run(tokens: &[String]) -> bool {
    let args = PromoteArgs::parse_from(
        std::iter::once("promote".to_string()).chain(tokens.iter().cloned()),
    );
    let dry_run = if args.apply { false } else { args.dry_run };
    std::process::exit(execute(
        args.project_root.as_deref(),
        dry_run,
        args.actor.as_deref(),
        args.json,
    ));
}

fn current_os_user() -> String {
    // getpass.getuser(): LOGNAME → USER → LNAME → USERNAME.
    for key in ["LOGNAME", "USER", "LNAME", "USERNAME"] {
        if let Ok(v) = std::env::var(key) {
            if !v.is_empty() {
                return v;
            }
        }
    }
    "unknown".to_string()
}

fn resolve(raw: Option<&str>) -> std::path::PathBuf {
    match raw {
        Some(p) => python_resolve(&expand_user(Path::new(p))),
        None => python_resolve(&std::env::current_dir().unwrap_or_default()),
    }
}

fn candidate_pyval(c: &cortex_enterprise::promotion_models::PromotionCandidate) -> PyVal {
    use crate::pyjson::PyVal as V;
    V::obj(vec![
        ("origin_id", V::s(&c.origin_id)),
        ("doc_type", V::s(&c.doc_type)),
        ("local_rel_path", V::s(&c.local_rel_path)),
        ("local_abs_path", V::s(&c.local_abs_path)),
        ("dest_rel_path", V::s(&c.dest_rel_path)),
        ("fingerprint", V::s(&c.fingerprint)),
        ("status", V::s(&c.status)),
        ("issues", V::Arr(c.issues.iter().map(issue_pyval).collect())),
        (
            "metadata",
            V::Obj(
                c.metadata
                    .iter()
                    .map(|(k, v)| (k.clone(), json_to_pyval(v)))
                    .collect(),
            ),
        ),
    ])
}

fn issue_pyval(i: &cortex_enterprise::promotion_models::PromotionIssue) -> PyVal {
    use crate::pyjson::PyVal as V;
    V::obj(vec![
        ("file", V::s(&i.file)),
        ("field", V::s(&i.field)),
        ("message", V::s(&i.message)),
        ("severity", V::s(&i.severity)),
    ])
}

fn json_to_pyval(v: &serde_json::Value) -> PyVal {
    use crate::pyjson::PyVal as V;
    match v {
        serde_json::Value::Null => V::Null,
        serde_json::Value::Bool(b) => V::Bool(*b),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                V::Num(Num::Int(i))
            } else {
                V::Num(Num::Float(n.as_f64().unwrap_or(0.0)))
            }
        }
        serde_json::Value::String(s) => V::s(s),
        serde_json::Value::Array(items) => V::Arr(items.iter().map(json_to_pyval).collect()),
        serde_json::Value::Object(map) => {
            // BTreeMap ⇒ orden alfabético; solo metadata libre cae acá.
            V::Obj(
                map.iter()
                    .map(|(k, v)| (k.clone(), json_to_pyval(v)))
                    .collect(),
            )
        }
    }
}

pub fn execute(
    project_root: Option<&str>,
    dry_run: bool,
    actor: Option<&str>,
    json_output: bool,
) -> i32 {
    let root = resolve(project_root);
    let actor_name = actor.map(str::to_string).unwrap_or_else(current_os_user);
    let layout = cortex_workspace::WorkspaceLayout::discover(&root);

    let mut service =
        match cortex_enterprise::knowledge_promotion::KnowledgePromotionService::from_project_root(
            &root,
            Some(layout),
            std::sync::Arc::new(cortex_enterprise::clock::SystemClock),
        ) {
            Ok(svc) => svc,
            Err(err) => {
                eprintln!("{err}");
                return 1;
            }
        };

    let plan = match service.plan_promotion() {
        Ok(plan) => plan,
        Err(err) => {
            eprintln!("{err}");
            return 1;
        }
    };

    let enterprise_vault = service.paths.enterprise_vault.display().to_string();
    let mut payload = PyVal::obj(vec![
        ("project_root", PyVal::s(root.display().to_string())),
        ("enterprise_vault", PyVal::s(enterprise_vault.clone())),
        ("dry_run", PyVal::Bool(dry_run)),
        (
            "planned",
            PyVal::Arr(plan.iter().map(candidate_pyval).collect()),
        ),
    ]);

    if dry_run {
        if json_output {
            println!("{}", crate::pyjson::stdlib_dumps_indent2(&payload));
            return 0;
        }
        if plan.is_empty() {
            println!("No reviewed candidates ready for promotion.");
            return 0;
        }
        println!("Planned promotions: {}", plan.len());
        for c in &plan {
            println!(
                "  - {} -> {}  ({})",
                c.local_rel_path, c.dest_rel_path, c.origin_id
            );
        }
        return 0;
    }

    let written = match service.apply_promotion(&plan, &actor_name) {
        Ok(w) => w,
        Err(err) => {
            eprintln!("{err}");
            return 1;
        }
    };

    if let PyVal::Obj(items) = &mut payload {
        items.push((
            "written".to_string(),
            PyVal::Arr(written.iter().map(record_pyval).collect()),
        ));
    }

    if json_output {
        println!("{}", crate::pyjson::stdlib_dumps_indent2(&payload));
        return 0;
    }

    println!(
        "Promoted {} document(s) into {enterprise_vault}",
        written.len()
    );
    for r in &written {
        println!(
            "  - {} -> {}  ({})",
            r.local_rel_path, r.dest_rel_path, r.origin_id
        );
    }
    0
}

fn record_pyval(r: &cortex_enterprise::promotion_models::PromotionRecord) -> PyVal {
    // model_dump(mode="json") en orden de declaración.
    use crate::pyjson::PyVal as V;
    let decision = r.decision.as_ref().map(|d| {
        V::obj(vec![
            ("decision", V::s(d.decision.as_str())),
            ("actor", V::s(&d.actor)),
            ("decided_at", V::s(&d.decided_at)),
            ("reason", d.reason.as_ref().map(V::s).unwrap_or(V::Null)),
        ])
    });
    let events: Vec<PyVal> = r
        .events
        .iter()
        .map(|e| {
            V::obj(vec![
                ("event", V::s(e.event.as_str())),
                ("at", V::s(&e.at)),
                ("actor", e.actor.as_ref().map(V::s).unwrap_or(V::Null)),
                (
                    "payload",
                    PyVal::Obj(
                        e.payload
                            .iter()
                            .map(|(k, v)| (k.clone(), json_to_pyval(v)))
                            .collect(),
                    ),
                ),
            ])
        })
        .collect();

    let decision_val = match (&r.decision, decision) {
        (_, Some(d)) => d,
        (None, _) => PyVal::Null,
        (Some(_), None) => unreachable!(),
    };
    PyVal::obj(vec![
        ("origin_id", V::s(&r.origin_id)),
        ("local_rel_path", V::s(&r.local_rel_path)),
        ("doc_type", V::s(&r.doc_type)),
        ("dest_rel_path", V::s(&r.dest_rel_path)),
        ("fingerprint", V::s(&r.fingerprint)),
        ("status", V::s(r.status.as_str())),
        ("created_at", V::s(&r.created_at)),
        ("updated_at", V::s(&r.updated_at)),
        ("decision", decision_val),
        ("events", PyVal::Arr(events)),
    ])
}
