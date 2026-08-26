//! `cortex review-knowledge` — puerto de cortex/cli/review_knowledge.py.

use std::path::Path;

use clap::Parser;

use crate::paths::{expand_user, python_resolve};
use crate::pyjson::PyVal;

fn resolve(raw: Option<&str>) -> std::path::PathBuf {
    match raw {
        Some(p) => python_resolve(&expand_user(Path::new(p))),
        None => python_resolve(&std::env::current_dir().unwrap_or_default()),
    }
}

fn current_os_user() -> String {
    for key in ["LOGNAME", "USER", "LNAME", "USERNAME"] {
        if let Ok(v) = std::env::var(key) {
            if !v.is_empty() {
                return v;
            }
        }
    }
    "unknown".to_string()
}

#[derive(Parser, Debug)]
#[command(
    name = "review-knowledge",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct ReviewArgs {
    #[command(subcommand)]
    pub cmd: ReviewCmd,
}

#[derive(clap::Subcommand, Debug)]
pub enum ReviewCmd {
    /// List enterprise notes awaiting promotion review (status: draft).
    Pending {
        /// Filter by doc_type (repeat to allow multiple).
        #[arg(long = "doc-type")]
        doc_type: Vec<String>,
        /// Project root containing .cortex/ (defaults to cwd).
        #[arg(long)]
        project_root: Option<String>,
        /// Emit JSON instead of a table.
        #[arg(long)]
        json: bool,
    },
    /// Promote a draft note to status: accepted and append an audit_trail entry.
    Approve {
        /// Vault-relative path to the draft note.
        path: String,
        /// Reviewer name for the audit_trail (default: current OS user).
        #[arg(long)]
        reviewer: Option<String>,
        /// Optional rationale.
        #[arg(long, default_value = "")]
        reason: String,
        /// Project root containing .cortex/ (defaults to cwd).
        #[arg(long)]
        project_root: Option<String>,
    },
    /// Reject a draft note. Default: move to rejected/. With --delete: remove.
    Reject {
        /// Vault-relative path to the draft note.
        path: String,
        /// Reviewer name for the audit_trail (default: current OS user).
        #[arg(long)]
        reviewer: Option<String>,
        /// Required rationale for the rejection.
        #[arg(long)]
        reason: String,
        /// Permanently delete instead of moving the note to rejected/.
        #[arg(long)]
        delete: bool,
        /// Project root containing .cortex/ (defaults to cwd).
        #[arg(long)]
        project_root: Option<String>,
    },
    /// Legacy candidate review (KnowledgePromotionService JSONL records).
    Candidate {
        /// Candidate selector: origin_id or vault-relative path.
        selector: String,
        /// Approve by default. Use --reject to reject a candidate.
        #[arg(long, overrides_with = "reject", default_value_t = true)]
        approve: bool,
        /// Use --reject to reject a candidate.
        #[arg(long)]
        reject: bool,
        /// Actor name for audit records (default: current OS user).
        #[arg(long)]
        actor: Option<String>,
        /// Optional rationale for approve/reject.
        #[arg(long)]
        reason: Option<String>,
        /// Project root containing .cortex/org.yaml.
        #[arg(long)]
        project_root: Option<String>,
        /// Output raw JSON record.
        #[arg(long)]
        json: bool,
    },
}

pub fn run(tokens: &[String]) -> bool {
    let args = ReviewArgs::parse_from(
        std::iter::once("review-knowledge".to_string()).chain(tokens.iter().cloned()),
    );
    std::process::exit(match args.cmd {
        ReviewCmd::Pending {
            doc_type,
            project_root,
            json,
        } => pending(&doc_type, project_root.as_deref(), json),
        ReviewCmd::Approve {
            path,
            reviewer,
            reason,
            project_root,
        } => approve(&path, reviewer.as_deref(), &reason, project_root.as_deref()),
        ReviewCmd::Reject {
            path,
            reviewer,
            reason,
            delete,
            project_root,
        } => reject(
            &path,
            reviewer.as_deref(),
            Some(reason.as_str()),
            delete,
            project_root.as_deref(),
        ),
        ReviewCmd::Candidate {
            selector,
            approve,
            reject,
            actor,
            reason,
            project_root,
            json,
        } => candidate(
            &selector,
            if reject { false } else { approve },
            actor.as_deref(),
            reason.as_deref(),
            project_root.as_deref(),
            json,
        ),
    });
}

fn vault_root_of(project_root: Option<&str>) -> cortex_workspace::WorkspaceLayout {
    let root = resolve(project_root);
    cortex_workspace::WorkspaceLayout::discover(&root)
}

