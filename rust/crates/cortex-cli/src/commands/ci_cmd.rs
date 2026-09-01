//! Native `cortex ci` commands over `cortex_app::ci`.
use clap::Parser;
use cortex_app::ci::{self, CiValidator, ValidationInput};
use cortex_app::session::service::SessionService;
use cortex_app::session::verification::VerificationRunner;
use cortex_app::session::{SessionStatus, SessionStorage};
use cortex_workspace::WorkspaceLayout;
use std::io::Write as _;
use std::path::PathBuf;

fn out(s: &str) {
    let _ = writeln!(std::io::stdout(), "{s}");
}
fn err(s: &str) {
    let _ = writeln!(std::io::stderr(), "{s}");
}
fn service(root: Option<&str>) -> (SessionService, PathBuf) {
    let start = crate::paths::resolve_project_root(root);
    let l = WorkspaceLayout::discover(&start);
    (
        SessionService::new(SessionStorage::new(l.sessions_dir()), &l.repo_root),
        l.repo_root,
    )
}
fn exit_error(msg: &str) -> ! {
    err(msg);
    std::process::exit(ci::EXIT_ERROR)
}

#[derive(Parser)]
struct Validate {
    #[arg(long)]
    diff: Option<PathBuf>,
    #[arg(long)]
    base_commit: Option<String>,
    #[arg(long)]
    head_commit: Option<String>,
    #[arg(long)]
    base_branch: Option<String>,
    #[arg(long)]
    head_branch: Option<String>,
    #[arg(long)]
    pr_number: Option<i64>,
    #[arg(long)]
    pr_author: Option<String>,
    #[arg(long = "session")]
    session_id: Option<String>,
    #[arg(long = "format", default_value = "json")]
    format: String,
    #[arg(long)]
    project_root: Option<String>,
}
fn validate(argv: &[String]) -> bool {
    let a = match Validate::try_parse_from(
        std::iter::once("validate-pr".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => exit_error(&e.to_string()),
    };
    if !matches!(a.format.as_str(), "json" | "text" | "pr-comment") {
        exit_error(&format!(
            "✗ --format must be one of {:?}",
            vec!["json", "pr-comment", "text"]
        ));
    }
    let (svc, root) = service(a.project_root.as_deref());
    let diff = match ci::read_diff_from_args(
        a.diff.as_deref(),
        a.base_commit.as_deref(),
        a.head_commit.as_deref(),
        &root,
    ) {
        Ok(d) => d,
        Err(e) => exit_error(&format!("✗ {e}")),
    };
    let input = ValidationInput {
        diff_text: diff,
        repo_root: root.clone(),
        base_commit: a.base_commit,
        head_commit: a.head_commit,
        base_branch: a.base_branch,
        head_branch: a.head_branch,
        pr_number: a.pr_number,
        pr_author: a.pr_author,
        explicit_session_id: a.session_id,
    };
    let result =
        CiValidator::new(svc, VerificationRunner::new(root.clone()), &root).validate(&input);
    match a.format.as_str() {
        "json" => out(&result.to_json_string()),
        "pr-comment" => out(&ci::render_pr_comment(&result, ci::DEFAULT_MARKER)),
        _ => {
            out(&result.summary_text);
            if let Some(r) = &result.matched_session {
                out(&format!("  session: {}", r.session_id));
            }
            out(&format!("  status:  {}", result.status.as_str()));
            for w in &result.warnings {
                out(&format!("  warn: {w}"));
            }
            for b in &result.blockers {
                let text = format!("  block: {b}");
                let mut rest = text.as_str();
                while rest.chars().count() > 80 {
                    let cut = rest
                        .char_indices()
                        .take_while(|(i, _)| *i <= 80)
                        .filter(|(_, c)| c.is_whitespace())
                        .map(|(i, _)| i)
                        .last()
                        .unwrap_or(80);
                    out(&rest[..=cut]);
                    rest = rest[cut + 1..].trim_start();
                }
                out(rest);
            }
        }
    }
    std::process::exit(result.exit_code)
}

#[derive(Parser)]
struct Open {
    #[arg(long)]
    pr_number: Option<i64>,
    #[arg(long)]
    base_commit: String,
    #[arg(long)]
    head_branch: String,
    #[arg(long = "spec")]
    spec_path: Option<String>,
    #[arg(long)]
    project_root: Option<String>,
    #[arg(long)]
    json: bool,
}
fn open(argv: &[String]) -> bool {
    let a = match Open::try_parse_from(
        std::iter::once("open-review-session".into()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => exit_error(&e.to_string()),
    };
    let (s, _) = service(a.project_root.as_deref());
    let today = chrono::Utc::now().format("%Y-%m-%d");
    let suffix = a
        .pr_number
        .map(|n| format!("pr-{n}-review"))
        .unwrap_or_else(|| format!("{}-review", a.head_branch.replace('/', "-").to_lowercase()));
    let id = format!("{today}_{suffix}");
    match ci::open_review_session(
        &s,
        &id,
        &a.base_commit,
        &a.head_branch,
        a.pr_number,
        a.spec_path.as_deref(),
    ) {
        Ok(r) => {
            if a.json {
                out(&format!(
                    r#"{{"session_id": "{}", "status": "{}"}}"#,
                    r.session_id,
                    r.status.as_str()
                ))
            } else {
                out(&r.session_id)
            };
            true
        }
        Err(e) => exit_error(&e),
    }
}

#[derive(Parser)]
struct Report {
    #[arg(long)]
    session_id: String,
    #[arg(long)]
    from_validation_result: Option<PathBuf>,
    #[arg(long)]
    manual_claim: Vec<String>,
    #[arg(long)]
    manual_artifact: Vec<String>,
    #[arg(long, default_value = "")]
    note: String,
    #[arg(long)]
    project_root: Option<String>,
    #[arg(long)]
    json: bool,
}
fn report(argv: &[String]) -> bool {
    let a = match Report::try_parse_from(
        std::iter::once("report-checkpoint".into()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => exit_error(&e.to_string()),
    };
    let payload = a
        .from_validation_result
        .as_ref()
        .map(|p| {
            std::fs::read_to_string(p)
                .and_then(|s| serde_json::from_str(&s).map_err(std::io::Error::other))
        })
        .transpose()
        .unwrap_or_else(|e| exit_error(&format!("✗ could not load --from-validation-result: {e}")));
    let (s, _) = service(a.project_root.as_deref());
    match ci::report_ci_checkpoint(
        &s,
        &a.session_id,
        payload.as_ref(),
        &a.manual_claim,
        &a.manual_artifact,
        &a.note,
    ) {
        Ok(r) => {
            if a.json {
                out(&format!(
                    r#"{{"session_id": "{}", "checkpoint_count": {}}}"#,
                    r.session_id,
                    r.checkpoints.len()
                ))
            } else {
                out(&format!(
                    "checkpoint emitted; total={}",
                    r.checkpoints.len()
                ))
            };
            true
        }
        Err(e) => exit_error(&e),
    }
}

#[derive(Parser)]
struct Close {
    #[arg(long)]
    session_id: String,
    #[arg(long, default_value = "closed")]
    status: String,
    #[arg(long, default_value = "")]
    reason: String,
    #[arg(long)]
    project_root: Option<String>,
    #[arg(long)]
    json: bool,
}
fn close(argv: &[String]) -> bool {
    let a = match Close::try_parse_from(
        std::iter::once("close-review-session".into()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => exit_error(&e.to_string()),
    };
    let status = match a.status.as_str() {
        "closed" => SessionStatus::Closed,
        "handoff" => SessionStatus::Handoff,
        "abandoned" => SessionStatus::Abandoned,
        _ => exit_error(&format!(
            "✗ --status must be one of {:?}",
            vec!["abandoned", "closed", "handoff"]
        )),
    };
    let (s, _) = service(a.project_root.as_deref());
    match ci::close_review_session(&s, &a.session_id, status, &a.reason) {
        Ok(r) => {
            let mode = super::session_cmd::mode_str(r.mode);
            if a.json {
                out(&format!(
                    r#"{{"session_id": "{}", "status": "{}", "mode": "{}"}}"#,
                    r.session_id,
                    r.status.as_str(),
                    mode
                ))
            } else {
                out(&format!(
                    "{} → {} (mode={})",
                    r.session_id,
                    r.status.as_str(),
                    mode
                ))
            };
            true
        }
        Err(e) => exit_error(&e),
    }
}

pub fn run(argv: &[String]) -> bool {
    match argv.first().map(String::as_str) {
        Some("validate-pr") => validate(&argv[1..]),
        Some("open-review-session") => open(&argv[1..]),
        Some("report-checkpoint") => report(&argv[1..]),
        Some("close-review-session") => close(&argv[1..]),
        Some(first) => {
            eprintln!("No such command '{first}'.");
            std::process::exit(2);
        }
        None => {
            eprintln!("cortex ci: se requiere un subcomando");
            std::process::exit(2);
        }
    }
}
