//! Native `cortex docs search` and `cortex docs migrate` routes.

use clap::Parser;
use cortex_app::context::filters::{apply_filters, EnrichmentFilters};
use cortex_app::context::models::WorkContext;
use cortex_app::context::{presenter, ContextEnricher, ContextEnricherConfig};
use cortex_services::migration::{format_report, migrate_vault, MigrateOpts};
use std::io::Write as _;
use std::path::PathBuf;

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

pub fn run(argv: &[String]) -> bool {
    match argv.first().map(String::as_str) {
        Some("search") => run_search(&argv[1..]),
        Some("migrate") => run_migrate(&argv[1..]),
        _ => false,
    }
}
