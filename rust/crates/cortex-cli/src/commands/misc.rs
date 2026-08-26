//! `agent-guidelines` e `install-skills` — puertos de cli/main.py.

use std::path::Path;

use clap::Parser;

/// Recurso byte-idéntico al paquete Python (`cortex/agent_guidelines.md`).
const AGENT_GUIDELINES: &str = include_str!("../../../../../cortex/agent_guidelines.md");

/// `cortex agent-guidelines`: typer.echo(content) = contenido + "\\n".
pub fn agent_guidelines() {
    println!("{AGENT_GUIDELINES}");
}

#[derive(Parser, Debug)]
#[command(
    name = "install-skills",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct InstallSkillsArgs {
    /// Directory to install skills into.
    #[arg(long, default_value = ".cortex/skills")]
    pub dest: String,
}

/// `cortex install-skills [--dest D]`.
pub fn install_skills(tokens: &[String]) -> bool {
    let args = InstallSkillsArgs::parse_from(
        std::iter::once("install-skills".to_string()).chain(tokens.iter().cloned()),
    );
    let installed = cortex_workspace::skills::install_skills(Path::new(&args.dest));
    if installed.is_empty() {
        println!("All skills already installed.");
    } else {
        println!(
            "✅ Installed {} skills into {}/",
            installed.len(),
            args.dest
        );
        for skill in &installed {
            println!("   • {skill}");
        }
    }
    true
}
