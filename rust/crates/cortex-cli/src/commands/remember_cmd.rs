//! Comandos raíz `cortex remember` / `cortex forget` (MITAD A ruta 1) —
//! oráculo `cortex/cli/main.py:1237-1290` y `1900-1915`.
//!
//! Glue in-process sobre `NativeMemory` + `NativeEpisodicStore::append` /
//! `delete` (puerto de `AgentMemory.remember` / `EpisodicMemoryStore.delete`).
//! `remember` persiste una memoria episódica real en el JSONL nativo con el
//! embedder ONNX compartido con el oráculo; `forget` borra la entrada por
//! `mem_*` con los mismos mensajes de salida.

use std::io::Write as _;

use clap::Parser;
use cortex_app::episodic::AppendParams;

fn echo(s: &str) {
    let mut out = std::io::stdout();
    let _ = writeln!(out, "{s}");
}

fn eecho(s: &str) {
    let mut out = std::io::stderr();
    let _ = writeln!(out, "{s}");
}

fn config_llm_provider(config_path: &std::path::Path) -> String {
    let cfg: serde_yaml::Value =
        serde_yaml::from_str(&std::fs::read_to_string(config_path).unwrap_or_default())
            .unwrap_or(serde_yaml::Value::Null);
    cfg.get("llm")
        .and_then(|m| m.get("provider"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string()
}

#[derive(Parser, Debug)]
#[command(
    name = "remember",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
struct RememberArgs {
    pub content: String,
    #[arg(long, short = 't', default_value = "general")]
    pub r#type: String,
    #[arg(long)]
    pub tag: Vec<String>,
    #[arg(long)]
    pub file: Vec<String>,
    #[arg(long)]
    pub branch: Option<String>,
    #[arg(long)]
    pub repo: Option<String>,
    #[arg(long)]
    pub commit: Option<String>,
    #[arg(long, short = 's')]
    pub summarize: bool,
}

pub fn run_remember(argv: &[String]) -> bool {
    let args = match RememberArgs::try_parse_from(
        std::iter::once("remember".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let root = crate::paths::resolve_project_root(None);
    let mut mem = match crate::memory::NativeMemory::open(Some(&root)) {
        Ok(m) => m,
        Err(e) => {
            eecho(&e.message());
            std::process::exit(1);
        }
    };
    // Espejo del warning del oráculo (main.py remember): solo cuando el
    // provider configurado es "none" y el usuario pidió --summarize.
    if args.summarize && config_llm_provider(&mem.layout.config_path()) == "none" {
        eecho(
            "⚠ Warning: --summarize was requested but no LLM provider is configured.\n  \
             Falling back to simple truncation (300 chars).\n  \
             Configure an LLM provider in config.yaml to enable true summarization.",
        );
    }
    let mut extra_metadata = serde_json::Map::new();
    for (k, v) in [
        ("branch", args.branch.as_deref()),
        ("repo", args.repo.as_deref()),
        ("commit", args.commit.as_deref()),
    ] {
        if let Some(v) = v {
            extra_metadata.insert(k.to_string(), serde_json::Value::String(v.to_string()));
        }
    }
    let params = AppendParams {
        content: args.content.clone(),
        memory_type: args.r#type,
        tags: args.tag,
        files: args.file,
        extra_metadata: if extra_metadata.is_empty() {
            None
        } else {
            Some(extra_metadata)
        },
    };
    let (store, embedder) = match (mem.episodic.store_mut(), mem.embedder.as_mut()) {
        (Some(s), Some(e)) => (s, e),
        _ => {
            eecho("episodic memory or embedding model is unavailable");
            std::process::exit(1);
        }
    };
    let entry = match store.append(params, &mut |text| {
        embedder
            .embed_batch(&[text.to_string()])
            .map_err(|e| e.to_string())
            .and_then(|v| v.into_iter().next().ok_or_else(|| "empty embedding".into()))
    }) {
        Ok(e) => e,
        Err(e) => {
            eecho(&e);
            std::process::exit(1);
        }
    };
    echo(&format!("Memory stored -> {}", entry.id));
    echo(&format!("   type: {}", entry.memory_type));
    let summary: String = entry.content.chars().take(120).collect();
    echo(&format!("   summary: {summary}"));
    true
}

#[derive(Parser, Debug)]
#[command(
    name = "forget",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
struct ForgetArgs {
    pub memory_id: String,
}

fn forget_not_found(memory_id: &str) -> ! {
    eecho(&format!(
        "✗ Memory '{memory_id}' not found.\n  \
         Run `cortex stats` to see available memory counts, or\n  \
         `cortex search <query>` to find the ID you want."
    ));
    std::process::exit(1);
}

pub fn run_forget(argv: &[String]) -> bool {
    let args = match ForgetArgs::try_parse_from(
        std::iter::once("forget".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let root = crate::paths::resolve_project_root(None);
    let mut mem = match crate::memory::NativeMemory::open_without_embeddings(Some(&root)) {
        Ok(m) => m,
        Err(e) => {
            eecho(&e.message());
            std::process::exit(1);
        }
    };
    match mem.episodic.store_mut() {
        Some(store) => match store.delete(&args.memory_id) {
            Ok(true) => {
                echo(&format!("Memory {} deleted.", args.memory_id));
                true
            }
            Ok(false) => forget_not_found(&args.memory_id),
            Err(e) => {
                eecho(&e);
                std::process::exit(1);
            }
        },
        // Sin store JSONL local ⇒ el id no existe (chroma vacío del oráculo).
        None => forget_not_found(&args.memory_id),
    }
}
