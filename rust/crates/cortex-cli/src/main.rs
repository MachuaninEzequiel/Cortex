// cortex-cli — CLI nativo clap nivel-1 (P12B-8, cierre del Stream B).
//
// Arquitectura de dispatch (BAJA DEFINITIVA — fase física):
//   1. `CORTEX_PY=1` → aviso histórico + CONTINÚA nativo (rollback eliminado).
//   2. `--cli-version`/`--help`/invocación sin args → línea nativa.
//   3. Primer token ∈ subárboles wireados → clap parsea ESE subárbol y
//      ejecuta nativo contra los crates B.
//   4. Cualquier otra cosa → error Typer-like `No such command '<first>'.`
//      rc 2 (precedente: rechazo install/uninstall de autopilot).
//
// Paridad: comandos funcionales wireados = byte-parity vs oráculo Python
// (gate bench/parity/cli_golden_p12b.py). Textos --help/errores de comandos
// wireados = self-golden (Typer y clap formatean distinto por diseño).

use cortex_cli::commands;

/// Versión de este binario nativo.
const CLI_VERSION: &str = "0.1.0";

/// Árbol raíz solo para el texto de ayuda self-golden (el dispatch real es
/// manual por primer token; ver `dispatch_native`).
fn root_command() -> clap::Command {
    use clap::Command;
    Command::new("cortex-cli")
        .disable_version_flag(true)
        .disable_help_subcommand(true)
        .about("Cortex -- hybrid cognitive memory for AI agents (CLI nativo)")
        .subcommand(
            Command::new("doctor")
                .about("Validate Cortex runtime prerequisites and governance state"),
        )
        .subcommand(Command::new("tutor").about("Guía interactiva offline de Cortex. Zero tokens."))
        .subcommand(
            Command::new("hint").about("Tip contextual: qué hacer ahora con Cortex. Zero tokens."),
        )
        .subcommand(
            Command::new("org-config").about("Display the resolved enterprise organization config"),
        )
        .subcommand(
            Command::new("promote-knowledge")
                .about("Promote reviewed knowledge candidates into the enterprise vault"),
        )
        .subcommand(
            Command::new("review-knowledge")
                .about("Enterprise review queue (pending/approve/reject/candidate)"),
        )
        .subcommand(
            Command::new("memory-report")
                .about("Report enterprise memory health and promotion visibility"),
        )
        .subcommand(
            Command::new("webgraph").about("Webgraph snapshots (export/serve/doctor nativos)"),
        )
        .subcommand(
            Command::new("autopilot").about("Autopilot decision layer (subarbol 100% nativo)"),
        )
        .subcommand(Command::new("agent-guidelines").about("Display agent behavior guidelines"))
        .subcommand(
            Command::new("install-skills").about("Install Obsidian skills into the project"),
        )
        .after_help(
            "CLI 100% nativo (sin passthrough a Python). Instalá por binario: \
             `cargo install --path rust/crates/cortex-cli`.",
        )
}

fn main() {
    let argv: Vec<String> = std::env::args().skip(1).collect();

    // 1. CORTEX_PY=1 = rollback histórico de la migración; el CLI es 100%
    //    nativo ⇒ imprimimos un aviso y CONTINUAMOS el flujo nativo (no delega).
    if std::env::var("CORTEX_PY").as_deref() == Ok("1") {
        eprintln!("cortex-cli: CORTEX_PY=1 es rollback histórico de la migración — el CLI es 100% nativo; eliminá la variable");
    }

    // 2. Flag propio de la fachada nativa.
    if argv.first().map(String::as_str) == Some("--cli-version") {
        println!("cortex-cli {CLI_VERSION}");
        std::process::exit(0);
    }

    // 2b. Help raíz self-golden (Typer ≠ clap por diseño; texto congelado).
    if matches!(argv.as_slice(), [a] if *a == "--help" || *a == "-h") {
        print!("{}", root_command().render_help());
        std::process::exit(0);
    }

    // 2c. Invocación sin argumentos: el Home TUI del oráculo no está wireado
    //    ⇒ mostramos la ayuda raíz (sin passthrough).
    if argv.is_empty() {
        print!("{}", root_command().render_help());
        std::process::exit(0);
    }

    let first = argv[0].as_str();

    // 3. Subárboles wireados (se pueblan tarea por tarea).
    if dispatch_native(&argv) {
        return;
    }

    // 4. Comando desconocido: error Typer-like, rc 2. Nunca passthrough.
    eprintln!("No such command '{first}'.");
    std::process::exit(2);
}

/// Intenta despachar nativamente `argv`. Devuelve false si el primer token
/// no pertenece a ningún subárbol wireado (⇒ catch-all `No such command`).
fn dispatch_native(argv: &[String]) -> bool {
    let Some(first) = argv.first().map(String::as_str) else {
        return false;
    };
    let rest = &argv[1..];
    match first {
        "doctor" => commands::doctor::run(rest),
        "agent-guidelines" => {
            commands::misc::agent_guidelines();
            true
        }
        "install-skills" => commands::misc::install_skills(rest),
        "tutor" => commands::tutor::run(rest),
        "hint" => commands::tutor::run_hint(),
        "org-config" => commands::org_config::run(rest),
        "promote-knowledge" => commands::promote::run(rest),
        "review-knowledge" => commands::review::run(rest),
        "memory-report" => commands::memory_report::run(rest),
        "webgraph" => commands::webgraph::run(rest),
        "autopilot" => commands::autopilot::run(rest),
        "search" => cortex_cli::memory_cmds::run_search(rest),
        "context" => cortex_cli::memory_cmds::run_context(rest),
        "stats" => cortex_cli::memory_cmds::run_stats(rest),
        "session" => cortex_cli::commands::session_cmd::run(argv),
        "next" => cortex_cli::commands::next_cmd::run(rest),
        "hu" => cortex_cli::commands::hu_cmd::run(rest),
        "ide" => cortex_cli::commands::ide_cmd::run(rest),
        "remember" => cortex_cli::commands::remember_cmd::run_remember(rest),
        "forget" => cortex_cli::commands::remember_cmd::run_forget(rest),
        "docs" => commands::docs_cmd::run(rest),
        "ci" => commands::ci_cmd::run(rest),
        "setup" => commands::setup_cmd::run(rest),
        "pr-context" => commands::pr_context_cmd::run(rest),
        "mcp-server" | "mcp-serve" => commands::mcp_cmd::run(rest),
        "reindex" => cortex_cli::memory_cmds::run_reindex(rest),
        "init" => commands::setup_cmd::run_init(rest),
        _ => false,
    }
}
