//! Native rmcp stdio entrypoint for `mcp-server` and `mcp-serve`.
use clap::Parser;

#[derive(Parser)]
#[command(
    name = "mcp-server",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
struct Args {
    #[arg(long)]
    project_root: Option<String>,
    #[arg(long, default_value_t = true)]
    stdio: bool,
}

pub fn run(argv: &[String]) -> bool {
    let args = match Args::try_parse_from(
        std::iter::once("mcp-server".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };
    if !args.stdio {
        eprintln!("Only stdio transport is supported.");
        return true;
    }
    let mut server = cortex_mcp::server::CortexMcpServer::new();
    let resolved_root = crate::paths::resolve_project_root(args.project_root.as_deref());
    server.project_root = resolved_root.clone();

    // Backends NATIVOS de producción (Cierre T1): sesiones, search,
    // spec y finish wireados a los servicios nativos. Search se abre con
    // el motor keyword; sin config (o error de apertura) queda None ⇒ el
    // fallo explícito documentado del server.
    use cortex_mcp::backends::{
        autopilot::NativeAutopilotBackend, docs::NativeDocsBackend, finish::NativeFinishBackend,
        search::NativeSearchBackend, sessions::NativeSessionsBackend, spec::NativeSpecBackend,
    };
    use std::sync::{Arc, Mutex};
    server = server
        .with_sessions_backend(Arc::new(Mutex::new(NativeSessionsBackend::new(
            &resolved_root,
        ))))
        .with_spec_backend(Arc::new(Mutex::new(NativeSpecBackend::new(&resolved_root))))
        .with_finish_backend(Arc::new(Mutex::new(NativeFinishBackend::new(
            &resolved_root,
        ))))
        .with_docs_backend(Arc::new(Mutex::new(NativeDocsBackend::new(&resolved_root))))
        .with_autopilot_backend(Arc::new(Mutex::new(NativeAutopilotBackend::new(
            &resolved_root,
        ))));
    match NativeSearchBackend::open(&resolved_root) {
        Ok(b) => {
            server = server.with_search_backend(Arc::new(Mutex::new(b)));
        }
        Err(e) => {
            eprintln!("mcp: search backend no disponible: {e}");
        }
    }

    if let Err(e) = cortex_mcp::server::serve_stdio_blocking(server) {
        eprintln!("{e}");
        std::process::exit(1)
    }
    true
}
