//! Entrypoint del binario `cortex-brain` (G-A1 a G-A4).
//!
//! Decide el rol según argv:
//! - `--query <text> [--project <path>]`  ⇒ cliente IPC: conecta al
//!   server, manda query, lee respuestas, imprime a stdout, sale.
//!   Desde G-A4 el server responde de verdad (chat in-process con el
//!   motor); los tool calls propuestos se listan como `> TOOL: …`.
//! - `--projects-list`                     ⇒ lista proyectos Cortex
//!   detectados desde el cache y sale (G-A3).
//! - sin flag reconocido                    ⇒ GUI Tauri (default).

use std::io::Write as _;
use std::process::ExitCode;

use cortex_brain_app::chat;
use cortex_brain_app::ipc::{
    read_json_line, write_json_line, ConnectError, QueryRequest, QueryResponse,
};
use cortex_brain_app::{projects, run as run_app, Role};

fn main() -> ExitCode {
    let argv: Vec<String> = std::env::args().collect();
    let role = Role::from_argv(&argv);

    match role {
        Role::App => run_app_entrypoint(),
        Role::QueryClient => run_query_client(&argv),
        Role::ProjectsList => run_projects_list(),
    }
}

/// Entrypoint para `Role::App`: single-instance estricto (G-A9).
/// Si ya hay una instancia de la GUI escuchando en el socket IPC,
/// le envía un request `focus` para traer la ventana existente al frente
/// e informa al usuario sin abrir una segunda app.
fn run_app_entrypoint() -> ExitCode {
    if let Ok(client) = cortex_brain_app::ipc::try_connect() {
        let conn = client.into_connection();
        if let Ok((read, mut write)) = conn.into_split() {
            let req = QueryRequest {
                kind: "focus".into(),
                project: String::new(),
                text: String::new(),
                request_id: format!("focus-{}", std::process::id()),
            };
            if write_json_line(&mut write, &req).is_ok() {
                let mut reader = std::io::BufReader::new(read);
                let _ = read_json_line::<QueryResponse, _>(&mut reader);
            }
        }
        println!("Cortex Brain ya está corriendo. Se trajo la ventana al frente.");
        return ExitCode::SUCCESS;
    }

    run_app();
    ExitCode::SUCCESS
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

    // G-A6: los chunks llegan ANTES del done (streaming). Se imprimen
    // en vivo; el done lleva el texto final procesado (autoritativo,
    // con la salida de las tools integrada).
    let mut chunks: usize = 0;
    let mut saw_done = false;
    let mut final_text = String::new();
    let mut final_tool_calls: Option<Vec<chat::ToolCall>> = None;
    let mut error_msg: Option<String> = None;
    loop {
        match read_json_line::<QueryResponse, _>(&mut read) {
            Ok(Some(resp)) => match resp.kind.as_str() {
                "chunk" => {
                    print!("{}", resp.text);
                    let _ = std::io::stdout().flush();
                    chunks += 1;
                }
                "done" => {
                    saw_done = true;
                    final_text = resp.text;
                    final_tool_calls = resp.tool_calls;
                }
                "error" => error_msg = Some(resp.text),
                _ => {}
            },
            Ok(None) => break,
            Err(e) => {
                eprintln!("cortex-brain: error al leer: {e}");
                break;
            }
        }
    }

    if let Some(msg) = error_msg {
        eprintln!("cortex-brain: error del server: {msg}");
        return ExitCode::SUCCESS;
    }
    if !saw_done && chunks == 0 {
        eprintln!(
            "cortex-brain: query enviada pero el server no respondió nada.\n\
             query: {text:?}"
        );
        return ExitCode::SUCCESS;
    }
    if chunks == 0 {
        // Respuesta batch (server viejo): comportamiento G-A4.
        print!("{final_text}");
    }
    if let Some(tcs) = &final_tool_calls {
        for tc in tcs {
            // Patrón del motor (doc 19 §3.3): el TOOL propuesto se
            // muestra como línea aparte. Se ejecutó si era read;
            // safe-action queda propuesta.
            println!("> TOOL: {} {}", tc.tool, tc.args);
        }
        if chunks > 0 {
            // Con streaming la salida de la tool NO viaja en los
            // chunks (viajó el texto crudo): el done la trae procesada.
            print!("{final_text}");
        }
    }
    let _ = std::io::stdout().flush();
    ExitCode::SUCCESS
}
