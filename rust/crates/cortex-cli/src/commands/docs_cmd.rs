//! Native `cortex docs search` and `cortex docs migrate` routes.

use crate::pyjson::{Num, PyVal};
use clap::Parser;
use cortex_app::context::filters::{apply_filters, EnrichmentFilters};
use cortex_app::context::models::WorkContext;
use cortex_app::context::{presenter, ContextEnricher, ContextEnricherConfig};
use cortex_app::semantic::routing::{parse_doc_type, route_spec, DOC_TYPE_VALID_SLUGS};
use cortex_services::migration::{
    format_report, list_backups, migrate_vault, restore_backup, validate_vault, MigrateOpts,
};
use std::io::Write as _;
use std::path::{Path, PathBuf};

fn echo(s: &str) {
    let _ = writeln!(std::io::stdout(), "{s}");
}
fn fail(s: &str) -> bool {
    let _ = writeln!(std::io::stderr(), "{s}");
    true
}

#[derive(Parser, Debug)]
#[command(
    name = "search",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
struct SearchArgs {
    query: String,
    #[arg(long)]
    project_root: Option<String>,
    #[arg(long, short = 'k', default_value_t = 5)]
    top_k: usize,
    #[arg(long = "doc-type")]
    doc_type: Vec<String>,
    #[arg(long = "exclude-doc-type")]
    exclude_doc_type: Vec<String>,
    #[arg(long)]
    status: Vec<String>,
    #[arg(long)]
    tag: Vec<String>,
    #[arg(long = "tag-any")]
    tag_any: Vec<String>,
    #[arg(long, default_value = "all")]
    scope: String,
    #[arg(long = "max-age-days")]
    max_age_days: Option<i64>,
    #[arg(long = "project-id")]
    project_id: Vec<String>,
    #[arg(long)]
    strict: bool,
    #[arg(long = "format", short = 'f', default_value = "text")]
    format: String,
}

