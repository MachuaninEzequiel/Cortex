//! Entrypoint del binario `cortex-brain` (G-A1 + G-A2 + G-A3).
//!
//! Decide el rol según argv:
//! - `--query <text> [--project <path>]`  ⇒ cliente IPC: conecta al
//!   server, manda query, lee respuestas, imprime a stdout, sale.
//! - `--projects-list`                     ⇒ lista proyectos Cortex
//!   detectados desde el cache y sale (G-A3).
//! - sin flag reconocido                    ⇒ GUI Tauri (default).
//!
//! G-A1 implementó el camino GUI. G-A2 el camino cliente. G-A3 el
//! listado de proyectos.

use std::process::ExitCode;

use cortex_brain_app::ipc::{
    read_json_line, write_json_line, ConnectError, QueryRequest, QueryResponse,
};
use cortex_brain_app::{projects, run as run_app, Role};

fn main() -> ExitCode {
    let argv: Vec<String> = std::env::args().collect();
    let role = Role::from_argv(&argv);

    match role {
        Role::App => {
            run_app();
            ExitCode::SUCCESS
        }
        Role::QueryClient => run_query_client(&argv),
        Role::ProjectsList => run_projects_list(),
    }
}

/// Implementación del flag `--projects-list` (G-A3): lista los
/// proyectos Cortex detectados, sin abrir GUI. Formato
/// machine-readable: una línea por proyecto,
/// `path\tbranch\tstatus`.
///
/// Lee el cache; si el cache todavía no existe (primera vez en esta
/// máquina), corre un scan fresh una vez para que el flag sirva
/// standalone y deje el cache listo.
fn run_projects_list() -> ExitCode {
    let entries = if projects::cache_path().is_file() {
        projects::list_projects()
    } else {
        projects::refresh_projects()
    };
    if entries.is_empty() {
        eprintln!(
            "cortex-brain: no hay proyectos Cortex detectados todavía.\n\
             Un proyecto Cortex tiene config.yaml + .cortex/. Corré \
             `cortex-brain` para que la app escanee tu HOME."
        );
        return ExitCode::SUCCESS;
    }
    for entry in &entries {
        let status = if !entry.valid_config {
            "invalid"
        } else if entry.has_session {
            "session"
        } else {
            "ok"
        };
        println!("{}\t{}\t{}", entry.path, entry.branch, status);
    }
    ExitCode::SUCCESS
}

/// Implementación del flag `--query`: conecta al server, manda el
/// query, lee respuestas hasta EOF y las imprime a stdout.
///
/// G-A2: el server loggea pero NO responde todavía. El cliente manda
/// la query, espera hasta EOF, e informa si no recibió nada. G-A4
/// reemplaza esto por el protocolo de respuesta real.
fn run_query_client(argv: &[String]) -> ExitCode {
    // Parsear --query <text> y --project <path> (opcional, default "").
    let mut text: Option<String> = None;
    let mut project: Option<String> = None;
    let mut i = 0;
    while i < argv.len() {
        match argv[i].as_str() {
            "--query" => {
                text = argv.get(i + 1).cloned();
                i += 2;
            }
            "--project" => {
                project = argv.get(i + 1).cloned();
                i += 2;
            }
            _ => i += 1,
        }
    }
    let Some(text) = text else {
        eprintln!("cortex-brain: --query requiere un texto (--query \"<texto>\")");
        return ExitCode::from(2);
    };
    let project = project.unwrap_or_default();

    // Conectar al server.
    let client = match cortex_brain_app::ipc::try_connect() {
        Ok(c) => c,
        Err(ConnectError::NoServer(p)) => {
            eprintln!(
                "cortex-brain: no hay GUI escuchando en {}.\n\
                 Abrí `cortex-brain` (sin flags) en otra terminal y reintentá.",
                p.display()
            );
            return ExitCode::from(2);
        }
        Err(ConnectError::NotSupported) => {
            eprintln!("cortex-brain: IPC no soportado en este OS (G-A2: sólo Unix)");
            return ExitCode::from(2);
        }
        Err(e) => {
            eprintln!("cortex-brain: error al conectar: {e}");
            return ExitCode::from(1);
        }
    };

    let conn = client.into_connection();
    let (read, mut write) = match conn.into_split() {
        Ok(p) => p,
        Err(e) => {
            eprintln!("cortex-brain: split falló: {e}");
            return ExitCode::from(1);
        }
    };
    let mut read = std::io::BufReader::new(read);

    let req = QueryRequest {
        kind: "query".into(),
        project,
        text: text.clone(),
        request_id: format!("cli-{}", std::process::id()),
    };
    if let Err(e) = write_json_line(&mut write, &req) {
        eprintln!("cortex-brain: error al enviar: {e}");
        return ExitCode::from(1);
    }

    // G-A2: el server loggea pero NO responde. Leemos hasta EOF.
    let mut received: Vec<QueryResponse> = Vec::new();
    loop {
        match read_json_line::<QueryResponse, _>(&mut read) {
            Ok(Some(resp)) => received.push(resp),
            Ok(None) => break,
            Err(e) => {
                eprintln!("cortex-brain: error al leer: {e}");
                break;
            }
        }
    }

    if received.is_empty() {
        eprintln!(
            "cortex-brain: query enviada (server la loggeó, sin respuesta todavía —\n\
             el server GUI corre pero G-A2 sólo recibe; la respuesta real llega en G-A4).\n\
             query: {text:?}"
        );
    } else {
        for r in &received {
            println!("{}", r.text);
        }
    }
    ExitCode::SUCCESS
}
