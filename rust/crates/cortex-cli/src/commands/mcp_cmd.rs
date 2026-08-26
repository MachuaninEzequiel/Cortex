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
    server.project_root = crate::paths::resolve_project_root(args.project_root.as_deref());
    if let Err(e) = cortex_mcp::server::serve_stdio_blocking(server) {
        eprintln!("{e}");
        std::process::exit(1)
    }
    true
}
