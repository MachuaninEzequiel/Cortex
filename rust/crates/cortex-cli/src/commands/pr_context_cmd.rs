//! Native `cortex pr-context` capture/store/search/generate/full pipeline.
use clap::Parser;
use cortex_app::doc_generator::DocGenerator;
use cortex_app::episodic::AppendParams;
use cortex_app::pr::{
    capture_from_json, capture_manual, enrich_with_pipeline, save_context, CaptureManualArgs,
    PRContext,
};
use std::io::Write as _;
use std::path::Path;

fn echo(s: &str) {
    let _ = writeln!(std::io::stdout(), "{s}");
}
fn fail(s: &str) -> ! {
    let _ = writeln!(std::io::stderr(), "{s}");
    std::process::exit(1)
}
fn labels(s: &str) -> Vec<String> {
    s.split(',')
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(str::to_string)
        .collect()
}

#[derive(Parser, Debug)]
struct CaptureArgs {
    #[arg(long, default_value = "Untitled PR")]
    title: String,
    #[arg(long, default_value = "")]
    body: String,
    #[arg(long, default_value = "unknown")]
    author: String,
    #[arg(long, default_value = "")]
    branch: String,
    #[arg(long, default_value = "")]
    commit: String,
    #[arg(long, default_value_t = 0)]
    pr_number: i64,
    #[arg(long, default_value = "main")]
    target_branch: String,
    #[arg(long, default_value = "")]
    labels: String,
    #[arg(long, default_value = ".pr-context.json")]
    output: String,
}
fn captured(a: &CaptureArgs) -> PRContext {
    capture_manual(CaptureManualArgs {
        title: a.title.clone(),
        author: a.author.clone(),
        branch: a.branch.clone(),
        commit: a.commit.clone(),
        body: a.body.clone(),
        pr_number: a.pr_number,
        target_branch: a.target_branch.clone(),
        labels: labels(&a.labels),
    })
}
pub fn run_capture(argv: &[String]) -> bool {
    let a = match CaptureArgs::try_parse_from(
        std::iter::once("capture".into()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => fail(&e.to_string()),
    };
    let c = captured(&a);
    match save_context(&c, Path::new(&a.output)) {
        Ok(p) => {
            echo(&format!("PR context captured -> {}", p.display()));
            echo(&format!("   title: {}", c.title));
            echo(&format!("   author: {}", c.author));
            echo(&format!("   branch: {}", c.source_branch));
            echo(&format!("   files changed: {}", c.files_changed.len()));
            true
        }
        Err(e) => fail(&e),
    }
}

fn memory_content(c: &PRContext) -> String {
    let mut p = vec![format!(
        "PR #{}: {} by {} ({} -> {})",
        c.pr_number, c.title, c.author, c.source_branch, c.target_branch
    )];
    if !c.body.is_empty() {
        p.push(format!(
            "\nDescription: {}",
            c.body.chars().take(500).collect::<String>()
        ));
    }
    if !c.diff_summary.is_empty() {
        p.push(format!("\nDiff:\n{}", c.diff_summary));
    }
    p.push(format!(
        "\nLint: {}",
        c.lint_result.as_deref().unwrap_or("n/a")
    ));
    p.push(format!(
        "\nAudit: {}",
        c.audit_result.as_deref().unwrap_or("n/a")
    ));
    p.push(format!(
        "\nTests: {}",
        c.test_result.as_deref().unwrap_or("n/a")
    ));
    p.join("\n")
}
fn store_ctx(c: &PRContext) -> Result<(crate::memory::NativeMemory, String), String> {
    let root = crate::paths::resolve_project_root(None);
    let mut mem = crate::memory::NativeMemory::open(Some(&root)).map_err(|e| e.message())?;
    let mut tags = vec!["pr".into(), c.author.clone()];
    tags.extend(c.labels.clone());
    let params = AppendParams {
        content: memory_content(c),
        memory_type: "pr".into(),
        tags,
        files: c.files_changed.iter().take(20).cloned().collect(),
        extra_metadata: None,
    };
    let (store, embedder) = match (mem.episodic.store_mut(), mem.embedder.as_mut()) {
        (Some(s), Some(e)) => (s, e),
        _ => return Err("episodic memory or embedding model is unavailable".into()),
    };
    let entry = store.append(params, &mut |text| {
        embedder
            .embed_batch(&[text.to_string()])
            .map_err(|e| e.to_string())
            .and_then(|v| v.into_iter().next().ok_or_else(|| "empty embedding".into()))
    })?;
    let id = entry.id;
    Ok((mem, id))
}

#[derive(Parser)]
struct StoreArgs {
    #[arg(long, default_value = ".pr-context.json")]
    context_file: String,
    #[arg(long)]
    lint_result: Option<String>,
    #[arg(long)]
    audit_result: Option<String>,
    #[arg(long)]
    test_result: Option<String>,
}
fn run_store(argv: &[String]) -> bool {
    let a = match StoreArgs::try_parse_from(
        std::iter::once("store".into()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => fail(&e.to_string()),
    };
    let c = match capture_from_json(Path::new(&a.context_file)) {
        Ok(c) => c,
        Err(e) => fail(&e),
    };
    let c = enrich_with_pipeline(
        &c,
        a.lint_result.as_deref(),
        a.audit_result.as_deref(),
        a.test_result.as_deref(),
    );
    match store_ctx(&c) {
        Ok((_, id)) => {
            echo(&format!("PR context stored -> {id}"));
            true
        }
        Err(e) => fail(&e),
    }
}

#[derive(Parser)]
struct SearchArgs {
    #[arg(long, default_value = ".pr-context.json")]
    context_file: String,
    #[arg(long, default_value_t = 3)]
    top_k: usize,
    #[arg(long, default_value = ".past-context.json")]
    output: String,
}
fn run_search(argv: &[String]) -> bool {
    let a = match SearchArgs::try_parse_from(
        std::iter::once("search".into()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => fail(&e.to_string()),
    };
    let c = match capture_from_json(Path::new(&a.context_file)) {
        Ok(c) => c,
        Err(e) => fail(&e),
    };
    let mut mem = match crate::memory::NativeMemory::open(None) {
        Ok(m) => m,
        Err(e) => fail(&e.message()),
    };
    let query = format!(
        "{} {}",
        c.title,
        c.body.chars().take(200).collect::<String>()
    );
    let result = mem.retrieve(&query, a.top_k, true);
    if let Err(e) = std::fs::write(&a.output, crate::memory_cmds::retrieval_json(&result)) {
        fail(&e.to_string())
    }
    echo(&format!("Past context search saved -> {}", a.output));
    echo(&format!(
        "\nQuery: '{}...'",
        query.chars().take(100).collect::<String>()
    ));
    if result.unified_hits.is_empty() {
        echo("No related memories found.")
    } else {
        echo(&format!(
            "Found {} related memories:",
            result.unified_hits.len()
        ));
        for h in &result.unified_hits {
            let title = if h.source == "episodic" {
                h.entry
                    .as_ref()
                    .map(|e| {
                        format!(
                            "[{}] {}",
                            e.memory_type.to_uppercase(),
                            e.content.lines().next().unwrap_or("Untitled Session")
                        )
                    })
                    .unwrap_or_default()
            } else {
                h.doc.map(|d| d.title.clone()).unwrap_or_default()
            };
            echo(&format!(
                "  [{}] {} (score={:.4})",
                h.source, title, h.score
            ));
        }
    }
    true
}

#[derive(Parser)]
struct GenerateArgs {
    #[arg(long, default_value = ".pr-context.json")]
    context_file: String,
    #[arg(long, default_value = "vault")]
    vault: String,
}
fn generate(c: &PRContext, vault: &str, indent: &str) -> Result<Vec<std::path::PathBuf>, String> {
    let g = DocGenerator::new(vault);
    let docs = g.generate_all(c, chrono::Utc::now(), &[]);
    let written = g.write_docs(&docs)?;
    echo(&format!("{indent}Generated {} documents:", written.len()));
    for p in &written {
        echo(&format!("{indent}  {}", p.display()));
    }
    Ok(written)
}
fn run_generate(argv: &[String]) -> bool {
    let a = match GenerateArgs::try_parse_from(
        std::iter::once("generate".into()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => fail(&e.to_string()),
    };
    let c = match capture_from_json(Path::new(&a.context_file)) {
        Ok(c) => c,
        Err(e) => fail(&e),
    };
    match generate(&c, &a.vault, "") {
        Ok(_) => true,
        Err(e) => fail(&e),
    }
}

#[derive(Parser)]
struct FullArgs {
    #[arg(long, default_value = "Untitled PR")]
    title: String,
    #[arg(long, default_value = "")]
    body: String,
    #[arg(long, default_value = "unknown")]
    author: String,
    #[arg(long, default_value = "")]
    branch: String,
    #[arg(long, default_value = "")]
    commit: String,
    #[arg(long, default_value_t = 0)]
    pr_number: i64,
    #[arg(long, default_value = "main")]
    target_branch: String,
    #[arg(long, default_value = "")]
    labels: String,
    #[arg(long)]
    lint_result: Option<String>,
    #[arg(long)]
    audit_result: Option<String>,
    #[arg(long)]
    test_result: Option<String>,
    #[arg(long, default_value = "vault")]
    vault: String,
    #[arg(long, default_value = ".pr-context.json")]
    context_file: String,
}
fn run_full(argv: &[String]) -> bool {
    let a = match FullArgs::try_parse_from(
        std::iter::once("full".into()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => fail(&e.to_string()),
    };
    echo("🧠 Cortex DevSecDocOps — Full PR Context Pipeline");
    echo("");
    echo("📸 Step 1: Capturing PR context...");
    let c = capture_manual(CaptureManualArgs {
        title: a.title,
        author: a.author,
        branch: a.branch,
        commit: a.commit,
        body: a.body,
        pr_number: a.pr_number,
        target_branch: a.target_branch,
        labels: labels(&a.labels),
    });
    let c = enrich_with_pipeline(
        &c,
        a.lint_result.as_deref(),
        a.audit_result.as_deref(),
        a.test_result.as_deref(),
    );
    if let Err(e) = save_context(&c, Path::new(&a.context_file)) {
        fail(&e)
    }
    echo(&format!("  Context saved -> {}\n", a.context_file));
    echo("💾 Step 2: Storing in episodic memory...");
    let (mut mem, id) = match store_ctx(&c) {
        Ok(v) => v,
        Err(e) => fail(&e),
    };
    echo(&format!("  Stored -> {id}\n"));
    echo("🔍 Step 3: Searching past context...");
    let q = format!(
        "{} {}",
        c.title,
        c.body.chars().take(200).collect::<String>()
    );
    let r = mem.retrieve(&q, 3, true);
    if r.unified_hits.is_empty() {
        echo("  No related memories found.");
    } else {
        echo(&format!(
            "  Found {} related memories:",
            r.unified_hits.len()
        ));
        for h in &r.unified_hits {
            let title = if h.source == "episodic" {
                h.entry
                    .as_ref()
                    .map(|e| {
                        format!(
                            "[{}] {}",
                            e.memory_type.to_uppercase(),
                            e.content.lines().next().unwrap_or("Untitled Session")
                        )
                    })
                    .unwrap_or_default()
            } else {
                h.doc.map(|d| d.title.clone()).unwrap_or_default()
            };
            echo(&format!(
                "    [{}] {} (score={:.4})",
                h.source, title, h.score
            ));
        }
    }
    echo("");
    echo("📄 Step 4: Generating documentation...");
    if let Err(e) = generate(&c, &a.vault, "  ") {
        fail(&e)
    }
    echo("");
    echo("🔄 Step 5: Syncing vault...");
    let count = mem.semantic.docs.len();
    echo(&format!("  Vault synced — {count} documents indexed.\n"));
    echo("✅ DevSecDocOps pipeline complete");
    true
}

pub fn run(argv: &[String]) -> bool {
    match argv.first().map(String::as_str) {
        Some("capture") => run_capture(&argv[1..]),
        Some("store") => run_store(&argv[1..]),
        Some("search") => run_search(&argv[1..]),
        Some("generate") => run_generate(&argv[1..]),
        Some("full") => run_full(&argv[1..]),
        Some(first) => {
            eprintln!("No such command '{first}'.");
            std::process::exit(2);
        }
        None => {
            eprintln!("cortex pr-context: se requiere un subcomando");
            std::process::exit(2);
        }
    }
}
