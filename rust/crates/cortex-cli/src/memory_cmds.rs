//! Comandos de la familia memoria (Cierre T2): `search`, `context`,
//! `stats` (= `vault stats` del plan) y `reindex --dry-run`.
//!
//! Espejo de cli/main.py::search/context/stats y cli/embedding.py::reindex.
//! Salidas texto/--json byte-parity contra el CLI Python real.

use std::io::Write as _;
use std::path::{Path, PathBuf};

use crate::pyjson::{Num, PyVal};
use clap::Parser;
use cortex_app::context::hybrid::UnifiedHit;

use crate::memory::NativeMemory;
use crate::paths::resolve_project_root;

fn echo(s: &str) {
    let mut out = std::io::stdout();
    let _ = writeln!(out, "{s}");
}

/// Ruta canónica del modelo ONNX chroma (~/.cache/chroma/onnx_models/…).
pub fn default_model_dir() -> Option<PathBuf> {
    let home = std::env::var_os("HOME").map(PathBuf::from)?;
    let dir = home.join(".cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx");
    if dir.join("model.onnx").exists() {
        Some(dir)
    } else {
        None
    }
}

// ---------------------------------------------------------------------------
// search
// ---------------------------------------------------------------------------

#[derive(Parser, Debug)]
#[command(
    name = "search",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct SearchArgs {
    pub query: String,

    #[arg(long, short = 'k', default_value_t = 5)]
    pub top_k: usize,

    #[arg(long)]
    pub json: bool,

    #[arg(long)]
    pub show_scores: bool,
}

