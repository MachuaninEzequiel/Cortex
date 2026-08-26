//! Comandos `cortex hu …` (Cierre T2) — espejo de cli/hu.py sobre
//! WorkItemService nativo (P12A-2). Sin providers configurados, `import`
//! falla con el mensaje canónico (igual que Python sin integraciones).

use std::collections::HashMap;
use std::io::Write as _;

use clap::Parser;
use cortex_app::workitems::WorkItemService;

fn echo(s: &str) {
    let mut out = std::io::stdout();
    let _ = writeln!(out, "{s}");
}

fn eecho(s: &str) {
    let mut out = std::io::stderr();
    let _ = writeln!(out, "{s}");
}

/// Servicio con vault del layout y sin providers (paridad de defaults).
///
/// Leak controlado de una sola configuración por proceso: los comandos hu
/// son one-shot (el CLI termina tras ejecutarlos).
fn service_for() -> WorkItemService<'static> {
    let start = crate::paths::resolve_project_root(None);
    let layout = cortex_workspace::WorkspaceLayout::discover(&start);
    let vault: &'static std::path::PathBuf = Box::leak(Box::new(layout.vault_path()));
    WorkItemService::new(vault.as_path(), HashMap::new(), None, None)
}

#[derive(Parser, Debug)]
#[command(
    name = "hu",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct HuArgs {
    #[command(subcommand)]
    pub cmd: HuCmd,
}

#[derive(clap::Subcommand, Debug)]
pub enum HuCmd {
    /// Import one external tracked item into ``vault/hu/``.
    Import {
        external_id: String,
        #[arg(long, default_value = "jira")]
        provider: String,
        #[arg(long)]
        no_remember: bool,
    },
    /// List tracked item notes already stored in ``vault/hu/``.
    List,
    /// Show the local vault note path for one tracked item.
    Show { item_id: String },
}

pub fn run(argv: &[String]) -> bool {
    let args =
        match HuArgs::try_parse_from(std::iter::once("hu".to_string()).chain(argv.iter().cloned()))
        {
            Ok(a) => a,
            Err(e) => {
                eprint!("{e}");
                return true;
            }
        };
    match args.cmd {
        HuCmd::Import {
            external_id,
            provider,
            no_remember,
        } => {
            let mut svc = service_for();
            match svc.import_item(&external_id, &provider, !no_remember, chrono_utc_now()) {
                Ok(path) => echo(&format!("Tracked item imported -> {}", path.display())),
                Err(e) => {
                    eecho(&e);
                    std::process::exit(1);
                }
            }
        }
        HuCmd::List => {
            let svc = service_for();
            let notes = svc.list_item_notes();
            if notes.is_empty() {
                echo("No tracked items imported yet.");
            } else {
                for n in notes {
                    echo(&n.to_string_lossy());
                }
            }
        }
        HuCmd::Show { item_id } => match service_for().get_item_note(&item_id) {
            Ok(path) => echo(&path.to_string_lossy()),
            Err(e) => {
                eecho(&e);
                std::process::exit(1);
            }
        },
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
