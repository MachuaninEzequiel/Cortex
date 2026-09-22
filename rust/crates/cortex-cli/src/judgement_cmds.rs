//! `cortex judgement status` — disabled / typesafe / degraded.

use std::io::Write as _;
use std::path::Path;

use clap::Parser;
use cortex_config::CortexConfig;
use cortex_judgement::{status, ClientOptions, JudgementStatus};

use crate::judgement_squeeze::options_from_config;
use crate::paths::resolve_project_root;

#[derive(Parser, Debug)]
#[command(
    name = "judgement",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct JudgementArgs {
    #[arg(default_value = "status")]
    pub action: String,
}

pub fn run(argv: &[String]) -> bool {
    let args = match JudgementArgs::try_parse_from(
        std::iter::once("judgement".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    match args.action.as_str() {
        "status" | "" => {
            let st = current_status(None);
            let _ = writeln!(std::io::stdout(), "{}", st.as_str());
            true
        }
        other => {
            let _ = writeln!(
                std::io::stderr(),
                "Unknown judgement action '{other}'. Try: cortex judgement status"
            );
            true
        }
    }
}

pub fn current_status(project_root: Option<&Path>) -> JudgementStatus {
    let root = match project_root {
        Some(p) => p.to_path_buf(),
        None => resolve_project_root(None),
    };
    let layout = cortex_workspace::WorkspaceLayout::discover(&root);
    let cfg_path = layout.config_path();
    let opts = load_options(&cfg_path);
    status(&opts)
}

fn load_options(config_path: &Path) -> ClientOptions {
    let Ok(text) = std::fs::read_to_string(config_path) else {
        return ClientOptions::default();
    };
    let Ok(cfg) = serde_yaml::from_str::<CortexConfig>(&text) else {
        return ClientOptions::default();
    };
    options_from_config(&cfg.judgement, None)
}
