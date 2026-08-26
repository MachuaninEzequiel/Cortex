//! Comando `cortex pr-context capture` (Cierre T2) — espejo de
//! cli/pr_context.py::capture sobre PRContext/capture_manual nativos (P12A-3).
//! Los demás subcomandos (store/search/generate/full) quedan passthrough.

use std::io::Write as _;

use clap::Parser;
use cortex_app::pr::{capture_manual, save_context, CaptureManualArgs};

fn echo(s: &str) {
    let mut out = std::io::stdout();
    let _ = writeln!(out, "{s}");
}

#[derive(Parser, Debug)]
#[command(
    name = "pr-context",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct CaptureArgs {
    #[arg(long, default_value = "Untitled PR")]
    pub title: String,
    #[arg(long, default_value = "")]
    pub body: String,
    #[arg(long, default_value = "unknown")]
    pub author: String,
    #[arg(long, default_value = "")]
    pub branch: String,
    #[arg(long, default_value = "")]
    pub commit: String,
    #[arg(long, default_value_t = 0)]
    pub pr_number: i64,
    #[arg(long, default_value = "main")]
    pub target_branch: String,
    #[arg(long, default_value = "")]
    pub labels: String,
    #[arg(long, default_value = ".pr-context.json")]
    pub output: String,
}

pub fn run_capture(argv: &[String]) -> bool {
    let args = match CaptureArgs::try_parse_from(
        std::iter::once("capture".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    let labels_list: Vec<String> = if args.labels.is_empty() {
        vec![]
    } else {
        args.labels
            .split(',')
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .map(String::from)
            .collect()
    };

    let ctx = capture_manual(CaptureManualArgs {
        title: args.title.clone(),
        author: args.author.clone(),
        branch: args.branch.clone(),
        commit: args.commit.clone(),
        body: args.body.clone(),
        pr_number: args.pr_number,
        target_branch: args.target_branch.clone(),
        labels: labels_list,
    });

    match save_context(&ctx, std::path::Path::new(&args.output)) {
        Ok(path) => {
            echo(&format!("PR context captured -> {}", path.display()));
            echo(&format!("   title: {}", ctx.title));
            echo(&format!("   author: {}", ctx.author));
            echo(&format!("   branch: {}", ctx.source_branch));
            echo(&format!("   files changed: {}", ctx.files_changed.len()));
            true
        }
        Err(e) => {
            eprintln!("{e}");
            true
        }
    }
}