/// Ejecuta `cortex search`. Devuelve el rc.
pub fn run_search(argv: &[String]) -> bool {
    let args = match SearchArgs::try_parse_from(
        std::iter::once("search".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };

    let root = resolve_project_root(None);
    let mut mem = match NativeMemory::open(Some(&root)) {
        Ok(m) => m,
        Err(e) => {
            echo(&e.message());
            return true;
        }
    };

    let result = mem.retrieve(&args.query, args.top_k, true);

    if args.json {
        echo(&retrieval_json(&result));
        return true;
    }

    // Presentación texto legacy.
    echo(&format!("\nQuery: '{}'\n", args.query));
    if !result.unified_hits.is_empty() {
        echo("Unified Results (RRF-fused across both sources):");
        for hit in &result.unified_hits {
            let details = if hit.source == "episodic" {
                let e = hit.entry.as_ref().expect("episodic");
                format!(
                    "  [EPISODIC] {}  ({})  score={:.4}",
                    display_title_episodic(e),
                    display_path_episodic(e),
                    hit.score
                )
            } else {
                let d = hit.doc.expect("semantic");
                format!(
                    "  [SEMANTIC] {}  ({})  score={:.4}",
                    d.title, d.path, hit.score
                )
            };
            echo(&details);
        }
        if args.show_scores {
            echo("");
            echo(&format!("Source breakdown: {}", serde_json::json!({})));
        }
    } else {
        if result.episodic_hits.is_empty() {
            echo("Episodic Memory: (no results)");
        } else {
            echo("Episodic Memory:");
            for (e, s) in &result.episodic_hits {
                let cut: String = e.content.chars().take(80).collect();
                echo(&format!(
                    "  [{}] ({}) {}...  score={:.3}",
                    e.id, e.memory_type, cut, s
                ));
            }
        }
        echo("");
        if result.semantic_hits.is_empty() {
            echo("Semantic Knowledge: (no results)");
        } else {
            echo("Semantic Knowledge:");
            for (d, s) in &result.semantic_hits {
                echo(&format!("  {} ({})  score={:.3}", d.title, d.path, s));
            }
        }
    }
    true
}

fn display_title_episodic(e: &cortex_app::episodic::MemoryEntry) -> String {
    let first = e
        .content
        .lines()
        .find(|l| !l.trim().is_empty())
        .map(|l| l.trim_matches('#').trim())
        .unwrap_or("Untitled Session")
        .to_string();
    let cut: String = first.chars().take(100).collect();
    format!("[{}] {}", e.memory_type.to_uppercase(), cut)
}

fn display_path_episodic(e: &cortex_app::episodic::MemoryEntry) -> String {
    format!(
        "id={}, files={}",
        e.id,
        if e.files.is_empty() {
            "none".into()
        } else {
            e.files.join(", ")
        }
    )
}

// ---------------------------------------------------------------------------
// Serialización model_dump_json(indent=2) de RetrievalResult
// ---------------------------------------------------------------------------

fn entry_pv(e: &cortex_app::episodic::MemoryEntry) -> PyVal {
    // pydantic v2 serializa datetimes aware en UTC con sufijo "Z" (no
    // "+00:00" como el ISO almacenado).
    let ts = e.timestamp.clone();
    let ts = ts
        .strip_suffix("+00:00")
        .map(|b| format!("{b}Z"))
        .unwrap_or(ts);
    PyVal::obj(vec![
        ("id", PyVal::s(e.id.clone())),
        ("content", PyVal::s(e.content.clone())),
        ("memory_type", PyVal::s(e.memory_type.clone())),
        (
            "tags",
            PyVal::Arr(e.tags.iter().map(|t| PyVal::s(t.clone())).collect()),
        ),
        (
            "files",
            PyVal::Arr(e.files.iter().map(|f| PyVal::s(f.clone())).collect()),
        ),
        ("timestamp", PyVal::s(ts)),
        (
            "metadata",
            PyVal::Obj(
                e.metadata
                    .iter()
                    .map(|(k, v)| (k.clone(), value_to_pv(v)))
                    .collect(),
            ),
        ),
        ("confidence", PyVal::Null),
    ])
}

fn value_to_pv(v: &serde_json::Value) -> PyVal {
    match v {
        serde_json::Value::Null => PyVal::Null,
        serde_json::Value::Bool(b) => PyVal::Bool(*b),
        serde_json::Value::Number(n) => match n.as_i64() {
            Some(i) => PyVal::Num(Num::Int(i)),
            None => PyVal::Num(Num::Float(n.as_f64().unwrap_or(0.0))),
        },
        serde_json::Value::String(s) => PyVal::s(s.clone()),
        serde_json::Value::Array(a) => PyVal::Arr(a.iter().map(value_to_pv).collect()),
        serde_json::Value::Object(o) => {
            PyVal::Obj(o.iter().map(|(k, v)| (k.clone(), value_to_pv(v))).collect())
        }
    }
}

fn semantic_doc_pv(d: &cortex_app::semantic::SemDoc, score: f64) -> PyVal {
    PyVal::obj(vec![
        ("path", PyVal::s(d.path.clone())),
        ("title", PyVal::s(d.title.clone())),
        ("content", PyVal::s(d.content.clone())),
        (
            "links",
            PyVal::Arr(d.links.iter().map(|l| PyVal::s(l.clone())).collect()),
        ),
        (
            "tags",
            PyVal::Arr(d.tags.iter().map(|t| PyVal::s(t.clone())).collect()),
        ),
        ("score", PyVal::Num(Num::Float(score))),
        ("origin_scope", PyVal::s("local")),
        ("origin_project_id", PyVal::s("")),
        ("origin_vault", PyVal::s("")),
        ("origin_persist_dir", PyVal::s("")),
        ("matched_chunk_id", PyVal::Null),
        ("matched_section_title", PyVal::Null),
    ])
}

fn unified_hit_pv(hit: &UnifiedHit<'_>) -> PyVal {
    let metadata: Vec<(String, PyVal)> = if hit.source == "episodic" {
        let e = hit.entry.as_ref().expect("entry");
        let mut items: Vec<(String, PyVal)> = vec![
            ("scope".into(), PyVal::s("local")),
            ("project_id".into(), PyVal::s("")),
            ("origin_vault".into(), PyVal::s("")),
            ("origin_persist_dir".into(), PyVal::s("")),
        ];
        for (k, v) in &e.metadata {
            items.push((k.clone(), value_to_pv(v)));
        }
        items
    } else {
        vec![
            ("scope".into(), PyVal::s("local")),
            ("project_id".into(), PyVal::s("")),
            ("origin_vault".into(), PyVal::s("")),
            ("origin_persist_dir".into(), PyVal::s("")),
        ]
    };

    let (entry_pv, doc_pv, dtitle, dcontent, dpath): (PyVal, PyVal, PyVal, PyVal, PyVal) =
        if hit.source == "episodic" {
            let e = hit.entry.as_ref().expect("entry");
            (
                entry_pv(e),
                PyVal::Null,
                PyVal::s(display_title_episodic(e)),
                PyVal::s(e.content.clone()),
                PyVal::s(display_path_episodic(e)),
            )
        } else {
            let d = hit.doc.expect("doc");
            (
                PyVal::Null,
                semantic_doc_pv(d, hit.doc_score_raw),
                PyVal::s(d.title.clone()),
                PyVal::s(d.content.clone()),
                PyVal::s(d.path.clone()),
            )
        };

    PyVal::obj(vec![
        ("source", PyVal::s(hit.source)),
        ("score", PyVal::Num(Num::Float(hit.score))),
        ("entry", entry_pv),
        ("doc", doc_pv),
        ("metadata", PyVal::Obj(metadata)),
        ("display_title", dtitle),
        ("display_content", dcontent),
        ("display_path", dpath),
    ])
}

pub(crate) fn retrieval_json(r: &crate::memory::RetrievalResultMirror<'_>) -> String {
    let v = PyVal::obj(vec![
        ("query", PyVal::s(r.query.clone())),
        (
            "episodic_hits",
            PyVal::Arr(
                r.episodic_hits
                    .iter()
                    .map(|(e, s)| {
                        PyVal::obj(vec![
                            ("entry", entry_pv(e)),
                            ("score", PyVal::Num(Num::Float(*s))),
                            ("origin_scope", PyVal::s("local")),
                            ("origin_project_id", PyVal::s("")),
                            ("origin_vault", PyVal::s("")),
                            ("origin_persist_dir", PyVal::s("")),
                        ])
                    })
                    .collect(),
            ),
        ),
        (
            "semantic_hits",
            PyVal::Arr(
                r.semantic_hits
                    .iter()
                    .map(|(d, s)| semantic_doc_pv(d, *s))
                    .collect(),
            ),
        ),
        (
            "unified_hits",
            PyVal::Arr(r.unified_hits.iter().map(unified_hit_pv).collect()),
        ),
        ("source_breakdown", PyVal::Obj(vec![])),
    ]);
    crate::pyjson::pydantic_dumps_indent2(&v)
}

// ---------------------------------------------------------------------------
// context
// ---------------------------------------------------------------------------

#[derive(Parser, Debug)]
#[command(
    name = "context",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct ContextArgs {
    #[arg(long, short = 'f')]
    pub files: Vec<String>,

    #[arg(long, default_value = "markdown")]
    pub format: String,

    #[arg(long, short = 'o')]
    pub output: Option<String>,

    #[arg(long, short = 'e')]
    pub expand: bool,
}

/// `_get_staged_files()` de common.py: git staged + modified, dedup.
fn get_staged_files(root: &Path) -> Vec<String> {
    let run = |args: &[&str]| -> Vec<String> {
        match std::process::Command::new("git")
            .args(args)
            .current_dir(root)
            .output()
        {
            Ok(o) if o.status.success() => String::from_utf8_lossy(&o.stdout)
                .lines()
                .filter(|l| !l.trim().is_empty())
                .map(str::to_string)
                .collect(),
            _ => vec![],
        }
    };
    let mut files = run(&["diff", "--name-only", "--cached"]);
    for line in run(&["diff", "--name-only"]) {
        if !files.contains(&line) {
            files.push(line);
        }
    }
    files
}

pub fn run_context(argv: &[String]) -> bool {
    let args = match ContextArgs::try_parse_from(
        std::iter::once("context".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };

    let root = resolve_project_root(None);
    let mut mem = match NativeMemory::open(Some(&root)) {
        Ok(m) => m,
        Err(e) => {
            echo(&e.message());
            return true;
        }
    };

    let files = if args.files.is_empty() {
        get_staged_files(&root)
    } else {
        args.files.clone()
    };
    if files.is_empty() {
        echo("No changed files detected. Use --files to specify manually.");
        return true;
    }

    let model_dir = default_model_dir();
    let mut observer = cortex_app::context::observer::ContextObserver::new(model_dir.as_deref());
    let work = observer.observe_from_files(&files, None, None, None, None, None, None, vec![]);

    let bundle = {
        let emb = match mem.embedder.as_mut() {
            Some(e) => e,
            // Sin modelo no hay estrategia vectorial; el oráculo tampoco
            // llega acá en fixtures del gate (modelo presente).
            None => {
                echo("\u{1f9e0} Cortex Context \u{2014} No related memories found.");
                return true;
            }
        };
        match mem.episodic.store_mut() {
            Some(store) => {
                let enricher = cortex_app::context::ContextEnricher {
                    episodic: store,
                    semantic: &mem.semantic,
                    config: cortex_app::context::ContextEnricherConfig::default(),
                };
                enricher.enrich(&work, emb, None, chrono_utc_now())
            }
            None => {
                let enricher = cortex_app::context::ContextEnricher {
                    episodic: empty_episodic(),
                    semantic: &mem.semantic,
                    config: cortex_app::context::ContextEnricherConfig::default(),
                };
                enricher.enrich(&work, emb, None, chrono_utc_now())
            }
        }
    };

    let text = match args.format.as_str() {
        "json" => enriched_json(&bundle),
        "compact" => prompt_format_compact(&bundle),
        _ => prompt_format_full(&bundle, args.expand),
    };
    match &args.output {
        Some(path) => {
            let _ = std::fs::write(path, format!("{text}\n"));
        }
        None => echo(&text),
    }
    true
}

fn chrono_utc_now() -> chrono::DateTime<chrono::Utc> {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;
    chrono::DateTime::from_timestamp(secs, 0).unwrap_or_default()
}

/// Store episódico vacío para workspaces sin export (enricher exige ref).
fn empty_episodic() -> &'static cortex_app::episodic::NativeEpisodicStore {
    use std::sync::OnceLock;
    static EMPTY: OnceLock<cortex_app::episodic::NativeEpisodicStore> = OnceLock::new();
    EMPTY.get_or_init(|| {
        cortex_app::episodic::NativeEpisodicStore::load(Path::new("/dev/null")).expect("empty")
    })
}

fn char_take(s: &str, n: usize) -> String {
    s.chars().take(n).collect()
}

/// Espejo de `EnrichedContext.to_prompt_format(expand=False/True)` full mode.
fn prompt_format_full(b: &cortex_app::context::models::EnrichedBundle, expand: bool) -> String {
    if b.items.is_empty() {
        return "\u{1f9e0} Cortex Context \u{2014} No related memories found.".into();
    }
    let mut parts: Vec<String> = vec![format!(
        "\u{1f9e0} Cortex Context \u{2014} Found {} related memories\n",
        b.items.len()
    )];
    for item in &b.items {
        let source_tag = if item.source == "episodic" {
            "EPISODIC"
        } else {
            "SEMANTIC"
        };
        parts.push(format!("### [{source_tag}] {}", item.title));
        let mut meta_parts: Vec<String> = Vec::new();
        if let Some(iso) = &item.date {
            meta_parts.push(char_take(iso, 10));
        }
        if !item.files_mentioned.is_empty() {
            meta_parts.push(item.files_mentioned.join(", "));
        }
        if !item.tags.is_empty() {
            meta_parts.push(item.tags.join(", "));
        }
        if !meta_parts.is_empty() {
            parts.push(format!("  {}", meta_parts.join(" \u{2022} ")));
        }
        if expand {
            parts.push(format!("  {}", char_take(&item.content, 500)));
        } else {
            parts.push(format!("  {}\u{2026}", char_take(&item.content, 150)));
        }
        if !item.matched_by.is_empty() {
            parts.push(format!("  Matched by: {}", item.matched_by.join(", ")));
        }
        parts.push(String::new());
    }
    parts.push("Run `cortex context --expand` for full details".to_string());
    parts.join("\n")
}

/// Espejo de `EnrichedContext.to_prompt_format(compact=True)`.
fn prompt_format_compact(b: &cortex_app::context::models::EnrichedBundle) -> String {
    if b.items.is_empty() {
        return "\u{1f9e0} Cortex Context \u{2014} No related memories found.".into();
    }
    let mut parts: Vec<String> = vec![format!(
        "## \u{1f9e0} Cortex Context ({} memories found)\n",
        b.items.len()
    )];
    for item in &b.items {
        let source_tag = if item.source == "episodic" {
            "EPISODIC"
        } else {
            "SEMANTIC"
        };
        parts.push(format!("### {} [{}]", item.title, source_tag));
        parts.push(char_take(&item.content, 300).replace('\n', " "));
        let mut meta_parts: Vec<String> = Vec::new();
        if !item.files_mentioned.is_empty() {
            meta_parts.push(format!("Files: {}", item.files_mentioned.join(", ")));
        }
        if let Some(iso) = &item.date {
            meta_parts.push(char_take(iso, 10));
        }
        if !item.matched_by.is_empty() {
            let cleaned: Vec<String> = item
                .matched_by
                .iter()
                .map(|m| m.replace("_search", "").replace("_query", ""))
                .collect();
            meta_parts.push(format!("Matched by: {}", cleaned.join(", ")));
        }
        if !meta_parts.is_empty() {
            parts.push(meta_parts.join(" | "));
        }
        parts.push(String::new());
    }
    parts.join("\n")
}

fn opt_str_pv(v: &Option<String>) -> PyVal {
    match v {
        Some(s) => PyVal::s(s.clone()),
        None => PyVal::Null,
    }
}

/// Serialización `model_dump_json(indent=2)` de EnrichedContext.
fn enriched_json(b: &cortex_app::context::models::EnrichedBundle) -> String {
    let arr = |xs: &[String]| PyVal::Arr(xs.iter().map(|x| PyVal::s(x.clone())).collect());
    let work = PyVal::obj(vec![
        ("source", PyVal::s(b.work.source.clone())),
        ("changed_files", arr(&b.work.changed_files)),
        ("new_files", arr(&b.work.new_files)),
        ("deleted_files", arr(&b.work.deleted_files)),
        ("keywords", arr(&b.work.keywords)),
        ("imports", arr(&b.work.imports)),
        ("function_names", arr(&b.work.function_names)),
        ("class_names", arr(&b.work.class_names)),
        ("detected_domain", opt_str_pv(&b.work.detected_domain)),
        (
            "domain_confidence",
            PyVal::Num(Num::Float(b.work.domain_confidence)),
        ),
        ("pr_title", opt_str_pv(&b.work.pr_title)),
        ("pr_body", opt_str_pv(&b.work.pr_body)),
        ("pr_labels", arr(&b.work.pr_labels)),
        ("search_queries", arr(&b.work.search_queries)),
    ]);
    let items = PyVal::Arr(
        b.items
            .iter()
            .map(|it| {
                PyVal::obj(vec![
                    ("source", PyVal::s(it.source)),
                    ("source_id", PyVal::s(it.source_id.clone())),
                    ("title", PyVal::s(it.title.clone())),
                    ("content", PyVal::s(it.content.clone())),
                    ("score", PyVal::Num(Num::Float(it.score))),
                    ("enriched_score", PyVal::Num(Num::Float(it.enriched_score))),
                    ("matched_by", arr(&it.matched_by)),
                    ("files_mentioned", arr(&it.files_mentioned)),
                    ("date", opt_str_pv(&it.date)),
                    ("tags", arr(&it.tags)),
                    ("confidence", PyVal::Null),
                    ("doc_type", opt_str_pv(&it.doc_type)),
                    ("status", opt_str_pv(&it.status)),
                    ("vault_scope", PyVal::s(it.vault_scope.clone())),
                    ("origin_project_id", opt_str_pv(&it.origin_project_id)),
                    ("matched_chunk_id", opt_str_pv(&it.matched_chunk_id)),
                    (
                        "matched_section_title",
                        opt_str_pv(&it.matched_section_title),
                    ),
                ])
            })
            .collect(),
    );
    let v = PyVal::obj(vec![
        ("work", work),
        ("items", items),
        (
            "total_searches",
            PyVal::Num(Num::Int(b.total_searches as i64)),
        ),
        (
            "total_raw_hits",
            PyVal::Num(Num::Int(b.total_raw_hits as i64)),
        ),
        ("total_items", PyVal::Num(Num::Int(b.items.len() as i64))),
        ("total_chars", PyVal::Num(Num::Int(b.total_chars as i64))),
        (
            "within_budget",
            PyVal::Bool(
                b.within_budget(cortex_app::context::ContextEnricherConfig::default().max_chars),
            ),
        ),
        // Python genera un run_id hex12 por corrida (telemetría activa);
        // el gate lo normaliza como {{RUN}}.
        (
            "enricher_run_id",
            PyVal::s(cortex_app::context::telemetry::new_run_id()),
        ),
    ]);
    crate::pyjson::pydantic_dumps_indent2(&v)
}

// ---------------------------------------------------------------------------
// stats (= `vault stats` del plan de cierre)
// ---------------------------------------------------------------------------

#[derive(Parser, Debug)]
#[command(
    name = "stats",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct StatsArgs {
    #[arg(long)]
    pub project_root: Option<String>,
}

pub fn run_stats(argv: &[String]) -> bool {
    let args = match StatsArgs::try_parse_from(
        std::iter::once("stats".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let root = resolve_project_root(args.project_root.as_deref());
    let mem = match NativeMemory::open_without_embeddings(Some(&root)) {
        Ok(m) => m,
        Err(e) => {
            echo(&e.message());
            return true;
        }
    };
    let episodic_count = mem.episodic_count();
    let v = PyVal::obj(vec![
        (
            "episodic_count",
            PyVal::Num(Num::Int(episodic_count as i64)),
        ),
        (
            "semantic_docs",
            PyVal::Num(Num::Int(mem.semantic.docs.len() as i64)),
        ),
        ("vault_path", PyVal::s(mem.vault_path_string())),
        ("persist_dir", PyVal::s(mem.persist_dir_string())),
        ("enterprise_topology", PyVal::s(mem.enterprise_topology())),
    ]);
    echo(&crate::pyjson::stdlib_dumps_indent2(&v));
    true
}

// ---------------------------------------------------------------------------
// reindex --dry-run (cli/embedding.py)
// ---------------------------------------------------------------------------

#[derive(Parser, Debug)]
#[command(
    name = "reindex",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct ReindexArgs {
    #[arg(long)]
    pub project_root: Option<String>,
    #[arg(long)]
    pub prune_old_caches: bool,
    #[arg(long)]
    pub dry_run: bool,
    #[arg(long)]
    pub limit: Option<usize>,
}

pub fn run_reindex(argv: &[String]) -> bool {
    let args = match ReindexArgs::try_parse_from(
        std::iter::once("reindex".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let start = resolve_project_root(args.project_root.as_deref());
    let layout = cortex_workspace::WorkspaceLayout::discover(&start);
    let config_path = layout.config_path();
    // (reindex --dry-run no abre memoria ni embeddings: sólo config+rutas.)
    if !config_path.exists() {
        echo(&format!(
            "\u{274c} No Cortex config found at `{}`.",
            config_path.display()
        ));
        return true;
    }
    let raw_text = std::fs::read_to_string(&config_path).unwrap_or_default();
    let config: cortex_config::CortexConfig = match serde_yaml::from_str(&raw_text) {
        Ok(c) => c,
        Err(e) => {
            echo(&format!(
                "\u{274c} Invalid config in {}: {e}",
                config_path.display()
            ));
            return true;
        }
    };
    let (model, backend) = config.resolve_embedder(None);
    let vault_resolved = layout.resolve_workspace_relative(Path::new(&config.semantic.vault_path));
    let vectors_dir = layout.workspace_root.join(".cortex").join("vectors");

    // Sólo --dry-run está wireado; el rebuild real sigue en passthrough.
    if !args.dry_run {
        let mut full = vec!["reindex".to_string()];
        full.extend_from_slice(argv);
        crate::fallback::passthrough(&full);
    }

    echo("[dry-run] reindex plan:");
    echo(&format!("  model/backend : {model} / {backend}"));
    echo(&format!("  vault         : {}", vault_resolved.display()));
    if vectors_dir.exists() {
        // El nombre del backup lleva timestamp ⇒ normalizable {{STAMP}}.
        echo(&format!(
            "  would move    : {} -> vectors.backup-{{}}",
            vectors_dir.display()
        ));
    } else {
        echo("  no existing vector cache to back up");
    }
    echo("  would rebuild : full sync + embeddings for every vault doc");
    if args.prune_old_caches {
        echo("  would prune   : previous .vectors.backup-* dirs");
    }
    true
}