fn run_search(argv: &[String]) -> bool {
    let args = match SearchArgs::try_parse_from(
        std::iter::once("search".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => return fail(&e.to_string()),
    };
    if !matches!(args.format.as_str(), "text" | "json" | "compact") {
        return fail(&format!("Invalid --format value: {:?}", args.format));
    }
    if !matches!(args.scope.as_str(), "local" | "enterprise" | "all") {
        return fail("scope must be one of: local, enterprise, all");
    }
    if args.max_age_days.is_some_and(|n| n < 0) {
        return fail("max_age_days must be >= 0");
    }
    let root = crate::paths::resolve_project_root(args.project_root.as_deref());
    let mut mem = match crate::memory::NativeMemory::open(Some(&root)) {
        Ok(m) => m,
        Err(e) => {
            echo(&e.message());
            return true;
        }
    };
    let work = WorkContext {
        source: "manual".into(),
        keywords: args.query.split_whitespace().map(str::to_string).collect(),
        search_queries: vec![args.query.clone()],
        ..Default::default()
    };
    let Some(embedder) = mem.embedder.as_mut() else {
        return fail("embedding model is unavailable");
    };
    let mut bundle = match mem.episodic.store_mut() {
        Some(store) => ContextEnricher {
            episodic: store,
            semantic: &mem.semantic,
            config: ContextEnricherConfig::default(),
        }
        .enrich(&work, embedder, Some(args.top_k), chrono::Utc::now()),
        None => cortex_app::context::models::EnrichedBundle {
            work,
            items: vec![],
            total_searches: 0,
            total_raw_hits: 0,
            total_chars: 0,
            within_budget_override: None,
        },
    };
    let filters = EnrichmentFilters {
        doc_types: (!args.doc_type.is_empty()).then_some(args.doc_type),
        exclude_doc_types: args.exclude_doc_type,
        statuses_allowed: (!args.status.is_empty()).then_some(args.status),
        tags_required: args.tag,
        tags_any_of: args.tag_any,
        vault_scope: args.scope,
        max_age_days: args.max_age_days,
        project_ids: (!args.project_id.is_empty()).then_some(args.project_id),
        strict: args.strict,
        ..Default::default()
    };
    bundle.items = apply_filters(&bundle.items, Some(&filters));
    bundle.total_chars = bundle.items.iter().map(|i| i.content.chars().count()).sum();
    let rendered = match args.format.as_str() {
        "json" => bundle.to_json(ContextEnricherConfig::default().max_chars),
        "compact" => presenter::to_compact_grouped(&bundle),
        _ => presenter::to_markdown_grouped(&bundle),
    };
    echo(&rendered);
    true
}

#[derive(Parser, Debug)]
#[command(
    name = "migrate",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
struct MigrateArgs {
    #[arg(long)]
    project_root: Option<String>,
    #[arg(long)]
    path: Option<PathBuf>,
    #[arg(long)]
    apply: bool,
    #[arg(long)]
    force: bool,
    #[arg(long)]
    output: Option<PathBuf>,
    #[arg(long = "no-backup")]
    no_backup: bool,
    #[arg(long)]
    json: bool,
}

fn run_migrate(argv: &[String]) -> bool {
    let args = match MigrateArgs::try_parse_from(
        std::iter::once("migrate".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => return fail(&e.to_string()),
    };
    let root = crate::paths::resolve_project_root(args.project_root.as_deref());
    let vault = root.join("vault");
    let opts = MigrateOpts {
        apply: args.apply,
        force: args.force,
        path_filter: args
            .path
            .map(|p| if p.is_absolute() { p } else { vault.join(p) }),
        create_backup_archive: args.apply && !args.no_backup,
        ..Default::default()
    };
    let result = migrate_vault(&vault, &opts);
    if args.json {
        let payload = serde_json::json!({"applied":result.applied,"total_scanned":result.total_scanned,"migrated":result.migrated.iter().map(|d|d.path.to_string_lossy().to_string()).collect::<Vec<_>>(),"already_migrated":result.already_migrated.iter().map(|d|d.path.to_string_lossy().to_string()).collect::<Vec<_>>(),"unclassifiable":result.unclassifiable.iter().map(|d|serde_json::json!({"path":d.path.to_string_lossy(),"reason":d.reason})).collect::<Vec<_>>(),"errors":result.errors.iter().map(|d|serde_json::json!({"path":d.path.to_string_lossy(),"reason":d.reason})).collect::<Vec<_>>(),"backup_path":result.backup_path.as_ref().map(|p|p.to_string_lossy().to_string())});
        echo(&serde_json::to_string_pretty(&payload).unwrap());
        return true;
    }
    let report = format_report(&result);
    if let Some(path) = args.output {
        match std::fs::write(&path, &report) {
            Ok(()) => echo(&format!("Report written to {}", path.display())),
            Err(e) => return fail(&e.to_string()),
        }
    } else {
        echo(&report);
    }
    true
}

fn run_validate(argv: &[String]) -> bool {
    #[derive(Parser, Debug)]
    #[command(
        name = "validate",
        disable_help_subcommand = true,
        disable_version_flag = true
    )]
    struct ValidateArgs {
        #[arg(long)]
        project_root: Option<String>,
        // --all es el comportamiento por defecto en el oráculo (inert).
        #[arg(long)]
        all: bool,
        #[arg(long)]
        json: bool,
    }
    let args = match ValidateArgs::try_parse_from(
        std::iter::once("validate".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let root = crate::paths::resolve_project_root(args.project_root.as_deref());
    let vault = root.join("vault");
    let payload = validate_vault(&vault);
    if args.json {
        let issues: Vec<PyVal> = payload
            .issues
            .iter()
            .map(|(path, err)| {
                PyVal::obj(vec![
                    ("path", PyVal::s(path.clone())),
                    ("error", PyVal::s(err.clone())),
                ])
            })
            .collect();
        let pv = PyVal::obj(vec![
            ("vault_path", PyVal::s(payload.vault_path_str.clone())),
            ("total", PyVal::Num(Num::Int(payload.total as i64))),
            ("valid", PyVal::Num(Num::Int(payload.valid as i64))),
            ("invalid", PyVal::Num(Num::Int(payload.invalid as i64))),
            (
                "no_frontmatter",
                PyVal::Num(Num::Int(payload.no_frontmatter as i64)),
            ),
            ("issues", PyVal::Arr(issues)),
        ]);
        echo(&crate::pyjson::stdlib_dumps_indent2(&pv));
        return true;
    }
    echo(&format!("Vault: {}", payload.vault_path_str));
    echo(&format!("Total notes: {}", payload.total));
    echo(&format!("Valid: {}", payload.valid));
    echo(&format!("Invalid: {}", payload.invalid));
    echo(&format!("No frontmatter: {}", payload.no_frontmatter));
    if !payload.issues.is_empty() {
        echo("\nIssues:");
        for (path, err) in &payload.issues {
            echo(&format!("  - {path}: {err}"));
        }
    }
    true
}

fn run_restore(argv: &[String]) -> bool {
    #[derive(Parser, Debug)]
    #[command(
        name = "restore",
        disable_help_subcommand = true,
        disable_version_flag = true
    )]
    struct RestoreArgs {
        #[arg(long)]
        backup: String,
        #[arg(long)]
        target: Option<PathBuf>,
        #[arg(long)]
        project_root: Option<String>,
    }
    let args = match RestoreArgs::try_parse_from(
        std::iter::once("restore".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let root = crate::paths::resolve_project_root(args.project_root.as_deref());
    let vault = root.join("vault");
    let backups_dir = vault
        .parent()
        .unwrap_or(Path::new("."))
        .join(".cortex")
        .join("backups");
    let explicit = PathBuf::from(&args.backup);
    let backup_path = if explicit.exists() {
        explicit
    } else {
        // Resolución por nombre corto: candidatos donde `backup in p.name`;
        // último de la lista (orden por nombre), igual que el oráculo.
        let candidates: Vec<PathBuf> = list_backups(&backups_dir)
            .into_iter()
            .filter(|p| {
                p.file_name()
                    .and_then(|n| n.to_str())
                    .map(|n| n.contains(&args.backup))
                    .unwrap_or(false)
            })
            .collect();
        if candidates.is_empty() {
            eprintln!("Backup not found: {}", args.backup);
            std::process::exit(1);
        }
        candidates[candidates.len() - 1].clone()
    };
    let target = args
        .target
        .unwrap_or_else(|| vault.parent().unwrap_or(Path::new(".")).to_path_buf());
    match restore_backup(&backup_path, &target) {
        Ok(restored) => echo(&format!("Restored: {}", restored.display())),
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(1);
        }
    }
    true
}

fn run_list_backups(argv: &[String]) -> bool {
    #[derive(Parser, Debug)]
    #[command(
        name = "list-backups",
        disable_help_subcommand = true,
        disable_version_flag = true
    )]
    struct ListBackupsArgs {
        #[arg(long)]
        project_root: Option<String>,
    }
    let args = match ListBackupsArgs::try_parse_from(
        std::iter::once("list-backups".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let root = crate::paths::resolve_project_root(args.project_root.as_deref());
    let vault = root.join("vault");
    let backups_dir = vault
        .parent()
        .unwrap_or(Path::new("."))
        .join(".cortex")
        .join("backups");
    let backups = list_backups(&backups_dir);
    if backups.is_empty() {
        echo(&format!("No backups found in {}", backups_dir.display()));
        return true;
    }
    for b in &backups {
        let size = std::fs::metadata(b).map(|m| m.len()).unwrap_or(0);
        let name = b.file_name().unwrap_or_default().to_string_lossy();
        echo(&format!("{name}\t{size} bytes"));
    }
    true
}

/// `_spec_to_serializable` del oráculo (orden del `asdict` frozen dataclass).
fn spec_to_pv(spec: &cortex_app::semantic::routing::RouteSpec) -> PyVal {
    PyVal::obj(vec![
        ("doc_type", PyVal::s(spec.doc_type.value())),
        ("subfolder", PyVal::s(spec.subfolder)),
        ("filename_template", PyVal::s(spec.filename_template)),
        ("template_path", PyVal::s(spec.template_path.clone())),
        ("writer", PyVal::s(spec.writer)),
        ("indexer", PyVal::s(spec.indexer)),
        ("promotable", PyVal::Bool(spec.promotable)),
        ("promotion_mode", PyVal::s(spec.promotion_mode)),
        (
            "enterprise_subfolder",
            match spec.enterprise_subfolder {
                Some(s) => PyVal::s(s),
                None => PyVal::Null,
            },
        ),
        (
            "retrieval_boost_per_intent",
            PyVal::Obj(
                spec.retrieval_boost_per_intent
                    .iter()
                    .map(|(k, v)| (k.to_string(), PyVal::Num(Num::Float(*v))))
                    .collect(),
            ),
        ),
        ("chunking_enabled", PyVal::Bool(spec.chunking_enabled)),
        (
            "chunking_min_words",
            PyVal::Num(Num::Int(spec.chunking_min_words as i64)),
        ),
        ("chunking_boundary", PyVal::s(spec.chunking_boundary)),
        ("webgraph_color", PyVal::s(spec.webgraph_color)),
        ("webgraph_shape", PyVal::s(spec.webgraph_shape)),
        (
            "requires_review_before_publish",
            PyVal::Bool(spec.requires_review_before_publish),
        ),
        (
            "auto_expire_days",
            PyVal::Num(Num::Int(spec.auto_expire_days as i64)),
        ),
    ])
}

/// Panel de error typer (BadParameter) byte-parity en consola no-TTY de 80
/// columnas: título " Error ", padding (1,1), wrap greedy a 76 celdas.
fn typer_error_panel(message: &str) -> String {
    use unicode_width::UnicodeWidthChar;
    let width = |s: &str| s.chars().map(|c| c.width().unwrap_or(0)).sum::<usize>();
    let inner = 76usize;
    let mut wrapped: Vec<String> = Vec::new();
    let mut cur = String::new();
    let mut used = 0usize;
    for word in message.split(' ') {
        let w = width(word);
        if used > 0 && used + 1 + w > inner {
            wrapped.push(std::mem::take(&mut cur));
            used = 0;
        }
        if used > 0 {
            cur.push(' ');
            used += 1;
        }
        cur.push_str(word);
        used += w;
    }
    wrapped.push(cur);

    let mut out = String::new();
    // borde superior: título " Error " a la izquierda (panel rich de typer).
    out.push('╭');
    out.push('─');
    out.push_str(" Error ");
    for _ in 0..70 {
        out.push('─');
    }
    out.push_str("╮\n");
    for line in &wrapped {
        out.push('│');
        out.push(' ');
        let w = width(line);
        out.push_str(line);
        for _ in w..inner {
            out.push(' ');
        }
        out.push(' ');
        out.push_str("│\n");
    }
    out.push('╰');
    for _ in 0..78 {
        out.push('─');
    }
    out.push_str("╯\n");
    out
}

/// Error BadParameter de typer para `--doc-type` inválido (stderr, rc 2).
fn routing_table_invalid_doc_type(raw: &str) -> ! {
    let valid: Vec<String> = DOC_TYPE_VALID_SLUGS
        .iter()
        .map(|s| format!("'{s}'"))
        .collect();
    let repr_raw = format!("'{raw}'");
    let message = format!(
        "Invalid value: Unknown doc_type: {repr_raw}. Valid: [{}]",
        valid.join(", ")
    );
    eprint!(
        "Usage: cortex docs routing-table [OPTIONS]\n\
         Try 'cortex docs routing-table --help' for help.\n{}",
        typer_error_panel(&message)
    );
    std::process::exit(2);
}

fn run_routing_table(argv: &[String]) -> bool {
    #[derive(Parser, Debug)]
    #[command(
        name = "routing-table",
        disable_help_subcommand = true,
        disable_version_flag = true
    )]
    struct RoutingTableArgs {
        #[arg(long = "doc-type")]
        doc_type: Option<String>,
        #[arg(long)]
        json: bool,
    }
    let args = match RoutingTableArgs::try_parse_from(
        std::iter::once("routing-table".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let specs = match &args.doc_type {
        Some(raw) => match parse_doc_type(raw) {
            Some(dt) => vec![route_spec(dt)],
            None => routing_table_invalid_doc_type(raw),
        },
        None => cortex_app::semantic::routing::list_all_routes(),
    };
    if args.json {
        let payload: Vec<PyVal> = specs.iter().map(spec_to_pv).collect();
        if payload.len() == 1 && args.doc_type.is_some() {
            echo(&crate::pyjson::stdlib_dumps_indent2(&payload[0].clone()));
        } else {
            echo(&crate::pyjson::stdlib_dumps_indent2(&PyVal::Arr(payload)));
        }
        return true;
    }
    let header = format!(
        "{:<14} {:<14} {:<38} {:<22} {:<8} {:<14}",
        "DocType", "Subfolder", "Filename pattern", "Writer", "Indexer", "Promote"
    );
    echo(&header);
    echo(&"-".repeat(header.chars().count()));
    for spec in &specs {
        let promote = if spec.promotable {
            spec.promotion_mode
        } else {
            "no"
        };
        echo(&format!(
            "{:<14} {:<14} {:<38} {:<22} {:<8} {:<14}",
            spec.doc_type.value(),
            spec.subfolder,
            spec.filename_template,
            spec.writer,
            spec.indexer,
            promote
        ));
    }
    true
}

pub fn run(argv: &[String]) -> bool {
    match argv.first().map(String::as_str) {
        Some("search") => run_search(&argv[1..]),
        Some("migrate") => run_migrate(&argv[1..]),
        Some("validate") => run_validate(&argv[1..]),
        Some("restore") => run_restore(&argv[1..]),
        Some("list-backups") => run_list_backups(&argv[1..]),
        Some("routing-table") => run_routing_table(&argv[1..]),
        Some(first) => {
            eprintln!("No such command '{first}'.");
            std::process::exit(2);
        }
        None => {
            eprintln!("cortex docs: se requiere un subcomando");
            std::process::exit(2);
        }
    }
}
