//! `cortex org-config` — puerto de cli/main.py::org_config sobre
//! cortex-enterprise.

use std::io::Write;
use std::path::Path;

use clap::Parser;

use crate::paths::{expand_user, python_resolve};

#[derive(Parser, Debug)]
#[command(
    name = "org-config",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct OrgConfigArgs {
    /// Absolute path to the target project root (where .cortex/org.yaml lives).
    #[arg(long)]
    pub project_root: Option<String>,

    /// Print the resolved enterprise config as JSON.
    #[arg(long)]
    pub json: bool,

    /// Fail if the enterprise config is missing.
    #[arg(long)]
    pub required: bool,
}

pub fn run(tokens: &[String]) -> bool {
    let args = OrgConfigArgs::parse_from(
        std::iter::once("org-config".to_string()).chain(tokens.iter().cloned()),
    );
    std::process::exit(execute(
        &args.project_root.as_deref(),
        args.json,
        args.required,
    ));
}

fn resolve(raw: Option<&str>) -> std::path::PathBuf {
    match raw {
        Some(p) => python_resolve(&expand_user(Path::new(p))),
        None => python_resolve(&std::env::current_dir().unwrap_or_default()),
    }
}

pub fn execute(project_root: &Option<&str>, json_output: bool, required: bool) -> i32 {
    let root = resolve(*project_root);

    let discovered = cortex_enterprise::config::discover_enterprise_config_path(&root, None);
    if discovered.is_none() {
        let expected = root.join(".cortex").join("org.yaml");
        let message = format!("Enterprise config not found under {}", expected.display());
        if required {
            let _ = writeln!(std::io::stderr(), "{message}");
            return 1;
        }
        println!("{message}");
        return 0;
    }
    let discovered = discovered.unwrap();

    let config = match cortex_enterprise::config::load_enterprise_config(
        &root,
        true,
        Some(&discovered),
        None,
    ) {
        Ok(Some(config)) => config,
        Ok(None) => return fail("Failed to load enterprise config: missing config".into()),
        Err(err) => return fail(format!("Failed to load enterprise config: {err}")),
    };

    if json_output {
        // model_dump_json(indent=2): UTF-8 crudo, orden de declaración.
        match serde_json::to_string_pretty(&config) {
            Ok(s) => {
                println!("{s}");
                return 0;
            }
            Err(err) => return fail(format!("Failed to serialize enterprise config: {err}")),
        }
    }

    let layout = cortex_workspace::WorkspaceLayout::discover(&root);
    println!("Enterprise config: {}", discovered.display());
    println!(
        "Organization: {} ({})",
        config.organization.name, config.organization.profile
    );
    println!(
        "Topology: {}",
        cortex_enterprise::config::describe_enterprise_topology(
            Some(&config),
            Some(&root),
            Some(&layout)
        )
    );
    println!();
    // typer.echo(yaml) agrega "\n" al dump (que ya termina en una).
    println!(
        "{}",
        cortex_enterprise::config::dump_enterprise_config_yaml(&config)
    );
    0
}

fn fail(message: String) -> i32 {
    let _ = writeln!(std::io::stderr(), "{message}");
    1
}
