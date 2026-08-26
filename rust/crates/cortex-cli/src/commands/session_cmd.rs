//! Comandos `cortex session …` (Cierre T2) — espejo de cli/session.py.
//!
//! Cubre current/list/show/diff/switch/checkpoint/abandon sobre
//! SessionService nativo (P4). El JSON de record replica
//! `model_dump(mode="json")` con orden pydantic. La tabla rich de `list`
//! texto se replica para los casos del gate; watch/TUI queda en passthrough
//! (decisión doc 09 §3.8 — reemplazo ratatui es T6).

use std::io::Write as _;

use clap::Parser;
use cortex_app::session::service::SessionService;
use cortex_app::session::{CheckpointSource, SessionRecord, SessionStatus, SessionStorage};
use cortex_workspace::WorkspaceLayout;

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

/// Despachador de la familia `session`. Devuelve false para pasar al CLI
/// Python (subcomandos no wireados: watch, hooks y task).
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
        _ => false,
    }
}
