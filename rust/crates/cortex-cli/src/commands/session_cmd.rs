//! Comandos `cortex session …` (Cierre T2 + T6-b) — espejo de cli/session.py.
//!
//! Cubre current/list/show/diff/switch/checkpoint/abandon sobre
//! SessionService nativo (P4) y watch/tui sobre la pantalla ratatui nativa
//! de cortex-tui (T6/T6-b). El JSON de record replica
//! `model_dump(mode="json")` con orden pydantic. La tabla rich de `list`
//! texto se replica para los casos del gate; hooks/task quedan en passthrough.

use std::io::IsTerminal;
use std::io::Write as _;

use clap::Parser;
use cortex_app::session::service::SessionService;
use cortex_app::session::{
    CheckpointSource, SessionRecord, SessionStatus, SessionStorage, Task, TaskStatus,
};
use cortex_workspace::WorkspaceLayout;
use unicode_width::UnicodeWidthChar;

fn echo(s: &str) {
    let mut out = std::io::stdout();
    let _ = writeln!(out, "{s}");
}

fn eecho(s: &str) {
    let mut out = std::io::stderr();
    let _ = writeln!(out, "{s}");
}

struct SessionCli {
    service: SessionService,
    repo_root: std::path::PathBuf,
}

fn build_service(project_root: Option<&str>) -> SessionCli {
    let start = crate::paths::resolve_project_root(project_root);
    let layout = WorkspaceLayout::discover(&start);
    let storage = SessionStorage::new(layout.sessions_dir());
    let service = SessionService::new(storage, &layout.repo_root);
    SessionCli {
        service,
        repo_root: layout.repo_root.clone(),
    }
}

const VALID_STATUSES: &str = "open, closed, handoff, abandoned";
const SOURCES_LIST: &str =
    "cortex-sync, cortex-SDDwork, cortex-code-explorer, cortex-code-implementer, \
     cortex-code-designer, user-skill, ide-hook, manual, ci-bot";

/// Mapeo `string → SessionStatus` (misma semántica que `session list`).
fn parse_status_filter(s: &str) -> Option<SessionStatus> {
    match s {
        "open" => Some(SessionStatus::Open),
        "closed" => Some(SessionStatus::Closed),
        "handoff" => Some(SessionStatus::Handoff),
        "abandoned" => Some(SessionStatus::Abandoned),
        _ => None,
    }
}

fn resolve_record(cli: &SessionCli, session_id: Option<&String>) -> Result<SessionRecord, i32> {
    match session_id {
        None => cli.service.get_active().ok_or_else(|| {
            eecho("No active session. Pass an explicit session id.");
            1
        }),
        Some(id) => cli.service.get(id).map_err(|_| {
            eecho(&format!("Session not found: {id}"));
            1
        }),
    }
}

// ---------------------------------------------------------------------------
// current
// ---------------------------------------------------------------------------

#[derive(Parser, Debug)]
#[command(
    name = "current",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct CurrentArgs {
    #[arg(long)]
    pub project_root: Option<String>,
    #[arg(long)]
    pub json: bool,
}