fn pending(doc_types: &[String], project_root: Option<&str>, json_output: bool) -> i32 {
    let layout = vault_root_of(project_root);
    let vault_root = layout.enterprise_vault_path();
    let pending = cortex_enterprise::promotion_doctype::list_pending_drafts(
        &vault_root,
        if doc_types.is_empty() {
            None
        } else {
            Some(doc_types)
        },
    );

    if json_output {
        let val = PyVal::Arr(pending.iter().map(draft_pyval).collect());
        println!("{}", crate::pyjson::stdlib_dumps_indent2(&val));
        return 0;
    }

    if pending.is_empty() {
        println!("No drafts pending review.");
        return 0;
    }

    println!("Pending review ({}):", pending.len());
    for entry in &pending {
        let doc_type = entry.doc_type.as_deref().unwrap_or("-");
        let owner = entry.owner.as_deref().unwrap_or("-");
        // f"{path:<60} doc_type={dt:<10} owner={owner}" — left-justify.
        println!(
            "  - {:<60} doc_type={:<10} owner={}",
            entry.path, doc_type, owner
        );
    }
    0
}

fn draft_pyval(d: &cortex_enterprise::promotion_doctype::PendingDraft) -> PyVal {
    PyVal::obj(vec![
        ("path", PyVal::s(&d.path)),
        (
            "doc_type",
            d.doc_type.as_ref().map(PyVal::s).unwrap_or(PyVal::Null),
        ),
        (
            "title",
            d.title.as_ref().map(PyVal::s).unwrap_or(PyVal::Null),
        ),
        (
            "owner",
            d.owner.as_ref().map(PyVal::s).unwrap_or(PyVal::Null),
        ),
        ("team", d.team.as_ref().map(PyVal::s).unwrap_or(PyVal::Null)),
        (
            "created_at",
            d.created_at.as_ref().map(PyVal::s).unwrap_or(PyVal::Null),
        ),
    ])
}

fn approve(path: &str, reviewer: Option<&str>, reason: &str, project_root: Option<&str>) -> i32 {
    let layout = vault_root_of(project_root);
    let clock = std::sync::Arc::new(cortex_enterprise::clock::SystemClock);
    match cortex_enterprise::review_knowledge::approve_output(
        &layout,
        path,
        &reviewer.map(str::to_string).unwrap_or_else(current_os_user),
        reason,
        clock.as_ref(),
    ) {
        Ok(output) => {
            println!("{output}");
            0
        }
        Err(err) => {
            eprintln!("{err}");
            1
        }
    }
}

fn reject(
    path: &str,
    reviewer: Option<&str>,
    reason: Option<&str>,
    delete: bool,
    project_root: Option<&str>,
) -> i32 {
    let layout = vault_root_of(project_root);
    let clock = std::sync::Arc::new(cortex_enterprise::clock::SystemClock);
    match cortex_enterprise::review_knowledge::reject_output(
        &layout,
        path,
        &reviewer.map(str::to_string).unwrap_or_else(current_os_user),
        reason.unwrap_or_default(),
        delete,
        clock.as_ref(),
    ) {
        Ok(output) => {
            println!("{output}");
            0
        }
        Err(err) => {
            eprintln!("{err}");
            1
        }
    }
}

fn candidate(
    selector: &str,
    approve: bool,
    actor: Option<&str>,
    reason: Option<&str>,
    project_root: Option<&str>,
    json_output: bool,
) -> i32 {
    use cortex_enterprise::knowledge_promotion::KnowledgePromotionService;

    let root = resolve(project_root);
    let actor_name = actor.map(str::to_string).unwrap_or_else(current_os_user);
    let layout = cortex_workspace::WorkspaceLayout::discover(&root);
    let mut service = match KnowledgePromotionService::from_project_root(
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

    match service.review(selector, approve, &actor_name, reason) {
        Ok(record) => {
            if json_output {
                // record.model_dump_json(indent=2)
                match serde_json::to_string_pretty(&record) {
                    Ok(s) => println!("{s}"),
                    Err(_) => return 1,
                }
                return 0;
            }
            println!("Recorded review: {}", record.origin_id);
            println!("  status: {}", record.status);
            if let Some(decision) = &record.decision {
                println!(
                    "  decision: {} by {}",
                    decision.decision.as_str(),
                    decision.actor
                );
            }
            0
        }
        Err(err) => {
            eprintln!("{err}");
            1
        }
    }
}
