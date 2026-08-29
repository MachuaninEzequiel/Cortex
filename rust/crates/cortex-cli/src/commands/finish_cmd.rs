//! Subcomando `cortex finish` / `cortex finish-session`.

use std::io::Write as _;
use std::path::Path;

use clap::Parser;
use cortex_mcp::backends::finish::NativeFinishBackend;
use cortex_mcp::handlers_finish::finish_session_text;

fn echo(s: &str) {
    let mut out = std::io::stdout();
    let _ = writeln!(out, "{s}");
}

#[derive(Parser, Debug)]
#[command(
    name = "finish",
    about = "Cierra la sesión activa con evidencia",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct FinishArgs {
    /// ID de la sesión a cerrar (default: sesión activa).
    #[arg(long)]
    pub session_id: Option<String>,

    /// Intención de cierre: auto (default), abandon, handoff.
    #[arg(long, default_value = "auto")]
    pub intent: String,

    /// Razón del cierre (requerido si intent != auto).
    #[arg(long)]
    pub reason: Option<String>,

    /// Modo interactivo (CLI-only).
    #[arg(long)]
    pub interactive: bool,

    /// Raíz del proyecto.
    #[arg(long)]
    pub project_root: Option<String>,
}

pub fn finish_session(
    project_root: Option<&Path>,
    session_id: Option<&str>,
    intent: &str,
) -> Result<String, String> {
    let root = match project_root {
        Some(r) => r.to_path_buf(),
        None => crate::paths::resolve_project_root(None),
    };
    let mut backend = NativeFinishBackend::new(&root);
    let mut args = serde_json::json!({
        "intent": intent,
    });
    if let Some(id) = session_id {
        args["session_id"] = serde_json::Value::String(id.to_string());
    }
    let res = finish_session_text(&mut backend, &args)?;
    if res.starts_with("❌") {
        Err(res)
    } else {
        Ok(res)
    }
}

pub fn run(argv: &[String]) -> bool {
    let args = match FinishArgs::try_parse_from(
        std::iter::once("finish".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            let _ = e.print();
            return true;
        }
    };

    if args.interactive {
        eprintln!("interactive no cableado; omití --interactive");
        std::process::exit(1);
    }

    let root = args.project_root.as_deref().map(Path::new);
    let root_path = match root {
        Some(r) => r.to_path_buf(),
        None => crate::paths::resolve_project_root(None),
    };

    let mut backend = NativeFinishBackend::new(&root_path);
    let mut json_args = serde_json::json!({
        "intent": args.intent,
    });
    if let Some(ref id) = args.session_id {
        json_args["session_id"] = serde_json::Value::String(id.clone());
    }
    if let Some(ref r) = args.reason {
        json_args["reason"] = serde_json::Value::String(r.clone());
    }

    match finish_session_text(&mut backend, &json_args) {
        Ok(out) => {
            if out.starts_with("❌") {
                eprintln!("{out}");
                std::process::exit(1);
            } else {
                echo(&out);
                true
            }
        }
        Err(e) => {
            eprintln!("Error al finalizar sesión: {e}");
            std::process::exit(1);
        }
    }
}