pub fn run_current(argv: &[String]) -> bool {
    let args = match CurrentArgs::try_parse_from(
        std::iter::once("current".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let cli = build_service(args.project_root.as_deref());
    match cli.service.get_active() {
        None => {
            if args.json {
                echo(r#"{"session_id": null}"#);
            } else {
                echo("(no active session)");
            }
        }
        Some(record) => {
            if args.json {
                echo(&format!("{{\"session_id\": \"{}\"}}", record.session_id));
            } else {
                echo(&record.session_id);
            }
        }
    }
    true
}

// ---------------------------------------------------------------------------
// checkpoint
// ---------------------------------------------------------------------------

#[derive(Parser, Debug)]
#[command(
    name = "checkpoint",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct CheckpointArgs {
    #[arg(long, default_value = "manual")]
    pub source: String,
    #[arg(long, default_value = "")]
    pub note: String,
    #[arg(long)]
    pub verified_claim: Vec<String>,
    #[arg(long)]
    pub unverified_claim: Vec<String>,
    #[arg(long)]
    pub artifact: Vec<String>,
    #[arg(long)]
    pub session_id: Option<String>,
    #[arg(long)]
    pub project_root: Option<String>,
    #[arg(long)]
    pub json: bool,
}

pub fn run_checkpoint(argv: &[String]) -> bool {
    let args = match CheckpointArgs::try_parse_from(
        std::iter::once("checkpoint".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let source = match parse_source(&args.source) {
        Some(s) => s,
        None => {
            eecho(&format!(
                "Invalid --source '{}'; valid: {}",
                args.source, SOURCES_LIST
            ));
            return true;
        }
    };
    let cli = build_service(args.project_root.as_deref());
    let record = match resolve_record(&cli, args.session_id.as_ref()) {
        Ok(r) => r,
        Err(_) => return true,
    };
    // Nota: los errores de estado suben como excepción Python ⇒ Typer traza
    // y rc=1; el mensaje nativo va a stderr y rc=1 también.
    match cli.service.checkpoint(
        &record.session_id,
        source,
        args.verified_claim.clone(),
        args.unverified_claim.clone(),
        args.artifact.clone(),
        &args.note,
    ) {
        Ok(updated) => {
            if args.json {
                echo(&format!(
                    "{{\"session_id\": \"{}\", \"checkpoint_count\": {}, \"source\": \"{}\"}}",
                    updated.session_id,
                    updated.checkpoints.len(),
                    source_str(&source)
                ));
            } else {
                echo(&format!(
                    "checkpoint #{} appended (source={}) to {}",
                    updated.checkpoints.len(),
                    source_str(&source),
                    updated.session_id
                ));
            }
            true
        }
        Err(e) => {
            eecho(&e);
            std::process::exit(1);
        }
    }
}

fn parse_source(s: &str) -> Option<CheckpointSource> {
    use CheckpointSource as C;
    Some(match s {
        "cortex-sync" => C::CortexSync,
        "cortex-SDDwork" => C::CortexSddwork,
        "cortex-code-explorer" => C::CortexCodeExplorer,
        "cortex-code-implementer" => C::CortexCodeImplementer,
        "cortex-code-designer" => C::CortexCodeDesigner,
        "user-skill" => C::UserSkill,
        "ide-hook" => C::IdeHook,
        "manual" => C::Manual,
        "ci-bot" => C::CiBot,
        _ => return None,
    })
}

pub(crate) fn mode_str(m: cortex_app::session::SessionMode) -> &'static str {
    use cortex_app::session::SessionMode as M;
    match m {
        M::Unknown => "unknown",
        M::Managed => "managed",
        M::Observed => "observed",
        M::Byo => "byo",
        M::CiReview => "ci-review",
    }
}

fn task_status_str(s: cortex_app::session::TaskStatus) -> &'static str {
    use cortex_app::session::TaskStatus as T;
    match s {
        T::Pending => "pending",
        T::InProgress => "in-progress",
        T::Done => "done",
        T::Skipped => "skipped",
        T::Blocked => "blocked",
    }
}

fn source_str(s: &CheckpointSource) -> &'static str {
    use CheckpointSource as C;
    match s {
        C::CortexSync => "cortex-sync",
        C::CortexSddwork => "cortex-SDDwork",
        C::CortexCodeExplorer => "cortex-code-explorer",
        C::CortexCodeImplementer => "cortex-code-implementer",
        C::CortexCodeDesigner => "cortex-code-designer",
        C::UserSkill => "user-skill",
        C::IdeHook => "ide-hook",
        C::Manual => "manual",
        C::CiBot => "ci-bot",
    }
}

// ---------------------------------------------------------------------------
// switch / diff / abandon
// ---------------------------------------------------------------------------

#[derive(Parser, Debug)]
#[command(
    name = "switch",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct SwitchArgs {
    pub session_id: String,
    #[arg(long)]
    pub project_root: Option<String>,
}

pub fn run_switch(argv: &[String]) -> bool {
    let args = match SwitchArgs::try_parse_from(
        std::iter::once("switch".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let cli = build_service(args.project_root.as_deref());
    // Espejo del mensaje canónico: SessionNotFound(str) lleva SOLO el id.
    if cli.service.get(&args.session_id).is_err() {
        eecho(&args.session_id);
        std::process::exit(1);
    }
    match cli.service.set_active(&args.session_id) {
        Ok(()) => {
            echo(&format!("active session: {}", args.session_id));
            true
        }
        Err(e) => {
            eecho(&e);
            std::process::exit(1);
        }
    }
}

#[derive(Parser, Debug)]
#[command(
    name = "diff",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct DiffArgs {
    pub session_id: Option<String>,
    #[arg(long)]
    pub project_root: Option<String>,
}

pub fn run_diff(argv: &[String]) -> bool {
    let args = match DiffArgs::try_parse_from(
        std::iter::once("diff".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let cli = build_service(args.project_root.as_deref());
    let record = match resolve_record(&cli, args.session_id.as_ref()) {
        Ok(r) => r,
        Err(_) => return true,
    };
    // compute_diff: git diff <start>..<end_ref> (HEAD si sesión abierta).
    let end_ref = record.end_commit.clone().unwrap_or_else(|| "HEAD".into());
    let out = std::process::Command::new("git")
        .args(["diff", &format!("{}..{}", record.start_commit, end_ref)])
        .current_dir(&cli.repo_root)
        .output();
    let text = match out {
        Ok(o) if o.status.success() => String::from_utf8_lossy(&o.stdout).trim_end().to_string(),
        Ok(o) => {
            eecho(&format!(
                "git error: {}",
                String::from_utf8_lossy(&o.stderr)
            ));
            return true;
        }
        Err(e) => {
            eecho(&format!("git error: {e}"));
            return true;
        }
    };
    if text.is_empty() {
        echo("(no diff — start_commit equals end_ref)");
    } else {
        echo(&text);
    }
    true
}

#[derive(Parser, Debug)]
#[command(
    name = "abandon",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct AbandonArgs {
    pub session_id: String,
    #[arg(long)]
    pub reason: String,
    #[arg(long)]
    pub yes: bool,
    #[arg(long)]
    pub project_root: Option<String>,
}

pub fn run_abandon(argv: &[String]) -> bool {
    let args = match AbandonArgs::try_parse_from(
        std::iter::once("abandon".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    if !args.yes {
        // Sin TTY interactiva el confirm de typer aborta con EOF ⇒ rc=1.
        eecho("Aborted by user (no interactive terminal).");
        return true;
    }
    let cli = build_service(args.project_root.as_deref());
    // Espejo de SessionService.abandon: checkpoint MANUAL con la razón y close.
    if let Ok(record) = cli.service.get(&args.session_id) {
        let open = record.status == SessionStatus::Open;
        if open && !args.reason.is_empty() {
            if let Err(e) = cli.service.checkpoint(
                &args.session_id,
                CheckpointSource::Manual,
                vec![],
                vec![],
                vec![],
                &format!("Abandoned: {}", args.reason),
            ) {
                eecho(&e);
                return true;
            }
        }
    }
    match cli.service.close(
        &args.session_id,
        SessionStatus::Abandoned,
        SessionStatus::Abandoned,
        None,
        vec![],
    ) {
        Ok(record) => {
            echo(&format!("abandoned session: {}", record.session_id));
            true
        }
        Err(e) => {
            eecho(&e);
            std::process::exit(1);
        }
    }
}

// ---------------------------------------------------------------------------
// list (--json nativo; tabla rich de texto ⇒ passthrough)
// ---------------------------------------------------------------------------

#[derive(Parser, Debug)]
#[command(
    name = "list",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct ListArgs {
    #[arg(long)]
    pub status: Option<String>,
    #[arg(long)]
    pub project_root: Option<String>,
    #[arg(long)]
    pub json: bool,
}

fn record_summary_pv(r: &SessionRecord) -> crate::pyjson::PyVal {
    use crate::pyjson::{Num, PyVal};
    PyVal::obj(vec![
        ("session_id", PyVal::s(r.session_id.clone())),
        ("status", PyVal::s(r.status.as_str())),
        ("mode", PyVal::s(mode_str(r.mode))),
        ("opened_at", PyVal::s(r.opened_at.clone())),
        (
            "closed_at",
            match &r.closed_at {
                Some(c) => PyVal::s(c.clone()),
                None => PyVal::Null,
            },
        ),
        (
            "checkpoint_count",
            PyVal::Num(Num::Int(r.checkpoints.len() as i64)),
        ),
        ("spec_summary", PyVal::s(r.spec_summary.clone())),
    ])
}

pub fn run_list(argv: &[String]) -> bool {
    let args = match ListArgs::try_parse_from(
        std::iter::once("list".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let filter = match &args.status {
        None => None,
        Some(s) => match s.as_str() {
            "open" => Some(SessionStatus::Open),
            "closed" => Some(SessionStatus::Closed),
            "handoff" => Some(SessionStatus::Handoff),
            "abandoned" => Some(SessionStatus::Abandoned),
            other => {
                eecho(&format!(
                    "Invalid status '{other}'. Must be one of: {VALID_STATUSES}"
                ));
                return true;
            }
        },
    };
    let cli = build_service(args.project_root.as_deref());
    let records = match cli.service.list(filter) {
        Ok(rs) => rs,
        Err(e) => {
            eecho(&e);
            return true;
        }
    };
    // sort(key=opened_at, reverse=True) — string ISO compara cronológico.
    let mut records = records;
    records.sort_by(|a, b| b.opened_at.cmp(&a.opened_at));
    let active_id = cli.service.get_active().map(|r| r.session_id);
    if args.json {
        let items: Vec<crate::pyjson::PyVal> = records.iter().map(record_summary_pv).collect();
        echo(&crate::pyjson::stdlib_dumps_compact_array(&items));
        return true;
    }
    if records.is_empty() {
        echo("(no sessions on disk)");
        return true;
    }
    let rows: Vec<Vec<String>> = records
        .iter()
        .map(|r| {
            vec![
                if active_id.as_deref() == Some(&r.session_id) {
                    "►".into()
                } else {
                    String::new()
                },
                r.session_id.clone(),
                r.status.as_str().into(),
                mode_str(r.mode).into(),
                r.opened_at
                    .get(..16)
                    .unwrap_or(&r.opened_at)
                    .replace('T', "\n"),
                r.checkpoints.len().to_string(),
                r.spec_summary.chars().take(60).collect(),
            ]
        })
        .collect();
    echo(&render_table(
        &[
            "",
            "ID",
            "STATUS",
            "MODE",
            "OPENED",
            "CHECKPOINTS",
            "SUMMARY",
        ],
        &rows,
        None,
    ));
    if let Some(id) = active_id {
        echo(&format!("► = active session ({id})"));
    }
    true
}

// ---------------------------------------------------------------------------
// show (--json nativo; detalle rich de texto ⇒ passthrough)
// ---------------------------------------------------------------------------

#[derive(Parser, Debug)]
#[command(
    name = "show",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct ShowArgs {
    pub session_id: Option<String>,
    #[arg(long)]
    pub project_root: Option<String>,
    #[arg(long)]
    pub json: bool,
}

pub fn run_show(argv: &[String]) -> bool {
    let args = match ShowArgs::try_parse_from(
        std::iter::once("show".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let cli = build_service(args.project_root.as_deref());
    let record = match resolve_record(&cli, args.session_id.as_ref()) {
        Ok(r) => r,
        Err(_) => return true,
    };
    if args.json {
        echo(&record_dump_json(&record));
        return true;
    }
    echo(&format!("Session: {}", record.session_id));
    echo(&format!("  status:      {}", record.status.as_str()));
    echo(&format!("  mode:        {}", mode_str(record.mode)));
    echo(&format!("  spec:        {}", record.spec_path));
    echo(&format!("  summary:     {}", record.spec_summary));
    echo(&format!("  opened:      {}", record.opened_at));
    echo(&format!("  branch:      {}", record.start_branch));
    echo(&format!("  start commit:{}", record.start_commit));
    if let Some(closed) = &record.closed_at {
        echo(&format!("  closed:      {closed}"));
        echo(&format!(
            "  end commit:  {}",
            record.end_commit.as_deref().unwrap_or("None")
        ));
        echo(&format!(
            "  decision:    {}",
            record
                .documenter_decision
                .map(|s| s.as_str())
                .unwrap_or("None")
        ));
    }
    echo("");
    if record.checkpoints.is_empty() {
        echo("(no checkpoints)");
    } else {
        let rows: Vec<Vec<String>> = record
            .checkpoints
            .iter()
            .map(|c| {
                vec![
                    c.timestamp
                        .get(..19)
                        .unwrap_or(&c.timestamp)
                        .replace('T', " "),
                    source_str(&c.source).into(),
                    c.verified_claims.len().to_string(),
                    c.artifacts_touched.len().to_string(),
                    c.note.chars().take(60).collect(),
                ]
            })
            .collect();
        echo(&render_table(
            &["TIMESTAMP", "SOURCE", "VERIFIED", "ARTIFACTS", "NOTE"],
            &rows,
            Some("Checkpoints"),
        ));
    }
    if let Some(note) = &record.session_note_path {
        echo(&format!("\nsession note: {note}"));
    }
    if !record.adrs_created.is_empty() {
        echo(&format!("ADRs created: {}", record.adrs_created.len()));
    }
    true
}

/// Espejo de `record.model_dump(mode="json")` (indent=2, UTF-8 crudo).
pub fn record_dump_json(r: &SessionRecord) -> String {
    use crate::pyjson::{Num, PyVal};
    fn arr(xs: &[String]) -> PyVal {
        PyVal::Arr(xs.iter().map(|x| PyVal::s(x.clone())).collect())
    }
    fn opt(v: &Option<String>) -> PyVal {
        match v {
            Some(s) => PyVal::s(s.clone()),
            None => PyVal::Null,
        }
    }
    fn opt_status(v: &Option<SessionStatus>) -> PyVal {
        match v {
            Some(s) => PyVal::s(s.as_str()),
            None => PyVal::Null,
        }
    }
    let checkpoints = PyVal::Arr(
        r.checkpoints
            .iter()
            .map(|c| {
                PyVal::obj(vec![
                    ("timestamp", PyVal::s(c.timestamp.clone())),
                    ("source", PyVal::s(source_str(&c.source))),
                    ("verified_claims", arr(&c.verified_claims)),
                    ("unverified_claims", arr(&c.unverified_claims)),
                    ("artifacts_touched", arr(&c.artifacts_touched)),
                    ("note", PyVal::s(c.note.clone())),
                ])
            })
            .collect(),
    );
    let verification = PyVal::Arr(
        r.verification_results
            .iter()
            .map(|h| {
                PyVal::obj(vec![
                    ("name", PyVal::s(h.name.clone())),
                    ("command", PyVal::s(h.command.clone())),
                    ("passed", PyVal::Bool(h.passed)),
                    ("exit_code", PyVal::Num(Num::Int(h.exit_code as i64))),
                    ("output", PyVal::s(h.output.clone())),
                    ("duration_ms", PyVal::Num(Num::Int(h.duration_ms as i64))),
                    ("run_at", PyVal::s(h.run_at.clone())),
                ])
            })
            .collect(),
    );
    let tasks = PyVal::Arr(
        r.tasks
            .iter()
            .map(|t| {
                PyVal::obj(vec![
                    ("id", PyVal::s(t.id.clone())),
                    ("description", PyVal::s(t.description.clone())),
                    ("files_in_scope", arr(&t.files_in_scope)),
                    ("depends_on", arr(&t.depends_on)),
                    ("status", PyVal::s(task_status_str(t.status))),
                    ("completed_at", opt(&t.completed_at)),
                    (
                        "checkpoint_index",
                        match t.checkpoint_index {
                            Some(i) => PyVal::Num(Num::Int(i as i64)),
                            None => PyVal::Null,
                        },
                    ),
                    ("note", PyVal::s(t.note.clone())),
                ])
            })
            .collect(),
    );
    let v = PyVal::obj(vec![
        ("session_id", PyVal::s(r.session_id.clone())),
        ("spec_path", PyVal::s(r.spec_path.clone())),
        ("spec_summary", PyVal::s(r.spec_summary.clone())),
        ("start_commit", PyVal::s(r.start_commit.clone())),
        ("start_branch", PyVal::s(r.start_branch.clone())),
        ("opened_at", PyVal::s(r.opened_at.clone())),
        ("status", PyVal::s(r.status.as_str())),
        ("mode", PyVal::s(mode_str(r.mode))),
        ("checkpoints", checkpoints),
        ("verification_results", verification),
        ("tasks", tasks),
        ("closed_at", opt(&r.closed_at)),
        ("end_commit", opt(&r.end_commit)),
        ("documenter_decision", opt_status(&r.documenter_decision)),
        ("session_note_path", opt(&r.session_note_path)),
        ("adrs_created", arr(&r.adrs_created)),
    ]);
    crate::pyjson::pydantic_dumps_indent2(&v)
}

fn cell_width(s: &str) -> usize {
    use unicode_width::UnicodeWidthStr;
    UnicodeWidthStr::width(s)
}

fn wrap_cell(s: &str, width: usize) -> Vec<String> {
    if width == 0 {
        return vec![String::new()];
    }
    let mut all = Vec::new();
    for source in s.split('\n') {
        let mut out = Vec::new();
        let mut cur = String::new();
        let mut used = 0;
        for ch in source.chars() {
            use unicode_width::UnicodeWidthChar;
            let w = ch.width().unwrap_or(0);
            if used + w > width && !cur.is_empty() {
                out.push(std::mem::take(&mut cur));
                used = 0;
            }
            cur.push(ch);
            used += w;
        }
        if cur.is_empty() && out.is_empty() {
            out.push(String::new())
        } else if !cur.is_empty() {
            out.push(cur)
        }
        all.extend(out);
    }
    all
}

/// Render mínimo del box `rich.table.Table` en consola no-TTY de 80 columnas.
fn render_table(headers: &[&str], rows: &[Vec<String>], title: Option<&str>) -> String {
    let n = headers.len();
    let mut widths: Vec<usize> = (0..n)
        .map(|i| {
            rows.iter()
                .flat_map(|r| r[i].split('\n'))
                .map(cell_width)
                .chain(std::iter::once(cell_width(headers[i])))
                .max()
                .unwrap_or(1)
        })
        .collect();
    let list_table = headers
        == [
            "",
            "ID",
            "STATUS",
            "MODE",
            "OPENED",
            "CHECKPOINTS",
            "SUMMARY",
        ];
    if list_table {
        widths = vec![2, 13, 6, 7, 12, 11, 7];
    } else {
        if headers.first() == Some(&"") {
            widths[0] = 2;
        }
        let budget = 80usize.saturating_sub(3 * n + 1);
        while widths.iter().sum::<usize>() > budget {
            if let Some((i, _)) = widths
                .iter()
                .enumerate()
                .filter(|(_, w)| **w > 3)
                .max_by_key(|(_, w)| **w)
            {
                widths[i] -= 1
            } else {
                break;
            }
        }
    }
    let line = |left: char, mid: char, right: char, fill: char| {
        let mut s = String::new();
        s.push(left);
        for (i, w) in widths.iter().enumerate() {
            s.extend(std::iter::repeat_n(fill, w + 2));
            if i + 1 < n {
                s.push(mid)
            }
        }
        s.push(right);
        s
    };
    let mut lines = Vec::new();
    if let Some(t) = title {
        let total = widths.iter().sum::<usize>() + 3 * n + 1;
        let pad = total.saturating_sub(cell_width(t)) / 2;
        let right = total.saturating_sub(pad + cell_width(t));
        lines.push(format!("{}{}{}", " ".repeat(pad), t, " ".repeat(right)));
    }
    lines.push(line('┏', '┳', '┓', '━'));
    let emit = |cells: Vec<Vec<String>>, lines: &mut Vec<String>, heavy: bool| {
        let height = cells.iter().map(Vec::len).max().unwrap_or(1);
        for row in 0..height {
            let edge = if heavy { "┃" } else { "│" };
            let mut s = String::from(edge);
            for i in 0..n {
                let raw = cells[i].get(row).map(String::as_str).unwrap_or("");
                let clipped = if list_table && i == 1 && cell_width(raw) > widths[i] {
                    format!("{}…", raw.chars().take(widths[i] - 1).collect::<String>())
                } else {
                    raw.to_string()
                };
                let val = &clipped;
                let pad = widths[i].saturating_sub(cell_width(val));
                let right = matches!(headers[i], "CHECKPOINTS" | "VERIFIED" | "ARTIFACTS");
                if right {
                    s.push_str(&format!(" {}{} {edge}", " ".repeat(pad), val));
                } else {
                    s.push_str(&format!(" {}{} {edge}", val, " ".repeat(pad)));
                }
            }
            lines.push(s)
        }
    };
    emit(
        headers
            .iter()
            .enumerate()
            .map(|(i, h)| wrap_cell(h, widths[i]))
            .collect(),
        &mut lines,
        true,
    );
    lines.push(line('┡', '╇', '┩', '━'));
    for r in rows {
        emit(
            r.iter()
                .enumerate()
                .map(|(i, c)| {
                    if list_table && i == 1 && cell_width(c) > widths[i] {
                        vec![format!(
                            "{}…",
                            c.chars().take(widths[i] - 1).collect::<String>()
                        )]
                    } else {
                        wrap_cell(c, widths[i])
                    }
                })
                .collect(),
            &mut lines,
            false,
        );
    }
    lines.push(line('└', '┴', '┘', '─'));
    lines.join("\n")
}

// ---------------------------------------------------------------------------
// watch / tui — pantalla ratatui nativa (T6-b)
// ---------------------------------------------------------------------------

#[derive(Parser, Debug)]
#[command(
    name = "watch",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct WatchArgs {
    #[arg(long)]
    pub project_root: Option<String>,
    /// Filtrar por estado: uno de {open, closed, handoff, abandoned}.
    #[arg(long)]
    pub status: Option<String>,
}

/// `cortex session watch` / `cortex session tui` — mismo entrypoint sobre la
/// pantalla sesiones de cortex-tui (`SessionsScreenData::from_service` +
/// `render`, contrato v1 read-only). En consola no-interactiva (CI) emite un
/// snapshot único en vez de fallar: rc 0 + la tabla del mismo storage.
pub fn run_watch(argv: &[String]) -> bool {
    let args = match WatchArgs::try_parse_from(
        std::iter::once("watch".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let status_filter = match &args.status {
        Some(s) => match parse_status_filter(s) {
            Some(f) => Some(f),
            None => {
                eecho(&format!(
                    "Invalid status '{s}'. Must be one of: {VALID_STATUSES}"
                ));
                return true;
            }
        },
        None => None,
    };
    let cli = build_service(args.project_root.as_deref());
    if !std::io::stdout().is_terminal() {
        return snapshot_once(&cli, status_filter);
    }
    interactive_loop(&cli, status_filter)
}

/// Consola no-interactiva (pipes, CI): render único vía `TestBackend` de
/// dimensiones fijas y salida por stdout, rc 0. Los asserts del gate son
/// sobre ids/marca presentes, no sobre bytes exactos de la tabla.
fn snapshot_once(cli: &SessionCli, status_filter: Option<SessionStatus>) -> bool {
    use ratatui::backend::TestBackend;
    use ratatui::{Terminal, TerminalOptions, Viewport};

    let data =
        match cortex_tui::sessions::SessionsScreenData::from_service(&cli.service, status_filter) {
            Ok(d) => d,
            Err(e) => {
                eecho(&e);
                return true;
            }
        };
    let (w, h) = (100u16, 40u16);
    let mut terminal = match Terminal::with_options(
        TestBackend::new(w, h),
        TerminalOptions {
            viewport: Viewport::Fixed(ratatui::prelude::Rect::new(0, 0, w, h)),
        },
    ) {
        Ok(t) => t,
        Err(e) => {
            eecho(&format!("watch: {e}"));
            return true;
        }
    };
    if let Err(e) = terminal.draw(|f| cortex_tui::sessions::render(f, &data)) {
        eecho(&format!("watch: {e}"));
        return true;
    }
    let buf = terminal.backend().buffer();
    let mut lines: Vec<String> = (0..buf.area.height)
        .map(|y| {
            (0..buf.area.width)
                .map(|x| buf[(x, y)].symbol().to_string())
                .collect::<String>()
                .trim_end()
                .to_string()
        })
        .collect();
    while lines.last().is_some_and(|l| l.is_empty()) {
        lines.pop();
    }
    echo(&lines.join("\n"));
    eecho("watch: terminal no interactivo — snapshot emitido; usá un terminal real para el modo en vivo.");
    true
}

/// Loop ratatui read-only mínimo (contrato v1): tick ~250 ms, reconstruye el
/// snapshot en cada tick (las sesiones cambian en disco) y sale con `q` o
/// `Ctrl+C`. La restauración del terminal es RAII (drop/panic incluidos).
fn interactive_loop(cli: &SessionCli, status_filter: Option<SessionStatus>) -> bool {
    use ratatui::crossterm::cursor::Show;
    use ratatui::crossterm::event::{self, Event, KeyCode, KeyEventKind, KeyModifiers};
    use ratatui::crossterm::execute;
    use ratatui::crossterm::terminal::{
        disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
    };

    /// Restaura pantalla alterna, cursor y modo raw pase lo que pase.
    struct Restore;
    impl Drop for Restore {
        fn drop(&mut self) {
            let _ = execute!(std::io::stdout(), LeaveAlternateScreen, Show);
            let _ = disable_raw_mode();
        }
    }

    let mut stdout = std::io::stdout();
    if enable_raw_mode().is_err() {
        eecho("watch: no se pudo habilitar el modo raw.");
        return true;
    }
    // El guard vive desde que el raw mode queda activo: restaura sí o sí.
    let _guard = Restore;
    if execute!(stdout, EnterAlternateScreen, Show).is_err() {
        eecho("watch: no se pudo entrar a la pantalla alterna.");
        return true;
    }

    let backend = ratatui::backend::CrosstermBackend::new(stdout);
    let mut terminal = match ratatui::Terminal::new(backend) {
        Ok(t) => t,
        Err(e) => {
            eecho(&format!("watch: {e}"));
            return true;
        }
    };
    let tick = std::time::Duration::from_millis(250);
    loop {
        let drawn =
            terminal.draw(|f| {
                match cortex_tui::sessions::SessionsScreenData::from_service(
                    &cli.service,
                    status_filter,
                ) {
                    Ok(data) => cortex_tui::sessions::render(f, &data),
                    Err(e) => {
                        f.render_widget(
                            ratatui::widgets::Paragraph::new(format!(
                                "cortex · sesiones · error: {e}"
                            )),
                            f.area(),
                        );
                    }
                }
            });
        let _ = drawn;
        if event::poll(tick).unwrap_or(false) {
            if let Ok(Event::Key(key)) = event::read() {
                let quit = key.kind == KeyEventKind::Press
                    && (matches!(key.code, KeyCode::Char('q') | KeyCode::Char('Q'))
                        || (key.code == KeyCode::Char('c')
                            && key.modifiers.contains(KeyModifiers::CONTROL)));
                if quit {
                    break;
                }
            }
        }
    }
    true
}

// ---------------------------------------------------------------------------
// task ×5 (oráculo cli/session.py:485-670) — wireado MITAD A ruta 1
// ---------------------------------------------------------------------------

const TASK_VALID_STATUSES: &str = "pending, in-progress, done, skipped, blocked";

fn parse_task_status(s: &str) -> Option<TaskStatus> {
    use TaskStatus as T;
    match s {
        "pending" => Some(T::Pending),
        "in-progress" => Some(T::InProgress),
        "done" => Some(T::Done),
        "skipped" => Some(T::Skipped),
        "blocked" => Some(T::Blocked),
        _ => None,
    }
}

/// Espejo de `_resolve_task_session` (session.py): la sesión pedida o la
/// activa, con los mensajes EXACTOS del oráculo en stderr + exit(1).
fn resolve_task_session(cli: &SessionCli, session_id: Option<&str>) -> SessionRecord {
    match session_id {
        None => cli.service.get_active().unwrap_or_else(|| {
            eecho("No active session. Pass --session-id explicitly.");
            std::process::exit(1);
        }),
        Some(id) => cli.service.get(id).unwrap_or_else(|_| {
            eecho(&format!("Session not found: {id}"));
            std::process::exit(1);
        }),
    }
}

#[derive(Parser, Debug)]
#[command(
    name = "task",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct TaskListArgs {
    #[arg(long)]
    pub session_id: Option<String>,
    #[arg(long)]
    pub status: Option<String>,
    #[arg(long)]
    pub project_root: Option<String>,
    #[arg(long)]
    pub json: bool,
}

fn task_pv(t: &Task) -> crate::pyjson::PyVal {
    use crate::pyjson::{Num, PyVal};
    let arr = |xs: &[String]| PyVal::Arr(xs.iter().map(|s| PyVal::s(s.clone())).collect());
    PyVal::obj(vec![
        ("id", PyVal::s(t.id.clone())),
        ("description", PyVal::s(t.description.clone())),
        ("files_in_scope", arr(&t.files_in_scope)),
        ("depends_on", arr(&t.depends_on)),
        ("status", PyVal::s(task_status_str(t.status).to_string())),
        (
            "completed_at",
            match &t.completed_at {
                Some(s) => PyVal::s(s.clone()),
                None => PyVal::Null,
            },
        ),
        (
            "checkpoint_index",
            match t.checkpoint_index {
                Some(i) => PyVal::Num(Num::Int(i as i64)),
                None => PyVal::Null,
            },
        ),
        ("note", PyVal::s(t.note.clone())),
    ])
}

pub fn run_task_list(argv: &[String]) -> bool {
    let args = match TaskListArgs::try_parse_from(
        std::iter::once("list".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let filter = match &args.status {
        None => None,
        Some(s) => match parse_task_status(s) {
            Some(f) => Some(f),
            None => {
                eecho(&format!(
                    "Invalid --status '{s}'. Must be one of: {TASK_VALID_STATUSES}"
                ));
                std::process::exit(1);
            }
        },
    };
    let cli = build_service(args.project_root.as_deref());
    let record = resolve_task_session(&cli, args.session_id.as_deref());
    let tasks = match cli.service.list_tasks(&record.session_id, filter) {
        Ok(t) => t,
        Err(e) => {
            eecho(&e);
            return true;
        }
    };
    if args.json {
        let items: Vec<crate::pyjson::PyVal> = tasks.iter().map(task_pv).collect();
        echo(&compact_dumps_utf8(&crate::pyjson::PyVal::Arr(items)));
        return true;
    }
    if tasks.is_empty() {
        echo("(no tasks)");
        return true;
    }
    let rows: Vec<Vec<String>> = tasks
        .iter()
        .map(|t| {
            vec![
                t.id.clone(),
                task_status_str(t.status).into(),
                t.description.chars().take(60).collect(),
                format_files(&t.files_in_scope),
            ]
        })
        .collect();
    let table = render_rich_table(
        &["ID", "STATUS", "DESCRIPTION", "FILES"],
        &rows,
        &["left", "left", "left", "left"],
    );
    echo(table.trim_end_matches('\n'));
    true
}

/// `", ".join(t.files_in_scope[:3]) + (f" (+{len-3})" if len > 3 else "")`.
fn format_files(files: &[String]) -> String {
    let head = files.iter().take(3).cloned().collect::<Vec<_>>().join(", ");
    if files.len() > 3 {
        format!("{head} (+{})", files.len() - 3)
    } else {
        head
    }
}

#[derive(Parser, Debug)]
#[command(
    name = "update",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
struct TaskUpdateNoteArgs {
    pub task_id: String,
    #[arg(long, default_value = "")]
    pub note: String,
    #[arg(long)]
    pub session_id: Option<String>,
    #[arg(long)]
    pub project_root: Option<String>,
    #[arg(long)]
    pub json: bool,
}

#[derive(Parser, Debug)]
#[command(
    name = "update",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
struct TaskUpdateReasonArgs {
    pub task_id: String,
    #[arg(long, required = true)]
    pub reason: String,
    #[arg(long)]
    pub session_id: Option<String>,
    #[arg(long)]
    pub project_root: Option<String>,
    #[arg(long)]
    pub json: bool,
}

fn run_task_update_status(
    argv: &[String],
    sub: &str,
    new_status: TaskStatus,
    need_reason: bool,
) -> bool {
    // skip/block exigen --reason (typer) ⇒ nota obligatoria; done/in-progress
    // usan --note opcional.
    let (task_id, note, session_id, project_root, json) = if need_reason {
        let args = match TaskUpdateReasonArgs::try_parse_from(
            std::iter::once(sub.to_string()).chain(argv.iter().cloned()),
        ) {
            Ok(a) => a,
            Err(e) => {
                eprint!("{e}");
                return true;
            }
        };
        (
            args.task_id,
            args.reason,
            args.session_id,
            args.project_root,
            args.json,
        )
    } else {
        let args = match TaskUpdateNoteArgs::try_parse_from(
            std::iter::once(sub.to_string()).chain(argv.iter().cloned()),
        ) {
            Ok(a) => a,
            Err(e) => {
                eprint!("{e}");
                return true;
            }
        };
        (
            args.task_id,
            args.note,
            args.session_id,
            args.project_root,
            args.json,
        )
    };
    let cli = build_service(project_root.as_deref());
    let record = resolve_task_session(&cli, session_id.as_deref());
    match cli
        .service
        .update_task_status(&record.session_id, &task_id, new_status, &note)
    {
        Ok(_) => {
            if json {
                echo(&format!(
                    "{{\"session_id\": \"{}\", \"task_id\": \"{}\", \"status\": \"{}\"}}",
                    record.session_id,
                    task_id,
                    task_status_str(new_status)
                ));
            } else {
                echo(&format!("{task_id} → {}", task_status_str(new_status)));
            }
            true
        }
        Err(e) => {
            eecho(&e);
            std::process::exit(1);
        }
    }
}

pub fn run_task(argv: &[String]) -> bool {
    let Some(first) = argv.first().map(String::as_str) else {
        return false;
    };
    let rest = &argv[1..];
    match first {
        "list" => run_task_list(rest),
        "done" => run_task_update_status(rest, "done", TaskStatus::Done, false),
        "in-progress" => run_task_update_status(rest, "in-progress", TaskStatus::InProgress, false),
        "skip" => run_task_update_status(rest, "skip", TaskStatus::Skipped, true),
        "block" => run_task_update_status(rest, "block", TaskStatus::Blocked, true),
        _ => false,
    }
}

// ---------------------------------------------------------------------------
// hooks ×4 (oráculo cli/session.py:680-845) — glue sobre cortex-setup
// ---------------------------------------------------------------------------

fn hooks_installer() -> cortex_setup::session_hooks::HookInstaller {
    cortex_setup::session_hooks::default_installer()
}

fn hooks_target(project_root: Option<&str>) -> std::path::PathBuf {
    crate::paths::resolve_project_root(project_root)
}

#[derive(Parser, Debug)]
#[command(
    name = "list",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
struct HooksListArgs {
    #[arg(long)]
    pub project_root: Option<String>,
    #[arg(long)]
    pub json: bool,
}

/// `KeyError.__str__` de Python: el mensaje va entre comillas dobles.
fn unknown_ide_message(
    installer: &cortex_setup::session_hooks::HookInstaller,
    ide: &str,
) -> String {
    format!(
        "\"unknown IDE adapter '{ide}'; available: {}\"",
        installer.list_available_adapters().join(", ")
    )
}

fn hook_status_pv(s: &cortex_setup::session_hooks::HookStatus) -> crate::pyjson::PyVal {
    use crate::pyjson::PyVal;
    PyVal::obj(vec![
        ("ide", PyVal::s(s.ide.to_string())),
        ("installed", PyVal::Bool(s.installed)),
        ("supported", PyVal::Bool(true)),
        ("detail", PyVal::s(s.detail.clone())),
    ])
}

pub fn run_hooks_list(argv: &[String]) -> bool {
    let args = match HooksListArgs::try_parse_from(
        std::iter::once("list".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let installer = hooks_installer();
    let target = hooks_target(args.project_root.as_deref());
    let statuses = installer.status_all(&target);
    if args.json {
        let items: Vec<crate::pyjson::PyVal> = statuses.iter().map(hook_status_pv).collect();
        echo(&compact_dumps_utf8(&crate::pyjson::PyVal::Arr(items)));
        return true;
    }
    let rows: Vec<Vec<String>> = statuses
        .iter()
        .map(|s| {
            vec![
                s.ide.to_string(),
                if s.installed {
                    "✓".into()
                } else {
                    "—".into()
                },
                "✓".into(), // supported=true para los 4 adapters bundled
                s.detail.clone(),
            ]
        })
        .collect();
    let table = render_rich_table(
        &["IDE", "INSTALLED", "SUPPORTED", "DETAIL"],
        &rows,
        &["left", "center", "center", "left"],
    );
    echo(table.trim_end_matches('\n'));
    true
}

#[derive(Parser, Debug)]
#[command(
    name = "install",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
struct HooksInstallArgs {
    #[arg(long, required = true)]
    pub ide: String,
    #[arg(long)]
    pub project_root: Option<String>,
    #[arg(long)]
    pub json: bool,
}

/// `json.dumps(str, ensure_ascii=False)` de Python para un solo valor.
fn json_quote(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
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
    out.push('"');
    out
}

/// `json.dumps(ensure_ascii=False)` de una lista de strings (paths).
fn json_quote_list(xs: &[std::path::PathBuf]) -> String {
    let items: Vec<String> = xs
        .iter()
        .map(|p| json_quote(&p.to_string_lossy()))
        .collect();
    format!("[{}]", items.join(", "))
}

/// `json.dumps(ensure_ascii=False)` compacta (separadores ", " / ": ")
/// sobre un valor PyVal — para `task list --json` / `hooks list --json` /
/// `hooks status --json`, que en el oráculo NO escapan no-ASCII (a
/// diferencia de `pyjson::stdlib_dumps_compact_array`, ensure_ascii=True).
fn compact_dumps_utf8(v: &crate::pyjson::PyVal) -> String {
    let mut out = String::new();
    write_compact_utf8(v, &mut out);
    out
}

fn write_compact_utf8(v: &crate::pyjson::PyVal, out: &mut String) {
    use crate::pyjson::{Num, PyVal};
    match v {
        PyVal::Null => out.push_str("null"),
        PyVal::Bool(true) => out.push_str("true"),
        PyVal::Bool(false) => out.push_str("false"),
        PyVal::Num(Num::Int(i)) => out.push_str(&i.to_string()),
        PyVal::Num(Num::Float(f)) => out.push_str(&crate::pyjson::format_float(*f)),
        PyVal::Str(s) => out.push_str(&json_quote(s)),
        PyVal::Arr(items) => {
            out.push('[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push_str(", ");
                }
                write_compact_utf8(item, out);
            }
            out.push(']');
        }
        PyVal::Obj(items) => {
            out.push('{');
            for (i, (k, val)) in items.iter().enumerate() {
                if i > 0 {
                    out.push_str(", ");
                }
                out.push_str(&json_quote(k));
                out.push_str(": ");
                write_compact_utf8(val, out);
            }
            out.push('}');
        }
    }
}

pub fn run_hooks_install(argv: &[String]) -> bool {
    let args = match HooksInstallArgs::try_parse_from(
        std::iter::once("install".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let installer = hooks_installer();
    let target = hooks_target(args.project_root.as_deref());
    let result = match installer.install(&args.ide, &target) {
        Ok(r) => r,
        Err(e) => {
            // KeyError de Python (IDE desconocido) ⇒ mensaje entre comillas
            // dobles (str(KeyError) incluye las comillas exteriores).
            if e.contains("unknown IDE adapter") {
                eecho(&unknown_ide_message(&installer, &args.ide));
            } else {
                eecho(&format!("Could not install {}: {e}", args.ide));
            }
            std::process::exit(1);
        }
    };
    if args.json {
        echo(&format!(
            "{{\"ide\": {}, \"installed\": {}, \"modified_paths\": {}, \"message\": {}}}",
            json_quote(result.ide),
            if result.installed { "true" } else { "false" },
            json_quote_list(&result.modified_paths),
            json_quote(&result.message)
        ));
        return true;
    }
    let marker = if result.installed { "✓" } else { "✗" };
    echo(&format!("{marker} {}: {}", result.ide, result.message));
    for p in &result.modified_paths {
        echo(&format!("  modified: {}", p.display()));
    }
    true
}

#[derive(Parser, Debug)]
#[command(
    name = "uninstall",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
struct HooksUninstallArgs {
    #[arg(long, required = true)]
    pub ide: String,
    #[arg(long)]
    pub project_root: Option<String>,
    #[arg(long)]
    pub json: bool,
}

pub fn run_hooks_uninstall(argv: &[String]) -> bool {
    let args = match HooksUninstallArgs::try_parse_from(
        std::iter::once("uninstall".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let installer = hooks_installer();
    let target = hooks_target(args.project_root.as_deref());
    let result = match installer.uninstall(&args.ide, &target) {
        Ok(r) => r,
        Err(e) => {
            if e.contains("unknown IDE adapter") {
                eecho(&unknown_ide_message(&installer, &args.ide));
            } else {
                eecho(&e);
            }
            std::process::exit(1);
        }
    };
    if args.json {
        echo(&format!(
            "{{\"ide\": {}, \"uninstalled\": {}, \"removed_paths\": {}, \"message\": {}}}",
            json_quote(result.ide),
            if result.uninstalled { "true" } else { "false" },
            json_quote_list(&result.removed_paths),
            json_quote(&result.message)
        ));
        return true;
    }
    let marker = if result.uninstalled { "✓" } else { "—" };
    echo(&format!("{marker} {}: {}", result.ide, result.message));
    for p in &result.removed_paths {
        echo(&format!("  removed: {}", p.display()));
    }
    true
}

#[derive(Parser, Debug)]
#[command(
    name = "status",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
struct HooksStatusArgs {
    #[arg(long)]
    pub ide: Option<String>,
    #[arg(long)]
    pub project_root: Option<String>,
    #[arg(long)]
    pub json: bool,
}

pub fn run_hooks_status(argv: &[String]) -> bool {
    let args = match HooksStatusArgs::try_parse_from(
        std::iter::once("status".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let installer = hooks_installer();
    let target = hooks_target(args.project_root.as_deref());
    let statuses: Vec<cortex_setup::session_hooks::HookStatus> = match &args.ide {
        Some(ide) => match installer.status(ide, &target) {
            Ok(s) => vec![s],
            Err(e) => {
                if e.contains("unknown IDE adapter") {
                    eecho(&unknown_ide_message(&installer, ide));
                } else {
                    eecho(&e);
                }
                std::process::exit(1);
            }
        },
        None => installer.status_all(&target),
    };
    if args.json {
        let items: Vec<crate::pyjson::PyVal> = statuses.iter().map(hook_status_pv).collect();
        echo(&compact_dumps_utf8(&crate::pyjson::PyVal::Arr(items)));
        return true;
    }
    for s in &statuses {
        let marker = if s.installed { "✓" } else { "—" };
        echo(&format!("{marker} {}: {}", s.ide, s.detail));
    }
    true
}

pub fn run_hooks(argv: &[String]) -> bool {
    let Some(first) = argv.first().map(String::as_str) else {
        return false;
    };
    let rest = &argv[1..];
    match first {
        "list" => run_hooks_list(rest),
        "install" => run_hooks_install(rest),
        "uninstall" => run_hooks_uninstall(rest),
        "status" => run_hooks_status(rest),
        _ => false,
    }
}

// ---------------------------------------------------------------------------
// Tabla rich-compatible (port de rich.table.Table para task/hooks)
// ---------------------------------------------------------------------------
//
// Réplica byte-a-byte del render de `rich.table.Table` en consola no-TTY
// (width=80, box estándar con `show_edge`, padding (0,1), sin expand, sin
// título): `_calculate_column_widths` (medida natural + padding 2 por
// columna; colapso `_collapse_widths` + `ratio_reduce` al presupuesto
// `80 - extra_width`; re-medida que re-wrapa) + `Text.wrap` con
// `overflow="ellipsis"` por celda (word-wrap con fold-off, truncate "…",
// justify left/center) + caja ┏━┳━┓/┃ ┃/┡━╇━┩/└━┴━┘.

fn rich_is_ws(c: char) -> bool {
    matches!(c, ' ' | '\t' | '\n' | '\r' | '\u{0c}' | '\u{0b}')
}

/// Port de `words()` (rich/_wrap.py, regex `\s*\S+\s*`): tuplas
/// (start, end, palabra-con-whitespace) en índices de bytes.
fn rich_words(text: &str) -> Vec<(usize, usize)> {
    let chars: Vec<(usize, char)> = text.char_indices().collect();
    let n = chars.len();
    let mut out = Vec::new();
    let mut i = 0usize;
    while i < n {
        while i < n && rich_is_ws(chars[i].1) {
            i += 1;
        }
        let start = chars.get(i).map(|c| c.0).unwrap_or(text.len());
        while i < n && !rich_is_ws(chars[i].1) {
            i += 1;
        }
        // Todo whitespace ⇒ no hay palabra que emitir.
        if i >= n && start == text.len() {
            break;
        }
        // `\s*` final (pega al word para el span de Python).
        while i < n && rich_is_ws(chars[i].1) {
            i += 1;
        }
        let end = chars.get(i).map(|c| c.0).unwrap_or(text.len());
        out.push((start, end));
    }
    out
}

/// Port de `divide_line(text, width, fold=False)`.
fn rich_divide_line(text: &str, width: usize) -> Vec<usize> {
    let mut breaks = Vec::new();
    let mut cell_offset = 0usize;
    for (start, end) in rich_words(text) {
        let word = &text[start..end];
        let word_length = cell_width(word.trim_end());
        let remaining = width as i64 - cell_offset as i64;
        let fits = remaining >= word_length as i64;
        if fits {
            cell_offset = cell_offset.saturating_add(cell_width(word));
        } else if word_length > width {
            // fold=False ⇒ crop: romper antes de la palabra (si no es la
            // primera) y dejar que `truncate(…, ellipsis)` corte después.
            if start != 0 {
                breaks.push(start);
            }
            cell_offset = cell_width(word);
        } else if cell_offset != 0 && start != 0 {
            breaks.push(start);
            cell_offset = cell_width(word);
        }
    }
    breaks
}

/// Port de `Text.rstrip_end(width)` (quita whitespace final si la línea
/// excede el ancho), `set_cell_size` + `truncate(…, ellipsis)` y el
/// justify de `Lines.justify`.
fn rich_wrap_line(line: &str, width: usize, justify: &str) -> String {
    let mut s = line.to_string();
    // rstrip_end(width)
    let len = cell_width(&s);
    if len > width {
        let excess = len - width;
        let trailing: usize = s
            .chars()
            .rev()
            .take_while(|c| rich_is_ws(*c))
            .map(|c| c.width().unwrap_or(0))
            .sum();
        let crop = trailing.min(excess);
        let mut cut = 0usize;
        for c in s.chars().rev() {
            if cut >= crop {
                break;
            }
            if rich_is_ws(c) {
                cut += 1;
            }
        }
        if cut > 0 {
            let keep = s.chars().count() - cut;
            s = s.chars().take(keep).collect();
        }
    }
    let ellipsis_truncate = |t: &str, w: usize| -> String {
        let len = cell_width(t);
        if len <= w {
            t.to_string()
        } else {
            // set_cell_size(t, w - 1) + "…"
            let mut acc = String::new();
            let mut used = 0usize;
            for c in t.chars() {
                let cw = c.width().unwrap_or(0);
                if used + cw > w - 1 {
                    break;
                }
                acc.push(c);
                used += cw;
            }
            acc.push('…');
            acc
        }
    };
    match justify {
        "center" => {
            let trimmed = s.trim_end_matches(rich_is_ws);
            let t = ellipsis_truncate(trimmed, width);
            let len = cell_width(&t);
            if len < width {
                let left = (width - len) / 2;
                let right = width - len - left;
                format!("{}{}{}", " ".repeat(left), t, " ".repeat(right))
            } else {
                t
            }
        }
        _ => {
            // left: truncate(width, ellipsis, pad=True)
            let t = ellipsis_truncate(&s, width);
            let len = cell_width(&t);
            if len < width {
                format!("{t}{}", " ".repeat(width - len))
            } else {
                t
            }
        }
    }
}

/// Port de `Text.wrap(console, width, justify=…, overflow="ellipsis")` para
/// una celda de una línea.
fn rich_wrap_cell(cell: &str, width: usize, justify: &str) -> Vec<String> {
    let mut out = Vec::new();
    for line in cell.split('\n') {
        let breaks = rich_divide_line(line, width);
        let mut prev = 0usize;
        let mut pieces = Vec::new();
        for &b in &breaks {
            pieces.push(&line[prev..b]);
            prev = b;
        }
        pieces.push(&line[prev..]);
        if pieces.is_empty() {
            pieces.push("");
        }
        for p in pieces {
            out.push(rich_wrap_line(p, width, justify));
        }
    }
    out
}

/// Port de `ratio_reduce` de rich._ratio (los ratios ya vienen resueltos
/// como 0/1 por el llamador) con `round()` half-even de CPython.
fn rich_ratio_reduce(
    values: &[usize],
    ratios: &[usize],
    maximums: &[usize],
    total: usize,
) -> Vec<usize> {
    let mut total_ratio: usize = ratios.iter().sum();
    if total_ratio == 0 {
        return values.to_vec();
    }
    let mut remaining = total;
    let mut out = Vec::with_capacity(values.len());
    for ((v, &r), &m) in values.iter().zip(ratios).zip(maximums) {
        if r > 0 && total_ratio > 0 {
            let x = (r * remaining) as f64 / total_ratio as f64;
            let fl = x.floor();
            let frac = x - fl;
            let base = fl as i64;
            let rounded = if frac < 0.5 {
                base
            } else if frac > 0.5 {
                base + 1
            } else if base % 2 == 0 {
                base
            } else {
                base + 1
            };
            let distributed = m.min(rounded.max(0) as usize);
            out.push(v - distributed);
            remaining -= distributed;
            total_ratio -= r;
        } else {
            out.push(*v);
        }
    }
    out
}

/// Port de `_collapse_widths` (rich.table) sobre anchos CON padding.
fn rich_collapse(widths: &[usize], max_width: usize) -> Vec<usize> {
    let mut widths = widths.to_vec();
    let n = widths.len();
    let mut total: usize = widths.iter().sum();
    let mut excess = total as i64 - max_width as i64;
    while total > 0 && excess > 0 {
        let max_column = *widths.iter().max().unwrap();
        let second_max = widths
            .iter()
            .filter(|w| **w != max_column)
            .max()
            .copied()
            .unwrap_or(0);
        let column_difference = max_column - second_max;
        let ratios: Vec<usize> = widths
            .iter()
            .map(|w| if *w == max_column { 1 } else { 0 })
            .collect();
        if ratios.iter().all(|r| *r == 0) || column_difference == 0 {
            break;
        }
        let max_reduce = vec![excess.min(column_difference as i64) as usize; n];
        widths = rich_ratio_reduce(&widths, &ratios, &max_reduce, excess.max(0) as usize);
        total = widths.iter().sum();
        excess = total as i64 - max_width as i64;
    }
    widths
}

/// Render de tabla rich-compatible (ancho 80, versión pipeline).
fn render_rich_table(headers: &[&str], rows: &[Vec<String>], justify: &[&str]) -> String {
    let n = headers.len();
    let pad = 2usize; // padding rich (0,1)
    let extra_width = 2 + (n - 1); // `_extra_width`: bordes externos + internos
    let max_width = 80usize.saturating_sub(extra_width);
    // Medida natural (línea más ancha por columna) + padding.
    let mut widths: Vec<usize> = headers
        .iter()
        .enumerate()
        .map(|(i, h)| {
            let mut w = cell_width(h);
            for row in rows {
                let cw = row[i].split('\n').map(cell_width).max().unwrap_or(0);
                w = w.max(cw);
            }
            (w + pad).min(max_width)
        })
        .collect();
    let mut table_width: usize = widths.iter().sum();
    if table_width > max_width {
        widths = rich_collapse(&widths, max_width);
        table_width = widths.iter().sum();
        if table_width > max_width {
            // Último recurso: reducir parejo (ratio_reduce con ratios 1).
            let excess = table_width - max_width;
            let ratios = vec![1usize; n];
            let maximums = widths.clone();
            widths = rich_ratio_reduce(&widths, &ratios, &maximums, excess);
        }
    }
    let content_widths: Vec<usize> = widths.iter().map(|w| w - pad).collect();

    // Filas pre-renderizadas: (header + data). Cada celda → líneas wrap.
    let rich_cell = |cell: &str, i: usize| rich_wrap_cell(cell, content_widths[i], justify[i]);
    let header_lines: Vec<Vec<String>> = headers
        .iter()
        .enumerate()
        .map(|(i, h)| rich_cell(h, i))
        .collect();
    let data_lines: Vec<Vec<Vec<String>>> = rows
        .iter()
        .map(|row| {
            row.iter()
                .enumerate()
                .map(|(i, c)| rich_cell(c, i))
                .collect()
        })
        .collect();

    let border = |left: char, mid: char, right: char, fill: char| -> String {
        let mut s = String::new();
        s.push(left);
        for (i, w) in widths.iter().enumerate() {
            for _ in 0..*w {
                s.push(fill);
            }
            if i + 1 < n {
                s.push(mid);
            }
        }
        s.push(right);
        s
    };

    let emit_row = |cells: &[Vec<String>], out: &mut String, heavy: bool| {
        let sep = if heavy { '┃' } else { '│' };
        let height = cells.iter().map(Vec::len).max().unwrap_or(1);
        for li in 0..height {
            out.push(sep);
            for i in 0..n {
                let line = cells[i]
                    .get(li)
                    .cloned()
                    .unwrap_or_else(|| " ".repeat(content_widths[i]));
                out.push(' ');
                out.push_str(&line);
                out.push(' ');
                out.push(sep);
            }
            out.push('\n');
        }
    };

    let mut out = String::new();
    out.push_str(&border('┏', '┳', '┓', '━'));
    out.push('\n');
    emit_row(&header_lines, &mut out, true);
    out.push_str(&border('┡', '╇', '┩', '━'));
    out.push('\n');
    for cells in &data_lines {
        emit_row(cells, &mut out, false);
    }
    out.push_str(&border('└', '┴', '┘', '─'));
    out.push('\n');
    out
}

/// Despachador de la familia `session`. Devuelve false para pasar al CLI
/// Python (subcomandos no wireados).
pub fn run(argv: &[String]) -> bool {
    // argv[0] = "session"; el subcomando es argv[1].
    let Some(second) = argv.get(1).map(String::as_str) else {
        return false;
    };
    let rest = &argv[2..];
    match second {
        "current" => run_current(rest),
        "checkpoint" => run_checkpoint(rest),
        "switch" => run_switch(rest),
        "diff" => run_diff(rest),
        "abandon" => run_abandon(rest),
        "list" => run_list(rest),
        "show" => run_show(rest),
        "watch" | "tui" => run_watch(rest),
        "task" => run_task(rest),
        "hooks" => run_hooks(rest),
        _ => false,
    }
}
